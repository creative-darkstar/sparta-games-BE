import requests

from celery import shared_task

from spartagames.config import ADMIN_USER_EMAIL, ADMIN_STAFF_EMAIL


@shared_task
def routine_email_by_token():
    """
    매일 오전 6시에 실행
    구글 access 토큰 강제 발급해서 refresh 토큰 유지
    """
    data = {
        "email": ADMIN_STAFF_EMAIL,
    }
    
    try:
        resp = requests.post("https://sparta-games.net/accounts/api/email/", data=data)
    except Exception as e:
        print(e)
