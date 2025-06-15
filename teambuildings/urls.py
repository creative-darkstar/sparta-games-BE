from django.urls import path
from . import views


app_name = "teambuildings"

urlpatterns = [
    path("api/profile/", views.CreateTeamBuildProfileAPIView.as_view(), name="createteamprofile"),
    path("api/profile/<int:user_id>/", views.TeamBuildProfileAPIView.as_view(), name="teamprofile"),
    # ---------- API---------- #
    # 참고용: path("api/<int:user_id>/", views.ProfileAPIView.as_view(), name="profile"),
    path("api/teambuild/", views.TeamBuildPostAPIView.as_view(), name="teambuild_list"),
    path("api/teambuild/<int:post_id>/", views.TeamBuildPostDetailAPIView.as_view(), name="teambuild_detail"),
]
