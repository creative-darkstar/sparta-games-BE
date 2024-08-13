from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

import rest_framework
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer

from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client

from dj_rest_auth import views
from dj_rest_auth.registration.views import SocialLoginView
from dj_rest_auth.serializers import JWTSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib import messages
from django.contrib.auth import get_user_model, login
import re
import requests
from rest_framework import status
from spartagames import config


class AlertException(Exception):
    pass


class TokenException(Exception):
    pass


# ---------- API---------- #
class SignUpAPIView(APIView):
    # 유효성 검사 정규식 패턴
    USERNAME_PATTERN = re.compile(r'^[a-zA-Z0-9_]{4,20}$')
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        password_check = request.data.get("password_check")
        email = request.data.get("email")

        # username 유효성 검사
        if not self.USERNAME_PATTERN.match(username):
            return Response({"error_message":"올바른 username을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif get_user_model().objects.filter(username=username).exists():
            return Response({"error_message":"이미 존재하는 username입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # password 유효성 검사
        if not self.PASSWORD_PATTERN.match(password):
            return Response({"error_message":"올바른 password.password_check를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif not password == password_check:
            return Response({"error_message":"암호를 확인해주세요."}, status=status.HTTP_400_BAD_REQUEST)

        # email 유효성 검사
        if not self.EMAIL_PATTERN.match(email):
            return Response({"error_message":"올바른 email을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif get_user_model().objects.filter(email=email).exists():
            return Response({"error_message":"이미 존재하는 email입니다.."}, status=status.HTTP_400_BAD_REQUEST)
        

        # DB에 유저 등록
        user = get_user_model().objects.create_user(
            username = username,
            password = password,
            email = email
        )
        
        return Response({
            "message":"회원가입 성공",
            "data":{
                "username":user.username,
                "email":user.email,
            },
        }, status=status.HTTP_201_CREATED)


@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def google_login_callback(request):
    # Authorization code를 token으로 전환
    try:
        authorization_code = request.META.get('HTTP_AUTHORIZATION')
        url = "https://oauth2.googleapis.com/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "code": authorization_code,
            "client_id": config.GOOGLE_AUTH["client_id"],
            "client_secret": config.GOOGLE_AUTH["client_secret"],
            "redirect_uri": config.GOOGLE_AUTH["redirect_uri"],
            "grant_type": "authorization_code"
        }
        tokens_request = requests.post(url, headers=headers, data=data)
        tokens_json = tokens_request.json()
    except Exception as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    # token 유효성 확인 및 로그인 진행, 유저 정보 전달
    try:
        # token_id = request.META.get('HTTP_AUTHORIZATION')
        id_token = tokens_json["id_token"]
        profile_request = requests.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={id_token}')
        profile_json = profile_request.json()

        username = profile_json.get('name', None)
        email = profile_json.get('email', None)
        try:
            user = get_user_model().objects.get(email=email)
        except get_user_model().DoesNotExist:
            user = None
        if user is not None:
            pass
            # if user.login_method != get_user_model().LOGIN_GOOGLE:
            #     AlertException(f'{user.login_method}로 로그인 해주세요')
        else:
            # user = get_user_model()(email=email, login_method=get_user_model().LOGIN_GOOGLE, nickname=nickname)
            user = get_user_model()(email=email, username=username)
            user.set_unusable_password()
            user.save()
        messages.success(request, f'{user.email} 구글 로그인 성공')
        # login(request, user, backend="django.contrib.auth.backends.ModelBackend",)

        token = RefreshToken.for_user(user)
        data = {
            'user': user,
            'access': str(token.access_token),
            'refresh': str(token),
        }
        serializer = JWTSerializer(data)
        return Response({'message': '로그인 성공', **serializer.data}, status=status.HTTP_200_OK)
    except AlertException as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except TokenException as e:
        print(e)
        # 개발 단계에서 확인
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# ---------- Web---------- #
def login_page(request):
    return render(request, 'accounts/login.html')


def signup_page(request):
    return render(request, 'accounts/signup.html')
