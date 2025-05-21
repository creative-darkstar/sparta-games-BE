from django.db import models
from django.conf import settings
from django.utils import timezone

from games.models import validate_text_content


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


ROLE_CHOICES = (
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


class TeamBuildPost(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_build_posts")
    want_roles = models.JSONField()  # user.user_tech에서 선택한 기술 최대 10개
    title = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to="images/thumbnail/teambuildings/")
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    meeting_type = models.CharField(max_length=10, choices=MEETING_TYPE_CHOICES)
    deadline = models.DateField()
    contact = models.CharField(max_length=100)
    content = models.TextField(validators=[validate_text_content])
    is_visible = models.BooleanField(default=True)
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    @property
    def status_chip(self):
        return "모집마감" if self.deadline < timezone.now().date() else "모집중"

    def __str__(self):
        return f"{self.title} ({self.status_chip})"


class TeamBuildProfile(models.Model):
    CAREER_CHOICES = [
        ("STUDENT", "대학생"),
        ("JOBSEEKER", "취준생"),
        ("WORKER", "현직자"),
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="team_build_profile")
    career = models.CharField(max_length=10, choices=CAREER_CHOICES)
    my_role = models.CharField(max_length=4, choices=ROLE_CHOICES)
    tech_stack = models.TextField(max_length=200, null=True, blank=True)
    portfolio = models.JSONField(null=True, blank=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    meeting_type = models.CharField(max_length=10, choices=MEETING_TYPE_CHOICES)
    contact = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    content = models.TextField(validators=[validate_text_content])
    create_dt = models.DateTimeField(auto_now_add=True)
    update_dt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} - {self.author.nickname}"


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


class TeamBuildScreenshot(models.Model):
    TYPE_CHOICES = [
        ("PR", "프로필"),
        ("PT", "모집글"),
    ]
    
    content_type = models.CharField(max_length=4, choices=TYPE_CHOICES)
    content_id = models.PositiveIntegerField()
    src = models.ImageField(
        upload_to="images/screenshot/teambuildings/",
        blank=True,
        null=True,
    )
    order = models.IntegerField()
