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


def _notify_zip_rejection(game_id, file_key):
    from django.db import transaction
    with transaction.atomic():
        game = Game.objects.select_for_update().filter(pk=game_id, gamefile=file_key, register_state=2, is_visible=True).first()
        if game:
            create_notification(user=game.maker, noti_type=Notification.NotificationType.GAME_UPLOAD,
                                noti_sub_type=NotificationSubType.REGISTER_REJECT,
                                related_object=game, game_title=game.title)


@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def validate_game_zip_task(self, game_id, file_key=None, submission_id=None):
    from django.db import transaction

    def outcome(value, reason=None, code=None):
        return dict(kind="game_zip_validation", schema_version=1, game_id=game_id,
                    submission_id=submission_id, outcome=value, reason_code=code, reason=reason)

    # Legacy queued arguments cannot identify which submission they belong to.
    if not file_key or not submission_id:
        return outcome("skipped", "제출 식별자가 없는 이전 작업입니다.", "LEGACY_TASK")
    tmp_path = None
    try:
        game = Game.objects.filter(pk=game_id, is_visible=True, gamefile=file_key).first()
        if not game:
            return outcome("skipped")
        s3 = get_s3_client()
        object_key = f"media/{file_key}"
        try:
            zip_resp = s3.get_object(Bucket=AWS_S3_BUCKET_NAME, Key=object_key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("404", "NoSuchKey", "NotFound"):
                is_valid, error_msg = False, "업로드된 게임 파일을 찾을 수 없습니다."
            else:
                raise
        else:
            with NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
                tmp_path = tmp_file.name
                try:
                    for chunk in zip_resp["Body"].iter_chunks(chunk_size=8192):
                        tmp_file.write(chunk)
                finally:
                    zip_resp["Body"].close()
            with open(tmp_path, "rb") as zip_fp:
                zip_fp.size = os.path.getsize(tmp_path)
                is_valid, error_msg = validate_zip_file(zip_fp)
        if is_valid:
            # Tag failure must propagate into retry/FAILURE, never SUCCESS/valid.
            safe_s3_tag(s3, AWS_S3_BUCKET_NAME, object_key, {"is_used": "true"})
        with transaction.atomic():
            game = Game.objects.select_for_update().filter(pk=game_id, is_visible=True).first()
            if not game or game.gamefile.name != file_key:
                return outcome("skipped")
            if is_valid:
                return outcome("valid")
            if game.register_state == 1:
                return outcome("skipped")
            marker = f"zip 검증 실패 [{submission_id}]: {error_msg}"
            if not game.logs_game.filter(content=marker).exists():
                game.register_state = 2
                game.save(update_fields=["register_state"])
                game.logs_game.create(recoder=game.maker, maker=game.maker, game=game, content=marker)
                transaction.on_commit(lambda: _notify_zip_rejection(game_id, file_key), robust=True)
            code = "SYMLINK_NOT_ALLOWED" if "심볼릭" in (error_msg or "") else "INVALID_ZIP"
            return outcome("invalid", error_msg, code)
    except Exception as exc:
        logger.exception("ZIP validation execution failed: game %s", game_id)
        raise self.retry(exc=exc)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                logger.warning("Temporary ZIP cleanup failed")
