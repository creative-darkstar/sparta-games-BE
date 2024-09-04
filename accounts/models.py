from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from games.models import GameCategory


class User(AbstractUser):
    email = models.EmailField(unique=True)
    nickname = models.CharField(max_length=30, unique=True)
    LOGIN_TYPE_CHOICES = (
        ("DEFAULT", "일반 로그인"),
        ("GOOGLE", "구글"),
        ("NAVER", "네이버"),
        ("KAKAO", "카카오"),
        ("DISCORD", "디스코드"),
    )
    login_type = models.CharField(max_length=20, choices=LOGIN_TYPE_CHOICES)
    image = models.ImageField(
        upload_to="images/profile/",
        blank=True,
        null=True,
    )
    is_maker = models.BooleanField(default=False)
    introduce = models.TextField()
    game_category = models.ManyToManyField(
        GameCategory, related_name="user_game_category"
    )
    USER_TECH_CHOICES = (
        ("NONE", "관심분야 없음"),
        ("ALL", "All"),
        ("DIR", "Director (PM/PO)"),
        ("2DG", "2D Graphic"),
        ("CA", "Concept Art"),
        ("UXUI", "UX/UI"),
        ("ART", "Artist"),
        ("3DG", "3D Graphic"),
        ("MDL", "Modeler"),
        ("FE", "Frontend"),
        ("BE", "Backend"),
    )
    user_tech = models.CharField(max_length=4, choices=USER_TECH_CHOICES)


# follower가 following을 팔로우하는 것
class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followings")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)


class BotCnt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.count}'
