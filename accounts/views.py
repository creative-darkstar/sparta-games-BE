import secrets
from django.shortcuts import render

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer


from dj_rest_auth.serializers import JWTSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import PBKDF2PasswordHasher
import re
import requests
import urllib.parse
from rest_framework import status
from spartagames import config


class AlertException(Exception):
    pass


class TokenException(Exception):
    pass


from games.models import GameCategory

# ---------- API---------- #
class SignUpAPIView(APIView):
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    NICKNAME_PATTERN = re.compile(r"^[a-zA-Z0-9]{4,10}$")
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')

    def post(self, request):
        login_type = request.data.get("login_type", "DEFAULT")
        email = request.data.get("email")
        nickname = request.data.get("nickname")
        # game_category = request.data.getlist("game_category")
        game_category = request.data.get("game_category", '')
        game_category = game_category.split(',')
        if len(game_category) > 3:
            return Response(
                {"error_message": "선택한 관심 카테고리가 최대 개수를 초과했습니다. 다시 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        user_tech = request.data.get("user_tech")
        is_maker = request.data.get("is_maker")
        
        login_type_list = [t[0] for t in get_user_model().LOGIN_TYPE_CHOICES]
        # login_type 유효성 검사
        if not login_type in login_type_list:
            return Response({"error_message":"올바른 로그인 타입을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        
        # email 유효성 검사
        if not self.EMAIL_PATTERN.match(email):
            return Response({"error_message":"올바른 email을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif get_user_model().objects.filter(email=email).exists():
            return Response({"error_message":"이미 존재하는 email입니다.."}, status=status.HTTP_400_BAD_REQUEST)
        
        # nickname 유효성 검사
        if len(nickname) == 0:
            return Response({"error_message":"닉네임을 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
        elif len(nickname) > 30 or len(nickname) < 4:
            return Response({"error_message":"닉네임은 4자 이상 10자 이하만 가능합니다."}, status=status.HTTP_400_BAD_REQUEST)
        elif not self.NICKNAME_PATTERN.match(nickname):
            return Response({"error_message":"올바른 닉네임을 입력해주세요. 4자 이상 10자 이하의 영숫자입니다."}, status=status.HTTP_400_BAD_REQUEST)
        elif get_user_model().objects.filter(nickname=nickname).exists():
            return Response({"error_message":"이미 존재하는 nickname입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        # 일반 로그인일 경우 비밀번호 유효성 검증 후 유저 데이터 추가
        if login_type == "DEFAULT":
            password = request.data.get("password")
            password_check = request.data.get("password_check")
            
            # password 유효성 검사
            if not self.PASSWORD_PATTERN.match(password):
                return Response({"error_message":"올바른 password.password_check를 입력해주세요."}, status=status.HTTP_400_BAD_REQUEST)
            elif not password == password_check:
                return Response({"error_message":"암호를 확인해주세요."}, status=status.HTTP_400_BAD_REQUEST)
            
            # DB에 유저 등록
            user = get_user_model().objects.create_user(
                email = email,
                nickname = nickname,
                password = password,
                user_tech = user_tech,
                is_maker = is_maker,
                login_type = login_type,
            )
        # 소셜 로그인일 경우 비밀번호 데이터 제외 유저 데이터 추가
        else:
            # DB에 유저 등록
            user = get_user_model().objects.create_user(
                email = email,
                nickname = nickname,
                user_tech = user_tech,
                is_maker = is_maker,
                login_type = login_type,
            )
        
        # 카테고리 가져오기
        game_categories = GameCategory.objects.filter(name__in=game_category)
        if not game_categories.exists():
            return Response(
                {"error_message": "올바른 game category를 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 관심 카테고리 등록
        user.game_category.set(game_categories)  # ManyToManyField 값 설정
        
        # return Response({
        #     "message":"회원가입 성공",
        #     "data":{
        #         "email":user.email,
        #         "nickname":user.nickname,
        #         "game_category": game_category,
        #         "user_tech": user_tech,
        #         "is_maker": is_maker,
        #     },
        # }, status=status.HTTP_201_CREATED)
        
        token = RefreshToken.for_user(user)
        data = {
            'user': user,
            'access': str(token.access_token),
            'refresh': str(token),
        }
        serializer = JWTSerializer(data)
        return Response({'message': f'{login_type} 로그인 성공', **serializer.data}, status=status.HTTP_200_OK)


@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def google_login_callback(request):
    # Authorization code를 token으로 전환
    try:
        authorization_code = request.META.get('HTTP_AUTHORIZATION')
        decoded_code = urllib.parse.unquote(authorization_code)
        url = "https://oauth2.googleapis.com/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "code": decoded_code,
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
        id_token = tokens_json["id_token"]
        profile_request = requests.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={id_token}')
        profile_json = profile_request.json()

        email = profile_json.get('email', None)

        try:
            user = get_user_model().objects.get(email=email)
            token = RefreshToken.for_user(user)
            data = {
                'user': user,
                'access': str(token.access_token),
                'refresh': str(token),
            }
            serializer = JWTSerializer(data)
            return Response({'message': '구글 소셜 로그인 성공, 기존 회원입니다.', **serializer.data}, status=status.HTTP_200_OK)
        except get_user_model().DoesNotExist:
            return Response({
                'message': '구글 소셜 로그인 성공, 회원가입이 필요합니다.',
                'email': email,
                'login_type': "GOOGLE",
            }, status=status.HTTP_200_OK)
        # return social_signinup(email=email, username=username, provider="구글")
        
    except AlertException as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except TokenException as e:
        print(e)
        # 개발 단계에서 확인
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def naver_login_callback(request):
    try:
        authorization_code = request.META.get('HTTP_AUTHORIZATION')
        url = "https://nid.naver.com/oauth2.0/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": config.NAVER_AUTH["client_id"],
            "client_secret": config.NAVER_AUTH["client_secret"],
            "code": authorization_code,
            "state": config.NAVER_AUTH["state"],
        }
        tokens_request = requests.get(url, params=data)
        tokens_json = tokens_request.json()
    except Exception as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    try:
        access_token = tokens_json["access_token"]
        url = "https://openapi.naver.com/v1/nid/me"
        headers = {
            "Authorization": "Bearer " + access_token,
        }
        profile_request = requests.get(url, headers=headers)
        profile_json = profile_request.json().get("response", None)

        email = profile_json.get('email', None)

        try:
            user = get_user_model().objects.get(email=email)
            token = RefreshToken.for_user(user)
            data = {
                'user': user,
                'access': str(token.access_token),
                'refresh': str(token),
            }
            serializer = JWTSerializer(data)
            return Response({
                'message': '네이버 소셜 로그인 성공, 기존 회원입니다.',
                **serializer.data
                }, status=status.HTTP_200_OK)
        except get_user_model().DoesNotExist:
            return Response({
                'message': '네이버 소셜 로그인 성공, 회원가입이 필요합니다.',
                'email': email,
                'login_type': "NAVER",
            }, status=status.HTTP_200_OK)
        # return social_signinup(email=email, username=username, provider="네이버")

    except AlertException as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except TokenException as e:
        print(e)
        # 개발 단계에서 확인
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def kakao_login_callback(request):
    # Authorization code를 token으로 전환
    try:
        authorization_code = request.META.get('HTTP_AUTHORIZATION')
        url = "https://kauth.kakao.com/oauth/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"}
        data = {
            "code": authorization_code,
            "client_id": config.KAKAO_AUTH["client_id"],
            "redirect_uri": config.KAKAO_AUTH["redirect_uri"],
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
        access_token = tokens_json["access_token"]
        url = "https://kapi.kakao.com/v2/user/me"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Authorization": "Bearer " + access_token,
        }
        profile_request = requests.get(url, headers=headers)
        profile_json = profile_request.json()
        
        account = profile_json.get('kakao_account', None)
        nickname = account["profile"]["nickname"]
        email = account["email"]
        
        try:
            user = get_user_model().objects.get(email=email)
            token = RefreshToken.for_user(user)
            data = {
                'user': user,
                'access': str(token.access_token),
                'refresh': str(token),
            }
            serializer = JWTSerializer(data)
            return Response({'message': '카카오 소셜 로그인 성공, 기존 회원입니다.', **serializer.data}, status=status.HTTP_200_OK)
        except get_user_model().DoesNotExist:
            return Response({
                'message': '카카오 소셜 로그인 성공, 회원가입이 필요합니다.',
                'email': email,
                'nickname': nickname,
                'account': account,
                'login_type': "KAKAO",
            }, status=status.HTTP_200_OK)
        # return social_signinup(email=email, username=username, provider="카카오")

    except AlertException as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except TokenException as e:
        print(e)
        # 개발 단계에서 확인
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(('GET',))
@renderer_classes((JSONRenderer,))
def discord_login_callback(request):
    # Authorization code를 token으로 전환
    try:
        authorization_code = request.META.get('HTTP_AUTHORIZATION')
        url = "https://discord.com/api/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "code": authorization_code,
            "client_id": config.DISCORD_AUTH["client_id"],
            "client_secret": config.DISCORD_AUTH["client_secret"],
            "redirect_uri": config.DISCORD_AUTH["redirect_uri"],
            "grant_type": "authorization_code",
            "scope": 'identify, email',
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
        access_token = tokens_json["access_token"]
        url = "https://discordapp.com/api/users/@me"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded;charset=utf-8",
            "Authorization": "Bearer " + access_token,
        }
        profile_request = requests.get(url, headers=headers)
        profile_json = profile_request.json()
        
        nickname = profile_json.get('username', None)
        email = profile_json.get('email', None)
        
        try:
            user = get_user_model().objects.get(email=email)
            token = RefreshToken.for_user(user)
            data = {
                'user': user,
                'access': str(token.access_token),
                'refresh': str(token),
            }
            serializer = JWTSerializer(data)
            return Response({'message': '디스코드 소셜 로그인 성공, 기존 회원입니다.', **serializer.data}, status=status.HTTP_200_OK)
        except get_user_model().DoesNotExist:
            return Response({
                'message': '디스코드 소셜 로그인 성공, 회원가입이 필요합니다.',
                'email': email,
                'nickname': nickname,
                'login_type': "DISCORD",
            }, status=status.HTTP_200_OK)
        # return social_signinup(email=email, username=username, provider="디스코드")

    except AlertException as e:
        print(e)
        messages.error(request, e)
        # 유저에게 알림
        return Response({'message': str(e)}, status=status.HTTP_406_NOT_ACCEPTABLE)
    except TokenException as e:
        print(e)
        # 개발 단계에서 확인
        return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# # 회원가입 또는 로그인을 처리하는 함수
# def social_signinup(email, provider=''):
#     try:
#         user = get_user_model().objects.get(email=email)
#     except get_user_model().DoesNotExist:
#         user = None
#     if user is None:
#         return Response({"message": "회원가입 페이지로 이동", "email": email})

#     token = RefreshToken.for_user(user)
#     data = {
#         'user': user,
#         'access': str(token.access_token),
#         'refresh': str(token),
#     }
#     serializer = JWTSerializer(data)
#     return Response({'message': f'{provider} 로그인 성공', **serializer.data}, status=status.HTTP_200_OK)


# ---------- Web---------- #
# def login_page(request):
#     return render(request, 'accounts/login.html')


# def signup_page(request):
#     email = request.GET.get('email', '')
#     username = request.GET.get('username', '')
#     return render(request, 'accounts/signup.html', {'email': email, 'username': username})
