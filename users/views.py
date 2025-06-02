import re

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from spartagames.utils import std_response
from spartagames.pagination import CustomPagination

from .serializers import MyGameListSerializer

from accounts.models import EmailVerification
from games.models import (
    Game,
    GameCategory,
)
from games.serializers import GameListSerializer
from qnas.models import DeleteUsers


# ---------- API---------- #
class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 유효성 검사 정규식 패턴
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    # 2025-02-19 닉네임 패턴 수정 (한, 영, 숫자로 이루어진 4 ~ 10자)
    NICKNAME_PATTERN = re.compile(r"^[가-힣a-zA-Z0-9]{4,10}$")

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
        profile_image = user.image.url if user.image else ''
        categories = list(user.game_category.values_list('name', flat=True))
        if len(categories) > 3:
            return std_response(
                message="선택한 관심 카테고리가 최대 개수를 초과했습니다. 다시 입력해주세요.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        data = {
            "user_id": user_id,
            "email": user.email,
            "nickname": user.nickname,
            "login_type": user.login_type,
            "profile_image": profile_image,
            "is_staff": user.is_staff,
            "is_maker": user.is_maker,
            "introduce": user.introduce,
            "game_category": categories,
        }
        return std_response(
            data=data,
            status="success",
            status_code=status.HTTP_200_OK
        )

    def put(self, request, user_id):
        # check_password = self.request.data.get("password")
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
        except get_user_model().DoesNotExist:
            return std_response(
                message="회원정보가 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # 현재 로그인한 유저와 수정 대상 회원이 일치하는지 확인
        if request.user.id != user.pk:
            return std_response(
                message="권한이 없습니다",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )

        # # 유저 비밀번호가 일치하지 않으면
        # if user.check_password(check_password) is False:
        #     return Response(
        #         {"message": "비밀번호가 일치하지 않습니다."},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        # 닉네임 검증
        nickname = self.request.data.get('nickname', user.nickname)
        # email 수정을 하지 않았을 경우 문제 없이 pass
        if nickname == user.nickname:
            pass
        # 닉네임이 유효하지 않거나 다른 유저의 이메일로 수정하려고 할 경우 error
        elif not self.NICKNAME_PATTERN.match(nickname):
            return std_response(
                message="올바른 닉네임을 입력해주세요. 4자 이상 10자 이하의 한영숫자입니다.",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        elif get_user_model().objects.filter(nickname=nickname).exists():
            return std_response(
                message="이미 존재하는 nickname입니다.",
                status="fail",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # 관심 게임 카테고리
        categories = request.data.get("game_category", '')
        categories = categories.split(',')
        if categories:
            game_categories = GameCategory.objects.filter(name__in=categories)
            if not game_categories.exists():
                return std_response(
                    message="올바른 game category를 입력해주세요.",
                    status="fail",
                    error_code="SERVER_FAIL",
                    status_code=status.HTTP_400_BAD_REQUEST
                )
            user.game_category.set(game_categories)
        else:
            categories = list(user.game_category.values_list('id', flat=True))
        
        # # 이메일 검증
        # email = self.request.data.get('email', user.email)
        # # email 수정을 하지 않았을 경우 문제 없이 pass
        # if email == user.email:
        #     pass
        # # 이메일이 유효하지 않거나 다른 유저의 이메일로 수정하려고 할 경우 error
        # elif not self.EMAIL_PATTERN.match(email):
        #     return Response({"error_message": "올바른 email을 입력해주세요."})
        # elif get_user_model().objects.filter(email=email).exists():
        #     return Response({"error_message": "이미 존재하는 email입니다.."})

        # 닉네임
        user.nickname = nickname
        # 프로필 이미지
        # 2025-03-22 FE팀 요청
        # "image" 데이터를 우선 data.get으로 확인. 확인 시 빈 값("")일 경우 이미지 삭제
        # 변경할 이미지 값이 있거나 "image" 데이터를 포함하지 않았을 경우 기존대로 동작
        image = self.request.data.get("image")
        if image == "":
            user.image = None
        else:
            user.image = self.request.FILES.get("image", user.image)
        # 유저 / 메이커 구분
        user.is_maker = self.request.data.get('is_maker', user.is_maker)
        # 자기소개
        user.introduce = self.request.data.get('introduce', user.introduce)
        
        # 변경한 데이터 저장
        user.save()

        categories = list(user.game_category.values_list('id', flat=True))
        data = {
            "nickname": user.nickname,
            "profile_image": user.image.url if user.image else "이미지 없음",
            "is_staff": user.is_staff,
            "is_maker": user.is_maker,
            "introduce": user.introduce,
            "game_category": categories,
        }
        return std_response(
            message="회원 정보 수정 완료",
            data=data,
            status="success",
            status_code=status.HTTP_202_ACCEPTED
        )

    def delete(self, request, user_id):
        # check_password = self.request.data.get("password")
        try:
            user = get_user_model().objects.get(pk=user_id, is_active=True)
        except get_user_model().DoesNotExist:
            return std_response(
                message="회원정보가 존재하지 않습니다.",
                status="error",
                error_code="SERVER_FAIL",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 현재 로그인한 유저와 탈퇴 대상 회원이 일치하는지 확인
        if request.user.id != user.pk:
            return std_response(
                message="권한이 없습니다",
                status="fail",
                error_code="CLIENT_FAIL",
                status_code=status.HTTP_403_FORBIDDEN
            )

        user.is_active = False
        user.save()
        
        # 회원 탈퇴(임시) 리스트에 데이터 추가
        DeleteUsers.objects.create(user=user)
        
        return std_response(
            message=f"회원 탈퇴 완료 (회원 아이디: {user.nickname})",
            status="success",
            status_code=status.HTTP_200_OK
        )


# teambuildings 앱으로 이관 예정
# @api_view(["GET"])
# def user_tech_list(request):
#     techs = ROLE_CHOICES
#     return std_response(
#         data=techs,
#         status="success",
#         status_code=status.HTTP_200_OK
#     )


@api_view(["GET"])
def check_nickname(request):
    # 유효성 검사 정규식 패턴
    # 2025-02-19 닉네임 패턴 수정 (한, 영, 숫자로 이루어진 4 ~ 10자)
    NICKNAME_PATTERN = re.compile(r"^[가-힣a-zA-Z0-9]{4,10}$")

    nickname = request.data.get('nickname', None)
        
    # 닉네임이 유효하지 않거나 다른 유저의 이메일로 수정하려고 할 경우 error
    if not NICKNAME_PATTERN.match(nickname):
        return std_response(
            message="올바른 닉네임을 입력해주세요. 4자 이상 10자 이하의 한영숫자입니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    elif get_user_model().objects.filter(nickname=nickname).exists():
        return std_response(
            message="이미 존재하는 nickname입니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    else:
        return std_response(
            message="사용 가능한 닉네임입니다.",
            status="success",
            status_code=status.HTTP_200_OK
        )


@api_view(["PUT"])
def change_password(request, user_id):
    # 유효성 검사 정규식 패턴
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')

    try:
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except get_user_model().DoesNotExist:
        return std_response(
            message="회원정보가 존재하지 않습니다.",
            status="error",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_404_NOT_FOUND
        )
    # 로그인 타입 확인
    if user.login_type != "DEFAULT":
        return std_response(
            message="비밀번호 변경은 일반 로그인(DEFAULT) 사용자만 가능합니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_403_FORBIDDEN
        )

    check_password = request.data.get("password")
    new_password = request.data.get("new_password")
    new_password_check = request.data.get("new_password_check")

    # 현재 로그인한 유저와 비밀번호 수정 대상 회원이 일치하는지 확인
    if request.user.id != user.pk:
        return std_response(
            message="권한이 없습니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_403_FORBIDDEN
        )

    # 유저 비밀번호가 일치하지 않으면
    if user.check_password(check_password) is False:
        return std_response(
            message="비밀번호가 일치하지 않습니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if check_password == new_password:
        return std_response(
            message="현재 비밀번호와 동일합니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # new password 유효성 검사
    if not PASSWORD_PATTERN.match(new_password):
        return std_response(
            message="올바른 password, password_check를 입력해주세요.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    elif not new_password == new_password_check:
        return std_response(
            message="동일한 password와 password_check를 입력해주세요.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 유저 비밀번호가 일치한다면
    user.set_password(new_password)
    user.save()
    return std_response(
        message=f"비밀번호 수정 완료 (회원 아이디: {user.nickname})",
        status="success",
        status_code=status.HTTP_202_ACCEPTED
    )


@api_view(["POST"])
def password_verify_code(request):
    email = request.data.get('email')
    code = request.data.get('code')

    try:
        verification = EmailVerification.objects.get(email=email)
    except EmailVerification.DoesNotExist:
        return std_response(
            message=f"유효하지 않은 이메일입니다.",
            status="error",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if verification.is_expired():
        return std_response(
            message="인증 번호가 만료되었습니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if verification.verification_code == code:
        return std_response(
            message=f"이메일 인증이 완료되었습니다.",
            status="success",
            status_code=status.HTTP_200_OK
        )
    else:
        return std_response(
            message="잘못된 인증 번호입니다",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )


@api_view(["PUT"])
def reset_password(request):
    # 유효성 검사 정규식 패턴
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')
    
    email = request.data.get("email")
    code = request.data.get('code')
    new_password = request.data.get("new_password")
    new_password_check = request.data.get("new_password_check")
    
    user = get_user_model().objects.get(email=email)
    
    if user.login_type != "DEFAULT":
        return std_response(
            message="비밀번호 변경은 일반 로그인(DEFAULT) 사용자만 가능합니다. 소셜 로그인 사용자는 비밀번호를 변경할 수 없습니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_403_FORBIDDEN
        )

    try:
        verification = EmailVerification.objects.get(email=email)
    except EmailVerification.DoesNotExist:
        return std_response(
            message=f"유효하지 않은 이메일입니다.",
            status="error",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if verification.is_expired():
        return std_response(
            message="인증 번호가 만료되었습니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if verification.verification_code != code:
        return std_response(
            message="잘못된 인증 번호입니다",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # new password 유효성 검사
    if not PASSWORD_PATTERN.match(new_password):
        return std_response(
            message="올바른 password, password_check를 입력해주세요.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    elif not new_password == new_password_check:
        return std_response(
            message="동일한 password와 password_check를 입력해주세요.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    user.set_password(new_password)
    user.save()
    # 기존 이메일 인증 데이터 삭제
    EmailVerification.objects.filter(email=email).delete()
    
    return std_response(
        message=f"비밀번호 수정 완료 (회원 아이디: {user.nickname})",
        status="success",
        status_code=status.HTTP_202_ACCEPTED
    )


@api_view(["GET"])
def my_games(request, user_id):
    try:
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except get_user_model().DoesNotExist:
        return std_response(
            message="회원정보가 존재하지 않습니다.",
            status="error",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_404_NOT_FOUND
        )
    my_games = user.games.filter(is_visible=True).order_by('-created_at')
    if not my_games.exists():
        return std_response(
            message=f"{request.user}가 제작한 게임이 없습니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_404_NOT_FOUND
        )

    # 대상 일치 여부 확인
    if user != request.user:
        my_games = my_games.filter(register_state=1)

    # 페이지네이션 적용
    paginator = CustomPagination()
    paginated_data = paginator.paginate_queryset(my_games, request)
    
    # 시리얼라이저 적용
    serializer = MyGameListSerializer(paginated_data, many=True, context={'user': user})
    data = paginator.get_paginated_response(serializer.data).data
    
    # 리턴
    return std_response(
        data=data["results"],
        status="success",
        pagination={
            "count": data["count"],
            "next": data["next"],
            "previous": data["previous"]
        },
        status_code=status.HTTP_200_OK
    )
    
    # item_list = list()
    # for item in my_games:
    #     category_list = list(item.category.values_list('name', flat=True))
    #     chip_list = list(item.chip.values_list('name', flat=True))
    #     item_list.append({
    #         "game_pk": item.pk,
    #         "title": item.title,
    #         "thumbnail": item.thumbnail.url if item.thumbnail else None,
    #         "register_state": item.register_state,
    #         "created_at": item.created_at,
    #         "category_name": category_list,
    #         "chip_list": chip_list,
    #         "star": item.star,
    #         "review_cnt": item.review_cnt
    #     })
    
    # # 페이지네이션 적용
    # paginator = CustomPagination()
    # paginated_data = paginator.paginate_queryset(item_list, request)

    # return paginator.get_paginated_response(paginated_data)


@api_view(["GET"])
def like_games(request, user_id):
    try:
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except get_user_model().DoesNotExist:
        return std_response(
            message="회원정보가 존재하지 않습니다.",
            status="error",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_404_NOT_FOUND
        )
    like_games = Game.objects.filter(likes__user=user, is_visible=True, register_state=1)
    if not like_games.exists():
        return std_response(
            data={},
            message=f"{request.user}가 즐겨찾기한 게임이 없습니다.",
            status="success",
            status_code=status.HTTP_204_NO_CONTENT
        )

    # 페이지네이션 적용
    paginator = CustomPagination()
    paginated_data = paginator.paginate_queryset(like_games, request)
    
    # 시리얼라이저 적용
    serializer = GameListSerializer(paginated_data, many=True, context={'user': user})
    data = paginator.get_paginated_response(serializer.data).data
    
    # 리턴
    return std_response(
        data=data["results"],
        status="success",
        pagination={
            "count": data["count"],
            "next": data["next"],
            "previous": data["previous"]
        },
        status_code=status.HTTP_200_OK
    )
    
    # item_list = list()
    # for item in like_games:
    #     game = item.game  # Like 인스턴스의 game 필드를 통해 Game 객체에 접근
    #     category_list = list(game.category.values_list('name', flat=True))
    #     chip_list = list(game.chip.values_list('name', flat=True))
    #     item_list.append({
    #         "game_pk": game.pk,
    #         "title": game.title,
    #         "maker_info": {
    #             "pk": game.maker.pk,
    #             "nickname": game.maker.nickname,
    #         },
    #         "thumbnail": game.thumbnail.url if game.thumbnail else None,
    #         "register_state": game.register_state,
    #         "created_at": game.created_at,
    #         "category_name": category_list,
    #         "chip_list": chip_list,
    #         "star": game.star,
    #         "review_cnt": game.review_cnt
    #     })

    # # 페이지네이션 적용
    # paginator = CustomPagination()
    # paginated_data = paginator.paginate_queryset(item_list, request)

    # return paginator.get_paginated_response(paginated_data)


# 2024-12-23 유저 페이지 게임팩 API 삭제
# 2024-12-30 유저 페이지 게임팩 API 복구
@api_view(["GET"])
def gamepacks(request, user_id):
    try:
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except get_user_model().DoesNotExist:
        return std_response(
            message="회원정보가 존재하지 않습니다.",
            status="error",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_404_NOT_FOUND
        )
    # 대상 일치 여부 확인
    if user != request.user:
        return std_response(
            message="유저 본인의 유저 페이지가 아니므로 데이터를 불러올 수 없습니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # 게임팩 세팅
    # 1. 즐겨찾기한 게임
    liked_games = Game.objects.filter(likes__user=user, is_visible=True, register_state=1).order_by('-created_at')[:4]
    # 2. 관심 있는 카테고리의 게임 가져오기
    interested_categories = user.game_category.all()
    category_games = Game.objects.filter(
        category__in=interested_categories,
        is_visible=True,
        register_state=1
    ).exclude(likes__user=user).distinct().order_by('-star','-created_at')
    # 좋아요한 게임과 최근 플레이한 게임을 조합하여 최대 4개의 게임으로 구성
    liked_games_count = liked_games.count()
    if liked_games_count < 4:
        additional_category_games = category_games[:4 - liked_games_count]
        combined_games = list(liked_games) + list(additional_category_games)
    else:
        combined_games = list(liked_games)  # 좋아요한 게임만으로 4개가 이미 채워짐
    
    # 리턴
    if combined_games:
        serializer = GameListSerializer(combined_games, many=True, context={'user': user})
        return std_response(
            data=serializer.data,
            status="success",
            status_code=status.HTTP_200_OK
        )
    else:
        latest_games=list(Game.objects.filter(is_visible=True, register_state=1).order_by('-created_at')[:4])
        serializer = GameListSerializer(latest_games, many=True, context={'user': user})
        return std_response(
            data=serializer.data,
            status="success",
            status_code=status.HTTP_200_OK
        )


@api_view(["GET"])
def recently_played_games(request, user_id):
    try:
        user = get_user_model().objects.get(pk=user_id, is_active=True)
    except get_user_model().DoesNotExist:
        return std_response(
            message="회원정보가 존재하지 않습니다.",
            status="error",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_404_NOT_FOUND
        )
    # 대상 일치 여부 확인
    if user != request.user:
        return std_response(
            message="유저 본인의 유저 페이지가 아니므로 데이터를 불러올 수 없습니다.",
            status="fail",
            error_code="SERVER_FAIL",
            status_code=status.HTTP_403_FORBIDDEN
        )
    
    # 최근 플레이한 게임
    recently_played_games = Game.objects.filter(is_visible=True, register_state=1, totalplaytime__user=user).order_by('-totalplaytime__latest_at').distinct()

    # 리턴
    if recently_played_games:
        # 페이지네이션 적용
        paginator = CustomPagination()
        paginated_data = paginator.paginate_queryset(recently_played_games, request)
        serializer = GameListSerializer(paginated_data, many=True, context={'user': user})
        data = paginator.get_paginated_response(serializer.data).data
        return std_response(
            data=data["results"],
            status="success",
            pagination={
                "count": data["count"],
                "next": data["next"],
                "previous": data["previous"]
            },
            status_code=status.HTTP_200_OK
        )
    else:
        return std_response(
            data={},
            message="최근 플레이한 게임이 존재하지 않습니다.",
            status="success",
            status_code=status.HTTP_204_NO_CONTENT
        )


# ---------- Web---------- #
# def profile_page(request, user_pk):
#     return render(request, 'users/profile_page.html')