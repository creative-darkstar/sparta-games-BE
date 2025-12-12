import logging
import requests

from celery import shared_task

from spartagames.config import ADMIN_USER_EMAIL, ADMIN_STAFF_EMAIL


logger = logging.getLogger("sparta_games_celery")


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
        logger.info("routine_email_by_token_success")
    except Exception as e:
        logger.error("routine_email_by_token_failed", exc_info=True)
