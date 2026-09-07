from datetime import datetime
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage, FileSystemStorage
from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from rest_framework import generics, permissions
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response

from spartagames.utils import std_response, get_s3_client
from spartagames.config import AWS_S3_BUCKET_NAME, AWS_S3_CUSTOM_DOMAIN, AWS_S3_BUCKET_IMAGES

from .models import Notification
from .pagination import NotificationPagination
from .serializers import NotificationSerializer


# 업로드 용 presigned url 발급
def generate_presigned_url_for_upload(base_path, extension, filename=None):
    if extension in ['jpeg', 'png', 'gif']:
        file_type = "image"
        s3 = get_s3_client()
        time_data = timezone.now().strftime("%Y%m%d%H%M%S%f")
        object_key = f'{base_path}/{time_data}_{uuid.uuid4()}.{extension}'

        presigned_url = s3.generate_presigned_url(
            ClientMethod='put_object',
            Params={
                'Bucket': AWS_S3_BUCKET_NAME,
                'Key': object_key,
                'ContentType': f'{file_type}/*',
                'Tagging': 'is_used=false',
                # 'ACL': 'public-read'  # presigned로 public 업로드 허용
            },
            ExpiresIn=600,  # 10분간 유효
        )

        real_url = f'https://{AWS_S3_CUSTOM_DOMAIN}/{object_key}'
        return presigned_url, real_url

    if extension != 'zip':
        return std_response(
            message="지원하는 확장자가 아닙니다. 'jpeg', 'png', 'gif', 'zip' 중에 해당되는 파일을 올려주십시오.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if base_path not in ('zips', 'media/zips'):
        return std_response(
            message="zip 업로드의 base_path는 'zips' 여야 합니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if not filename or not isinstance(filename, str):
        return std_response(
            message="원본 파일명(filename)이 필요합니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    sanitized_filename = filename.strip()
    if (
        not sanitized_filename
        or sanitized_filename != os.path.basename(sanitized_filename)
        or '/' in sanitized_filename
        or '\\' in sanitized_filename
        or '..' in sanitized_filename
    ):
        return std_response(
            message="파일명에 경로 구분자가 포함될 수 없습니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    if os.path.splitext(sanitized_filename)[-1].lower() != '.zip':
        return std_response(
            message="zip 파일명만 허용됩니다.",
            status="fail",
            error_code="CLIENT_FAIL",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 순환 import 방지: 발급 시점에만 Game.upload_to_func 사용
    from games.models import Game

    file_key = Game.upload_to_func(None, sanitized_filename)
    object_key = "media/" + file_key
    s3 = get_s3_client()

    presigned_url = s3.generate_presigned_url(
        ClientMethod='put_object',
        Params={
            'Bucket': AWS_S3_BUCKET_NAME,
            'Key': object_key,
            'ContentType': 'application/zip',
            'Tagging': 'is_used=false',
        },
        ExpiresIn=1800,
    )

    real_url = f'https://{AWS_S3_CUSTOM_DOMAIN}/{object_key}'
    return presigned_url, real_url, object_key, file_key


# 업로드 용 presigned url 응답
class S3UploadPresignedUrlView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        base_path = request.data.get("base_path")
        extension = request.data.get('extension')
        filename = request.data.get('filename')

        res = generate_presigned_url_for_upload(base_path, extension, filename)
        if isinstance(res, Response):
            return res

        if len(res) == 4:
            presigned_url, real_url, object_key, file_key = res
            return std_response(
                status="success",
                data={
                    'upload_url': presigned_url,
                    'url': real_url,
                    'object_key': object_key,
                    'file_key': file_key,
                },
                status_code=status.HTTP_200_OK
            )

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


class NotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = Notification.objects.filter(user=user)

        paginator = NotificationPagination()
        paginated_qs = paginator.paginate_queryset(qs, request)

        serializer = NotificationSerializer(paginated_qs, many=True)
        response_data = paginator.get_paginated_response(serializer.data).data
        
        # return response_data
        return std_response(
            data=response_data["results"],
            message="알람을 불러왔습니다.", status="success",
            pagination={"count": qs.count(), "next":response_data["next"], "previous":response_data["previous"]},
            status_code=status.HTTP_200_OK
        )


class NotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, noti_id):
        qs = Notification.objects.get(id=noti_id)
        if qs.user != request.user:
            return std_response(message="잘못된 접근입니다.", status="fail", error_code="CLIENT_FAIL", status_code=status.HTTP_403_FORBIDDEN)
        qs.is_read = True
        qs.save()
        return std_response(message="알림 읽음 처리를 완료했습니다.", status="success", status_code=status.HTTP_200_OK)
