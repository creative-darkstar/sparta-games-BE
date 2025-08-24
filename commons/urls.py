from django.urls import path
from . import views


app_name = "commons"

urlpatterns = [
    # ---------- API---------- #
    path("api/presigned-url/img-upload/", views.S3ImageUploadPresignedUrlView.as_view(), name="presigned_url_for_image_upload"),
    path("api/presigned-url/zip-upload/", views.S3ZipUploadPresignedUrlView.as_view(), name="presigned_url_for_zip_upload"),
]
