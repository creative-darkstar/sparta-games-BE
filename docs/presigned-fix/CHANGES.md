# Presigned 업로드 수정: BE 변경 설명

- 기준 구현서: FE 저장소 `docs/presigned-upload-fix-implementation-guide-20261009.md` (확정본, 2026-10-30)
- 브랜치: `refact/testing`
- 라인 번호는 이 문서를 작성한 시점의 최종 커밋 기준이다.
- 표의 "구현서" 열은 근거가 되는 구현서 절 번호다.

## 한눈에 보기

| 항목 | 커밋 | 한 줄 요약 |
|---|---|---|
| F03 | `20797e5` | 검증 task가 "실행 성공"과 별개로 "파일이 유효한지"를 반환한다 |
| F01 | `d33b0b1` | task_id를 계산으로 정하고, 기존 상태 조회 API에 권한 검사를 붙였다 |
| F04 | `362f365` | 게임이 없는 개발목록을 404가 아닌 빈 목록(200)으로 응답한다 |
| F05 | `4ff3159` | 등록 응답 문구를 "검수 요청이 접수되었습니다."로 바꿨다 |
| F06 | `9e6506d` | 같은 업로드 키의 재사용과 S3 덮어쓰기를 막는다 |

## F03: 검증 task의 판정 결과 분리

**전에는:** 검증 task가 아무것도 반환하지 않아(None) Celery 상태는 항상 SUCCESS였다. 파일이 무효여도 SUCCESS였다. 재시도를 모두 실패해도 SUCCESS로 끝났다.

**이제는:** task가 `{outcome: valid | invalid | skipped, 사유}`를 반환한다. 검증을 실행하지 못하면 FAILURE로 남는다.

| 파일:라인 | 무엇을 바꿨나 | 왜 (구현서) |
|---|---|---|
| [games/tasks.py:238](../../games/tasks.py#L238) | `_zip_result()`: 반환 dict를 만드는 함수 추가. 필드는 kind, schema_version, game_id, file_key, outcome, reason_code, reason | FE가 SUCCESS만 보고 성공 처리하지 않도록 파일 판정을 따로 담는다 (4.3) |
| [games/tasks.py:251](../../games/tasks.py#L251) | `_reject_invalid_zip()`: 반려를 조건부 update로 변경. 조건은 "현재 파일이 이 file_key이고 검수 대기(0)일 때만" | 같은 작업이 다시 실행되거나 파일이 바뀌면 갱신되는 행이 0개가 되어 반려 로그·알림이 중복되지 않는다 (4.6-3) |
| [games/tasks.py:285](../../games/tasks.py#L285) | `_is_current_pending_file()`: 게임의 현재 파일이 검사 대상과 같은지 확인 | 이전 파일의 늦은 결과가 현재 제출에 적용되지 않게 한다 (4.6-2) |
| [games/tasks.py:292](../../games/tasks.py#L292) | `validate_game_zip_task(game_id, file_key)`: 검사할 파일 키를 인자로 고정 | 작업 도중 파일이 바뀌어도 어떤 파일을 검사했는지 분명하게 한다 (4.3) |
| [games/tasks.py:302](../../games/tasks.py#L302) | file_key가 없는 구형 인자 작업은 `skipped`(LEGACY_ARGS) 반환 | 배포 전에 큐에 남은 작업을 성공으로 오인하지 않게 한다 (4.3-4) |
| [games/tasks.py:333](../../games/tasks.py#L333) | 다운로드·검사 후 결과를 적용하기 직전에 현재 파일인지 다시 확인 | 검사하는 동안 행 잠금을 잡지 않고도 교체 경합을 막는다 (4.6-2) |
| [games/tasks.py:339](../../games/tasks.py#L339) | `safe_s3_tag` 실패 시 예외로 재시도. 태그가 붙은 뒤에만 valid 반환 | 보존 태그 없이 valid가 되지 않게 한다 (4.3-3) |
| [games/tasks.py:348](../../games/tasks.py#L348) | 재시도를 모두 쓰면 예외를 다시 던져 FAILURE로 기록 | 전에는 예외를 삼켜 SUCCESS/null로 끝났다 (4.3-2) |
| [games/views.py:84](../../games/views.py#L84) | 검증 작업 발행에 file_key 전달 | 위 인자 변경에 맞춘다 |

## F01: 계산 가능한 task_id와 결과 조회

**핵심 아이디어:** `task_id = uuid5(게임 ID + 파일 키)`. 서버가 현재 DB만 보고 언제든 같은 ID를 다시 계산할 수 있다. 그래서 Redis 매핑이나 제출 ID 없이도 새로고침 후 결과를 찾을 수 있다.

| 파일:라인 | 무엇을 바꿨나 | 왜 (구현서) |
|---|---|---|
| [games/utils.py:105](../../games/utils.py#L105) | `ZIP_TASK_NAMESPACE` 고정 UUID | 값을 바꾸면 기존 task_id를 다시 계산할 수 없으므로 고정한다 (4.2) |
| [games/utils.py:113](../../games/utils.py#L113) | `zip_validation_task_id(game_id, file_key)` | task_id 계산은 이 함수 하나로만 한다 (4.2) |
| [games/utils.py:121](../../games/utils.py#L121) | `zip_submitted_at()`: 파일 키에 들어 있는 발급 시각(UTC)을 읽음 | 보관기간이 지났는지 판단하는 기준 (4.2, 4.5) |
| [games/utils.py:129](../../games/utils.py#L129) | `is_zip_result_expired()`: 제출 후 7일이 지났는지 판단 | PENDING이 "아직 대기 중"인지 "결과가 지워짐"인지 구분한다 (4.5) |
| [games/views.py:60](../../games/views.py#L60) | `_publish_zip_validation()`: 계산한 task_id로 `apply_async` 발행. 실패해도 로그만 남김 | DB는 이미 커밋되어 접수가 유효하므로 재등록을 유도하지 않는다. 재처리 방법은 docstring에 적었다 (4.6-1, 5, 6) |
| [games/views.py:303](../../games/views.py#L303) | 등록 시 task_id 계산. 알림·검증 발행 on_commit을 `robust=True`로 지정 | 알림 발행이 실패해도 검증 발행이 막히지 않게 한다 (4.6-5) |
| [games/views.py:316](../../games/views.py#L316) | 등록 응답 `data`에 `game_id`, `task_id` 추가 | FE가 접수 직후 결과 조회를 시작할 수 있게 한다 (4.5) |
| [games/views.py:633](../../games/views.py#L633) | ZIP 교체 수정 시 새 task_id 계산·발행 | 교체마다 새 검증 결과를 연결한다 (4.5) |
| [games/views.py:651](../../games/views.py#L651) | 수정 응답 `data`의 `task_id`. 파일을 유지한 수정이면 null | 파일 유지 수정은 새 검증을 만들지 않는다 (4.5) |
| [games/serializers.py:67](../../games/serializers.py#L67) | `get_zip_task_id_for()`: 제작자·관리자에게만 task_id 계산값을 반환 | 다른 사람은 task_id를 알 수 없게 한다 (4.5) |
| [games/serializers.py:92](../../games/serializers.py#L92) | 게임 상세 응답에 `zip_task_id` | 상세 화면에 직접 들어와도 결과를 복원한다 (4.5) |
| [users/serializers.py:16](../../users/serializers.py#L16) | 개발목록 응답에 `zip_task_id`. 판단 기준은 실제 요청자(`viewer`) | `context["user"]`는 프로필 주인이라 권한 판단에 쓰면 안 된다 |
| [users/views.py:466](../../users/views.py#L466) | serializer에 `viewer=request.user` 전달 | 위와 같음 |
| [qnas/views.py:479](../../qnas/views.py#L479) | `get_task_status`: ① 비로그인 401 ② `game_id`가 없으면 관리자만 ③ `game_id`가 있으면 제작자·관리자 + 현재 파일 task_id와 일치해야 함(아니면 409) | 기존 API를 재사용하면서 UUID만 알아도 조회되던 문제를 막는다 (4.4) |
| [qnas/views.py:520](../../qnas/views.py#L520) | `lookup_status`: 정상이면 ok, PENDING이면서 7일이 지났으면 expired | Celery 상태값은 바꾸지 않고 만료 여부만 따로 알린다 (4.4-4) |
| [qnas/views.py:526](../../qnas/views.py#L526) | FAILURE에는 안전한 `error_code`/`message`만 담음 | 예외 원문을 내보내지 않는다 (4.4-2) |
| [spartagames/settings.py:183](../../spartagames/settings.py#L183) | `CELERY_RESULT_EXPIRES = 7일` | 사용자 결정. 전역 설정이라 다른 task 결과도 7일간 보관된다 (4.5) |
| [spartagames/test_settings.py:7](../../spartagames/test_settings.py#L7) | 테스트 전용 설정(메모리 SQLite) | 테스트가 실제 DB에 연결되지 않게 한다. 아래 "검증" 참고 |

## F04: 빈 개발목록 응답

| 파일:라인 | 무엇을 바꿨나 | 왜 (구현서) |
|---|---|---|
| [users/views.py:451](../../users/views.py#L451) | 게임이 없을 때 404 대신 200 + 빈 페이지 반환 | 전에는 FE가 실제 빈 목록을 "목록을 불러오지 못했습니다"로 표시했다. 타인 조회 시 미승인 게임을 숨기는 필터는 유지한다 (7장) |

## F05: 접수 문구

| 파일:라인 | 무엇을 바꿨나 | 왜 (구현서) |
|---|---|---|
| [games/views.py:318](../../games/views.py#L318) | 등록 응답 "게임 등록이 완료되었습니다." → "검수 요청이 접수되었습니다." | 응답 시점에는 ZIP 검증과 관리자 검수가 아직 남아 있다 (4.5, F05) |
| [games/views.py:652](../../games/views.py#L652) | ZIP 교체는 접수 문구, 파일 유지 수정은 기존 "게임 수정이 완료되었습니다." | 위와 같음 |

## F06: 업로드 키 재사용·덮어쓰기 차단

| 파일:라인 | 무엇을 바꿨나 | 왜 (구현서) |
|---|---|---|
| [games/utils.py:149](../../games/utils.py#L149) | `gamefile_key_claim()` 컨텍스트 매니저 추가 | 재사용 차단 로직을 등록·교체가 함께 쓴다 (4.7) |
| [games/utils.py:165](../../games/utils.py#L165) | Redis `SET upload_key_lock:{key} NX EX 60`. 잠금을 못 얻으면 409. 블록이 끝나면 해제 | 같은 키로 동시에 들어온 요청 2개를 막는다. 영구 매핑이 아니다. Redis 장애 시에는 잠금 없이 DB 확인만 한다 (4.7) |
| [games/utils.py:174](../../games/utils.py#L174) | 삭제 처리된 게임을 포함해 어떤 Game이든 이미 쓰는 키면 409 | 재등록이나 다른 게임에서 같은 키를 쓰는 것을 막는다 (4.7) |
| [games/views.py:262](../../games/views.py#L262) | 등록 트랜잭션을 `gamefile_key_claim`으로 감쌈 | 확인과 생성 사이에 다른 요청이 끼어들지 못하게 한다 |
| [games/views.py:584](../../games/views.py#L584) | 수정 트랜잭션을 같은 방식으로 감쌈. 파일을 교체할 때만 검사 | 위와 같음 |
| [commons/views.py:115](../../commons/views.py#L115) | presign 서명에 `IfNoneMatch='*'` 추가 | 객체가 이미 있으면 S3가 412로 거부해, 검증 후 같은 URL로 파일을 바꿔치기할 수 없다. 서명된 헤더 목록에 `if-none-match`가 포함되는 것을 오프라인으로 확인했다 (4.7) |
| [requirements.txt:14](../../requirements.txt#L14) | boto3/botocore 1.34.119 → 1.35.99 | 1.34에는 PutObject의 IfNoneMatch가 없다. 1.36부터는 기본 체크섬 동작이 바뀌어 presigned 업로드에 영향을 줄 수 있어 1.35 마지막 버전을 골랐다. 로컬 `.venv`에도 설치했다 (4.7) |

## 검증

**자동 테스트 (mock 기반)**
- [games/tests.py](../../games/tests.py) 25개 통과. 실행: `python manage.py test games --settings=spartagames.test_settings`
- 범위: F03 판정·중복 반려·교체·FAILURE, F01 task_id·권한·409·만료·노출, F04 빈 목록, F06 재사용·잠금·해제
- S3와 Redis는 mock이다. 실제 S3·worker를 연결한 통합 시험은 아직 하지 않았다.

**DB 관련 주의**
- 2026-10-30 작업 시점에 `spartagames/settings.py`의 `DATABASES`가 RDS(PostgreSQL)로 되어 있었다. 이 설정은 작업 중 바꾸지 않았다.
- 그래서 `test_settings` 없이 실행한 처음 두 번의 테스트는 RDS에 임시 DB `test_mydbsparta`를 만들었다가 삭제했다. 기존 데이터에는 영향이 없다.
- 이후에는 메모리 SQLite로만 실행했다.

**기타**
- `manage.py check` 통과. 새 모델·필드·마이그레이션은 없다.
- 미실행: 실제 브라우저·S3·Celery worker 통합 시험(T01~T06), 실제 버킷에서 두 번째 PUT의 412, 동시 요청 시 Redis 잠금, beat의 `backend_cleanup` 일정 등록 여부.
