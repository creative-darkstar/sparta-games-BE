# F03 변경 설명

구현서: presigned-upload-fix-implementation-guide-20261009.md, F03

Celery 실행 상태와 valid/invalid/skipped 반환값 분리. 행 잠금, 제출별 반려 로그, 태깅 실패 재시도 및 구형 인자 처리 구현.

- `games/tasks.py` 코드 라인: 234, 245, 257, 261, 264, 281, 283, 307 (해당 커밋 기준)
