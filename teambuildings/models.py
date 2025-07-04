import uuid

from django.db import models
from django.conf import settings
from django.utils import timezone

from commons.views import extract_content_text
from games.models import validate_text_content, GameCategory


PURPOSE_CHOICES = [
        ("PORTFOLIO", "포트폴리오"),
        ("CONTEST", "공모전"),
        ("STUDY", "스터디"),
        ("COMMERCIAL", "상용화"),
    ]

DURATION_CHOICES = [
    ("3M", "3개월 이내"),
    ("6M", "6개월 이내"),
    ("1Y", "1년 이내"),
    ("GT1Y", "1년 이상"),
]

MEETING_TYPE_CHOICES = [
    ("ONLINE", "온라인"),
    ("OFFLINE", "오프라인"),
    ("BOTH", "둘다 가능"),
]


# ROLE_CHOICES = (
#     ("", "Need Update"),
#     # 기획직군
#     ("DIR", "Director"),                # 디렉터 (게임 개발 전반적인 부분에 관여하며 리드하는 포지션)
#     ("PM", "Project Manager"),          # PM (게임 시스템,레벨,경제 등 요소들에 대한 기획)

#     # 디자인직군
#     ("A2D", "2D Artist"),               # 2D 아티스트 (컨셉/일러스트/UI 포함)
#     ("A3D", "3D Artist"),               # 3D 아티스트 (모델링/애니메이션/VFX 포함)
#     ("UXUI", "UXUI Designer"),          # UXUI 디자이너 (게임 사용성 및 내부 아이콘 등 요소 작업)

#     # 개발
#     ("CLNT", "Client Dev"),             # 클라이언트 개발자 (게임요소 직접 구현, 일반적으로 프론트엔드)
#     ("ENG", "Engine Dev"),              # 원활한 게임이용을 위한 엔진 개발 및 구현
#     ("SRVR", "Server / Network Dev"),   # 서버 및 네트워크 개발자 )일반적으로 백엔드 개발)

#     # 기타직군
#     ("AUD", "Sound / Audio"),           # 사운드 엔지니어 (게임 음악 및 효과음 등 오디오 전반)
#     ("QA", "QA / Test"),                # QA, 자동화 포함
# )


class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)


class TeamBuildPost(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_build_post")
    want_roles = models.ManyToManyField(
        Role, related_name="team_build_post"
    )
    title = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to="images/thumbnail/teambuildings/")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    meeting_type = models.CharField(max_length=10, choices=MEETING_TYPE_CHOICES)
    deadline = models.DateField()
    contact = models.CharField(max_length=100)
    content = models.TextField(validators=[validate_text_content])
    content_text = models.TextField(verbose_name="only text of content", null=True, blank=True)
    is_visible = models.BooleanField(default=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    @property
    def status_chip(self):
        return "모집마감" if self.deadline < timezone.now().date() else "모집중"

    def __str__(self):
        return f"{self.title} ({self.status_chip})"
    
    def save(self, *args, **kwargs):
        self.content_text = extract_content_text(self.content)
        super().save(*args, **kwargs)


class TeamBuildProfile(models.Model):
    CAREER_CHOICES = [
        ("STUDENT", "대학생"),
        ("JOBSEEKER", "취준생"),
        ("WORKER", "현직자"),
    ]
    
    def if_role_deleted():
        return Role.objects.get_or_create(name="Need Update")[0]


    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_build_profile")
    image = models.ImageField(
        upload_to="images/profile/teambuildings/",
        blank=True,
        null=True,
    )
    career = models.CharField(max_length=10, choices=CAREER_CHOICES)
    my_role = models.ForeignKey(Role, on_delete=models.SET(if_role_deleted), related_name="team_build_profile")
    tech_stack = models.TextField(max_length=200, null=True, blank=True)
    game_genre = models.ManyToManyField(
        GameCategory, related_name="team_build_profile"
    )
    portfolio = models.JSONField(null=True, blank=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    meeting_type = models.CharField(max_length=10, choices=MEETING_TYPE_CHOICES)
    contact = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    content = models.TextField(validators=[validate_text_content])
    content_text = models.TextField(verbose_name="only text of content", null=True, blank=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.author.nickname}"
    
    def save(self, *args, **kwargs):
        self.content_text = extract_content_text(self.content)
        super().save(*args, **kwargs)


class TeamBuildPostComment(models.Model):
    post = models.ForeignKey(
        TeamBuildPost, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
    )
    content = models.TextField(max_length=1000)
    is_visible = models.BooleanField(default=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)
