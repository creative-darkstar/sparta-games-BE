import re

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from spartagames.pagination import CustomPagination
from games.models import (
    Game,
    GameCategory,
)
from games.serializers import GameListSerializer


# ---------- API---------- #
class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 유효성 검사 정규식 패턴
    EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9+-_.]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    NICKNAME_PATTERN = re.compile(r"^[a-zA-Z0-9]{8,30}$")

    def get(self, request, user_pk):
        user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)
        profile_image = user.image.url if user.image else ''
        categories = list(user.game_category.values_list('name', flat=True))
        if len(categories) > 3:
            return Response(
                {"error_message": "선택한 관심 카테고리가 최대 개수를 초과했습니다. 다시 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response({
            "user_pk": user_pk,
            "email": user.email,
            "nickname": user.nickname,
            "login_type": user.login_type,
            "profile_image": profile_image,
            "is_staff": user.is_staff,
            "is_maker": user.is_maker,
            "introduce": user.introduce,
            "game_category": categories,
            "user_tech": user.user_tech
        }, status=status.HTTP_200_OK)

    def put(self, request, user_pk):
        # check_password = self.request.data.get("password")
        user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)

        # 현재 로그인한 유저와 수정 대상 회원이 일치하는지 확인
        if request.user.id != user.pk:
            return Response(status=status.HTTP_403_FORBIDDEN)

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
            return Response(
                {"error_message": "올바른 nickname을 입력해주세요."},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif get_user_model().objects.filter(nickname=nickname).exists():
            return Response(
                {"error_message": "이미 존재하는 nickname입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 관심 게임 카테고리
        categories = request.data.get("game_category", [])
        if categories:
            game_categories = GameCategory.objects.filter(name__in=categories)
            if not game_categories:
                return Response(
                    {"error_message": "올바른 game category를 입력해주세요."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            user.game_category.set(game_categories)
        else:
            categories = list(user.game_category.values_list('pk', flat=True))
        
        # 관심 기술분야
        user.user_tech = self.request.data.get('user_tech', user.user_tech)
        
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
        user.image = self.request.data.get('image', user.image)
        # 유저 / 메이커 구분
        user.is_maker = self.request.data.get('is_maker', user.is_maker)
        # 자기소개
        user.introduce = self.request.data.get('introduce', user.introduce)
        
        # 변경한 데이터 저장
        user.save()

        categories = list(user.game_category.values_list('pk', flat=True))
        return Response(
            {
                "message": "회원 정보 수정 완료",
                "data": {
                    "nickname": user.nickname,
                    "profile_image": user.image.url if user.image else "이미지 없음",
                    "is_staff": user.is_staff,
                    "is_maker": user.is_maker,
                    "introduce": user.introduce,
                    "game_category": categories,
                    "user_tech": user.user_tech
                }
            },
            status=status.HTTP_202_ACCEPTED
        )

    def delete(self, request, user_pk):
        # check_password = self.request.data.get("password")
        user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)

        # 현재 로그인한 유저와 탈퇴 대상 회원이 일치하는지 확인
        if request.user.id != user.pk:
            return Response(status=status.HTTP_403_FORBIDDEN)

        # # 유저 비밀번호가 일치하지 않으면
        # if user.check_password(check_password) is False:
        #     return Response(
        #         {"message": "비밀번호가 일치하지 않습니다."},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )

        # 유저 비밀번호가 일치한다면
        user.is_active = False
        user.save()
        return Response(
            {
                "message": f"회원 탈퇴 완료 (회원 아이디: {user.nickname})"
            },
            status=status.HTTP_200_OK
        )


@api_view(["GET"])
def user_tech_list(request):
    techs = get_user_model().USER_TECH_CHOICES
    return Response(techs, status=status.HTTP_200_OK)


@api_view(["GET"])
def check_nickname(request):
    # 유효성 검사 정규식 패턴
    NICKNAME_PATTERN = re.compile(r"^[a-zA-Z0-9]{8,30}$")

    nickname = request.data.get('nickname', None)
        
    # 닉네임이 유효하지 않거나 다른 유저의 이메일로 수정하려고 할 경우 error
    if not NICKNAME_PATTERN.match(nickname):
        return Response(
            {"error_message": "올바른 nickname을 입력해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )
    elif get_user_model().objects.filter(nickname=nickname).exists():
        return Response(
            {"error_message": "이미 존재하는 nickname입니다."},
            status=status.HTTP_400_BAD_REQUEST
        )
    else:
        return Response(
            {"message": "사용 가능한 닉네임입니다."},
            status=status.HTTP_200_OK
        )


@api_view(["PUT"])
def change_password(request, user_pk):
    # 유효성 검사 정규식 패턴
    PASSWORD_PATTERN = re.compile(r'^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[a-zA-Z]).{8,32}$')

    user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)

    check_password = request.data.get("password")
    new_password = request.data.get("new_password")
    new_password_check = request.data.get("new_password_check")

    # 현재 로그인한 유저와 비밀번호 수정 대상 회원이 일치하는지 확인
    if request.user.id != user.pk:
        return Response(status=status.HTTP_403_FORBIDDEN)

    # 유저 비밀번호가 일치하지 않으면
    if user.check_password(check_password) is False:
        return Response(
            {"message": "비밀번호가 일치하지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # new password 유효성 검사
    if not PASSWORD_PATTERN.match(new_password):
        return Response(
            {"error_message": "올바른 password와 password_check를 입력해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )
    elif not new_password == new_password_check:
        return Response(
            {"error_message": "동일한 password와 password_check를 입력해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 유저 비밀번호가 일치한다면
    user.set_password(new_password)
    user.save()
    return Response(
        {
            "message": f"비밀번호 수정 완료 (회원 아이디: {user.nickname})"
        },
        status=status.HTTP_202_ACCEPTED
    )


@api_view(["GET"])
def my_games(request, user_pk):
    user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)
    my_games = user.games.filter(is_visible=True).order_by('-created_at')
    if not my_games.exists():
        return Response(
            {"message": f"{request.user}가 제작한 게임이 없습니다."},
            status=status.HTTP_404_NOT_FOUND  # Not Found
        )

    # 대상 일치 여부 확인
    if user != request.user:
        my_games = my_games.filter(register_state=1)

    item_list = list()
    for item in my_games:
        category_list = list(item.category.values_list('name', flat=True))
        chip_list = list(item.chip.values_list('name', flat=True))
        item_list.append({
            "game_pk": item.pk,
            "title": item.title,
            "thumbnail": item.thumbnail.url if item.thumbnail else None,
            "register_state": item.register_state,
            "created_at": item.created_at,
            "category_list": category_list,
            "chip_list": chip_list,
            "star": item.star,
            "review_cnt": item.review_cnt
        })
    
    # 페이지네이션 적용
    paginator = CustomPagination()
    paginated_data = paginator.paginate_queryset(item_list, request)

    return paginator.get_paginated_response(paginated_data)


@api_view(["GET"])
def like_games(request, user_pk):
    user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)
    like_games = user.like_games.filter(game__is_visible=True, game__register_state=1)
    if not like_games.exists():
        return Response(
            {"message": f"{request.user}가 즐겨찾기한 게임이 없습니다."},
            status=status.HTTP_404_NOT_FOUND  # Not Found
        )

    item_list = list()
    for item in like_games:
        game = item.game  # Like 인스턴스의 game 필드를 통해 Game 객체에 접근
        category_list = list(game.category.values_list('name', flat=True))
        chip_list = list(game.chip.values_list('name', flat=True))
        item_list.append({
            "game_pk": game.pk,
            "title": game.title,
            "maker_info": {
                "pk": game.maker.pk,
                "nickname": game.maker.nickname,
            },
            "thumbnail": game.thumbnail.url if game.thumbnail else None,
            "register_state": game.register_state,
            "created_at": game.created_at,
            "category_list": category_list,
            "chip_list": chip_list,
            "star": game.star,
            "review_cnt": game.review_cnt
        })

    # 페이지네이션 적용
    paginator = CustomPagination()
    paginated_data = paginator.paginate_queryset(item_list, request)

    return paginator.get_paginated_response(paginated_data)


@api_view(["GET"])
def gamepacks(request, user_pk):
    user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)
    # 대상 일치 여부 확인
    if user != request.user:
        return Response({"message": "유저 본인의 유저 페이지가 아니므로 데이터를 불러올 수 없습니다."}, status=status.HTTP_200_OK)
    
    # 게임팩 세팅
    # 1. 즐겨찾기한 게임
    liked_games = Game.objects.filter(likes__user=user, is_visible=True, register_state=1).order_by('-created_at')[:4]
    # 2. 최근 플레이한 게임
    recently_played_games = Game.objects.filter(is_visible=True, register_state=1, totalplaytime__user=user).order_by('-totalplaytime__latest_at').distinct()
    
    # 좋아요한 게임과 최근 플레이한 게임을 조합하여 최대 4개의 게임으로 구성
    liked_games_count = liked_games.count()
    if liked_games_count < 4:
        additional_recent_games = recently_played_games[:4 - liked_games_count]
        combined_games = list(liked_games) + list(additional_recent_games)
    else:
        combined_games = liked_games  # 좋아요한 게임만으로 4개가 이미 채워짐

    # 리턴
    if combined_games:
        # 페이지네이션 적용
        paginator = CustomPagination()
        paginated_data = paginator.paginate_queryset(combined_games, request)
        serializer = GameListSerializer(paginated_data, many=True, context={'user': user})
        return paginator.get_paginated_response(serializer.data)
    else:
        return Response({"message": "게임팩 조건에 맞는 게임이 존재하지 않습니다."}, status=status.HTTP_200_OK)


@api_view(["GET"])
def recently_played_games(request, user_pk):
    user = get_object_or_404(get_user_model(), pk=user_pk, is_active=True)
    # 대상 일치 여부 확인
    if user != request.user:
        return Response({"message": "유저 본인의 유저 페이지가 아니므로 데이터를 불러올 수 없습니다."}, status=status.HTTP_200_OK)
    
    # 최근 플레이한 게임
    recently_played_games = Game.objects.filter(is_visible=True, register_state=1, totalplaytime__user=user).order_by('-totalplaytime__latest_at').distinct()

    # 리턴
    if recently_played_games:
        # 페이지네이션 적용
        paginator = CustomPagination()
        paginated_data = paginator.paginate_queryset(recently_played_games, request)
        serializer = GameListSerializer(paginated_data, many=True, context={'user': user})
        return paginator.get_paginated_response(serializer.data)
    else:
        return Response({"message": "최근 플레이한 게임이 존재하지 않습니다."}, status=status.HTTP_200_OK)


# ---------- Web---------- #
# def profile_page(request, user_pk):
#     return render(request, 'users/profile_page.html')