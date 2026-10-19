# F01 변경 설명

구현서: presigned-upload-fix-implementation-guide-20261009.md, F01

7일 작업 인덱스와 기존 상태 API 권한, 목록·상세 복원, 발행 실패 분리 구현. 스키마 변경 없음. 격리 DB 계약 테스트 14개 통과, 실제 S3·worker 인수 시험 미실행.

- `games/task_tracking.py` 코드 라인: 1 (해당 커밋 기준)
- `games/views.py` 코드 라인: 46, 68, 246, 285, 287, 289, 291, 476, 558, 594, 600, 603, 607, 622 (해당 커밋 기준)
- `games/serializers.py` 코드 라인: 66, 87 (해당 커밋 기준)
- `users/views.py` 코드 라인: 464 (해당 커밋 기준)
- `users/serializers.py` 코드 라인: 1, 4, 10 (해당 커밋 기준)
- `qnas/views.py` 코드 라인: 452, 461, 474, 483 (해당 커밋 기준)
- `commons/views.py` 코드 라인: 102, 106 (해당 커밋 기준)
- `spartagames/utils.py` 코드 라인: 4, 39 (해당 커밋 기준)
- `spartagames/settings.py` 코드 라인: 177 (해당 커밋 기준)
- `spartagames/test_settings.py` 코드 라인: 1 (해당 커밋 기준)
- `games/test_presigned.py` 코드 라인: 1 (해당 커밋 기준)

업로드 발급자와 30분 접수 기한을 확인해 만료 키 재사용 방지. 알림 콜백 실패 후에도 같은 task_id로 검증을 발행하는 회귀 검사 추가.

- `commons/views.py` 코드 라인: 141

- `games/task_tracking.py` 코드 라인: 96

- `games/utils.py` 코드 라인: 96, 111

- `games/views.py` 코드 라인: 229, 486

- `games/test_presigned.py` 코드 라인: 149, 186
