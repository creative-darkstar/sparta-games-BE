from django.shortcuts import render
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from spartagames.utils import std_response

from teambuildings.models import (
    TeamBuildProfile,
)


from games.utils import validate_image

class CreateTeamBuildProfileAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def post(self, request):
        # 필수 항목 확인
        required_fields = ["career", "my_role", "tech_stack", "purpose", "duration", "meeting_type", "contact", "title", "content"]
        missing_fields = [field for field in required_fields if not request.data.get(field)]

        # 누락된 필수 항목이 있을 경우 에러 메시지 반환
        if missing_fields:
            return std_response(message=f"필수 항목이 누락되었습니다: {', '.join(missing_fields)}", status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST)
        
        author = request.data.get("user_id")
        profile_image = request.FILES.get("image")
        career = request.data.get('career')
        my_role = request.data.get('my_role')
        tech_stack = request.data.get("tech_stack")
        game_genre = request.data.get('game_genre')
        portfolio = request.data.get('portfolio',)
        purpose = request.data.get('purpose')
        duration = request.data.get('duration')
        meeting_type = request.data.get('meeting_type')
        contact = request.data.get('contact')
        title = request.data.get('title')
        content = request.data.get('content')

        # 유효성 검사
        # 프로필 이미지 검증
        if profile_image:
            is_valid, error_msg = validate_image(profile_image)
            if not is_valid:
                return std_response(message=error_msg, status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_400_BAD_REQUEST)

        # 현재 상태

        # 장르 설정

        # 포트폴리오

        # 목적

        # 진행방식

        # 참여기간

        profile = TeamBuildProfile.objects.create(
            author = author,
            profile_image = profile_image,
            career = career,
            my_role = my_role,
            tech_stack = tech_stack,
            game_genre = game_genre,
            portfolio = portfolio,
            purpose = purpose,
            duration = duration,
            meeting_type = meeting_type,
            contact = contact,
            title = title,
            content = content,
        )

        return std_response(
            message="팀빌딩 프로필 등록 완료",
            data=profile,
            status="success",
            status_code=status.HTTP_200_OK
        )

# Create your views here.
class TeamBuildProfileAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    def get(self, request, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
            profile = TeamBuildProfile.objects.get(author=user_id)
        except get_user_model().DoesNotExist:
            return std_response(
                message="회원정보가 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except TeamBuildProfile.DoesNotExist:
            return std_response(
                message="아직 생성하지 않은 유저입니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        # 프로필 이미지 체크크
        profile_image = profile.image.url if profile.image else ''
        data = {
            "author" : user_id,
            "profile_image" : profile_image,
            "career" : profile.career,
            "my_role" : profile.my_role,
            "tech_stack" : profile.tech_stack,
            "game_genre" : profile.game_genre,
            "portfolio" : profile.portfolio,
            "purpose" : profile.purpose,
            "duration" : profile.duration,
            "meeting_type" : profile.meeting_type,
            "contact" : profile.contact,
            "title" : profile.title,
            "content" : profile.content,
        }
        return std_response(
            message="프로필 생성 완료",
            data=data,
            status="success",
            status_code=status.HTTP_200_OK
        )
    
    def put(self, request, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
            profile = TeamBuildProfile.objects.get(author=user_id)
        except:
            return std_response(
                message="회원정보가 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        if request.user.id != profile.author:
            return std_response(
                message="권한이 없습니다",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )
        # 프로필 이미지지
        # "image" 데이터를 우선 data.get으로 확인. 확인 시 빈 값("")일 경우 이미지 삭제
        # 변경할 이미지 값이 있거나 "image" 데이터를 포함하지 않았을 경우 기존대로 동작
        profile_image = request.data.get("profile_image")
        if profile_image == "":
            profile.image = None
        else:
            profile.image = self.request.FILES.get("profile_image", profile.image)

        profile.career = self.request.data.get('career', profile.career)
        profile.my_role = self.request.data.get('my_role', profile.my_role)
        profile.tech_stack = self.request.data.get('tech_stack', profile.tech_stack)
        profile.game_genre = self.request.data.get('game_genre', profile.game_genre)
        profile.portfolio = self.request.data.get('portfolio', profile.portfolio)
        profile.purpose = self.request.data.get('purpose', profile.purpose)
        profile.duration = self.request.data.get('duration', profile.duration)
        profile.meeting_type = self.request.data.get('meeting_type', profile.meeting_type)
        profile.contact = self.request.data.get('contact', profile.contact)
        profile.title = self.request.data.get('title', profile.title)
        profile.content = self.request.data.get('content', profile.content)

        profile.save()

        data = {
            "author" : user_id,
            "profile_image" : profile_image,
            "career" : profile.career,
            "my_role" : profile.my_role,
            "tech_stack" : profile.tech_stack,
            "game_genre" : profile.game_genre,
            "portfolio" : profile.portfolio,
            "purpose" : profile.purpose,
            "duration" : profile.duration,
            "meeting_type" : profile.meeting_type,
            "contact" : profile.contact,
            "title" : profile.title,
            "content" : profile.content,
        }
        return std_response(
            message="회원 정보 수정 완료",
            data=data,
            status="success",
            status_code=status.HTTP_202_ACCEPTED
        )
        return std_response()
    def delete(self, request, user_id):
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
            profile = TeamBuildProfile.objects.get(author=user_id)
        except get_user_model().DoesNotExist:
            return std_response(
                message="회원정보가 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except TeamBuildProfile.DoesNotExist:
            return std_response(
                message="아직 생성하지 않은 유저입니다다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 현재 로그인한 유저와 탈퇴 대상 회원이 일치하는지 확인
        if request.user.id != profile.author:
            return std_response(
                message="권한이 없습니다",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )
        
        profile.delete()

        return std_response(
            message="팀빌딩 프로필 삭제 완료",
            status="success",
            status_code=status.HTTP_200_OK
        )