from datetime import datetime, timedelta
import json
import os
import requests  # S3 사용
from urllib.parse import urlparse

import boto3

from django.utils import timezone
from django.db.models import Q
from django.core.files.storage import default_storage
from django.core.files.images import ImageFile
from django.core.files.base import ContentFile  # S3 사용
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny  # 로그인 인증토큰
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TeamBuildPost, TeamBuildProfile, TeamBuildPostComment, Role
from .models import PURPOSE_CHOICES, DURATION_CHOICES, MEETING_TYPE_CHOICES
from .pagination import (
    TeamBuildPostPagination,
    TeamBuildProfileListPagination,
    TeamBuildPostCommentPagination,
)
from .serializers import (
    TeamBuildPostSerializer,
    TeamBuildPostDetailSerializer,
    RecommendedTeamBuildPostSerializer,
    TeamBuildPostCommentSerializer,
    TeamBuildProfileSerializer,
)
from .utils import validate_want_roles, validate_choice, extract_srcs, parse_links

from games.models import GameCategory
from games.utils import validate_image

from spartagames.config import AWS_AUTH, AWS_S3_BUCKET_NAME, AWS_S3_REGION_NAME, AWS_S3_CUSTOM_DOMAIN, AWS_S3_BUCKET_IMAGES
from spartagames.utils import std_response
from commons.models import UploadImage


@api_view(["GET"])
def purpose_list(request):
    return std_response(
        data=[{"label": y, "value": x} for (x, y) in PURPOSE_CHOICES],
        status="success",
        status_code=status.HTTP_200_OK
    )


@api_view(["GET"])
def duration_list(request):
    return std_response(
        data=[{"label": y, "value": x} for (x, y) in DURATION_CHOICES],
        status="success",
        status_code=status.HTTP_200_OK
    )


@api_view(["GET"])
def meeting_type_list(request):
    return std_response(
        data=[{"label": y, "value": x} for (x, y) in MEETING_TYPE_CHOICES],
        status="success",
        status_code=status.HTTP_200_OK
    )


@api_view(["GET"])
def career_list(request):
    return std_response(
        data=[{"label": y, "value": x} for (x, y) in TeamBuildProfile.CAREER_CHOICES],
        status="success",
        status_code=status.HTTP_200_OK
    )


@api_view(["GET"])
def role_list(request):
    return std_response(
        data=list(Role.objects.all().values_list('name', flat=True).order_by("id")),
        status="success",
        status_code=status.HTTP_200_OK
    )


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
        teambuildposts = TeamBuildPost.objects.filter(is_visible=True).order_by('-create_dt')
        # 마감하지 않은 것만 추천하도록 조건 추가
        recommendedposts = TeamBuildPost.objects.filter(is_visible=True, deadline__gte=timezone.now().date())
        user = request.user if request.user.is_authenticated else None

        # 추천게시글/마감임박 게시글
        if not user or not user.is_authenticated:
            # 비회원 유저 : 마감 임박 4개
            recommendedposts = recommendedposts.order_by('deadline')[:4]
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

                _qs = recommendedposts.filter(
                    want_roles=my_role,
                    purpose=purpose,
                    duration__in=valid_duration,
                ).order_by('-create_dt')[:4]
                
                # 맞춤 팀빌딩 모집글 개수가 4개 미만인 경우, 마감 임박 글을 추가하도록 수정
                curr_cnt = _qs.count()
                if curr_cnt < 4:
                    # 마감 임박 팀빌딩 모집글 리스트
                    # 맞춤 팀빌딩 모집글에 있는 경우 제외 (.exclude(pk__in=[row.pk for row in _qs]))
                    # 마감 임박 팀빌딩 모집글 리스트는 본래 마감기한 순으로 정렬됨 (.order_by('deadline'))
                    # (4 - 맞춤 팀빌딩 모집글 개수) 개수만큼 가져옴 ([:4 - curr_cnt])
                    _extra_qs = recommendedposts.exclude(pk__in=[row.pk for row in _qs]).order_by('deadline')[:4 - curr_cnt]
                    # 최종적으로 4개로 제한 (이중 체크)
                    recommendedposts = (_qs | _extra_qs)[:4]
                else:
                    recommendedposts = _qs
            else:
                # 유저 프로필이 없으면 마감 임박 4개
                recommendedposts = recommendedposts.order_by('deadline')[:4]

        if request.query_params.get('status_chip') == "open":
            teambuildposts = teambuildposts.filter(
                deadline__gte=timezone.now().date()
            )

        # 유효한 역할코드 목록
        VALID_PURPOSE_KEYS = [p[0] for p in PURPOSE_CHOICES]
        purpose_list = request.query_params.getlist("purpose")
        if purpose_list:
            invalid_purpose = [p for p in purpose_list if p not in VALID_PURPOSE_KEYS]
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
            invalid_duration = [d for d in duration_list if d not in VALID_DURATION_KEYS]
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
            valid_role_names = list(Role.objects.filter(name__in=roles_list).values_list('name', flat=True))

            # 유효하지 않은 role 코드가 포함되면 에러 반환
            invalid_roles = [role for role in roles_list if role not in valid_role_names]
            if invalid_roles:
                return std_response(
                    message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            
            teambuildposts = teambuildposts.filter(want_roles__name__in=roles_list).distinct()

        # 페이지네이션
        paginator = TeamBuildPostPagination()
        paginated_posts = paginator.paginate_queryset(teambuildposts, request)
        serializer = TeamBuildPostSerializer(paginated_posts, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data

        # 추천 게시글 직렬화
        recommended_serializer = RecommendedTeamBuildPostSerializer(recommendedposts, many=True)

        # 프로필 존재 여부
        profile_exists = False
        if request.user.is_authenticated:
            profile_exists = TeamBuildProfile.objects.filter(author=request.user).exists()

        data = {
            "team_build_posts": response_data["results"],
            "recommended_posts": recommended_serializer.data,
            "is_profile": profile_exists
        }

        return std_response(
            data=data,
            message="팀빌딩 목록 불러오기 성공했습니다.",
            status="success",
            pagination={
                "count": response_data["count"],
                "next": response_data["next"],
                "previous": response_data["previous"]
            },
            status_code=status.HTTP_200_OK
        )

    def post(self, request):
        """
        팀빌딩 게시글 작성 API
        """
        user = request.user

        # 필수 필드 체크
        required_fields = [
            "title",
            "want_roles", "purpose", "duration", "meeting_type",
            "deadline", "contact", "content"
        ]
        missing_fields = [field for field in required_fields if not request.data.get(field)]

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
                value=request.data.get(field),
                valid_choices=choices,
                field_name=field
            )
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

        # S3 클라이언트 불러오기
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_AUTH["aws_access_key_id"],
            aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
            region_name=AWS_S3_REGION_NAME,
        )

        # content 에서 img src 파싱
        srcs = extract_srcs(post.content, base_url=f"{AWS_S3_BUCKET_IMAGES}/screenshot/teambuildings")
        for src in srcs:
            # DB 등록
            UploadImage.objects.create(
                content_type=ContentType.objects.get_for_model(post),
                content_id=post.id,
                uploader=user,
                src=src,
                is_used=True
            )
            
            # S3 태깅하기
            s3_file_key = urlparse(src).path.lstrip('/')
            s3.put_object_tagging(
                Bucket=AWS_S3_BUCKET_NAME,
                Key=s3_file_key,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'is_used',
                            'Value': 'true'
                        }
                    ]
                }
            )

        return std_response(
            data={"post_id": post.pk},
            message="팀빌딩 모집글이 등록되었습니다.",
            status="success",
            status_code=status.HTTP_201_CREATED
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # 인증이 필요할 경우 IsAuthenticated로 변경 가능
def teambuild_post_search(request):
    keyword = request.query_params.get('keyword')

    # 기본 필터 조건
    query = Q(is_visible=True)

    # 키워드 조건 추가
    if keyword:
        query &= Q(
            Q(title__icontains=keyword) |
            Q(content_text__icontains=keyword)
        )

    # 검색 키워드에 맞춰 필터링 및 최신순 정렬
    teambuild_posts = TeamBuildPost.objects.filter(query).distinct().order_by('-create_dt')

    # '모집중' 체크박스 체크 시
    if request.query_params.get('status_chip') == "open":
        teambuild_posts = teambuild_posts.filter(deadline__gte=timezone.now().date())

    # 필터 '포지션'(roles) 유효성 검사 및 필터링
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
        valid_role_names = list(Role.objects.filter(name__in=roles_list).values_list('name', flat=True))

        # 유효하지 않은 role 코드가 포함되면 에러 반환
        invalid_roles = [role for role in roles_list if role not in valid_role_names]
        if invalid_roles:
            return std_response(
                message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        teambuild_posts = teambuild_posts.filter(want_roles__name__in=roles_list).distinct()

    # 필터 '프로젝트 목적'(purpose) 유효성 검사 및 필터링
    VALID_PURPOSE_KEYS = [p[0] for p in PURPOSE_CHOICES]
    purpose_list = request.query_params.getlist("purpose")
    if purpose_list:
        invalid_purpose = [p for p in purpose_list if p not in VALID_PURPOSE_KEYS]
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
        
        teambuild_posts = teambuild_posts.filter(purpose_q)

    # 필터 '프로젝트 기간'(duration) 유효성 검사 및 필터링
    VALID_DURATION_KEYS = [d[0] for d in DURATION_CHOICES]
    duration_list = request.query_params.getlist("duration")
    if duration_list:
        invalid_duration = [d for d in duration_list if d not in VALID_DURATION_KEYS]
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
        
        teambuild_posts = teambuild_posts.filter(duration_q)

    # 페이지네이션
    paginator = TeamBuildPostPagination()
    paginated_teambuild_posts = paginator.paginate_queryset(teambuild_posts, request)
    _serializer = TeamBuildPostSerializer(paginated_teambuild_posts, many=True)
    response_data = paginator.get_paginated_response(_serializer.data).data

    data = {
        "search_teambuild_posts": response_data["results"],
    }

    return std_response(
        data=data,
        message="팀빌딩 모집글 - 검색 불러오기 성공했습니다.", status="success",
        pagination={
            "count": response_data["count"],
            "next": response_data["next"],
            "previous": response_data["previous"]
        },
        status_code=status.HTTP_200_OK
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
        
        return std_response(
            data=TeamBuildPostDetailSerializer(post).data,
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
        
            # content 에서 img src 파싱
            old_srcs = [x.src for x in UploadImage.objects.filter(content_type=ContentType.objects.get_for_model(post), content_id=post.id, is_used=True)]
            new_srcs = extract_srcs(post.content, base_url=f"{AWS_S3_BUCKET_IMAGES}/screenshot/teambuildings")
            
            # S3 클라이언트 불러오기
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_AUTH["aws_access_key_id"],
                aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
                region_name=AWS_S3_REGION_NAME,
            )
            
            # 수정 이후 사라진 이미지에 대해, DB 데이터 삭제 및 S3 오브젝트 삭제 처리
            delete_srcs = set(old_srcs) - set(new_srcs)
            if delete_srcs:
                # DB 데이터 삭제
                for src in delete_srcs:
                    obj = UploadImage.objects.get(src=src)
                    obj.delete()
                # S3 오브젝트 삭제
                s3.delete_objects(
                    Bucket=AWS_S3_BUCKET_NAME,
                    Delete={
                        'Objects': [{'Key': urlparse(x).path.lstrip('/')} for x in delete_srcs]
                    }
                )
                
            # 수정 이후 추가된 이미지에 대해 UploadImage에 데이터 추가 및 S3 오브젝트 태깅
            add_srcs = set(new_srcs) - set(old_srcs)
            if add_srcs:
                # DB 데이터 추가
                _add_file_data = [
                    UploadImage(
                        content_type=ContentType.objects.get_for_model(post),
                        content_id=post.id,
                        uploader=request.user,
                        src=x,
                        is_used=True
                    ) for x in add_srcs
                ]
                UploadImage.objects.bulk_create(_add_file_data)
                # S3 오브젝트 태깅
                for src in add_srcs:
                    s3_file_key = urlparse(src).path.lstrip('/')
                    s3.put_object_tagging(
                        Bucket=AWS_S3_BUCKET_NAME,
                        Key=s3_file_key,
                        Tagging={
                            'TagSet': [{'Key': 'is_used', 'Value': 'true'}]
                        }
                    )

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
        for field, choices in [("purpose", PURPOSE_CHOICES), ("duration", DURATION_CHOICES), ("meeting_type", MEETING_TYPE_CHOICES),]:
            value = data.get(field)
            if value and value != getattr(post, field):
                is_valid, error = validate_choice(
                    value=value,
                    valid_choices=choices,
                    field_name=field
                )
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
        raw_roles = data.getlist("want_roles", [])
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
            data={
                "post_id": post.id,
                "changes": changes
            },
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

        # 게시물이 삭제됨에 따라 사용된 모든 이미지에 대해, DB 데이터 삭제 및 S3 오브젝트 삭제 처리
        rows = UploadImage.objects.filter(content_type=ContentType.objects.get_for_model(post), content_id=post.id, is_used=True)
        srcs = [x.src for x in rows]
        
        if rows and srcs:
            # DB 데이터 삭제
            rows.delete()
            
            # S3 오브젝트 삭제
            # S3 클라이언트 불러오기
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_AUTH["aws_access_key_id"],
                aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
                region_name=AWS_S3_REGION_NAME,
            )
            # 삭제
            s3.delete_objects(
                Bucket=AWS_S3_BUCKET_NAME,
                Delete={
                    'Objects': [{'Key': urlparse(x).path.lstrip('/')} for x in srcs]
                }
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


# 팀빌딩 모집글 댓글
class TeamBuildPostCommentAPIView(APIView):
    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == 'post':  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    def get(self, request, post_id):
        order = request.query_params.get('order', 'new')  # 기본값 'new'

        # 모든 댓글 가져오기
        comments = TeamBuildPostComment.objects.filter(post_id=post_id, is_visible=True)

        # 정렬 조건 적용
        if order == 'old':
            # 오래된 순
            comments = comments.order_by('create_dt')
        else:
            # 최신 순
            comments = comments.order_by('-create_dt')
        
        # 페이지네이션 처리
        paginator = TeamBuildPostCommentPagination()
        paginated_comments = paginator.paginate_queryset(comments, request, self)
        if paginated_comments is None:
            return std_response(
                message="리뷰가 없습니다.",
                status="fail",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SERVER_FAIL"
            )

        # 직렬화
        serializer = TeamBuildPostCommentSerializer(paginated_comments, many=True)

        # 페이징 결과 직렬화
        response_data = paginator.get_paginated_response(serializer.data).data

        return std_response(
            data=response_data["results"],
            status="success",
            pagination={
                "count": response_data["count"],
                "next": response_data["next"],
                "previous": response_data["previous"],
            },
            status_code=status.HTTP_200_OK
        )

    def post(self, request, post_id):
        try:
            post = TeamBuildPost.objects.get(pk=post_id, is_visible=True)
        except:
            return std_response(
                message="팀빌딩 모집글이 존재하지 않습니다.",
                status="error",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SERVER_FAIL"
                )

        serializer = TeamBuildPostCommentSerializer(data=request.data)
        
        if serializer.is_valid(raise_exception=True):
            serializer.save(author=request.user, post=post)  # 데이터베이스에 저장
            return std_response(
                data=serializer.data,
                status="success",
                status_code=status.HTTP_201_CREATED
            )

        return std_response(
            data=serializer.errors,
            status="fail",
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="SERVER_FAIL"
        )


class TeamBuildPostCommentDetailAPIView(APIView):
    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == ('put' or 'delete'):
            permissions.append(IsAuthenticated())

        return permissions

    def get(self, request, comment_id):
        try:
        # 댓글이 존재하고, is_visible이 True인 경우만 가져옴
            comment = TeamBuildPostComment.objects.filter(pk=comment_id, is_visible=True)
        except comment.DoesNotExist:
            # 댓글이 존재하지 않으면 404 응답과 함께 메시지 반환
            return std_response(
                message="작성한 댓글이 없습니다.",
                status="fail",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SERVER_FAIL"
            )

        serializer = TeamBuildPostCommentSerializer(comment)

        return std_response(
            data=serializer.data,
            status="success",
            status_code=status.HTTP_200_OK
        )

    def put(self, request, comment_id):
        try:
            # 댓글이 존재하고, is_visible이 True인 경우에만 가져옴
            comment = TeamBuildPostComment.objects.get(pk=comment_id, is_visible=True)
        except:
            # 댓글이 없을 경우 사용자에게 메시지와 함께 404 응답 반환
            return std_response(
                message="작성한 댓글이 존재하지 않습니다.",
                status="fail",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SERVER_FAIL"
            )

        # 작성한 유저이거나 관리자일 경우 동작함
        if request.user == comment.author or request.user.is_staff == True:
            post = comment.post
            if not post.is_visible:
                return std_response(
                    message="해당하는 팀빌딩 모집글이 존재하지 않습니다.",
                    status="error",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="SERVER_FAIL"
                )
        
            serializer = TeamBuildPostCommentSerializer(
                comment, data=request.data, partial=True
            )

            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return std_response(
                    data=serializer.data,
                    status="success",
                    status_code=status.HTTP_200_OK
                )

            return std_response(
                data=serializer.errors,
                status="fail",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="SERVER_FAIL"
            )
        
        else:
            return std_response(
                message="작성자가 아닙니다",
                status="fail",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="CLIENT_FAIL"
            )

    def delete(self, request, comment_id):
        try:
            # 댓글이 존재하고, is_visible이 True인 경우에만 가져옴
            comment = TeamBuildPostComment.objects.get(pk=comment_id, is_visible=True)
        except:
            # 댓글이 없을 경우 사용자에게 메시지와 함께 404 응답 반환
            return std_response(
                message="작성한 댓글이 존재하지 않습니다.",
                status="fail",
                status_code=status.HTTP_404_NOT_FOUND,
                error_code="SERVER_FAIL"
            )

        # 작성한 유저이거나 관리자일 경우 동작함
        if request.user == comment.author or request.user.is_staff == True:
            post = comment.post
            if not post.is_visible:
                return std_response(
                    message="해당하는 팀빌딩 모집글이 존재하지 않습니다.",
                    status="error",
                    status_code=status.HTTP_404_NOT_FOUND,
                    error_code="SERVER_FAIL"
                )
            
            comment.is_visible = False
            comment.save()

            return std_response(
                message="댓글 삭제를 완료했습니다",
                status="success",
                status_code=status.HTTP_200_OK
            )
        else:
            return std_response(
                message="작성자가 아닙니다",
                status="fail",
                status_code=status.HTTP_400_BAD_REQUEST,
                error_code="CLIENT_FAIL"
            )


class CreateTeamBuildProfileAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 팀빌딩 프로필 목록 호출
    def get(self, request):
        # profiles = TeamBuildProfile.objects.order_by('-create_dt')
        profiles = TeamBuildProfile.objects.order_by('-update_dt')

        # 필터: career
        career_list = request.query_params.getlist('career')
        if career_list:
            valid_careers = [c[0] for c in TeamBuildProfile.CAREER_CHOICES]
            invalid_careers = [c for c in career_list if c not in valid_careers]
            if invalid_careers:
                return std_response(
                    message=f"유효하지 않은 커리어 코드입니다: {', '.join(invalid_careers)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            profiles = profiles.filter(career__in=career_list)

        # 필터: purpose
        purpose_list = request.query_params.getlist('purpose')
        if purpose_list:
            valid_purposes = [p[0] for p in PURPOSE_CHOICES]
            invalid_purposes = [p for p in purpose_list if p not in valid_purposes]
            if invalid_purposes:
                return std_response(
                    message=f"유효하지 않은 목적 코드입니다: {', '.join(invalid_purposes)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            profiles = profiles.filter(purpose__in=purpose_list)

        # 필터: duration
        duration_list = request.query_params.getlist('duration')
        if duration_list:
            valid_durations = [d[0] for d in DURATION_CHOICES]
            invalid_durations = [d for d in duration_list if d not in valid_durations]
            if invalid_durations:
                return std_response(
                    message=f"유효하지 않은 기간 코드입니다: {', '.join(invalid_durations)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            profiles = profiles.filter(duration__in=duration_list)

        # 필터: roles
        role_names = request.query_params.getlist('roles')
        if role_names:
            if len(role_names) > 10:
                return std_response(
                    message=f"역할은 최대 10개만 가능합니다. (현재 {len(role_names)}개)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            valid_role_names = list(Role.objects.filter(
                name__in=role_names).values_list('name', flat=True))

            invalid_roles = [r for r in role_names if r not in valid_role_names]
            if invalid_roles:
                return std_response(
                    message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

            profiles = profiles.filter(my_role__name__in=role_names)

        # 페이지네이션 적용
        paginator = TeamBuildProfileListPagination()
        paginated_profiles = paginator.paginate_queryset(profiles, request)
        serializer = TeamBuildProfileSerializer(paginated_profiles, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data

        return std_response(
            message="팀빌딩 프로필 목록 조회 성공",
            data=response_data["results"],
            status="success",
            pagination={
                "count": response_data["count"],
                "next": response_data["next"],
                "previous": response_data["previous"],
            },
            status_code=status.HTTP_200_OK
        )
    
    def post(self, request):
        if TeamBuildProfile.objects.filter(author=request.user).exists():
            return std_response(
                message="이미 팀빌딩 프로필이 존재합니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        required_fields = [
            "career", "my_role", "tech_stack", "purpose", "duration",
            "meeting_type", "contact", "title", "content"
        ]
        missing_fields = [field for field in required_fields if not request.data.get(field)]
        if missing_fields:
            return std_response(
                message=f"필수 항목이 누락되었습니다: {', '.join(missing_fields)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        author = request.user
        # profile_image = request.FILES.get("image")

        profile_image = None
        if "image" in request.data:
            if request.data.get("image") == "":
                profile_image = None
            elif request.FILES.get("image"):
                profile_image = request.FILES["image"]

        career = request.data.get("career")
        tech_stack = request.data.get("tech_stack")
        purpose = request.data.get("purpose")
        duration = request.data.get("duration")
        meeting_type = request.data.get("meeting_type")
        contact = request.data.get("contact")
        title = request.data.get("title")
        content = request.data.get("content")

        # 1. 역할 name 처리
        my_role_name = request.data.get("my_role")
        try:
            my_role = Role.objects.get(name=my_role_name)
        except Role.DoesNotExist:
            return std_response(
                message=f"역할 '{my_role_name}' 을(를) 찾을 수 없습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 2. 장르 name 리스트 처리
        genre_names = request.data.getlist("game_genre") or []
        game_genres = GameCategory.objects.filter(name__in=genre_names)

        # 3. 이미지 유효성 검사
        if profile_image:
            is_valid, error_msg = validate_image(profile_image)
            if not is_valid:
                return std_response(
                    message=error_msg,
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        # 4. 포트폴리오: getlist로 받은 후 JSONField에 저장
        portfolio, error = parse_links(request.data)
        if error:
            return std_response(
                message=error,
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 5. 프로필 생성
        profile = TeamBuildProfile.objects.create(
            author=author,
            image=profile_image,
            career=career,
            my_role=my_role,
            tech_stack=tech_stack,
            portfolio=portfolio,  # JSONField에 list 직접 저장 가능
            purpose=purpose,
            duration=duration,
            meeting_type=meeting_type,
            contact=contact,
            title=title,
            content=content,
        )
        profile.game_genre.set(game_genres)

        # S3 클라이언트 불러오기
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_AUTH["aws_access_key_id"],
            aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
            region_name=AWS_S3_REGION_NAME,
        )

        # content 에서 img src 파싱
        srcs = extract_srcs(profile.content, base_url=f"{AWS_S3_BUCKET_IMAGES}/screenshot/teambuildings")
        for src in srcs:
            UploadImage.objects.create(
                content_type=ContentType.objects.get_for_model(profile),
                content_id=profile.id,
                uploader=author,
                src=src,
                is_used=True
            )

            s3_file_key = urlparse(src).path.lstrip('/')
            s3.put_object_tagging(
                Bucket=AWS_S3_BUCKET_NAME,
                Key=s3_file_key,
                Tagging={
                    'TagSet': [
                        {
                            'Key': 'is_used',
                            'Value': 'true'
                        }
                    ]
                }
            )

        return std_response(
            data={"profile_id": profile.id},
            message="팀빌딩 프로필 등록 완료",
            status="success",
            status_code=status.HTTP_201_CREATED
        )


@api_view(['GET'])
@permission_classes([AllowAny])  # 인증이 필요할 경우 IsAuthenticated로 변경 가능
def teambuild_profile_search(request):
    keyword = request.query_params.get('keyword')

    query = Q()

    # 키워드 조건 추가
    if keyword:
        query &= Q(
            Q(title__icontains=keyword) |
            Q(content_text__icontains=keyword)
        )

    # 검색 키워드에 맞춰 필터링 및 최신순 정렬
    # teambuild_profiles = TeamBuildProfile.objects.filter(query).distinct().order_by('-create_dt')
    teambuild_profiles = TeamBuildProfile.objects.filter(query).distinct().order_by('-update_dt')

    # 필터 '현재 상태'(career) 유효성 검사 및 필터링
    career_list = request.query_params.getlist('career')
    if career_list:
        valid_careers = [c[0] for c in TeamBuildProfile.CAREER_CHOICES]
        invalid_careers = [c for c in career_list if c not in valid_careers]
        if invalid_careers:
            return std_response(
                message=f"유효하지 않은 커리어 코드입니다: {', '.join(invalid_careers)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        teambuild_profiles = teambuild_profiles.filter(career__in=career_list)

    # 필터 '포지션'(roles) 유효성 검사 및 필터링
    role_names = request.query_params.getlist('roles')
    if role_names:
        if len(role_names) > 10:
            return std_response(
                message=f"역할은 최대 10개만 가능합니다. (현재 {len(role_names)}개)",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        valid_role_names = list(Role.objects.filter(
            name__in=role_names).values_list('name', flat=True))

        invalid_roles = [r for r in role_names if r not in valid_role_names]
        if invalid_roles:
            return std_response(
                message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        teambuild_profiles = teambuild_profiles.filter(my_role__name__in=role_names)

    # 필터 '프로젝트 목적'(purpose) 유효성 검사 및 필터링
    purpose_list = request.query_params.getlist('purpose')
    if purpose_list:
        valid_purposes = [p[0] for p in PURPOSE_CHOICES]
        invalid_purposes = [p for p in purpose_list if p not in valid_purposes]
        if invalid_purposes:
            return std_response(
                message=f"유효하지 않은 목적 코드입니다: {', '.join(invalid_purposes)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        teambuild_profiles = teambuild_profiles.filter(purpose__in=purpose_list)

    # 필터 '프로젝트 기간'(duration) 유효성 검사 및 필터링
    duration_list = request.query_params.getlist('duration')
    if duration_list:
        valid_durations = [d[0] for d in DURATION_CHOICES]
        invalid_durations = [d for d in duration_list if d not in valid_durations]
        if invalid_durations:
            return std_response(
                message=f"유효하지 않은 기간 코드입니다: {', '.join(invalid_durations)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        teambuild_profiles = teambuild_profiles.filter(duration__in=duration_list)

    # 페이지네이션 적용
    paginator = TeamBuildProfileListPagination()
    paginated_teambuild_profiles = paginator.paginate_queryset(teambuild_profiles, request)
    serializer = TeamBuildProfileSerializer(paginated_teambuild_profiles, many=True)
    response_data = paginator.get_paginated_response(serializer.data).data

    data = {
        "search_teambuild_profiles": response_data["results"],
    }

    return std_response(
        message="팀빌딩 프로필 - 검색 불러오기 성공했습니다.",
        data=data,
        status="success",
        pagination={
            "count": response_data["count"],
            "next": response_data["next"],
            "previous": response_data["previous"],
        },
        status_code=status.HTTP_200_OK
    )


class TeamBuildProfileAPIView(APIView):
    def get_permissions(self):
        permissions = super().get_permissions()
        if self.request.method.lower() in ['put', 'delete']:
            permissions.append(IsAuthenticated())
        return permissions

    # 개인 프로필 호출
    def get(self, request, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
        except get_user_model().DoesNotExist:
            return std_response(
                message="회원정보가 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        try:
            profile = TeamBuildProfile.objects.get(author=user)
        except TeamBuildProfile.DoesNotExist:
            return std_response(
                message="아직 생성하지 않은 유저입니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )

        return std_response(
            message="팀빌딩 프로필 조회 성공",
            data=TeamBuildProfileSerializer(profile).data,
            status="success",
            status_code=status.HTTP_200_OK
        )

    def put(self, request, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
            profile = TeamBuildProfile.objects.get(author=user)
        except (get_user_model().DoesNotExist, TeamBuildProfile.DoesNotExist):
            return std_response(
                message="회원정보 또는 프로필이 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        if request.user != profile.author:
            return std_response(
                message="권한이 없습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 프로필 이미지 처리
        if "image" in request.data:
            if request.data.get("image") == "":
                profile.image = None
            elif request.FILES.get("image"):
                profile.image = request.FILES["image"]

        # 각 필드 업데이트
        profile.career = request.data.get("career", profile.career)

        role_name = request.data.get("my_role")
        if role_name:
            profile.my_role = Role.objects.filter(name=role_name).first() or profile.my_role

        game_genres = request.data.getlist("game_genre")
        if game_genres:
            genres = GameCategory.objects.filter(name__in=game_genres)
            profile.game_genre.set(genres)

        profile.tech_stack = request.data.get("tech_stack", profile.tech_stack)
        profile.purpose = request.data.get("purpose", profile.purpose)
        profile.duration = request.data.get("duration", profile.duration)
        profile.meeting_type = request.data.get("meeting_type", profile.meeting_type)
        profile.contact = request.data.get("contact", profile.contact)
        profile.title = request.data.get("title", profile.title)
        profile.content = request.data.get("content", profile.content)

        portfolio, error = parse_links(request.data)
        if error:
            return std_response(
                message=error,
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        profile.portfolio = portfolio
        
        # 이미지 처리
        # content 에서 img src 파싱
        old_srcs = [x.src for x in UploadImage.objects.filter(content_type=ContentType.objects.get_for_model(profile), content_id=profile.id, is_used=True)]
        new_srcs = extract_srcs(profile.content, base_url=f"{AWS_S3_BUCKET_IMAGES}/screenshot/teambuildings")
        
        # S3 클라이언트 불러오기
        s3 = boto3.client(
            's3',
            aws_access_key_id=AWS_AUTH["aws_access_key_id"],
            aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
            region_name=AWS_S3_REGION_NAME,
        )
        
        # 수정 이후 사라진 이미지에 대해, DB 데이터 삭제 및 S3 오브젝트 삭제 처리
        delete_srcs = set(old_srcs) - set(new_srcs)
        if delete_srcs:
            # DB 데이터 삭제
            for src in delete_srcs:
                obj = UploadImage.objects.get(src=src)
                obj.delete()
            # S3 오브젝트 삭제
            s3.delete_objects(
                Bucket=AWS_S3_BUCKET_NAME,
                Delete={
                    'Objects': [{'Key': urlparse(x).path.lstrip('/')} for x in delete_srcs]
                }
            )
        
        # 수정 이후 추가된 이미지에 대해 UploadImage에 데이터 추가 및 S3 오브젝트 태깅
        add_srcs = set(new_srcs) - set(old_srcs)
        if add_srcs:
            # DB 데이터 추가
            _add_file_data = [
                UploadImage(
                    content_type=ContentType.objects.get_for_model(profile),
                    content_id=profile.id,
                    uploader=request.user,
                    src=x,
                    is_used=True
                ) for x in add_srcs
            ]
            UploadImage.objects.bulk_create(_add_file_data)
            # S3 오브젝트 태깅
            for src in set(new_srcs) - set(old_srcs):
                s3_file_key = urlparse(src).path.lstrip('/')
                s3.put_object_tagging(
                    Bucket=AWS_S3_BUCKET_NAME,
                    Key=s3_file_key,
                    Tagging={
                        'TagSet': [{'Key': 'is_used', 'Value': 'true'}]
                    }
                )

        profile.save()

        serializer = TeamBuildProfileSerializer(profile)
        return std_response(
            message="팀빌딩 프로필 수정 완료",
            data=serializer.data,
            status="success",
            status_code=status.HTTP_202_ACCEPTED
        )

    def delete(self, request, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
            profile = TeamBuildProfile.objects.get(author=user)
        except (get_user_model().DoesNotExist, TeamBuildProfile.DoesNotExist):
            return std_response(
                message="회원정보 또는 프로필이 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        if request.user != profile.author:
            return std_response(
                message="권한이 없습니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # 게시물이 삭제됨에 따라 사용된 모든 이미지에 대해, DB 데이터 삭제 및 S3 오브젝트 삭제 처리
        rows = UploadImage.objects.filter(content_type=ContentType.objects.get_for_model(profile), content_id=profile.id, is_used=True)
        srcs = [x.src for x in rows]
        
        if rows and srcs:
            # DB 데이터 삭제
            rows.delete()
            
            # S3 오브젝트 삭제
            # S3 클라이언트 불러오기
            s3 = boto3.client(
                's3',
                aws_access_key_id=AWS_AUTH["aws_access_key_id"],
                aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
                region_name=AWS_S3_REGION_NAME,
            )
            # 삭제
            s3.delete_objects(
                Bucket=AWS_S3_BUCKET_NAME,
                Delete={
                    'Objects': [{'Key': urlparse(x).path.lstrip('/')} for x in srcs]
                }
            )

        # 팀빌딩 프로필 완전 삭제
        profile.delete()
        
        return std_response(
            message="팀빌딩 프로필 삭제 완료",
            status="success",
            status_code=status.HTTP_200_OK
        )
