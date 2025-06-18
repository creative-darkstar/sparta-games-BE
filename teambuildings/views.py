import os
import requests  # S3 사용

from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.images import ImageFile
from django.core.files.base import ContentFile  # S3 사용

from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .pagination import TeamBuildPostPagination
from .utils import validate_want_roles, validate_choice
from .models import TeamBuildPost, TeamBuildProfile, Role
from .models import PURPOSE_CHOICES, DURATION_CHOICES, MEETING_TYPE_CHOICES
from rest_framework import status
from spartagames.utils import std_response
from .serializers import TeamBuildPostSerializer, TeamBuildPostDetailSerializer, RecommendedTeamBuildPostSerializer

# Create your views here.


class TeamBuildPostAPIView(APIView):
    """
    포스트일 때 로그인 인증을 위한 함수
    """

    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == 'post':  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    """
    팀빌딩 목록 조회
    """

    def get(self, request):
        teambuildposts = TeamBuildPost.objects.filter(
            is_visible=True).order_by('-create_dt')
        recommendedposts = TeamBuildPost.objects.filter(is_visible=True)
        user = request.user if request.user.is_authenticated else None

        # 추천게시글/마감임박 게시글
        if not user or not user.is_authenticated:
            # 비회원 유저 : 마감 임박 4개
            recommendedposts = recommendedposts.filter(
                deadline__gte=timezone.now().date()).order_by('deadline')[:4]
        else:
            # 유저 프로필 존재 여부 확인
            profile = TeamBuildProfile.objects.filter(author=user).first()
            if profile and user:
                # 프로필 존재하면 직업 필터
                my_role = profile.my_role
                purpose = profile.purpose
                duration = profile.duration

                DURATION_ORDER = {
                    "3M": 1,
                    "6M": 2,
                    "1Y": 3,
                    "GT1Y": 4,
                }

                valid_duration = [
                    key for key, order in DURATION_ORDER.items()
                    if order <= DURATION_ORDER.get(duration, 4)
                ]

                recommendedposts = recommendedposts.filter(
                    want_roles=my_role,
                    purpose=purpose,
                    duration__in=valid_duration
                ).order_by('-create_dt')[:4]
            else:
                # 유저 프로필이 없으면 마감 임박 4개
                recommendedposts = recommendedposts.filter(
                    deadline__gte=timezone.now().date()).order_by('deadline')[:4]

        if request.query_params.get('status_chip') == "open":
            teambuildposts = teambuildposts.filter(
                deadline__gte=timezone.now().date())

        # 유효한 역할코드 목록
        VALID_PURPOSE_KEYS = [p[0] for p in PURPOSE_CHOICES]
        purpose_list = request.query_params.getlist("purpose")
        if purpose_list:
            invalid_purpose = [
                p for p in purpose_list if p not in VALID_PURPOSE_KEYS]
            if invalid_purpose:
                return std_response(
                    message=f"유효하지 않은 프로젝트 목적 코드입니다: {', '.join(invalid_purpose)} (PORTFOLIO, CONTEST, STUDY, COMMERCIAL 중 하나)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            purpose_q = Q()
            for p in purpose_list:
                purpose_q |= Q(purpose=p)
            teambuildposts = teambuildposts.filter(purpose_q)

        # 유효한 기간 코드 목록
        VALID_DURATION_KEYS = [d[0] for d in DURATION_CHOICES]
        duration_list = request.query_params.getlist("duration")
        if duration_list:
            invalid_duration = [
                d for d in duration_list if d not in VALID_DURATION_KEYS]
            if invalid_duration:
                return std_response(
                    message=f"유효하지 않은 프로젝트 기간 코드입니다: {', '.join(invalid_duration)} (3M, 6M, 1Y, GT1Y 중 하나)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            duration_q = Q()
            for d in duration_list:
                duration_q |= Q(duration=d)
            teambuildposts = teambuildposts.filter(duration_q)

        # 유효한 역할코드 목록
        roles_list = list(set(request.query_params.getlist('roles', None)))
        if roles_list:
            # 10개 초과 시 에러 반환
            if len(roles_list) > 10:
                return std_response(
                    message=f"역할은 최대 10개만 가능합니다.(현재 {len(roles_list)}개)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            # 유효한 Role name 목록을 DB에서 조회
            valid_role_names = list(Role.objects.filter(
                name__in=roles_list).values_list('name', flat=True))

            # 유효하지 않은 role 코드가 포함되면 에러 반환
            invalid_roles = [
                role for role in roles_list if role not in valid_role_names]
            if invalid_roles:
                return std_response(
                    message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            teambuildposts = teambuildposts.filter(
                want_roles__name__in=roles_list).distinct()

        # 페이지네이션
        paginator = TeamBuildPostPagination()
        paginated_posts = paginator.paginate_queryset(teambuildposts, request)
        serializer = TeamBuildPostSerializer(paginated_posts, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data

        # 추천 게시글 직렬화
        recommended_serializer = RecommendedTeamBuildPostSerializer(
            recommendedposts, many=True)

        # 프로필 존재 여부
        profile_exists = False
        if request.user.is_authenticated:
            profile_exists = TeamBuildProfile.objects.filter(author=request.user).exists()

        data = {
            "team_build_posts": response_data["results"],
            "recommended_posts": recommended_serializer.data,
            "is_profile": profile_exists
        }

        return std_response(data=data,
                            message="팀빌딩 목록 불러오기 성공했습니다.", status="success",
                            pagination={
                                "count": response_data["count"], "next": response_data["next"], "previous": response_data["previous"]},
                            status_code=status.HTTP_200_OK)

    def post(self, request):
        """
        팀빌딩 게시글 작성 API
        """
        user = request.user

        # 필수 필드 체크
        required_fields = ["title", "want_roles", "purpose",
                           "duration", "meeting_type", "deadline", "contact", "content"]
        missing_fields = [
            field for field in required_fields if not request.data.get(field)]

        if missing_fields:
            return std_response(
                message=f"필수 항목이 누락되었습니다: {', '.join(missing_fields)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 썸네일 필수
        thumbnail = request.FILES.get("thumbnail", None)
        thumbnail_basic = request.data.get("thumbnail_basic", None)
        if not thumbnail and thumbnail_basic != "default":
            return std_response(
                message="썸네일 이미지가 첨부되지 않았습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 역할 목록 유효성 검사
        raw_roles = request.data.getlist("want_roles", [])
        want_roles, role_error = validate_want_roles(raw_roles)
        if role_error:
            return std_response(
                message=role_error,
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 선택지 유효성 검증
        for field, choices in [("purpose", PURPOSE_CHOICES), ("duration", DURATION_CHOICES), ("meeting_type", MEETING_TYPE_CHOICES)]:
            is_valid, error = validate_choice(
                request.data.get(field), choices, field)
            if not is_valid:
                return std_response(
                    message=error,
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # 날짜 포맷 검증
        try:
            deadline = datetime.strptime(
                request.data.get("deadline"), "%Y-%m-%d").date()
        except ValueError:
            return std_response(
                message="마감일은 YYYY-MM-DD 형식의 날짜여야 합니다.",
                status="error",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 객체 생성
        post = TeamBuildPost.objects.create(
            author=user,
            title=request.data.get("title"),
            purpose=request.data.get("purpose"),
            duration=request.data.get("duration"),
            meeting_type=request.data.get("meeting_type"),
            deadline=deadline,
            contact=request.data.get("contact"),
            content=request.data.get("content"),
        )

        # 썸네일 할당
        if thumbnail:
            post.thumbnail = thumbnail
        elif thumbnail_basic == "default":
            post.thumbnail.name = "images/thumbnail/teambuildings/teambuilding_default.png"
        post.save()

        # 역할 추가
        post.want_roles.set(Role.objects.filter(name__in=want_roles))

        return std_response(
            data={"post_id": post.pk},
            message="팀빌딩 모집글이 등록되었습니다.",
            status="success",
            status_code=status.HTTP_201_CREATED
        )


class TeamBuildPostDetailAPIView(APIView):
    """
    PUT, DELETE일 때 로그인 인증을 위한 함수
    """

    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() in ('put', 'delete', 'patch'):  # 수정, 삭제, 마감할 때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    def get_object(self, post_id):
        try:
            return TeamBuildPost.objects.get(id=post_id, is_visible=True)
        except TeamBuildPost.DoesNotExist:
            return std_response(
                message="해당 팀빌딩 게시글을 찾을 수 없습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )

    def get(self, request, post_id):
        """
        팀빌딩 게시글 상세조회 API
        """
        post = self.get_object(post_id)
        if isinstance(post, Response):
            return post
        serilizer = TeamBuildPostDetailSerializer(post).data
        return std_response(
            data=serilizer,
            message="팀빌딩 게시글 상세조회 성공하였습니다.",
            status="success",
            status_code=status.HTTP_200_OK
        )

    def put(self, request, post_id):
        """
        팀빌딩 게시글 수정 API
        """
        post = self.get_object(post_id)
        if isinstance(post, Response):
            return post
        if post.author != request.user:
            return std_response(
                message="해당 게시글을 수정할 권한이 없습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )
        data = request.data
        changes = []

        # title
        title = data.get("title", post.title)
        if title != post.title:
            changes.append("title")
            post.title = title

        # content
        content = data.get("content", post.content)
        if content != post.content:
            changes.append("content")
            post.content = content

        # contact
        contact = data.get("contact", post.contact)
        if contact != post.contact:
            changes.append("contact")
            post.contact = contact

        # thumbnail
        thumbnail = request.FILES.get("thumbnail", None)
        thumbnail_basic = request.data.get("thumbnail_basic", None)
        if thumbnail:
            # 기존 썸네일 삭제(메인에서 활성화)
            # if post.thumbnail:
            #    default_storage.delete(post.thumbnail.name)
            #    post.thumbnail.delete(save=False)
            changes.append("thumbnail")
            post.thumbnail = thumbnail
        elif thumbnail_basic == "default":
            # 기본 이미지로 설정
            post.thumbnail.name = "images/thumbnail/teambuildings/teambuilding_default.png"
            changes.append("thumbnail")

        # 선택지 유효성 검증 (필드 변경 시만 적용)
        for field, choices in [
            ("purpose", PURPOSE_CHOICES),
            ("duration", DURATION_CHOICES),
            ("meeting_type", MEETING_TYPE_CHOICES),
        ]:
            value = data.get(field)
            if value and value != getattr(post, field):
                is_valid, error = validate_choice(value, choices, field)
                if not is_valid:
                    return std_response(
                        message=error,
                        status="fail",
                        error_code="CLIENT_FAIL",
                        status_code=status.HTTP_400_BAD_REQUEST
                    )
                setattr(post, field, value)
                changes.append(field)

        # deadline
        deadline = data.get("deadline")
        if deadline:
            try:
                deadline = datetime.strptime(deadline, "%Y-%m-%d").date()
                if deadline != post.deadline:
                    post.deadline = deadline
                    changes.append("deadline")
            except ValueError:
                return std_response(
                    message="마감일은 YYYY-MM-DD 형식이어야 합니다.",
                    status="error",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # want_roles
        raw_roles = data.get("want_roles", [])
        want_roles, role_error = validate_want_roles(raw_roles)
        if role_error:
            return std_response(
                message=role_error,
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        if want_roles:
            post.want_roles.set(Role.objects.filter(name__in=want_roles))
            changes.append("want_roles")

        # 변경사항이 있으면 저장
        if changes:
            post.save()

        return std_response(
            data={"post_id": post.id, "changes": changes},
            message="팀빌딩 게시글이 수정되었습니다.",
            status="success",
            status_code=status.HTTP_200_OK
        )

    def delete(self, request, post_id):
        """
        팀빌딩 게시글 삭제 API
        """
        post = self.get_object(post_id)
        if isinstance(post, Response):
            return post

        # 권한 확인
        if request.user != post.author and not request.user.is_staff:
            return std_response(
                message="작성자만 삭제할 수 있습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 팀빌딩 게시글 소프트 삭제
        post.is_visible = False
        post.save()
        return std_response(
            message="팀빌딩 게시글이 삭제되었습니다.",
            status="success",
            status_code=status.HTTP_200_OK
        )

    def patch(self, request, post_id):
        """
        팀빌딩 게시글 마감 API
        """

        post = self.get_object(post_id)
        if isinstance(post, Response):
            return post

        # 권한 확인
        if request.user != post.author:
            return std_response(
                message="작성자만 마감할 수 있습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )

        new_deadline = timezone.now().date() - timedelta(days=1)

        post.deadline = new_deadline
        post.save()

        return std_response(
            message="팀빌딩 게시글이 마감되었습니다.",
            status="success",
            status_code=status.HTTP_200_OK
        )
