from django.urls import path
from . import views


app_name = "users"

urlpatterns = [
    # ---------- API---------- #
    path("api/<int:user_id>/", views.ProfileAPIView.as_view(), name="profile"),
    path("api/nickname/", views.check_nickname, name="check_nickname"),
    path("api/<int:user_id>/password/", views.change_password, name="change_password"),
    path("api/reset-password/", views.reset_password, name="reset_password"),
    path("api/reset-password-verify/", views.password_verify_code, name="reset_password_verify_code"),
    path("api/<int:user_id>/games/", views.my_games, name="my_games"),
    path("api/<int:user_id>/likes/", views.like_games, name="like_games"),
    path("api/<int:user_id>/gamepacks/", views.gamepacks, name="gamepacks"),    # 2024-12-30 유저 페이지 게임팩 API 복구
    path("api/<int:user_id>/recent/", views.recently_played_games, name="recent_played_games"),
    path("api/<int:user_id>/teambuildposts/", views.teambuild_posts, name="teambuild_posts"),
    # ---------- Web---------- #
    # path("<int:user_pk>/", views.profile_page, name='profile_page'),
]
