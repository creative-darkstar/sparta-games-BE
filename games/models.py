import os

from django.conf import settings
from django.db import models
from django.utils import timezone


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
    thumbnail = models.ImageField(
        upload_to="images/thumbnail/",
        blank=True,
        null=True,
    )
    youtube_url = models.URLField(blank=True, null=True)
    maker = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="games"
    )
    content = models.TextField()
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
    base_control = models.TextField()
    release_note = models.TextField()
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


class Playtime(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="playtime_of_games"
    )
    game = models.ForeignKey(
        Game, on_delete=models.CASCADE, related_name="playtime"
    )
    entered_at = models.DateTimeField()
    exited_at = models.DateTimeField()
    total_playtime = models.IntegerField(null=True)    


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
    content = models.TextField()
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
