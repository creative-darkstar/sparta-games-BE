from django.urls import path
from . import views


app_name = "teambuildings"

urlpatterns = [
    # ---------- API---------- #
    path("api/purpose-list/", views.purpose_list, name="purpose_list"),
    path("api/duration-list/", views.duration_list, name="duration_list"),
    path("api/meeting-type-list/", views.meeting_type_list, name="meeting_type_list"),
    path("api/career-list/", views.career_list, name="career_list"),
    path("api/role-list/", views.role_list, name="role_list"),
    
    path("api/teambuild/", views.TeamBuildPostAPIView.as_view(), name="teambuild_post_list"),
    path("api/teambuild/search", views.teambuild_post_search, name="teambuild_post_search"),
    path("api/teambuild/<int:post_id>/", views.TeamBuildPostDetailAPIView.as_view(), name="teambuild_post_detail"),
    path("api/teambuild/<int:post_id>/comments/", views.TeamBuildPostCommentAPIView.as_view(), name="teambuild_post_comments"),
    path("api/teambuild/comments/<int:comment_id>/", views.TeamBuildPostCommentDetailAPIView.as_view(), name="teambuild_post_comment_detail"),
    
    path("api/teambuild/profile/", views.CreateTeamBuildProfileAPIView.as_view(), name="createteamprofile"),
    path("api/teambuild/profile/search", views.teambuild_profile_search, name="teambuild_profile_search"),
    path("api/teambuild/profile/<int:user_id>/", views.TeamBuildProfileAPIView.as_view(), name="teamprofile"),
]
