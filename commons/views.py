from datetime import datetime
import os
import re
import uuid

import boto3

from django.conf import settings
from django.core.files.storage import default_storage, FileSystemStorage
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from spartagames.utils import std_response


def generate_presigned_url(base_path, extension):
    if extension in ['jpeg', 'png', 'gif']:
        file_type = "image"
    else:
        return std_response(
            message="지원하는 확장자가 아닙니다. 'jpeg', 'png', 'gif' 중에 해당되는 파일을 올려주십시오.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    s3 = boto3.client(
        's3',
        aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )
    time_data = timezone.now().strftime("%Y%m%d%H%M%S%f")
    object_key = f'{base_path}/{time_data}_{uuid.uuid4()}.{extension}'
    
    presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
            'Key': object_key,
            'ContentType': f'{file_type}/{extension}',
            'ACL': 'public-read'  # presigned로 public 업로드 허용
        },
        ExpiresIn=600  # 10분간 유효
    )
    
    # image_url = f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/{object_key}'
    # return presigned_url, image_url
    return presigned_url


class S3UploadPresignedUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_path = request.data.get("base_path")
        extension = request.data.get('extension')
        # presigned_url, image_url = generate_presigned_url(extension)
        res = generate_presigned_url(base_path, extension)
        if isinstance(res, Response):
            return res
        presigned_url = res
        
        return std_response(
            status="success",
            data={
                'upload_url': presigned_url,
                # 'url': image_url  # FE가 content에 넣을 주소
            },
            status_code=status.HTTP_200_OK
        )


class LocalImageUploadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        image = request.FILES.get('image')
        if not image:
            return Response({'error': 'No image file found'}, status=400)

        ext = image.name.split('.')[-1]
        today = datetime.now()
        filename = f"{uuid.uuid4()}.{ext}"
        path = os.path.join('editor_images', f"{today:%Y}", f"{today:%m}", f"{today:%d}", filename)
        saved_path = default_storage.save(path, ContentFile(image.read()))

        image_url = os.path.join(settings.MEDIA_URL, saved_path)
        full_url = request.build_absolute_uri(image_url)
        return Response({'url': full_url})
