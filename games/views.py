import re
import os
import zipfile

from django.core.files.storage import FileSystemStorage
from django.http import FileResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Avg, Q
from django.db.models.functions import Round

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny  # 로그인 인증토큰
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import permission_classes

from .models import (
    Game,
    Like,
    View,
    Review,
    Screenshot,
    GameCategory,
    ReviewsLike,
    PlayLog,
    TotalPlayTime,
)
from accounts.models import BotCnt
from .serializers import (
    GameListSerializer,
    GameDetailSerializer,
    ReviewSerializer,
    ScreenshotSerializer,
    CategorySerailizer,
)

from django.conf import settings
from openai import OpenAI
from django.utils import timezone
from datetime import timedelta
from spartagames.pagination import CustomPagination
import random

class GameListAPIView(APIView):
    """
    포스트일 때 로그인 인증을 위한 함수
    """

    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == 'post':  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    """
    게임 목록 조회
    """

    def get(self, request):
        order = request.query_params.get('order')
        diff_time = timezone.now() - timedelta(hours=3)
        categories = list(GameCategory.objects.all().values_list('name',flat=True))
        if not categories:
            return Response({"message": "카테고리가 존재하지 않는다. 카테고리 생성이 필요하다"}, status=status.HTTP_404_NOT_FOUND)
        if len(categories) < 3:
            return Response({"message": "카테고리가 2개 이하입니다. 카테고리가 최소 3개 필요합니다."}, status=status.HTTP_404_NOT_FOUND)
        selected_categories = random.sample(categories, 3)
        
        rand1 = Game.objects.filter(is_visible=True, register_state=1,category__name=selected_categories[0])
        rand2 = Game.objects.filter(is_visible=True, register_state=1,category__name=selected_categories[1])
        rand3 = Game.objects.filter(is_visible=True, register_state=1,category__name=selected_categories[2])
        favorites = Game.objects.filter(chip="1",is_visible=True, register_state=1)
        recent_games = Game.objects.filter(created_at__gte=diff_time, is_visible=True, register_state=1)

        # 유저 존재 시 my_game_pack 추가
        my_game_pack = None
        if request.user.is_authenticated:
            # 1. 즐겨찾기한 게임
            liked_games = Game.objects.filter(likes__user=request.user, is_visible=True, register_state=1).order_by('-created_at')[:4]
            # 2. 최근 플레이한 게임
            recently_played_games = Game.objects.filter(is_visible=True, register_state=1,totalplaytime__user=request.user).order_by('-totalplaytime__latest_at').distinct()
            
            # 좋아요한 게임과 최근 플레이한 게임을 조합하여 최대 4개의 게임으로 구성
            liked_games_count = liked_games.count()
            if liked_games_count < 4:
                additional_recent_games = recently_played_games[:4 - liked_games_count]
                combined_games = list(liked_games) + list(additional_recent_games)
            else:
                combined_games = liked_games  # 좋아요한 게임만으로 4개가 이미 채워짐

            # my_game_pack 설정
            if combined_games:
                my_game_pack = GameListSerializer(combined_games, many=True, context={'user': request.user}).data
            else:
                my_game_pack = [{"message": "게임이 없습니다."}]
        else:
            my_game_pack = [{"message": "사용자가 인증되지 않았습니다."}]

        # 추가 옵션 정렬
        """ if order == 'new':
            rows = rows.order_by('-created_at')
        elif order == 'view':
            rows = rows.order_by('-view_cnt')
        elif order == 'star':
            rows = rows.order_by('-star')
        else:
            rows = rows.order_by('-created_at') """

        # 시리얼라이저 및 데이터 확인
        serializer = GameListSerializer(rand1, many=True, context={'user': request.user})
        serializer2 = GameListSerializer(rand2, many=True, context={'user': request.user})
        serializer3 = GameListSerializer(rand3, many=True, context={'user': request.user})
        favorite_serializer = GameListSerializer(favorites, many=True, context={'user': request.user}).data if favorites.exists() else []
        recent_serializer = GameListSerializer(recent_games, many=True, context={'user': request.user}).data if recent_games.exists() else []

        # 응답 데이터 구성
        data = {
            "rand1": {
                "category_name": selected_categories[0],
                "game_list": serializer.data if rand1.exists() else []
            },
            "rand2": {
                "category_name": selected_categories[1],
                "game_list": serializer2.data if rand2.exists() else []
            },
            "rand3": {
                "category_name": selected_categories[2],
                "game_list": serializer3.data if rand3.exists() else []
            },
            "trending_games": favorite_serializer,
            "recent": recent_serializer,
        }
        if request.user.is_authenticated:
            data["my_game_pack"] = my_game_pack
        return Response(data, status=status.HTTP_200_OK)

    """
    게임 등록
    """

    def post(self, request):
        # 필수 항목 확인
        required_fields = ["title", "category", "content", "gamefile"]
        missing_fields = [field for field in required_fields if not request.data.get(field)]

        # 누락된 필수 항목이 있을 경우 에러 메시지 반환
        if missing_fields:
            return Response(
                {"error": f"필수 항목이 누락되었습니다: {', '.join(missing_fields)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Game model에 우선 저장
        game = Game.objects.create(
            title=request.data.get('title'),
            thumbnail=request.FILES.get('thumbnail'),
            youtube_url=request.data.get('youtube_url'),
            maker=request.user,  # FE 확인필요
            content=request.data.get('content'),
            gamefile=request.FILES.get('gamefile'),
            base_control=request.data.get('base_control'),
            release_note=request.data.get('release_note'),
            star=0,
            review_cnt=0,
        )

        # 카테고리 저장
        category_data = request.data.get('category')
        if category_data:
            invalid_categories = []
            for item in category_data.split(','):
                try:
                    category = GameCategory.objects.get(name=item)
                    game.category.add(category)
                except GameCategory.DoesNotExist:
                    invalid_categories.append(item)
            
            # 존재하지 않는 카테고리가 있는 경우 오류 메시지 반환
            if invalid_categories:
                return Response(
                    {"message": f"다음 카테고리는 존재하지 않습니다: {', '.join(invalid_categories)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # 이후 Screenshot model에 저장
        screenshots = list()
        for item in request.FILES.getlist("screenshots"):
            screenshot = Screenshot.objects.create(
                src=item,
                game=game
            )
            screenshots.append(screenshot.src.url)

        return Response({"message": "게임업로드 성공했습니다"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([AllowAny])  # 인증이 필요할 경우 IsAuthenticated로 변경 가능
def game_list_search(request):
    category_q = request.query_params.get('category-q')
    game_q = request.query_params.get('game-q')
    maker_q = request.query_params.get('maker-q')
    gm_q = request.query_params.get('gm-q')
    order = request.query_params.get('order')

    # 누적 조건 필터링을 위한 Q 객체 초기화
    query = Q(is_visible=True, register_state=1)

    # 검색 옵션에 따라 Q 객체에 조건 추가
    search_tags = []
    if category_q:
        query &= Q(category__name=category_q)
        search_tags.append(f"카테고리: {category_q}")
    if game_q:
        query &= Q(title__icontains=game_q)
        search_tags.append(f"게임 이름: {game_q}")
    if maker_q:
        query &= Q(maker__nickname__icontains=maker_q)
        search_tags.append(f"제작자: {maker_q}")
    if gm_q:
        query &= Q(title__icontains=gm_q) | Q(maker__nickname__icontains=gm_q)
        search_tags.append(f"일반 검색: {gm_q}")

    # 누적된 조건으로 게임 필터링
    rows = Game.objects.filter(query)

    # 결과가 없는 경우 메시지 반환
    if not rows.exists():
        search_summary = ", ".join(search_tags) if search_tags else "모든 게임"
        return Response({"message": f"해당 검색 [{search_summary}]에 맞는 게임이 없습니다."}, status=404)

    # 정렬 옵션
    if order == 'new':
        rows = rows.order_by('-created_at')
    elif order == 'view':
        rows = rows.order_by('-view_cnt')
    elif order == 'star':
        rows = rows.order_by('-star')
    else:
        rows = rows.order_by('-created_at')

    # 좋아요 게임 목록 가져오기
    favorite_games = []
    if request.user.is_authenticated:
        favorite_games = rows.filter(likes__user=request.user)

    # 결과가 없는 경우 메시지 반환
    if not rows.exists() and not favorite_games:
        search_summary = ", ".join(search_tags) if search_tags else "모든 게임"
        return Response({"message": f"해당 검색 [{search_summary}]에 맞는 게임이 없습니다."}, status=404)
    
    # 페이지네이션
    paginator = CustomPagination()
    result = paginator.paginate_queryset(rows, request)
    serializer = GameListSerializer(result, many=True,context={'user': request.user})
    
    # 좋아요한 게임 직렬화
    favorite_serializer = GameListSerializer(favorite_games, many=True,context={'user': request.user})

    # 응답 데이터에 좋아요 게임 포함
    response_data = {
        "results": serializer.data,
        "favorite_games": favorite_serializer.data if request.user.is_authenticated else []
    }

    return paginator.get_paginated_response(response_data)

class GameDetailAPIView(APIView):
    """
    포스트일 때 로그인 인증을 위한 함수
    """

    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == ('put' or 'delete'):  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    def get_object(self, game_pk):
        return get_object_or_404(Game, pk=game_pk, is_visible=True)

    """
    게임 상세 조회
    """

    def get(self, request, game_pk):
        game = self.get_object(game_pk)

        serializer = GameDetailSerializer(game)
        # data에 serializer.data를 assignment
        # serializer.data의 리턴값인 ReturnDict는 불변객체이다
        data = serializer.data

        screenshots = Screenshot.objects.filter(game_id=game_pk)
        screenshot_serializer = ScreenshotSerializer(screenshots, many=True)

        categories = game.category.all()
        category_serializer = CategorySerailizer(categories, many=True)

        data["screenshot"] = screenshot_serializer.data
        data['category'] = category_serializer.data

        return Response(data, status=status.HTTP_200_OK)

    """
    게임 수정
    """

    def put(self, request, game_pk):
        game = self.get_object(game_pk)

        # 작성한 유저이거나 관리자일 경우 동작함
        if game.maker == request.user or request.user.is_staff == True:
            if request.FILES.get("gamefile"):  # 게임파일을 교체할 경우 검수페이지로 이동
                game.register_state = 0
                game.gamefile = request.FILES.get("gamefile")
            game.title = request.data.get("title", game.title)
            game.thumbnail = request.FILES.get("thumbnail", '')
            game.youtube_url = request.data.get(
                "youtube_url", game.youtube_url)
            game.content = request.data.get("content", game.content)
            game.base_control = request.data.get(
                'base_control', game.base_control),
            game.release_note = request.data.get(
                'release_note', game.release_note),
            game.save()

            category_data = request.data.get('category')
            if category_data is not None:  # 태그가 바뀔 경우 기존 태그를 초기화, 신규 태그로 교체
                game.category.clear()
                categories = [GameCategory.objects.get_or_create(name=item.strip())[
                    0] for item in category_data.split(',') if item.strip()]
                game.category.set(categories)

            # 기존 데이터 삭제
            pre_screenshots_data = Screenshot.objects.filter(game=game)
            pre_screenshots_data.delete()

            # 받아온 스크린샷으로 교체
            if request.data.get('screenshots'):
                for item in request.FILES.getlist("screenshots"):
                    game.screenshots.create(src=item)

            return Response({"messege": "수정이 완료됐습니다"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "작성자가 아닙니다"}, status=status.HTTP_400_BAD_REQUEST)

    """
    게임 삭제
    """

    def delete(self, request, game_pk):
        game = self.get_object(game_pk)

        # 작성한 유저이거나 관리자일 경우 동작함
        if game.maker == request.user or request.user.is_staff == True:
            game.is_visible = False
            game.save()
            return Response({"message": "삭제를 완료했습니다"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "작성자가 아닙니다"}, status=status.HTTP_400_BAD_REQUEST)


class GameLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, game_pk):
        game = get_object_or_404(Game, pk=game_pk)
        like_instance = Like.objects.filter(user=request.user, game=game).first()
        if like_instance:
            # 수정
            like_instance.delete()
            return Response({'message': "즐겨찾기 취소"}, status=status.HTTP_200_OK)
        else:
            # 생성
            Like.objects.create(user=request.user, game=game)
            return Response({'message': "즐겨찾기"}, status=status.HTTP_200_OK)


# class GameStarAPIView(APIView):
#     permission_classes = [IsAuthenticated]

#     def post(self, request, game_pk):
#         star_list = [1,2,3,4,5]
#         star = int(request.data['star'])
#         if star not in star_list:
#             star = 5
#         game = get_object_or_404(Game, pk=game_pk)
#         if game.stars.filter(user=request.user).exists():
#             # 수정
#             game.stars.filter(user=request.user).update(
#                 star=star)
#         else:
#             # 생성
#             Star.objects.create(
#                 star=star,
#                 user=request.user,
#                 game=game,
#             )
#         star_values=[item['star'] for item in game.stars.values()]
#         average_star = round(sum(star_values) / len(star_values),1)
#         return Response({"res":"ok","avg_star":average_star}, status=status.HTTP_200_OK)


class ReviewAPIView(APIView):
    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == 'post':  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    def get(self, request, game_pk):
        reviews = Review.objects.all().filter(game=game_pk, is_visible=True)

        if not reviews.exists():
            return Response({"message": "해당 게임에 리뷰가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 로그인한 경우
        if request.user.is_authenticated:
            reviews_serializer = ReviewSerializer(
                reviews, many=True, context={'user': request.user})
            my_review = reviews.filter(author__pk=request.user.pk).first()
            my_review_serializer = ReviewSerializer(
                my_review, context={'user': request.user})
            return Response(
                {
                    "my_review": my_review_serializer.data,
                    "all_reviews": reviews_serializer.data
                },
                status=status.HTTP_200_OK
            )
        # 로그인하지 않은 경우
        else:
            reviews_serializer = ReviewSerializer(reviews, many=True)
            return Response(
                {
                    "all_reviews": reviews_serializer.data
                },
                status=status.HTTP_200_OK
            )

    def post(self, request, game_pk):
        game = get_object_or_404(Game, pk=game_pk)  # game 객체를 올바르게 설정

        # 이미 리뷰를 작성한 사용자인 경우 등록 거부
        if game.reviews.filter(author__pk=request.user.pk, is_visible=True).exists():
            return Response({"message": "이미 리뷰를 등록한 사용자입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 별점 계산
        game.star = game.star + \
            ((request.data.get('star')-game.star)/(game.review_cnt+1))
        game.review_cnt = game.review_cnt+1
        game.save()

        serializer = ReviewSerializer(
            data=request.data, context={'user': request.user})
        if serializer.is_valid(raise_exception=True):
            serializer.save(author=request.user, game=game)  # 데이터베이스에 저장
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ReviewDetailAPIView(APIView):
    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == ('put' or 'delete'):  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    def get(self, request, review_id):
        try:
        # 리뷰가 존재하고, is_visible이 True인 경우만 가져옴
            review = Review.objects.get(pk=review_id, is_visible=True)
        except Review.DoesNotExist:
            # 리뷰가 존재하지 않으면 404 응답과 함께 메시지 반환
            return Response({"message": "상세 평가 기록이 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        serializer = ReviewSerializer(review, context={'user': request.user})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, review_id):
        try:
            # 리뷰가 존재하고, is_visible이 True인 경우에만 가져옴
            review = get_object_or_404(Review, pk=review_id, is_visible=True)
        except Http404:
            # 리뷰가 없을 경우 사용자에게 메시지와 함께 404 응답 반환
            return Response({"message": "리뷰가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 작성한 유저이거나 관리자일 경우 동작함
        if request.user == review.author or request.user.is_staff == True:
            game_pk = request.data.get('game_pk')
            game = get_object_or_404(Game, pk=game_pk)  # game 객체를 올바르게 설정
            game.star = game.star + \
                ((request.data.get('star')-request.data.get('pre_star'))/(game.review_cnt))
            game.save()
            serializer = ReviewSerializer(
                review, data=request.data, partial=True, context={'user': request.user})
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"error": "작성자가 아닙니다"}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, review_id):
        try:
            # 리뷰가 존재하고, is_visible이 True인 경우에만 가져옴
            review = get_object_or_404(Review, pk=review_id, is_visible=True)
        except Http404:
            # 리뷰가 없을 경우 사용자에게 메시지와 함께 404 응답 반환
            return Response({"message": "리뷰가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 작성한 유저이거나 관리자일 경우 동작함
        if request.user == review.author or request.user.is_staff == True:
            game_pk = request.data.get('game_pk')
            game = get_object_or_404(Game, pk=game_pk)  # game 객체를 올바르게 설정
            if game.review_cnt > 1:
                game.star = game.star + \
                    ((game.star-review.star)/(game.review_cnt-1))
            else:
                game.star = 0
            game.review_cnt = game.review_cnt-1
            game.save()
            review.is_visible = False
            review.save()
            return Response({"message": "삭제를 완료했습니다"}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "작성자가 아닙니다"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def toggle_review_like(request, review_id):
    """
    리뷰에 좋아요/싫어요 동작
    """
    user = request.user
    try:
        # 리뷰가 존재하고, is_visible이 True인 경우에만 가져옴
        review = get_object_or_404(Review, pk=review_id, is_visible=True)
    except Http404:
        # 리뷰가 없을 경우 사용자에게 메시지와 함께 404 응답 반환
        return Response({"message": "리뷰가 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)
    # ReviewsLike 객체를 가져오거나 새로 생성
    # get_or_create 리턴: review_like - ReviewsLike 객체(행), _ - 행 생성 여부
    review_like, _ = ReviewsLike.objects.get_or_create(
        user=user, review=review)

    # 요청에서 받은 'action'에 따라 상태 변경
    action = request.data.get('action', None)
    if action == 'like':
        if review_like.is_like != 1:  # 현재 상태가 'like'가 아니면 'like'로 변경
            review_like.is_like = 1
        else:
            # 이미 'like' 상태일 경우 'no state'로 전환
            review_like.is_like = 0
    elif action == 'dislike':
        if review_like.is_like != 2:  # 현재 상태가 'dislike'가 아니면 'dislike'로 변경
            review_like.is_like = 2
        else:
            # 이미 'dislike' 상태일 경우 'no state'로 전환
            review_like.is_like = 0

    review_like.save()  # 변경 사항 저장
    return Response({"message": f"리뷰(id: {review_id})에 {review_like.is_like} 동작을 수행했습니다."}, status=status.HTTP_200_OK)


class CategoryAPIView(APIView):
    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == ('post' or 'delete'):  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions
    
    def get(self, request):
        categories = GameCategory.objects.all()
        serializer = CategorySerailizer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.is_staff is False:
            return Response({"error": "권한이 없습니다"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CategorySerailizer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            category=request.data.get("name")
            return Response({"message": f"태그({category})를 추가했습니다"}, status=status.HTTP_200_OK)

    def delete(self, request):
        if request.user.is_staff is False:
            return Response({"error": "권한이 없습니다"}, status=status.HTTP_400_BAD_REQUEST)
        category = get_object_or_404(GameCategory, pk=request.data['pk'])
        category.delete()
        return Response({"message": "삭제를 완료했습니다"}, status=status.HTTP_200_OK)


class GamePlaytimeAPIView(APIView):
    def get(self, request, game_pk):
        # 로그인 여부 확인
        if request.user.is_authenticated is False:
            return Response({"error": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)
        if Game.objects.filter(pk=game_pk, is_visible=True).exists():
            playtime = PlayLog.objects.create(
                user=request.user,
                game=get_object_or_404(Game, pk=game_pk, is_visible=True),
                start_at=timezone.now()  # 현재 시간으로 start_time
            )
            playtime_pk = playtime.pk
            return Response({"message": "게임 플레이 시작시간 기록을 성공했습니다.", "playtime_pk":playtime_pk}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "게임이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, game_pk):
        # 로그인 여부 확인
        if request.user.is_authenticated is False:
            return Response({"error": "로그인이 필요합니다."}, status=status.HTTP_401_UNAUTHORIZED)
        if Game.objects.filter(pk=game_pk, is_visible=True).exists():
            game=get_object_or_404(Game, pk=game_pk, is_visible=True)
            playlog = get_object_or_404(PlayLog, pk=request.data.get("playtime_pk"))
            totalplaytime,_ = TotalPlayTime.objects.get_or_create(user=request.user, game=game)

            playlog.end_at = timezone.now()  # 현재 시간으로 end_time
            totalplaytime.latest_at = timezone.now()

            totaltime = (playlog.end_at - playlog.start_at).total_seconds()
            playlog.playtime = totaltime  # playtime_seconds로 playtime_seconds 계산
            totalplaytime.totaltime = totalplaytime.totaltime + totaltime

            playlog.save()
            totalplaytime.save()
            return Response({"message": "게임 플레이 종료시간 기록을 성공했습니다.", 
                            "start_time":playlog.start_at,
                            "end_time":playlog.end_at,
                            "playtime": playlog.playtime,
                            "totalplaytime":totalplaytime.totaltime}
                            , status=status.HTTP_200_OK)
        else:
            return Response({"error": "게임이 존재하지 않습니다."}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
def game_register(request, game_pk):
    # 관리자 여부 확인
    if request.user.is_staff is False:
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

    # game_pk에 해당하는 row 가져오기 (게시 중인 상태이면서 '등록 중' 상태)
    row = get_object_or_404(
        Game, pk=game_pk, is_visible=True, register_state=0)

    # gamefile 필드에 저장한 경로값을 'path' 변수에 저장
    path = row.gamefile.url

    # ~/<업로드시각>_<압축파일명>.zip 에서 '<업로드시각>_<압축파일명>' 추출
    game_folder = path.split('/')[-1].split('.')[0]

    # 게임 폴더 경로(압축을 풀 경로): './media/games/<업로드시각>_<압축파일명>'
    game_folder_path = f"./media/games/{game_folder}"

    # index.html 우선 압축 해제
    zipfile.ZipFile(f"./{path}").extract("index.html", game_folder_path)

    """
    index.html 내용 수정
    <link> 태그 href 값 수정 (line: 7, 8)
    var buildUrl 변수 값 수정 (line: 59)
    
    new_lines: 덮어쓸 내용 저장
    is_check_build: Build 키워드 찾은 후 True로 변경 (이후 라인에서 Build 찾는 것을 피하기 위함)
    """

    new_lines = str()
    is_check_build = False

    # 덮어쓸 내용 담기
    with open(f"{game_folder_path}/index.html", 'r') as f:
        for line in f.readlines():
            if line.find('link') > -1:
                cursor = line.find('TemplateData')
                new_lines += line[:cursor] + \
                    f'/media/games/{game_folder}/' + line[cursor:]
            elif line.find('buildUrl') > -1 and not is_check_build:
                is_check_build = True
                cursor = line.find('Build')
                new_lines += line[:cursor] + \
                    f'/media/games/{game_folder}/' + line[cursor:]
            else:
                new_lines += line
    # 추가할 JavaScript 코드 (iframe의 width, height 조절을 위해 추가함)
    additional_script = """
    <script>
      function sendSizeToParent() {
        var canvas = document.querySelector("#unity-canvas");
        var width = canvas.clientWidth;
        var height = canvas.clientHeight;
        window.parent.postMessage({ width: width, height: height }, '*');
      }

      window.addEventListener('resize', sendSizeToParent);
      window.addEventListener('load', sendSizeToParent);
    </script>
    """
    # CSS 스타일 추가 (body 태그와 unity-container에 overflow: hidden 추가)
    new_lines = new_lines.replace(
        '<body', '<body style="margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;"')
    new_lines = new_lines.replace(
        '<div id="unity-container"', '<div id="unity-container" style="width: 100%; height: 100%; overflow: hidden;"')

    # </body> 태그 전에 추가할 스크립트 삽입
    body_close_category_index = new_lines.find('</body>')
    new_lines = new_lines[:body_close_category_index] + \
        additional_script + new_lines[body_close_category_index:]

    # 덮어쓰기
    with open(f'{game_folder_path}/index.html', 'w') as f:
        f.write(new_lines)

    # index.html 외 다른 파일들 압축 해제
    zipfile.ZipFile(f"./{path}").extractall(
        path=game_folder_path,
        members=[item for item in zipfile.ZipFile(
            f"./{path}").namelist() if item != "index.html"]
    )

    # 게임 폴더 경로를 저장하고, 등록 상태 1로 변경(등록 성공)
    row.gamepath = game_folder_path[1:]
    row.register_state = 1
    row.save()

    # 알맞은 HTTP Response 리턴
    # return Response({"message": f"등록을 성공했습니다. (게시물 id: {game_pk})"}, status=status.HTTP_200_OK)

    # 2024-10-31 추가. return 수정 필요 (redirect -> response)
    # return redirect("games:admin_list")
    return Response({"message": "게임이 등록되었습니다."}, status=status.HTTP_200_OK)


@api_view(['POST'])
def game_register_deny(request, game_pk):
    # 관리자 여부 확인
    if request.user.is_staff is False:
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

    row = get_object_or_404(
        Game, pk=game_pk, is_visible=True, register_state=0)
    row.register_state = 2
    row.save()

    # 2024-10-31 추가. return 수정 필요 (redirect -> response)
    # return redirect("games:admin_list")
    return Response({"message": "게임 등록을 거부했습니다."}, status=status.HTTP_200_OK)


@api_view(['POST'])
def game_dzip(request, game_pk):
    # 관리자 여부 확인
    if request.user.is_staff is False:
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

    row = get_object_or_404(
        Game, pk=game_pk, register_state=0, is_visible=True)
    zip_path = row.gamefile.url
    zip_folder_path = "./media/zips/"
    zip_name = os.path.basename(zip_path)

    # FileSystemStorage 인스턴스 생성
    # zip_folder_path에 대해 FILE_UPLOAD_PERMISSIONS = 0o644 권한 설정
    # 파일을 어디서 가져오는지를 정하는 것으로 보면 됨
    # 디폴트 값: '/media/' 에서 가져옴
    fs = FileSystemStorage(zip_folder_path)

    # FileResponse 인스턴스 생성
    # FILE_UPLOAD_PERMISSIONS 권한을 가진 상태로 zip_folder_path 경로 내의 zip_name 파일에 'rb' 모드로 접근
    # content_type 으로 zip 파일임을 명시
    response = FileResponse(fs.open(zip_name, 'rb'),
                            content_type='application/zip')

    # 'Content-Disposition' value 값(HTTP Response 헤더값)을 설정
    # 파일 이름을 zip_name 으로 다운로드 폴더에 받겠다는 뜻
    response['Content-Disposition'] = f'attachment; filename="{zip_name}"'

    # FileResponse 객체를 리턴
    return response


CLIENT = OpenAI(api_key=settings.OPEN_API_KEY)
MAX_USES_PER_DAY = 10  # 하루 당 질문 10개로 제한기준

# chatbot API


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def ChatbotAPIView(request):
    user = request.user
    today = timezone.now().date()

    usage, created = BotCnt.objects.get_or_create(user=user, date=today)

    if usage.count >= MAX_USES_PER_DAY:
        return Response({"error": "Daily usage limit reached"}, status=status.HTTP_400_BAD_REQUEST)

    usage.count += 1
    usage.save()

    input_data = request.data.get('input_data')
    categorylist = list(GameCategory.objects.values_list('name', flat=True))

    # GPT API와 통신을 통해 답장을 받아온다.(아래 형식을 따라야함)(추가 옵션은 문서를 참고)
    instructions = f"""
    내가 제한한 카테고리 목록 : {categorylist} 여기서만 이야기를 해줘, 이외에는 말하지마
    받은 내용을 요약해서 내가 제한한 목록에서 제일 관련 있는 항목 한 개를 골라줘
    결과 형식은 다른 말은 없이 꾸미지도 말고 딱! '카테고리:'라는 형식으로만 작성해줘
    결과에 특수문자, 이모티콘 붙이지마
    """
    completion = CLIENT.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": instructions},
            {"role": "user", "content": f"받은 내용: {input_data}"},
        ],
    )

    # 응답받은 데이터 처리
    gpt_response = completion.choices[0].message.content
    about_category = gpt_response.split('태그:')[1]
    about_category = re.sub(
        '[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', '', about_category)
    about_category = about_category.strip()
    uncategorylist = ['없음', '']
    if about_category in uncategorylist:
        about_category = '없음'
    return Response({"category": about_category}, status=status.HTTP_200_OK)


# ---------- Web ---------- #


# # 게임 등록 Api 테스트용 페이지 렌더링
# def game_detail_view(request, game_pk):
#     return render(request, "games/game_detail.html", {'game_pk': game_pk})


# # 테스트용 base.html 렌더링
# def test_base_view(request):
#     return render(request, "base.html")


# # 테스트용 메인 페이지 렌더링
# def main_view(request):
#     return render(request, "games/main.html")


# # 테스트용 검색 페이지 렌더링
# def search_view(request):
#     # 쿼리스트링을 그대로 가져다가 '게임 목록 api' 호출
#     return render(request, "games/search.html")


# # 게임 검수용 페이지 뷰
# def admin_list(request):
#     rows = Game.objects.filter(is_visible=True, register_state=0)
#     return render(request, "games/admin_list.html", context={"rows": rows})


# def admin_category(request):
#     categories = GameCategory.objects.all()
#     return render(request, "games/admin_tags.html", context={"categories": categories})


# def game_create_view(request):
#     return render(request, "games/game_create.html")


# def game_update_view(request, game_pk):
#     return render(request, "games/game_update.html", {'game_pk': game_pk})


# def chatbot_view(request):
#     return render(request, "games/chatbot.html")
