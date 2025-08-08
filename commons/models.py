import uuid

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone

from games.models import validate_text_content, GameCategory


class UploadImage(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content_id = models.PositiveIntegerField()
    content_info = GenericForeignKey('content_type', 'content_id')
    
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="upload_images")
    src = models.URLField(unique=True)
    is_used = models.BooleanField(default=False)
    create_dt = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        GAME_UPLOAD = "game_upload", "게임업로드"
        GAME_PLAY = "game_play", "게임플레이"
        TEAMBUILDING = "teambuilding", "팀빌딩"
        SYSTEM = "system", "시스템"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications"
    )
    noti_type = models.CharField(max_length=50, choices=NotificationType.choices)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    create_dt = models.DateTimeField(auto_now_add=True)

    # Generic Foreign Key 설정
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    content_id = models.PositiveIntegerField()
    content_info = GenericForeignKey('content_type', 'content_id')

    class Meta:
        ordering = ['-create_dt']
