# Presigned 업로드 수정 결과 (2026-10-19 KST)

원본 구현서: FE `docs/presigned-upload-fix-implementation-guide-20261009.md`. 원본 지침서는 수정하지 않았다. 아래 라인은 최종 소스 기준이며 항목별 상세 파일은 같은 폴더의 Fxx-changes.md다. 작업 일지는 `log/presigned-fix/work-log.md`에 별도로 기록했다.

| 항목 | 파일:라인 | 변경 이유와 동작 |
|---|---|---|
| F03 | [games/tasks.py:245](../../games/tasks.py#L245) | 불변 파일 키와 제출 ID를 입력으로 받는다. 구형 인자는 skipped, 정상 검증은 valid/invalid로 반환하며 실행 실패는 retry 후 FAILURE로 남긴다. |
| F03 | [games/tasks.py:236](../../games/tasks.py#L236) | 검사 중에는 행 잠금을 유지하지 않는다. 결과 적용 직전에 현재 파일을 다시 검사하고 제출별 로그로 중복 반려를 막는다. |
| F01 | [games/task_tracking.py:50](../../games/task_tracking.py#L50) | 커밋 후 큐 발행 전에 Redis 작업/파일 인덱스를 원자적으로 기록한다. 발행 실패는 접수와 분리하며 GET에서 재발행하지 않는다. |
| F01 | [games/task_tracking.py:33](../../games/task_tracking.py#L33) | 현재 game_id와 파일 키로 식별자를 복원한다. Redis 유실은 결과 확인 불가로 반환하며 목록 자체는 유지한다. |
| F01 | [games/task_tracking.py:90](../../games/task_tracking.py#L90) | 동시 제출의 키 재사용을 NX 예약과 DB 확인으로 막는다. DB와 Redis 전체 원자성은 보장하지 않으며 중간 실패는 운영 확인 대상이다. |
| F01 | [games/task_tracking.py:102](../../games/task_tracking.py#L102) | 발급자 및 presign과 같은 30분 접수 기한을 기록한다. 만료·타인 발급 키는 제출할 수 없다. |
| F01 | [commons/views.py:107](../../commons/views.py#L107) | 설치된 botocore 1.34가 IfNoneMatch 모델 인자를 지원하지 않아 before-sign 이벤트로 조건 헤더를 서명한다. 오프라인 SignedHeaders 시험으로 확인했다. |
| F01 | [qnas/views.py:482](../../qnas/views.py#L482) | 인증·매핑·현재 게임 소유자를 확인한다. ZIP은 소유자/관리자, 공개 작업은 관리자만 조회 가능하다. 예외 원문은 내려주지 않는다. |
| F01 | [games/serializers.py:66](../../games/serializers.py#L66) | 본인/관리자에게만 현재 ZIP 작업 식별자를 제공한다. 목록에서 Celery 결과 DB를 반복 조회하지 않는다. |
| F01 | [spartagames/settings.py:178](../../spartagames/settings.py#L178) | 기존 django-db 결과 보관 설정을 Redis 인덱스와 같은 7일로 맞춘다. 전역 관리자 결과 저장량도 증가한다. |
| F04 | [users/views.py:441](../../users/views.py#L441) | 빈 목록을 정상 200 페이지로 반환한다. 타인에게 미승인 게임을 보여주지 않는 필터를 유지한다. |
| F05 | [games/views.py:291](../../games/views.py#L291) | 등록과 ZIP 교체는 검수 요청 접수로 응답한다. 파일 유지 수정에는 새 작업 ID나 검증 작업을 생성하지 않는다. |

## 검증 결과

- FE: Vitest 12개 파일, 63개 테스트 통과. 신규 ZIP 먼저/마지막 선택, 파일 A→B, 재제출, 캐시 분리, 결과 판별, 복원 및 기존 업로드 회귀 포함.
- BE: 격리된 메모리 SQLite에서 16개 테스트 통과. 유효/무효, 중복 로그, 파일 교체 경합 시뮬레이션, 재시도 소진, 권한, 빈 목록, 응답 래퍼, 메타데이터 수정, 발급 기한, 알림 콜백 실패를 포함. S3/Redis/브로커는 mock이다.
- FE `npm run build` 통과. 큰 번들 및 기존 `${icon}` 경고 있음.
- BE `manage.py check` 통과. `makemigrations --check --dry-run --settings=spartagames.test_settings`: No changes detected. 신규 모델/필드/마이그레이션 없음.
- FE `npm run typecheck`는 미변경 파일의 기존 오류로 실패. 대표적으로 UserProfile의 profileData props 불일치와 미사용 변수들. 원문은 FE `log/presigned-fix/typecheck.txt`. 이번 변경 파일 오류는 출력되지 않았다.

## 미실행 인수 시험 및 배포 조건

실제 UI/S3/API/worker가 연결된 T01~T07, Maze 전송, PostgreSQL 동시 트랜잭션, 브로커 재시작/결과 cleanup/Redis 영속성 유실은 미실행이다. 테스트 성공을 실서비스 인수 완료로 해석하지 않는다.

1. S3 CORS AllowedHeaders에 `If-None-Match`, `Content-Type`, `x-amz-tagging` 허용 여부를 확인한다. 기존 객체에 두 번째 PUT이 412로 거절되는지 실제 버킷에서 확인해야 한다. 원격 버킷 설정은 변경하지 않았다.
2. 새 서명은 If-None-Match 헤더를 요구한다. 구형 FE를 새 BE와 그대로 혼용하면 PUT이 실패하므로 업로드를 잠시 중지한 동시 배포 또는 FE 헤더 지원 선배포가 필요하다. 구형 발급 키는 새 발급자 인덱스가 없으므로 새로 발급해야 한다.
3. Redis AOF/RDB와 eviction 정책을 확인한다. 코드의 TTL 7일과 Celery result_expires 7일만으로 장애 시 보관을 보장하지 않는다. 전역 결과 보관량 및 cleanup 설정을 함께 확인한다.
4. 발행 실패/미확정 결과는 운영자가 DB의 현재 파일과 매핑의 file_key/submission_id를 대조한 뒤 기존 task_id로 재처리한다. 조회 API는 재발행하지 않는다. 구형 인자의 큐 작업은 skipped이며 필요한 경우 운영자가 현재 제출을 확인해야 한다.
5. 파일 예약 뒤 DB 롤백, DB 커밋 뒤 Redis/브로커 실패는 하나의 분산 트랜잭션으로 묶이지 않는다. 이 경우 자동 재등록을 유도하지 않고 접수 여부와 작업 매핑을 먼저 확인한다.
6. 관리자 승인·Unity 실행·회원가입 동작은 이번 구현으로 검증한 것으로 주장하지 않는다.

## 저장소 보존

FE는 `feat/sync-backend-ui-ux`, BE는 `refact/testing`에서 항목별 커밋했다. FE 기존 미추적 docs/log 자료와 BE 사용자의 SQLite DATABASES 변경은 커밋에서 제외하고 보존했다. push/배포는 수행하지 않았다.
