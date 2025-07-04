from datetime import datetime
import os
import re
import uuid

import boto3
from bs4 import BeautifulSoup

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
from spartagames.config import AWS_AUTH, AWS_S3_BUCKET_NAME, AWS_S3_REGION_NAME, AWS_S3_CUSTOM_DOMAIN, AWS_S3_BUCKET_IMAGES


# 업로드 용 presigned url 발급
def generate_presigned_url_for_upload(base_path, extension):
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
        aws_access_key_id=AWS_AUTH["aws_access_key_id"],
        aws_secret_access_key=AWS_AUTH["aws_secret_access_key"],
        region_name=AWS_S3_REGION_NAME,
    )
    time_data = timezone.now().strftime("%Y%m%d%H%M%S%f")
    object_key = f'{base_path}/{time_data}_{uuid.uuid4()}.{extension}'
    
    presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': AWS_S3_BUCKET_NAME,
            'Key': object_key,
            'ContentType': f'{file_type}/*',
            # 'ACL': 'public-read'  # presigned로 public 업로드 허용
        },
        ExpiresIn=600  # 10분간 유효
    )
    
    real_url = f'https://{AWS_S3_CUSTOM_DOMAIN}/{object_key}'
    return presigned_url, real_url


# 업로드 용 presigned url 응답
class S3UploadPresignedUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_path = request.data.get("base_path")
        extension = request.data.get('extension')

        res = generate_presigned_url_for_upload(base_path, extension)
        if isinstance(res, Response):
            return res
        presigned_url, real_url = res
        
        return std_response(
            status="success",
            data={
                'upload_url': presigned_url,
                'url': real_url  # FE가 content에 넣을 주소
            },
            status_code=status.HTTP_200_OK
        )


# 추후 필요할 경우 수정 예정
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


def extract_content_text(content):
    raw_text = BeautifulSoup(content or "", "html.parser").get_text()
    
    # 이스케이프 문자 -> 공백으로 치환
    clean_text = raw_text.replace('\xa0', ' ')
    clean_text = re.sub(r'[\n\r\t]+', ' ', clean_text)
    
    # 여러 공백 -> 단일 공백
    clean_text = re.sub(r'\s+', ' ', clean_text)
    
    return clean_text.strip()
