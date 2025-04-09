import os
import zipfile

from django.core.files.storage import FileSystemStorage
from django.db.models import Q
from django.http import FileResponse
from django.shortcuts import render, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
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
from spartagames.utils import std_response
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
    path = row.gamefile.url

    # ~/<업로드시각>_<압축파일명>.zip 에서 '<업로드시각>_<압축파일명>' 추출
    game_folder = path.split('/')[-1].split('.')[0]

    # 게임 폴더 경로(압축을 풀 경로): './media/games/<업로드시각>_<압축파일명>'
    game_folder_path = f"./media/games/{game_folder}"

    # index.html 우선 압축 해제
    zipfile.ZipFile(f"./{path}").extract("index.html", game_folder_path)

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
    with open(f"{game_folder_path}/index.html", 'r') as f:
        for line in f.readlines():
            if line.find('link') > -1:
                cursor = line.find('TemplateData')
                new_lines += line[:cursor] + \
                    f'/media/games/{game_folder}/' + line[cursor:]
            elif line.find('buildUrl') > -1 and not is_check_build:
                is_check_build = True
                cursor = line.find('Build')
                new_lines += line[:cursor] + \
                    f'/media/games/{game_folder}/' + line[cursor:]
            elif line.find('canvas.style.width') > -1 or line.find('canvas.style.height') > -1:
                is_check_build = True
                cursor = line.find('\"')
                new_lines += line[:cursor] + "\"100%\"\n"
            else:
                new_lines += line
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

    # 덮어쓰기
    with open(f'{game_folder_path}/index.html', 'w') as f:
        f.write(new_lines)

    # index.html 외 다른 파일들 압축 해제
    zipfile.ZipFile(f"./{path}").extractall(
        path=game_folder_path,
        members=[item for item in zipfile.ZipFile(
            f"./{path}").namelist() if item != "index.html"]
    )

    # 게임 폴더 경로를 저장하고, 등록 상태 1로 변경(등록 성공)
    row.gamepath = game_folder_path[1:]
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
    zip_path = row.gamefile.url
    zip_folder_path = "./media/zips/"
    zip_name = os.path.basename(zip_path)

    # FileSystemStorage 인스턴스 생성
    # zip_folder_path에 대해 FILE_UPLOAD_PERMISSIONS = 0o644 권한 설정
    # 파일을 어디서 가져오는지를 정하는 것으로 보면 됨
    # 디폴트 값: '/media/' 에서 가져옴
    fs = FileSystemStorage(zip_folder_path)

    # FileResponse 인스턴스 생성
    # FILE_UPLOAD_PERMISSIONS 권한을 가진 상태로 zip_folder_path 경로 내의 zip_name 파일에 'rb' 모드로 접근
    # content_type 으로 zip 파일임을 명시
    response = FileResponse(fs.open(zip_name, 'rb'),
                            content_type='application/zip')

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
