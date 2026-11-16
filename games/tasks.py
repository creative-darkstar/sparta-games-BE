from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
import os
from tempfile import NamedTemporaryFile

from botocore.exceptions import ClientError
from celery import shared_task
from django.db.models import Count, Q, Sum
import logging
import requests
from commons.models import Notification
from commons.utils import NotificationSubType, create_notification
from spartagames.config import AWS_S3_BUCKET_NAME, DISCORD_GAME_UPLOAD_CHANNEL_WEBHOOK_URL
from spartagames.utils import get_s3_client, safe_s3_tag

from .models import Game, Chip
from .utils import validate_zip_file


logger = logging.getLogger("sparta_games_celery")


@shared_task
def assign_chips_to_top_games():
    """
    매일 상위 4개의 게임에 'Daily Top' 칩을 할당합니다.
    기존에 할당된 'Daily Top' 칩을 제거하고 다시 할당합니다.
    """
    try:
        # 'Daily Top' 칩 가져오기 (없으면 생성)
        daily_chip, _ = Chip.objects.get_or_create(name='Daily Top')
        
        # 기존에 'Daily Top' 칩이 할당된 게임들에서 칩 제거
        games_with_daily_chip = Game.objects.filter(chip=daily_chip)
        for game in games_with_daily_chip:
            game.chip.remove(daily_chip)
        
        # 좋아요 수가 가장 많은 상위 4개 게임 가져오기
        top_games = Game.objects.annotate(
            score=(
                Count('likes') * 0.4 +
                Count('reviews', filter=Q(reviews__created_at__gte=timezone.now() - timedelta(days=1))) * 0.3 +
                Count('views', filter=Q(views__created_at__gte=timezone.now() - timedelta(days=1))) * 0.3
            )
        ).filter(
            is_visible=True,
            register_state=1,
        ).order_by('-score', '-created_at')[:4]
        
        # 상위 4개 게임에 'Daily Top' 칩 할당
        for game in top_games:
            game.chip.add(daily_chip)
        
        logger.info(f"Assigned 'Daily Top' chip to {len(top_games)} games.")
    except Exception as e:
        logger.error(f"Error in assigning 'Daily Top' chips: {str(e)}", exc_info=True)


@shared_task
def cleanup_new_game_chip():
    """
    주기적으로 'New Game' 칩을 제거합니다.
    """
    try:
        # 'New Game' 칩 가져오기
        new_game_chip = Chip.objects.filter(name='New Game').first()
        if not new_game_chip:
            return "새로 생성된 게임 칩이 없습니다."
        
        # 'New Game' 칩이 할당된 모든 게임에서 칩 제거
        games_with_new_game = Game.objects.filter(chip=new_game_chip)
        for game in games_with_new_game:
            game.chip.remove(new_game_chip)
        
        logger.info(f"Removed 'New Game' chip from {len(games_with_new_game)} games.")
    except Exception as e:
        logger.error(f"Error in cleaning up 'New Game' chips: {str(e)}", exc_info=True)


@shared_task
def assign_bookmark_top_chips():
    """
    매일 상위 4개의 게임에 'Bookmark Top' 칩을 할당합니다.
    최소 5개의 즐겨찾기를 가진 게임 중에서 즐겨찾기 수가 가장 많은 상위 4개를 선정합니다.
    중복 할당을 허용합니다.
    """
    try:
        # 'Bookmark Top' 칩 가져오기 (없으면 생성)
        bookmark_chip, created = Chip.objects.get_or_create(name='Bookmark Top')
        
        # 최소 5개의 즐겨찾기를 가진 게임 중 즐겨찾기 수가 가장 많은 상위 4개 게임 가져오기
        top_bookmarked_games = Game.objects.annotate(
            bookmark_count=Count('likes')
        ).filter(
            bookmark_count__gte=5,
            is_visible=True,
            register_state=1
        ).order_by('-bookmark_count', '-created_at')[:4]
        
        # 상위 4개 게임에 'Bookmark Top' 칩 할당 (중복 허용)
        for game in top_bookmarked_games:
            game.chip.add(bookmark_chip)
        
        logger.info(f"Assigned 'Bookmark Top' chip to {len(top_bookmarked_games)} games.")
    except Exception as e:
        logger.error(f"Error in assigning 'Bookmark Top' chips: {str(e)}", exc_info=True)
    
@shared_task
def assign_long_play_chips():
    """
    매일 상위 4개의 게임에 'Long Play' 칩을 할당합니다.
    지난 일주일 동안 사용자들의 총 플레이 시간이 가장 높은 4개의 게임을 선정합니다.
    기존에 할당된 'Long Play' 칩을 제거하고 새로 할당합니다.
    """
    try:
        # 'Long Play' 칩 가져오기 (없으면 생성)
        long_play_chip, created = Chip.objects.get_or_create(name='Long Play')
        
        # 기존에 'Long Play' 칩이 할당된 게임들에서 칩 제거
        games_with_long_play_chip = Game.objects.filter(chip=long_play_chip)
        for game in games_with_long_play_chip:
            game.chip.remove(long_play_chip)
        
        # 지난 일주일 동안의 총 플레이 시간을 계산
        one_week_ago = timezone.now() - timedelta(weeks=1)
        top_long_play_games = Game.objects.annotate(
            total_playtime=Sum('playlog__playtime')
        ).filter(
            total_playtime__isnull=False,
            #total_playtime__gte=0,  # 최소 조건 설정 가능
            is_visible=True,
            register_state=1
        ).order_by('-total_playtime', '-created_at')[:4]
        
        # 상위 4개 게임에 'Long Play' 칩 할당
        for game in top_long_play_games:
            game.chip.add(long_play_chip)
        
        logger.info(f"Assigned 'Long Play' chip to {len(top_long_play_games)} games.")
    except Exception as e:
        logger.error(f"Error in assigning 'Long Play' chips: {str(e)}", exc_info=True)
    
@shared_task
def assign_review_top_chips():
    """
    매일 상위 4개의 게임에 'Review Top' 칩을 할당합니다.
    지난 하루 동안 최소 10개의 리뷰가 달린 게임 중에서 리뷰 수가 가장 많은 상위 4개를 선정합니다.
    기존에 할당된 'Review Top' 칩을 제거하고 새로 할당합니다.
    """
    try:
        # 'Review Top' 칩 가져오기 (없으면 생성)
        review_top_chip, created = Chip.objects.get_or_create(name='Review Top')
        
        # 기존에 'Review Top' 칩이 할당된 게임들에서 칩 제거
        games_with_review_top_chip = Game.objects.filter(chip=review_top_chip)
        for game in games_with_review_top_chip:
            game.chip.remove(review_top_chip)
        
        # 총 리뷰 수가 최소 10개 이상인 게임 중 리뷰 수가 가장 많은 상위 4개 게임 가져오기
        top_reviewed_games = Game.objects.annotate(
            total_review_count=Count('reviews')
        ).filter(
            total_review_count__gte=10,
            is_visible=True,
            register_state=1
        ).order_by('-total_review_count', '-created_at')[:4]
        
        # 상위 4개 게임에 'Review Top' 칩 할당
        for game in top_reviewed_games:
            game.chip.add(review_top_chip)
        
        logger.info(f"Assigned 'Review Top' chip to {len(top_reviewed_games)} games.")
    except Exception as e:
        logger.error(f"Error in assigning 'Review Top' chips: {str(e)}", exc_info=True)


@shared_task
def send_discord_notification_task(game_id, msg_text="📢 새로운 게임이 업로드되었습니다! 관리자 계정으로 확인해주세요.\n"):
    """
    game_id로 Game을 재조회한 뒤 Discord 웹훅을 전송합니다.
    요청 경로에서 외부 I/O를 분리하기 위한 태스크입니다.
    """
    try:
        game = Game.objects.select_related("maker").get(pk=game_id)
    except Game.DoesNotExist:
        logger.warning(f"send_discord_notification_task: Game {game_id} does not exist")
        return

    webhook_url = DISCORD_GAME_UPLOAD_CHANNEL_WEBHOOK_URL
    message = {
        "content": f"""
{msg_text}
🎮 게임명: {game.title}\n"
👤 업로더: {game.maker.nickname}\n
"""
    }

    try:
        requests.post(webhook_url, json=message)
        logger.info(f"send_discord_notification_task: Discord 알림 전송 완료 (game_id={game_id})")
    except Exception as e:
        logger.error(f"send_discord_notification_task: Discord 알림 실패 (game_id={game_id}): {e}", exc_info=True)


@shared_task
def notify_game_register_task(user_id, game_id, game_title):
    """
    game_id로 Game을 재조회한 뒤 검수요청 페이지 알림을 생성합니다.
    유저는 탈퇴 유예 기간이 있어 태스크 실행 시점에 즉시 삭제되지 않으므로 재조회하지 않습니다.
    """
    try:
        game = Game.objects.get(pk=game_id)
    except Game.DoesNotExist:
        logger.warning(f"notify_game_register_task: Game {game_id} does not exist")
        return

    User = get_user_model()
    user = User(pk=user_id)

    try:
        create_notification(
            user=user,
            noti_type=Notification.NotificationType.GAME_UPLOAD,
            noti_sub_type=NotificationSubType.REGISTER_REQUEST,
            related_object=game,
            game_title=game_title,
        )
        logger.info(f"notify_game_register_task: 알림 생성 완료 (user_id={user_id}, game_id={game_id})")
    except Exception as e:
        logger.error(f"notify_game_register_task: 알림 생성 실패 (user_id={user_id}, game_id={game_id}): {e}", exc_info=True)


ZIP_RESULT_KIND = "game_zip_validation"
ZIP_RESULT_SCHEMA_VERSION = 1


def _zip_result(game_id, file_key, outcome, reason_code=None, reason=None):
    """validate_game_zip_task 반환값. Celery 상태(SUCCESS)와 별개로 파일 판정을 담는다."""
    return {
        "kind": ZIP_RESULT_KIND,
        "schema_version": ZIP_RESULT_SCHEMA_VERSION,
        "game_id": game_id,
        "file_key": file_key,
        "outcome": outcome,  # valid / invalid / skipped
        "reason_code": reason_code,
        "reason": reason,
    }


def _reject_invalid_zip(game_id, file_key, error_msg):
    """
    현재 파일이 file_key이고 검수 대기(0)일 때만 반려(2)한다.
    갱신된 행이 없으면(재실행, 파일 교체) 로그·알림을 만들지 않는다.
    """
    updated = Game.objects.filter(
        pk=game_id, gamefile=file_key, register_state=0, is_visible=True
    ).update(register_state=2)
    if not updated:
        return False

    game = Game.objects.select_related("maker").get(pk=game_id)
    try:
        game.logs_game.create(
            recoder=game.maker,
            maker=game.maker,
            game=game,
            content=f"zip 검증 실패: {error_msg}",
        )
    except Exception:
        logger.error(f"Failed to write zip reject log for game {game.id}", exc_info=True)
    try:
        create_notification(
            user=game.maker,
            noti_type=Notification.NotificationType.GAME_UPLOAD,
            noti_sub_type=NotificationSubType.REGISTER_REJECT,
            related_object=game,
            game_title=game.title,
        )
    except Exception:
        logger.error(f"Failed to notify zip reject for game {game.id}", exc_info=True)
    return True


def _is_current_pending_file(game_id, file_key):
    return Game.objects.filter(
        pk=game_id, gamefile=file_key, register_state=0, is_visible=True
    ).exists()


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def validate_game_zip_task(self, game_id, file_key=None):
    """
    S3에 올라간 게임 zip(file_key)을 다운로드해 검증하고 판정 dict를 반환한다.
    valid: is_used=true 태깅, invalid: register_state=2 (반려),
    skipped: 게임이 없거나 파일이 교체되어 결과를 적용하지 않음.
    검증을 실행하지 못한 채 재시도를 소진하면 예외를 그대로 올려 FAILURE로 남긴다.
    """
    if file_key is None:
        # 배포 전 큐에 남은 구형 인자 작업. 운영자가 현재 파일로 재발행한다.
        logger.warning(f"validate_game_zip_task: legacy args for game {game_id}, skipped")
        return _zip_result(game_id, None, "skipped", "LEGACY_ARGS")

    if not _is_current_pending_file(game_id, file_key):
        logger.info(f"validate_game_zip_task: game {game_id} not pending or file replaced")
        return _zip_result(game_id, file_key, "skipped", "FILE_REPLACED")

    tmp_path = None
    try:
        s3 = get_s3_client()
        object_key = f"media/{file_key}"

        try:
            zip_resp = s3.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=object_key)
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code", "")
            if code in ("404", "403", "NoSuchKey", "NotFound"):
                error_msg = "업로드된 게임 파일을 찾을 수 없습니다."
                if not _reject_invalid_zip(game_id, file_key, error_msg):
                    return _zip_result(game_id, file_key, "skipped", "FILE_REPLACED")
                return _zip_result(game_id, file_key, "invalid", "FILE_NOT_FOUND", error_msg)
            raise

        with NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            for chunk in zip_resp["Body"].iter_chunks(chunk_size=8192):
                tmp_file.write(chunk)
            tmp_path = tmp_file.name

        with open(tmp_path, "rb") as zip_fp:
            zip_fp.size = os.path.getsize(tmp_path)
            is_valid, error_msg = validate_zip_file(zip_fp)

        # 검사 중 파일이 교체되었으면 결과를 적용하지 않는다.
        if not _is_current_pending_file(game_id, file_key):
            return _zip_result(game_id, file_key, "skipped", "FILE_REPLACED")

        if is_valid:
            # 태깅 실패 시 예외 → 재시도. 보존 태그 없이 valid를 반환하지 않는다.
            safe_s3_tag(s3, AWS_S3_BUCKET_NAME, object_key, {"is_used": "true"})
            return _zip_result(game_id, file_key, "valid")

        if not _reject_invalid_zip(game_id, file_key, error_msg):
            return _zip_result(game_id, file_key, "skipped", "FILE_REPLACED")
        return _zip_result(game_id, file_key, "invalid", "INVALID_ZIP", error_msg)
    except Exception as e:
        logger.error(f"Error in validate_game_zip_task for game {game_id}: {e}", exc_info=True)
        if self.request.retries >= self.max_retries:
            logger.error(f"validate_game_zip_task retries exhausted for game {game_id}")
            raise  # FAILURE로 기록
        raise self.retry(exc=e)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning(f"Failed to remove temp zip {tmp_path}")
