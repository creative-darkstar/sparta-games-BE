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
