import os
from celery import Celery

# Django의 settings.py 파일을 Celery에서 사용할 수 있도록 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spartagames.settings')

# Celery 애플리케이션 생성
app = Celery('spartagames')

# Django의 설정에서 'CELERY_'로 시작하는 설정을 가져오도록 설정
app.config_from_object('django.conf:settings', namespace='CELERY')

# Django 앱에서 tasks.py 파일을 자동으로 찾아 Celery에 태스크로 등록
app.autodiscover_tasks()

# 기본 디버그 태스크
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')