import io
import os
import re
import zipfile

import boto3

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from spartagames import config
from .models import (
    GameRegisterLog,
    QnA,
)
from .pagination import (
    GameRegisterListPagination,
)
from .serializers import (
    QnAPostListSerializer,
    CategorySerializer,
    GameRegisterListSerializer,
)
from games.models import (
    Game,
)

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated  # 로그인 인증토큰


# ---------- API---------- #
class QnAPostListAPIView(APIView):
    """
    포스트일 때 로그인 인증을 위한 함수
    """

    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == 'post':  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    """
    QnA 목록 조회
    """

    def get(self, request):
        qna_q = request.query_params.get('qna-q')
        category = request.query_params.get('category')

        qnas = QnA.objects.filter(is_visible=True)

        if qna_q:
            qnas = qnas.filter(title__icontains=qna_q)
        if category:
            qnas = qnas.filter(category=category)
        serializer = QnAPostListSerializer(qnas, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    """
    QnA 등록
    """

    def post(self, request):
        if request.user.is_staff == False:
            return Response({"error": "권한이 없습니다"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = QnAPostListSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(is_visible=True)
            return Response(serializer.data, status=status.HTTP_200_OK)


class QnADetailAPIView(APIView):
    """
    포스트일 때 로그인 인증을 위한 함수
    """

    def get_permissions(self):  # 로그인 인증토큰
        permissions = super().get_permissions()

        if self.request.method.lower() == ('put' or 'delete'):  # 포스트할때만 로그인
            permissions.append(IsAuthenticated())

        return permissions

    def get_object(self, qna_pk):
        return get_object_or_404(QnA, pk=qna_pk, is_visible=True)

    """
    QnA 상세 조회
    """

    def get(self, request, qna_pk):
        qna = self.get_object(qna_pk)
        serializer = QnAPostListSerializer(qna)
        return Response(serializer.data, status=status.HTTP_200_OK)

    """
    QnA 수정
    """

    def put(self, request, qna_pk):
        if request.user.is_staff == False:
            return Response({"error": "권한이 없습니다"}, status=status.HTTP_400_BAD_REQUEST)
        qna = self.get_object(qna_pk)
        serializer = QnAPostListSerializer(
            qna, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)

    """
    QnA 삭제
    """

    def delete(self, request, qna_pk):
        if request.user.is_staff == False:
            return Response({"error": "권한이 없습니다"}, status=status.HTTP_400_BAD_REQUEST)
        qna = self.get_object(qna_pk)
        qna.is_visible = False
        qna.save()
        return Response({"message": "삭제를 완료했습니다"}, status=status.HTTP_200_OK)


class CategoryListView(APIView):
    def get(self, request):
        categories = QnA.CATEGORY_CHOICES
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



# 2025-01-03 관리자 페이지에 있을 기능을 games -> qnas 로 이관

# 관리자용 게임 통계
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_stats(request):
    if (request.user.is_staff == False) or (request.user.is_superuser == False):
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)
    
    rows = Game.objects.filter(is_visible=True)

    # 응답 데이터 구성
    data = {
        "state_ready": rows.filter(register_state=0).count(),
        "state_ok": rows.filter(register_state=1).count(),
        "state_deny": rows.filter(register_state=2).count(),
    }
    
    return Response(data, status=status.HTTP_200_OK)



# 관리자용 게임 등록 리스트
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_register_list(request):
    if (request.user.is_staff == False) or (request.user.is_superuser == False):
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)
    
    # 누적 조건 필터링을 위한 Q 객체 초기화
    query = Q(is_visible=True)
    
    # GET /games/?categories=1&categories=2 형태로 받게 됨
    categories_q = request.query_params.getlist('categories')
    # register_state
    state_q = request.query_params.get('state')
    # 키워드
    keyword_q = request.query_params.get('keyword')
    
    if categories_q:
        query &= Q(category__id__in=categories_q)
    if state_q:
        query &= Q(register_state=state_q)
    if keyword_q:
        query &= Q(title__icontains=keyword_q) | Q(maker__nickname__icontains=keyword_q)
    
    rows = Game.objects.filter(query).distinct()

    # 페이지네이션
    paginator = GameRegisterListPagination()
    result = paginator.paginate_queryset(rows, request)
    serializer = GameRegisterListSerializer(result, many=True)

    # 응답 데이터 구성
    response_data = {
        "game_register_list": serializer.data,
    }
    
    return paginator.get_paginated_response(response_data)


# 관리자용 게임 등록 로그 전체
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def game_register_logs_all(request, game_pk):
    if (request.user.is_staff == False) or (request.user.is_superuser == False):
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)
    
    rows = GameRegisterLog.objects.filter(game__pk=game_pk).order_by("-created_at")
    
    # 응답 데이터 구성
    data = {
        "results": [{"created_at": log.created_at, "content": log.content} for log in rows]
    }
    
    return Response(data, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def game_register(request, game_pk):
    # 관리자 여부 확인
    if request.user.is_staff is False:
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

    # game_pk에 해당하는 row 가져오기 (게시 중인 상태이면서 '등록 중' 상태)
    row = get_object_or_404(
        Game, pk=game_pk, is_visible=True, register_state=0)

    # gamefile 필드에 저장한 경로값을 'path' 변수에 저장
    path = "media/" + row.gamefile.name

    # ~/<업로드시각>_<압축파일명>.zip 에서 '<업로드시각>_<압축파일명>' 추출
    game_folder = path.split('/')[-1].split('.')[0]

    s3 = boto3.client(
        's3',
        aws_access_key_id=config.AWS_AUTH["aws_access_key_id"],
        aws_secret_access_key=config.AWS_AUTH["aws_secret_access_key"],
        region_name='ap-northeast-2'
    )
    
    # S3에서 zip 파일을 읽어옴
    zip_resp = s3.get_object(Bucket=config.AWS_S3_BUCKET_NAME, Key=path)

    # BytesIO를 사용하여 메모리에 파일 데이터를 읽음
    zip_data = io.BytesIO(zip_resp['Body'].read())

    zip_ref = zipfile.ZipFile(zip_data)

    """
    index.html 내용 수정
    <link> 태그 href 값 수정 (line: 7, 8)
    var buildUrl 변수 값 수정 (line: 59)
    
    new_lines: 덮어쓸 내용 저장
    is_check_build: Build 키워드 찾은 후 True로 변경 (이후 라인에서 Build 찾는 것을 피하기 위함)
    """

    new_lines = str()
    is_check_build = False

    # 덮어쓸 내용 담기
    index_text = zip_ref.read('index.html').decode('utf-8')
    for line in index_text.splitlines():
        if line.find('link') > -1:
            cursor = line.find('TemplateData')
            new_lines += line[:cursor] + \
                f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/media/games/{game_folder}/' + line[cursor:]
        elif line.find('buildUrl') > -1 and not is_check_build:
            is_check_build = True
            cursor = line.find('Build')
            new_lines += line[:cursor] + \
                f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/media/games/{game_folder}/' + line[cursor:]
        elif line.find('canvas.style.width') > -1 or line.find('canvas.style.height') > -1:
            is_check_build = True
            cursor = line.find('\"')
            new_lines += line[:cursor] + "\"100%\"\n"
        else:
            new_lines += line
        new_lines += '\n'
    
    # 추가할 JavaScript 코드 (iframe의 width, height 조절을 위해 추가함)
    additional_script = """
    <script>
      function sendSizeToParent() {
        var canvas = document.querySelector("#unity-canvas");
        var width = canvas.clientWidth;
        var height = canvas.clientHeight;
        window.parent.postMessage({ width: width, height: height }, '*');
      }

      window.addEventListener('resize', sendSizeToParent);
      window.addEventListener('load', sendSizeToParent);
    </script>
    """
    # CSS 스타일 추가 (body 태그와 unity-container에 overflow: hidden 추가)
    new_lines = new_lines.replace(
        '<body', '<body style="margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;"')
    new_lines = new_lines.replace(
        '<div id="unity-container"', '<div id="unity-container" style="width: 100%; height: 100%; overflow: hidden;"')

    # </body> 태그 전에 추가할 스크립트 삽입
    body_close_category_index = new_lines.find('</body>')
    new_lines = new_lines[:body_close_category_index] + \
        additional_script + new_lines[body_close_category_index:]

    new_zip_data = io.BytesIO()
    with zipfile.ZipFile(new_zip_data, 'w') as new_zip_ref:
        for item in zip_ref.infolist():
            if item.filename != 'index.html':
                new_zip_ref.writestr(item, zip_ref.read(item.filename))
        new_zip_ref.writestr('index.html', new_lines.encode('utf-8'))

        for file_name in new_zip_ref.namelist():
            pattern1 = r".+\.(data|symbols\.json)\.gz$"
            pattern2 = r".+\.js\.gz$"
            pattern3 = r".+\.wasm\.gz$"
            file_extension = file_name.split('.')[-1].lower()
            
            # 만약 file_name이 폴더명 이라면 S3에 올리는 과정 거치지 않도록 스킵
            if not file_extension or '/' in file_extension:
                continue

            content_type = None
            content_encoding = None

            # 메타데이터 설정
            metadata = {}
            if re.match(pattern1, file_name):
                content_type = 'application/octet-stream'
                content_encoding = 'gzip'
            elif re.match(pattern2, file_name):
                content_type = 'application/javascript'
                content_encoding = 'gzip'
            elif re.match(pattern3, file_name):
                content_type = 'application/wasm'
                content_encoding = 'gzip'
            else:
                if file_extension == "js":
                    content_type = 'application/javascript'
                elif file_extension == "html":
                    content_type = 'text/html'
                elif file_extension == "ico":
                    content_type = 'image/x-icon'
                elif file_extension == "png":
                    content_type = 'image/png'
                elif file_extension == "css":
                    content_type = 'text/css'

            response = s3.put_object(
                Body=new_zip_ref.open(file_name),
                Bucket=config.AWS_S3_BUCKET_NAME,
                Key=f"media/games/{game_folder}/{file_name}",
                ContentType=(content_type if content_type else 'text/plain'),
                ContentEncoding=(content_encoding if content_encoding else 'identity')
            )

    zip_ref.close()

    # 게임 폴더 경로를 저장하고, 등록 상태 1로 변경(등록 성공)
    row.gamepath = f'https://{settings.AWS_S3_CUSTOM_DOMAIN}/media/games/{game_folder}'
    row.register_state = 1
    row.save()

    # 알맞은 HTTP Response 리턴
    # return Response({"message": f"등록을 성공했습니다. (게시물 id: {game_pk})"}, status=status.HTTP_200_OK)

    # 게임 등록 로그에 데이터 추가
    row.logs_game.create(
        recoder = request.user,
        maker = row.maker,
        game = row,
        content = f"승인 (기록자: {request.user.email}, 제작자: {row.maker.email})",
    )
    
    # 2024-10-31 추가. return 수정 필요 (redirect -> response)
    # return redirect("games:admin_list")
    return Response({"message": "게임이 등록되었습니다."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def game_register_deny(request, game_pk):
    # 관리자 여부 확인
    if request.user.is_staff is False:
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)
    # # 등록 거부 사유 없을 시 400 (추후 추가)
    # if request.data.get("content", None) is None:
    #     return Response({"error": "반려 사유가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

    # 게임 정보 수정
    game = get_object_or_404(
        Game, pk=game_pk, is_visible=True, register_state=0)
    game.register_state = 2
    game.save()
    
    # 등록 거부 사유 로그 추가
    GameRegisterLog.objects.create(
        recoder=request.user,
        maker=game.maker,
        game=game,
        content=request.data.get("content")
    )

    # 2024-10-31 추가. return 수정 필요 (redirect -> response)
    # return redirect("games:admin_list")
    return Response({"message": "게임 등록을 거부했습니다."}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def game_dzip(request, game_pk):
    # 관리자 여부 확인
    if request.user.is_staff is False:
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

    row = get_object_or_404(
        Game, pk=game_pk, register_state=0, is_visible=True)
    zip_path = "media/" + row.gamefile.name
    zip_name = os.path.basename(zip_path)
    s3_client = boto3.client(
        's3',
        aws_access_key_id=config.AWS_AUTH["aws_access_key_id"],
        aws_secret_access_key=config.AWS_AUTH["aws_secret_access_key"],
        region_name='ap-northeast-2'
    )
    s3_response = s3_client.get_object(Bucket=config.AWS_S3_BUCKET_NAME, Key=zip_path)
    file_stream = s3_response['Body'].read()

    # 메모리 스트림을 FileResponse로 반환
    response = FileResponse(io.BytesIO(file_stream), content_type='application/zip')

    # 'Content-Disposition' value 값(HTTP Response 헤더값)을 설정
    # 파일 이름을 zip_name 으로 다운로드 폴더에 받겠다는 뜻
    response['Content-Disposition'] = f'attachment; filename="{zip_name}"'

    # FileResponse 객체를 리턴
    return response


# 게임 등록 거부 사유 불러오는 API
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def deny_log(request, game_pk):
    # 등록 거부된 게임 정보 불러오기
    game = get_object_or_404(
        Game, pk=game_pk, is_visible=True, register_state=2)
    
    # 관리자, 메이커 여부 확인
    if not (request.user.is_staff is True or request.user == game.maker):
        return Response({"error": "관리자 권한이 필요합니다."}, status=status.HTTP_403_FORBIDDEN)

    # 로그 불러오기
    rows = GameRegisterLog.objects.filter(game=game)
    if not rows.exists():
        return Response({"error": "등록 거부된 적이 없는 게임입니다."}, status=status.HTTP_400_BAD_REQUEST)
    row = rows.order_by("-created_at").first()

    return Response(
        {
            "content": row.content
        },
        status=status.HTTP_200_OK
    )


# 구현 예정
# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def maker_list(request):
#     return


# 2024-01-03 웹 기능 비활성화
# # ---------- Web---------- #
# def qna_main_view(request):
#     return render(request, 'qnas/qna_main.html')


# def qna_detail_view(request, qna_pk):
#     return render(request, "qnas/qna_detail.html")


# def qna_create_view(request):
#     return render(request, "qnas/qna_create.html")


# def qna_update_view(request, qna_pk):
#     return render(request, "qnas/qna_update.html")
