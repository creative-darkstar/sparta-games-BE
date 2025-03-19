import os
import re

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def validate_text_content(value):
    text_only = re.sub(r'<[^>]+>', '', value)  # HTML 태그 제거한 순수 텍스트
    tag_only = re.findall(r'<[^>]+>', value)   # HTML 태그 목록 추출

    text_length = len(text_only)
    tag_length = sum(len(tag) for tag in tag_only)

    # 순수 텍스트 10만 자 제한
    if text_length > 100000:    
        raise ValidationError('게시글이 너무 깁니다. 10만 글자 이하로 작성해주세요.')
    
    # HTML 포함 시 50만 자 제한
    if len(value) > 500000:
        raise ValidationError('게시글이 너무 깁니다.')

    # 태그 비율 70% 초과 시 차단
    if tag_length / len(value) > 0.7:
        raise ValidationError('HTML 태그가 지나치게 많습니다.')


class GameCategory(models.Model):
    name = models.CharField(max_length=50, unique=True)


class Chip(models.Model):
    name = models.CharField(max_length=50, unique=True)


class Game(models.Model):
    # media 폴더에 업로드할 게임 zip 파일명 변경 및 위치 설정
    def upload_to_func(instance, filename):
        time_data = timezone.now().strftime("%Y%m%d%H%M%S%f")
        file_name = os.path.splitext(filename)[0]
        extension = os.path.splitext(filename)[-1].lower()
        return "".join(["zips/", time_data, '_', file_name, extension,])

    title = models.CharField(max_length=100)
    thumbnail = models.ImageField(upload_to="images/thumbnail/")
    youtube_url = models.URLField(blank=True, null=True)
    maker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="games"
    )
    content = models.TextField(validators=[validate_text_content])
    gamefile = models.FileField(
        upload_to=upload_to_func
    )
    gamepath = models.CharField(blank=True, null=True, max_length=511)
    register_state = models.IntegerField(default=0)
    category = models.ManyToManyField(
        GameCategory, related_name="games"
    )
    chip = models.ManyToManyField(
        Chip, related_name="games"
    )
    is_visible = models.BooleanField(default=True)
    star = models.FloatField()
    review_cnt = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="like_games"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="likes"
    )
    created_at = models.DateTimeField(auto_now_add=True)


class View(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="view_games"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="views"
    )
    created_at = models.DateTimeField(auto_now_add=True)


class PlayLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playlog_of_games"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="playlog"
    )
    start_at = models.DateTimeField(null=True)
    end_at = models.DateTimeField(null=True)
    playtime = models.IntegerField(null=True)


class TotalPlayTime(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="totalplaytime_of_games"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="totalplaytime"
    )
    latest_at = models.DateTimeField(null=True)
    totaltime = models.IntegerField(default=0)


# 기존 Comment 테이블
# class Comment(models.Model):
#     content = models.TextField()
#     is_visible = models.BooleanField(default=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     game = models.ForeignKey(
#         Game, on_delete=models.CASCADE, related_name="comments"
#     )
#     root = models.ForeignKey(
#         "self", null=True, on_delete=models.CASCADE, related_name="reply")
#     author = models.ForeignKey(
#         settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="comments"
#     )
    

# Review로 바꿀 것
class Review(models.Model):
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews"
    )
    content = models.TextField(max_length=300)
    star = models.IntegerField(null=True)
    difficulty = models.IntegerField(null=True)
    is_visible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ReviewsLike(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_likes"
    )
    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name="reviews"
    )
    is_like = models.IntegerField(default=0)


class Screenshot(models.Model):
    src = models.ImageField(
        upload_to="images/screenshot/",
        blank=True,
        null=True,
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="screenshots"
    )


# class Star(models.Model):
#     star = models.IntegerField(null=True)
#     user = models.ForeignKey(
#         settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="stars"
#     )
#     game = models.ForeignKey(
#         Game, on_delete=models.CASCADE, related_name="stars"
#     )
