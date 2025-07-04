from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone

from games.models import GameCategory


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        extra_fields.setdefault('is_staff', False)  # 일반 사용자는 관리자 권한이 없으므로 False로 기본값 설정
        extra_fields.setdefault('is_superuser', False)  # 일반 사용자도 superuser가 아니므로 False로 기본값 설정
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)
    

class User(AbstractUser):
    # 비활성화 할 column
    username = None
    first_name = None
    last_name = None
    
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

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nickname']

    objects = CustomUserManager()

    def __str__(self):
        return self.email


# follower가 following을 팔로우하는 것
class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followings")
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)


# 이메일 및 인증 코드를 저장
class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    verification_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)


class BotCnt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.count}'
