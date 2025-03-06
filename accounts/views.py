import os
import pickle
import base64
import random
import re
import requests
import urllib.parse

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email.mime.text import MIMEText

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.renderers import JSONRenderer

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView

from spartagames import config
from .models import EmailVerification


class AlertException(Exception):
    pass


class TokenException(Exception):
    pass


from games.models import GameCategory

# ---------- API---------- #

# TokenObtainPairView에서 사용하는 serializer 커스터마이징
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        user_data = {
            'pk': self.user.id,
            'email': self.user.email,
            'nickname': self.user.nickname,
        }
        data.update({'user': user_data})
        
        return data


# TokenObtainPairView 커스터마이징. 로그인 api view
class CustomLoginAPIView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            user = get_user_model().objects.get(email=request.data.get('email'))
            if user.login_type != 'DEFAULT':
                return Response(
                    {"error_message": f"해당 유저는 기존에 {user.login_type} 로그인 방식으로 가입했습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except get_user_model().DoesNotExist:
            return Response({
                'message': '회원가입이 필요합니다.',
                'email': request.data.get('email'),
                'login_type': "DEFAULT",
            }, status=status.HTTP_200_OK)
        response = super().post(request, *args, **kwargs)
        return response


class SignUpAPIView(APIView):
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    # 2025-02-19 닉네임 패턴 수정 (한, 영, 숫자로 이루어진 4 ~ 10자)
    NICKNAME_PATTERN = re.compile(r"^[가-힣a-zA-Z0-9]{4,10}$")
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')

    def post(self, request):
        email = request.data.get("email")
        code = request.data.get('code')

        verification = get_object_or_404(EmailVerification, email=email)
        
        if verification.verification_code == code:
            # 기존 이메일 인증 데이터 삭제
            EmailVerification.objects.filter(email=email).delete()
        else:
            return Response({'error': '잘못된 인증 번호입니다.'}, status=status.HTTP_400_BAD_REQUEST)
        
        login_type = request.data.get("login_type", "DEFAULT")
        nickname = request.data.get("nickname")
        # game_category = request.data.getlist("game_category")
        game_category = request.data.get("game_category", '')
        game_category = game_category.split(',')
        if len(game_category) > 3:
            return Response(
                {"error_message": "선택한 관심 카테고리가 최대 개수를 초과했습니다. 다시 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        # 전체 게임 카테고리 가져오기
        game_categories = GameCategory.objects.filter(name__in=game_category)
        if not game_categories.exists():
            return Response(
                {"error_message": "올바른 game category를 입력해주세요."},
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
            return Response({"error_message":"올바른 닉네임을 입력해주세요. 4자 이상 10자 이하의 한영숫자입니다."}, status=status.HTTP_400_BAD_REQUEST)
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
            'user': {
                'pk': user.id,
                'email': user.email,
                'nickname': user.nickname,
            },
            'access': str(token.access_token),
            'refresh': str(token),
        }
        return Response({'message': f'회원가입 및 {login_type} 로그인 성공', **data}, status=status.HTTP_200_OK)


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
            if user.login_type != 'GOOGLE':
                return Response({'message': f"해당 유저는 기존에 {user.login_type} 로그인 방식으로 가입했습니다."}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken.for_user(user)
            data = {
                'user': {
                    'pk': user.id,
                    'email': user.email,
                    'nickname': user.nickname,
                },
                'access': str(token.access_token),
                'refresh': str(token),
            }
            return Response({'message': '구글 소셜 로그인 성공, 기존 회원입니다.', **data}, status=status.HTTP_200_OK)
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
            if user.login_type != 'NAVER':
                return Response({'message': f"해당 유저는 기존에 {user.login_type} 로그인 방식으로 가입했습니다."}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken.for_user(user)
            data = {
                'user': {
                    'pk': user.id,
                    'email': user.email,
                    'nickname': user.nickname,
                },
                'access': str(token.access_token),
                'refresh': str(token),
            }
            return Response({'message': '네이버 소셜 로그인 성공, 기존 회원입니다.', **data}, status=status.HTTP_200_OK)
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
            if user.login_type != 'KAKAO':
                return Response({'message': f"해당 유저는 기존에 {user.login_type} 로그인 방식으로 가입했습니다."}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken.for_user(user)
            data = {
                'user': {
                    'pk': user.id,
                    'email': user.email,
                    'nickname': user.nickname,
                },
                'access': str(token.access_token),
                'refresh': str(token),
            }
            return Response({'message': '카카오 소셜 로그인 성공, 기존 회원입니다.', **data}, status=status.HTTP_200_OK)
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
            if user.login_type != 'DISCORD':
                return Response({'message': f"해당 유저는 기존에 {user.login_type} 로그인 방식으로 가입했습니다."}, status=status.HTTP_400_BAD_REQUEST)
            token = RefreshToken.for_user(user)
            data = {
                'user': {
                    'pk': user.id,
                    'email': user.email,
                    'nickname': user.nickname,
                },
                'access': str(token.access_token),
                'refresh': str(token),
            }
            return Response({'message': '디스코드 소셜 로그인 성공, 기존 회원입니다.', **data}, status=status.HTTP_200_OK)
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


# 이메일 인증 관련 상수 값
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 현재 파일의 디렉토리를 기준으로 절대 경로 설정
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, 'client_secret.json')

def get_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds


@api_view(('POST',))
@renderer_classes((JSONRenderer,))
def email_verification(request):
    email = request.data.get("email")
    is_new = request.data.get("is_new", '')
    
    if not email:
        return Response({'error': "이메일을 입력하지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)
    
    # 해당 이메일의 유저 정보 가져오기=>중복 쿼리로 DB 성능 저하 가능성으로 한개로 처리
    user = get_user_model().objects.filter(email=email).first()

    # 소셜 로그인 타입 검사
    if user and user.login_type != "DEFAULT":
        return Response(
            {'error': f"해당 유저는 기존에 [{user.login_type}] 로그인 방식으로 가입했습니다."},
            status=status.HTTP_400_BAD_REQUEST
        )
    # 회원가입할 때(is_new=True) -> 이미 존재하는 이메일이면 에러
    if is_new and user:
            return Response({'error': '이미 가입한 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    # 비밀번호 리셋시(is_new=False) -> 존재하지 않는 이메일이면 에러
    if not is_new and not user:
        return Response({'error': '존재하지 않는 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    
    # 기존 이메일 인증 데이터 삭제=>여기서 이미 삭제 하기에 아래에는 필요가 없음(뭐가 있든 지우고 있기때문)
    EmailVerification.objects.filter(email=email).delete()
    
    creds = get_credentials()
    service = build('gmail', 'v1', credentials=creds)

    code = ''.join(random.choices('0123456789', k=6))
    message = MIMEText(f"이메일 인증 코드는  {code}  입니다.")
    message['from'] = 'sparta.games.master@gmail.com'
    message['to'] = email
    message['subject'] = "Sparta Games 메일 주소 인증 번호"
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    message = {
        'raw': raw
    }

    try:
        message = (service.users().messages().send(userId='me', body=message).execute())
    except Exception as error:
        print(f'An error occurred: {error}')
        return Response({'message': str(error)}, status=status.HTTP_400_BAD_REQUEST)
    
    #이메일 인증 데이터 저장
    EmailVerification.objects.create(email=email, verification_code=code)
    
    return Response({'message': f"인증번호를 발송했습니다. (이메일 message id: {message['id']})"}, status=status.HTTP_200_OK)


@api_view(('POST',))
@renderer_classes((JSONRenderer,))
def verify_code(request):
    email = request.data.get('email')
    code = request.data.get('code')

    try:
        verification = EmailVerification.objects.get(email=email)
    except EmailVerification.DoesNotExist:
        return Response({'error': '유효하지 않은 이메일입니다.'}, status=status.HTTP_400_BAD_REQUEST)

    if verification.is_expired():
        return Response({'error': '인증 번호가 만료되었습니다.'}, status=status.HTTP_400_BAD_REQUEST)

    if verification.verification_code == code:
        return Response({'message': '이메일 인증이 완료되었습니다.'}, status=status.HTTP_200_OK)
    else:
        return Response({'error': '잘못된 인증 번호입니다.'}, status=status.HTTP_400_BAD_REQUEST)


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
