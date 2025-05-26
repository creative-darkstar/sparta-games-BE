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
    ("NONE", "관심분야 없음"),        # 관심분야 없음
    ("ALL", "All"),                 # 전체

    # Director / Management
    ("DIR", "Game Director"),       # 게임 디렉터
    ("PM", "Project Manager"),      # 프로젝트 매니저
    ("PO", "Product Owner"),        # 프로덕트 오너

    # Design
    ("GDES", "Game Designer"),      # 게임 기획자
    ("SYSD", "System Designer"),    # 시스템 기획자
    ("LVLD", "Level Designer"),     # 레벨 디자이너
    ("CONT", "Content Designer"),   # 콘텐츠 기획자
    ("BAL", "Balance Designer"),    # 밸런스 기획자
    ("ECON", "Economy Designer"),   # 경제 시스템 기획자
    ("LOCA", "Localization Manager"), # 현지화 매니저

    # Art
    ("ADIR", "Art Director"),       # 아트 디렉터
    ("CART", "Concept Artist"),     # 콘셉트 아티스트
    ("2D", "2D Artist"),            # 2D 아티스트
    ("3D", "3D Artist"),            # 3D 아티스트
    ("MDLR", "3D Modeler"),         # 모델러
    ("RIG", "Rigger"),              # 리거
    ("ANIM", "Animator"),           # 애니메이터
    ("TEX", "Texture Artist"),      # 텍스처 아티스트
    ("LIGH", "Lighting Artist"),    # 라이팅 아티스트
    ("ENV", "Environment Artist"),  # 배경 아티스트
    ("VFX", "VFX Artist"),          # 이펙트 아티스트
    ("UIUX", "UI/UX Designer"),     # UI/UX 디자이너

    # Development
    ("CLNT", "Client Developer"),   # 클라이언트 개발자
    ("FRNT", "Frontend Developer"), # 프론트엔드 개발자
    ("BACK", "Backend Developer"),  # 백엔드 개발자
    ("SRVR", "Server Developer"),   # 서버 개발자
    ("TOOL", "Tools Developer"),    # 툴 개발자
    ("NET", "Network Programmer"),  # 네트워크 프로그래머
    ("ENGN", "Engine Programmer"),  # 엔진 프로그래머

    # Sound
    ("COMP", "Composer"),           # 작곡가
    ("SFX", "Sound Designer"),      # 사운드 디자이너
    ("AUDI", "Audio Engineer"),     # 오디오 엔지니어

    # QA / Test
    ("QA", "QA Tester"),            # QA 테스터
    ("QAPL", "QA Planner"),         # QA 기획자
    ("AUTO", "Test Automation Engineer"),  # 테스트 자동화 엔지니어

    # Operations / Biz
    ("LIVE", "Live Ops Manager"),   # 라이브 운영 관리자
    ("DATA", "Data Analyst"),       # 데이터 분석가
    ("BIZ", "Business Analyst"),    # 비즈니스 분석가
    ("COMM", "Community Manager"),  # 커뮤니티 매니저
    ("CS", "Customer Support"),     # 고객 지원
    ("MKT", "Marketing Manager"),   # 마케팅 매니저
    ("MON", "Monetization Designer"), # 수익화 디자이너

    # Visual (Marketing/Branding Design)
    ("VIS", "Visual Designer"),     # 비주얼 디자이너 (마케팅/브랜딩)
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
