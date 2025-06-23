from django.urls import path
from . import views


app_name = "commons"

urlpatterns = [
    # ---------- API---------- #
    # path("api/<int:user_id>/", views.ProfileAPIView.as_view(), name="profile"),
    path("api/presigned-url/upload/", views.S3UploadPresignedUrlView.as_view(), name="presigned_url_for_upload")
]
