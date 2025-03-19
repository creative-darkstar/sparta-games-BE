"""
Django settings for spartagames project.

Generated by 'django-admin startproject' using Django 4.2.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

from datetime import timedelta
from pathlib import Path
from celery.schedules import crontab
from . import config

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config.DJANGO_SECRET_KEY
OPEN_API_KEY = config.OPENAI_API_KEY
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = [
    'www.sparta-games.net',
    'sparta-games.net',
    '13.209.74.174',
    'localhost',
    '127.0.0.1',
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    # Third Party
    "corsheaders",
    "django_extensions",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "storages",
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.kakao',
    'allauth.socialaccount.providers.naver',
    'allauth.socialaccount.providers.discord',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'rest_framework.authtoken',
    'django_celery_results',  # Celery 태스크 결과 저장
    'django_celery_beat',     # Celery Beat 스케줄러

    # Apps
    "accounts",
    "games",
    "qnas",
    "users",
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'spartagames.custom_middleware.CustomXFrameOptionsMiddleware',  # Custom 설정 추가
    
    # Add the account middleware:
    "allauth.account.middleware.AccountMiddleware",
]

X_FRAME_OPTIONS = 'SAMEORIGIN'

# CORS settings
# Allow specific origins
CORS_ALLOWED_ORIGINS = [
    "https://sparta-games.net",
    "https://www.sparta-games.net",
    "http://localhost:5173",  # React 앱 주소
    "https://spartagames-git-dev-horanges-projects.vercel.app",
    "https://spartagames-horanges-projects.vercel.app",
]
CORS_ALLOW_CREDENTIALS = True # 인증 정보 포함 설정

# CSRF 오류 발생시 활성화
# CSRF_TRUSTED_ORIGINS = [
#     "http://localhost:5713",
# ]

ROOT_URLCONF = 'spartagames.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'spartagames.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'HOST': config.DATABASES["host"],
        'PORT': config.DATABASES["port"],
        'NAME': config.DATABASES["database"],
        'USER': config.DATABASES["user"],
        'PASSWORD': config.DATABASES["password"],
    }
}

# Celery 브로커로 Django 데이터베이스 사용
CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_RESULT_BACKEND = 'django-db'

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'

# Celery Beat 설정 (스케줄링)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'

CELERY_BEAT_SCHEDULE = {
    'assign-chips-every-day': {
        'task': 'games.tasks.assign_chips_to_top_games',
        'schedule': crontab(hour=4, minute=0),  #crontab(hour=0, minute=0)=>매일 00:00에 실행
    },
    'cleanup_new_game_chip':{
        'task': 'games.tasks.cleanup_new_game_chip',
        'schedule': timedelta(days=3),
    },
    'assign-bookmark-top-chips-daily': {
        'task': 'games.tasks.assign_bookmark_top_chips',
        'schedule': crontab(hour=3, minute=45),
    },
    'assign-long-play-chips-daily': {
        'task': 'games.tasks.assign_long_play_chips',
        'schedule': crontab(hour=3, minute=50),
    },
    'assign-review-top-chips-daily': {
        'task': 'games.tasks.assign_review_top_chips',
        'schedule': crontab(hour=3, minute=40),
    },
    'hard-delete-user': {
        'task': 'qnas.tasks.hard_delete_user',
        'schedule': crontab(hour=6, minute=0),
    },
}

# Auth User Model - Custom
AUTH_USER_MODEL = 'accounts.User'

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',

    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}

SITE_ID = 2

# DRF Auth setting - default: JWT
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    'DEFAULT_PAGINATION_CLASS': 'spartagames.pagination.CustomPagination',
    'PAGE_SIZE': 20,
}

# DRF JWT setting
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

# django-storages settings
# https://django-storages.readthedocs.io/en/latest/backends/amazon-S3.html#settings

AWS_S3_ACCESS_KEY_ID = config.AWS_AUTH["aws_access_key_id"]
AWS_S3_SECRET_ACCESS_KEY = config.AWS_AUTH["aws_secret_access_key"]

AWS_STORAGE_BUCKET_NAME = config.AWS_S3_BUCKET_NAME
AWS_S3_REGION_NAME = "ap-northeast-2"
AWS_S3_CUSTOM_DOMAIN = f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"

AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_AUTH = False

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# boto3 settings
STATICFILES_STORAGE = "spartagames.custom_storages.StaticStorage"

# Media files

MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
# boto3 settings
DEFAULT_FILE_STORAGE = "spartagames.custom_storages.MediaStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # username 필드를 사용하지 않음
ACCOUNT_EMAIL_REQUIRED = True  # 이메일을 필수로 요구
ACCOUNT_USERNAME_REQUIRED = False  # username 필드를 사용하지 않음
ACCOUNT_AUTHENTICATION_METHOD = 'email'  # 이메일을 로그인에 사용
