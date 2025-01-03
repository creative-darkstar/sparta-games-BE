from django.db import models
from django.conf import settings

from games.models import Game

# Create your models here.
class QnA(models.Model):
    CATEGORY_CHOICES = (
        ("U", "계정 문의"),
        ("E", "게임 실행 문의"),
        ("R", "게임 등록 문의"),
    )
    title=models.CharField(max_length=100)
    content=models.TextField()
    category = models.CharField(max_length=1, choices=CATEGORY_CHOICES)
    is_visible=models.BooleanField(default=True)


# 게임 등록 로그
class GameRegisterLog(models.Model):
    recoder = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="logs_recoder"
    )
    maker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="logs_maker"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="logs_game"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
