from django.urls import path
from . import views


app_name = "commons"

urlpatterns = [
    # ---------- API---------- #
    path("api/presigned-url/upload/", views.S3UploadPresignedUrlView.as_view(), name="presigned_url_for_upload"),
    path("api/alarm/", views.NotificationListView.as_view(), name="notification_list"),
    path("api/alarm/<int:noti_id>/read/", views.NotificationMarkReadView.as_view(), name="notification_read"),
]
