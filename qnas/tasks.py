from datetime import timedelta
import logging
from tempfile import NamedTemporaryFile
import os
import re
from urllib.parse import urlparse
import zipfile

import boto3
from celery import shared_task
from celery.exceptions import Ignore
import redis

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.utils import timezone

from spartagames.config import ADMIN_STAFF_EMAIL, ADMIN_USER_EMAIL
from .models import DeleteUsers, GameRegisterLog
from games.models import Game


logger = logging.getLogger(__name__)
redis_url = urlparse(settings.CELERY_BROKER_URL)
r = redis.Redis(
    host=redis_url.hostname,
    port=redis_url.port,
    password=redis_url.password,
    db=0
)

@shared_task
def hard_delete_user():
    """
    매일 오전 6시에 실행
    유예기간: 탈퇴 버튼을 누른 시점으로부터 이틀 뒤 (ex: 3월 5일에 탈퇴했다면 3월 7일 오전 6시에 삭제)
    """
    try:
        rows = DeleteUsers.objects.filter(created_at__lte=timezone.now()-timedelta(days=2))
        # 관리자 계정
        admin_staff = get_user_model().objects.get(email=ADMIN_STAFF_EMAIL)
        # 관리자 계정 (게임 이관용, 일반 유저 취급)
        admin_user = get_user_model().objects.get(email=ADMIN_USER_EMAIL)
        
        for row in rows:
            user = row.user
            
            # 게임 이관 처리
            games = user.games.all()
            for game in games:
                # 이관 로그 추가
                GameRegisterLog.objects.create(
                    recoder=admin_staff,
                    maker=admin_user,
                    game=game,
                    content=f"제작자 {user.nickname}의 게임 데이터를 관리자 계정으로 이관"
                )
                game.maker = admin_user
                game.save()

            # 리뷰 이관 처리
            reviews = user.reviews.all()
            for review in reviews:
                review.author = admin_user
                review.save()
            
            user.delete()
        
        return f"유저 완전 삭제 프로세스 완료"
    except Exception as e:
        # 예외 발생 시 로그 남기기 (추가적인 로깅 설정 필요 시 설정)
        return f"Error in assigning '' : {str(e)}"


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 0},
)
def game_register_task(self, game_id):
    # 락 생성 (동일 작업에 대한 잠금)
    lock = r.lock(f"game:lock:{game_id}", timeout=1800, blocking_timeout=0)
    if not lock.acquire(blocking=False):
        self.update_state(
            state="SKIPPED",
            meta={
                "message": "same task. will skip: it's locked",
                "game_id": game_id,
            }
        )
        raise Ignore()

    try:
        try:
            row = Game.objects.get(pk=game_id, is_visible=True, register_state=0)
        except ObjectDoesNotExist as e:
            logger.error(f"게임 {game_id} 없음 또는 등록 불가 상태")
            return
            # 무한 리트라이 문제 때문에 주석 처리
            # raise self.retry(exc=e)

        s3 = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        try:
            zip_resp = s3.get_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                Key=f"media/{row.gamefile.name}"
            )
        except Exception as e:
            logger.exception("S3에서 zip 파일 가져오기 실패")
            raise self.retry(exc=e)

        with NamedTemporaryFile(delete=False) as tmp_file:
            for chunk in zip_resp["Body"].iter_chunks(chunk_size=8192):
                tmp_file.write(chunk)
            zip_path = tmp_file.name

        game_folder = row.gamefile.name.split('/')[-1].split('.')[0]

        # 업로드 된 같은 이름의 폴더나 파일이 존재할 경우 제거
        s3_for_delete = boto3.resource(
            "s3",
            aws_access_key_id=settings.AWS_S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_S3_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        bucket_for_delete = s3_for_delete.Bucket(settings.AWS_STORAGE_BUCKET_NAME)
        bucket_for_delete.objects.filter(Prefix=f"media/games/{game_folder}/").delete()

        # index.html 변경 후 S3 업로드
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                index_text = zip_ref.read("index.html").decode("utf-8")
                new_lines = ""
                is_check_build = False

                for line in index_text.splitlines():
                    if 'link' in line:
                        cursor = line.find("TemplateData")
                        new_lines += line[:cursor] + f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/media/games/{game_folder}/" + line[cursor:]
                    elif "buildUrl" in line and not is_check_build:
                        is_check_build = True
                        cursor = line.find("Build")
                        new_lines += line[:cursor] + f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/media/games/{game_folder}/" + line[cursor:]
                    elif "canvas.style.width" in line or "canvas.style.height" in line:
                        cursor = line.find('"')
                        new_lines += line[:cursor] + '"100%"\n'
                    else:
                        new_lines += line
                    new_lines += "\n"

                new_lines = new_lines.replace(
                    '<body', '<body style="margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden;"'
                ).replace(
                    '<div id="unity-container"', '<div id="unity-container" style="width: 100%; height: 100%; overflow: hidden;"'
                )

                new_lines = new_lines.replace(
                    "</body>",
                    """
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
                    </body>
                    """
                )

                with NamedTemporaryFile(delete=False) as out_zip:
                    with zipfile.ZipFile(out_zip, "w") as new_zip:
                        for item in zip_ref.infolist():
                            if item.filename != "index.html":
                                new_zip.writestr(item, zip_ref.read(item.filename))
                        new_zip.writestr("index.html", new_lines.encode("utf-8"))

                    out_zip_path = out_zip.name

            with zipfile.ZipFile(out_zip_path) as final_zip:
                for file_name in final_zip.namelist():
                    pattern1 = r".+\.(data|symbols\.json)\.gz$"
                    pattern2 = r".+\.js\.gz$"
                    pattern3 = r".+\.wasm\.gz$"
                    
                    # 만약 file_name이 폴더명 이라면 S3에 올리는 과정 거치지 않도록 스킵
                    file_extension = file_name.split('.')[-1].lower()
                    if not file_extension or '/' in file_extension:
                        continue
                    
                    body = final_zip.open(file_name)

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

                    s3.put_object(
                        Body=body,
                        Bucket=settings.AWS_STORAGE_BUCKET_NAME,
                        Key=f"media/games/{game_folder}/{file_name}",
                        ContentType=(content_type if content_type else 'text/plain'),
                        ContentEncoding=(content_encoding if content_encoding else 'identity'),
                    )
                    
                    body.close()

        except Exception as e:
            logger.exception("게임 등록 중 에러 발생")
            raise self.retry(exc=e)
        
        # 생성했던 임시 파일 삭제
        finally:
            # 열린 파일 핸들 강제로 close 시도
            import gc
            gc.collect()

            if zip_path and os.path.exists(zip_path):
                try:
                    os.remove(zip_path)
                except Exception as e:
                    logger.warning(f"zip_path 삭제 실패: {e}")

            if out_zip_path and os.path.exists(out_zip_path):
                try:
                    os.remove(out_zip_path)
                except Exception as e:
                    logger.warning(f"out_zip_path 삭제 실패: {e}")

        row.gamepath = f"https://{settings.AWS_S3_CUSTOM_DOMAIN}/media/games/{game_folder}"
        row.register_state = 1
        row.save()

        return {
            "status": "success",
            "game_id": game_id,
            "gamepath": row.gamepath,
        }
    
    finally:
        try:
            # 락 해제
            lock.release()
        except Exception:
            pass
