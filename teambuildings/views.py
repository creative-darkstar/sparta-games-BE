from datetime import datetime
from django.utils import timezone
from django.db.models import Q
from django.core.files.storage import default_storage

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .pagination import TeamBuildPostPagination

from .models import TeamBuildPost, TeamBuildProfile
from .models import ROLE_CHOICES, PURPOSE_CHOICES, DURATION_CHOICES, MEETING_TYPE_CHOICES
from rest_framework import status
from spartagames.utils import std_response
from .serializers import TeamBuildPostSerializer, TeamBuildPostDetailSerializer

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
            recommendedposts = recommendedposts.order_by('deadline')[:4]
        # 유저 프로필 존재 여부 확인
        profile = TeamBuildProfile.objects.filter(author=user).first()
        if profile and user:
            # 프로필 존재하면 직업 필터
            my_role = profile.my_role
            purpose = profile.purpose
            duration = profile.duration

            # POSTgreSQL용
            # recommendedposts = recommendedposts.filter(
            #     want_roles__contains=[my_role],
            #     purpose=purpose,
            #     duration=duration
            # ).orderby('-create_dt')[:4]  # 최대 4개만 추천

            # SQLite용
            post_list = list(recommendedposts.orderby('-create_dt'))  # 쿼셋 평가
            filtered_posts = [
                post for post in post_list
                if (
                    my_role in post.want_roles and
                    post.purpose == purpose and
                    post.duration == duration
                )
            ]
            recommendedposts = filtered_posts[:4]  # 최대 4개만 추천
        else:
            # 유저 프로필이 없으면 마감 임박 4개
            recommendedposts = recommendedposts.order_by('deadline')[:4]

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
                    message=f"유효하지 않은 프로젝트 목적 코드입니다: {', '.join(invalid_purpose)}",
                    status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST
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
                    message=f"유효하지 않은 프로젝트 기간 코드입니다: {', '.join(invalid_duration)}",
                    status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST
                )
            duration_q = Q()
            for d in duration_list:
                duration_q |= Q(duration=d)
            teambuildposts = teambuildposts.filter(duration_q)

        # 유효한 역할코드 목록
        VALID_ROLE_KEYS = [choice[0] for choice in ROLE_CHOICES]
        roles_list = list(set(request.query_params.getlist('roles', None)))
        if roles_list:
            # 10개 초과 시 에러 반환
            if len(roles_list) > 10:
                return std_response(message=f"역할은 최대 10개만 가능합니다.(현재 {len(roles_list)}개)", status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST)

            # 유효하지 않은 role 코드가 포함되면 에러 반환
            invalid_roles = [
                role for role in roles_list if role not in VALID_ROLE_KEYS]
            if invalid_roles:
                return std_response(message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}", status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST)

            # role 필터링 SQLite에서 JSONField의 contains를 사용X=>POSTgreSQL로 전환이나 N:M 전환 필요
            # for role in role_list:
            #    teambuildposts = teambuildposts.filter(want_roles__contains=[role])
            # SQLite 용 임시
            posts = list(teambuildposts)  # 쿼셋 평가
            teambuildposts = [post for post in posts if any(
                role in post.want_roles for role in roles_list)]

        # 페이지네이션
        paginator = TeamBuildPostPagination()
        paginated_posts = paginator.paginate_queryset(teambuildposts, request)
        serializer = TeamBuildPostSerializer(paginated_posts, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data

        # 추천 게시글 직렬화
        recommended_serializer = TeamBuildPostSerializer(
            recommendedposts, many=True)

        data = {
            "team_build_posts": response_data["results"],
            "recommended_posts": recommended_serializer.data
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
        if "thumbnail" not in request.FILES:
            return std_response(
                message="썸네일 이미지를 첨부해주세요.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 역할 목록 유효성 검사
        want_roles = request.data.get("want_roles").split(",")
        if not isinstance(want_roles, list):
            return std_response(
                message="`want_roles`는 리스트 형식이어야 합니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        if len(want_roles) > 10:
            return std_response(
                message="`want_roles`는 최대 10개까지 선택 가능합니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # ROLE_CHOICES 검증
        valid_roles = [role[0] for role in ROLE_CHOICES]
        invalid_roles = [
            role for role in want_roles if role not in valid_roles]
        if invalid_roles:
            return std_response(
                message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # 선택지 유효성 검증
        if request.data.get("purpose") not in [p[0] for p in PURPOSE_CHOICES]:
            return std_response(
                message="유효하지 않은 프로젝트 목적 코드입니다.(PORTFOLIO, CONTEST, STUDY, COMMERCIAL 중 하나)",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if request.data.get("duration") not in [d[0] for d in DURATION_CHOICES]:
            return std_response(
                message="유효하지 않은 프로젝트 기간 코드입니다.(3M, 6M, 1Y, GT1Y 중 하나)",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        if request.data.get("meeting_type") not in [m[0] for m in MEETING_TYPE_CHOICES]:
            return std_response(
                message="유효하지 않은 진행 방식 코드입니다.(ONLINE, OFFLINE, BOTH 중 하나)",
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
            want_roles=want_roles,
            title=request.data.get("title"),
            thumbnail=request.FILES["thumbnail"],
            purpose=request.data.get("purpose"),
            duration=request.data.get("duration"),
            meeting_type=request.data.get("meeting_type"),
            deadline=request.data.get("deadline"),
            contact=request.data.get("contact"),
            content=request.data.get("content"),
        )

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

        if self.request.method.lower() == ('put' or 'delete'):  # 포스트할때만 로그인
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
        if isinstance(post, dict):
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
        if isinstance(post, dict):
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
        thumbnail = request.FILES.get("thumbnail")
        if thumbnail:
            #기존 썸네일 삭제(메인에서 활성화)
            #if post.thumbnail:
            #    default_storage.delete(post.thumbnail.name)
            #    post.thumbnail.delete(save=False)
            changes.append("thumbnail")
            post.thumbnail = thumbnail

        # purpose
        purpose = data.get("purpose", post.purpose)
        if purpose and purpose != post.purpose:
            if purpose not in dict(PURPOSE_CHOICES):
                return std_response(
                    message="유효하지 않은 프로젝트 목적입니다.(PORTFOLIO, CONTEST, STUDY, COMMERCIAL 중 하나)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            post.purpose = purpose
            changes.append("purpose")

        # duration
        duration = data.get("duration", post.duration)
        if duration and duration != post.duration:
            if duration not in dict(DURATION_CHOICES):
                return std_response(
                    message="유효하지 않은 프로젝트 기간입니다.(3M, 6M, 1Y, GT1Y 중 하나)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            post.duration = duration
            changes.append("duration")

        # meeting_type
        meeting_type = data.get("meeting_type", post.meeting_type)
        if meeting_type and meeting_type != post.meeting_type:
            if meeting_type not in dict(MEETING_TYPE_CHOICES):
                return std_response(
                    message="유효하지 않은 진행 방식입니다.(ONLINE, OFFLINE, BOTH 중 하나)",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST)
            post.meeting_type = meeting_type
            changes.append("meeting_type")

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
        want_roles = data.get("want_roles")
        if want_roles:
            if isinstance(want_roles, str):
                want_roles = want_roles.split(",")
            if not isinstance(want_roles, list):
                return std_response(
                    message="`want_roles`는 리스트여야 합니다.",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=400)
            if len(want_roles) > 10:
                return std_response(
                    message="역할은 최대 10개까지 선택 가능합니다.",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            invalid_roles = [
                r for r in want_roles if r not in dict(ROLE_CHOICES)]
            if invalid_roles:
                return std_response(
                    message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}",
                    status="fail",
                    error_code="CLIENT_FAIL",
                    status_code= status.HTTP_400_BAD_REQUEST
                )
            if want_roles != post.want_roles:
                post.want_roles = want_roles
                changes.append("want_roles")

        # 변경사항이 없으면 에러 반환
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
        pass
