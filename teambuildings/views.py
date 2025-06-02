from django.utils import timezone
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .pagination import TeamBuildPostPagination

from .models import TeamBuildPost, TeamBuildProfile
from .models import ROLE_CHOICES, PURPOSE_CHOICES, DURATION_CHOICES
from rest_framework import status
from spartagames.utils import std_response
from .serializers import TeamBuildPostSerializer

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
        teambuildposts= TeamBuildPost.objects.filter(is_visible=True).order_by('-create_dt')
        recommendedposts= TeamBuildPost.objects.filter(is_visible=True)
        user = request.user if request.user.is_authenticated else None
        
        # 추천게시글/마감임박 게시글
        if not user or not user.is_authenticated:
            # 비회원 유저 : 마감 임박 4개
            recommendedposts = recommendedposts.order_by('deadline')[:4]
        #유저 프로필 존재 여부 확인
        profile=TeamBuildProfile.objects.filter(author=user).first()
        if profile and user:
            # 프로필 존재하면 직업 필터
            my_role= profile.my_role
            purpose = profile.purpose
            duration = profile.duration

            # POSTgreSQL용
            # recommendedposts = recommendedposts.filter(
            #     want_roles__contains=[my_role],
            #     purpose=purpose,
            #     duration=duration
            # ).orderby('-create_dt')[:4]  # 최대 4개만 추천

            #SQLite용
            post_list= list(recommendedposts.orderby('-create_dt'))  # 쿼셋 평가
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

        if request.query_params.get('status_chip') =="open":
            teambuildposts = teambuildposts.filter(deadline__gte=timezone.now().date())
        
        # 유효한 역할코드 목록
        VALID_PURPOSE_KEYS = [p[0] for p in PURPOSE_CHOICES]
        purpose_list = request.query_params.getlist("purpose")
        if purpose_list:
            invalid_purpose = [p for p in purpose_list if p not in VALID_PURPOSE_KEYS]
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
            invalid_duration = [d for d in duration_list if d not in VALID_DURATION_KEYS]
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
        roles_list=list(set(request.query_params.getlist('roles', None)))
        if roles_list:
            # 10개 초과 시 에러 반환
            if len(roles_list) > 10:
                return std_response(message=f"역할은 최대 10개만 가능합니다.(현재 {len(roles_list)}개)", status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST)

            # 유효하지 않은 role 코드가 포함되면 에러 반환
            invalid_roles = [role for role in roles_list if role not in VALID_ROLE_KEYS]
            if invalid_roles:
                return std_response(message=f"유효하지 않은 역할 코드: {', '.join(invalid_roles)}", status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST)
            
            # role 필터링 SQLite에서 JSONField의 contains를 사용X=>POSTgreSQL로 전환이나 N:M 전환 필요
            #for role in role_list:
            #    teambuildposts = teambuildposts.filter(want_roles__contains=[role])
            #SQLite 용 임시
            posts = list(teambuildposts)  # 쿼셋 평가
            teambuildposts = [post for post in posts if any(role in post.want_roles for role in roles_list)]
        
        #페이지네이션
        paginator = TeamBuildPostPagination()
        paginated_posts = paginator.paginate_queryset(teambuildposts, request)
        serializer = TeamBuildPostSerializer(paginated_posts, many=True)
        response_data= paginator.get_paginated_response(serializer.data).data

        # 추천 게시글 직렬화
        recommended_serializer = TeamBuildPostSerializer(recommendedposts, many=True)

        data={
            "team_build_posts": response_data["results"],
            "recommended_posts": recommended_serializer.data
        }

        return std_response(data=data,
                        message="팀빌딩 목록 불러오기 성공했습니다.", status="success",
                        pagination={"count":response_data["count"], "next":response_data["next"], "previous":response_data["previous"]},
                        status_code=status.HTTP_200_OK)

    def post(self, request):
        # Logic to create a new team building post
        pass

class TeamBuildPostDetailAPIView(APIView):
    """
    API view to handle team building post detail retrieval and updates.
    """
    def get(self, request, post_id):
        # Logic to retrieve a specific team building post by post_id
        pass

    def put(self, request, post_id):
        # Logic to update a specific team building post by post_id
        pass

    def delete(self, request, post_id):
        # Logic to delete a specific team building post by post_id
        pass