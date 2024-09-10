from django.shortcuts import redirect, render
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
import re
from rest_framework import status

from games.models import GameCategory

# ---------- API---------- #
class SignUpAPIView(APIView):
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        password_check = request.data.get("password_check")
        nickname = request.data.get("nickname")
        game_category = request.data.getlist("game_category")
        user_tech = request.data.get("user_tech")
        is_maker = request.data.get("is_maker")
        
        # email 유효성 검사
        if not self.EMAIL_PATTERN.match(email):
            return Response({"error_message":"올바른 email을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif get_user_model().objects.filter(email=email).exists():
            return Response({"error_message":"이미 존재하는 email입니다.."}, status=status.HTTP_400_BAD_REQUEST)
        
        # password 유효성 검사
        if not self.PASSWORD_PATTERN.match(password):
            return Response({"error_message":"올바른 password.password_check를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif not password == password_check:
            return Response({"error_message":"암호를 확인해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # nickname 유효성 검사
        if len(nickname) > 30:
            return Response({"error_message":"닉네임은 30자 이하만 가능합니다."}, status=status.HTTP_400_BAD_REQUEST)
        elif len(nickname) == 0:
            return Response({"error_message":"닉네임을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif get_user_model().objects.filter(nickname=nickname).exists():
            return Response({"error_message":"이미 존재하는 username입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # DB에 유저 등록
        user = get_user_model().objects.create_user(
            email = email,
            password = password,
            nickname = nickname,
            user_tech = user_tech,
            is_maker = is_maker,
        )

        # 카테고리 가져오기
        game_categories = GameCategory.objects.filter(name__in=game_category)
        user.game_category.set(game_categories)  # ManyToManyField 값 설정
        
        return Response({
            "message":"회원가입 성공",
            "data":{
                "email":user.email,
                "nickname":user.nickname,
                "game_category": game_category,
                "user_tech": user_tech,
                "is_maker": is_maker,
            },
        }, status=status.HTTP_201_CREATED)

# ---------- Web---------- #
def login_page(request):
    return render(request, 'accounts/login.html')


def signup_page(request):
    return render(request, 'accounts/signup.html')
