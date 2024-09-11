from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
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
    

class User(AbstractBaseUser):
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


class BotCnt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f'{self.user.username} - {self.date} - {self.count}'
