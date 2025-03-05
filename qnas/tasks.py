from datetime import timedelta

from celery import shared_task

from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from spartagames.config import ADMIN_STAFF_EMAIL, ADMIN_USER_EMAIL
from .models import DeleteUsers, GameRegisterLog


@shared_task
def hard_delete_user():
    """
    매일 오전 4시에 실행
    유예기간: 탈퇴 버튼을 누른 시점으로부터 이틀 뒤 (ex: 3월 5일에 탈퇴했다면 3월 7일 오전 4시에 삭제)
    """
    try:
        rows = DeleteUsers.objects.filter(created_at__lte=timezone.now()-timedelta(days=2))
        # 관리자 계정
        admin_staff = get_user_model().objects.get(email=ADMIN_STAFF_EMAIL)
        # 관리자 계정 (게임 이관용, 일반 유저 취급)
        admin_user = get_user_model().objects.get(email=ADMIN_USER_EMAIL)
        
        for row in rows:
            user = row.user
            games = user.games.all()
            for game in games:
                # 등록 거부 사유 로그 추가
                GameRegisterLog.objects.create(
                    recoder=admin_staff,
                    maker=admin_user,
                    game=game,
                    content=f"제작자 {user.nickname}의 게임 데이터를 관리자 계정으로 이관"
                )
                game.maker = admin_user
                game.save()

            reviews = user.reviews.all()
            reviews.delete()

            user.delete()
        
        return f"유저 완전 삭제 프로세스 완료"
    except Exception as e:
        # 예외 발생 시 로그 남기기 (추가적인 로깅 설정 필요 시 설정)
        return f"Error in assigning '' : {str(e)}"
