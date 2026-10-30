"""
테스트 전용 설정. 로컬/운영 DB 설정과 무관하게 메모리 SQLite를 사용한다.
실행: python manage.py test --settings=spartagames.test_settings
"""
from .settings import *  # noqa: F401,F403

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
