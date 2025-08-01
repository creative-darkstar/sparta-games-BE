from PIL import Image
import requests
import zipfile

from django.db.models import Avg
from .models import Chip

from spartagames.config import DISCORD_GAME_UPLOAD_CHANNEL_WEBHOOK_URL
from spartagames.exceptions import DiscordAlertException


def validate_image(image):
    """
    이미지 파일 형식만 검증하는 함수 (확장자 무관)
    """
    try:
        img = Image.open(image)
        img.verify()  # 파일 손상 여부 확인

        # 확실한 검증을 위해 다시 열어서 실제로 로드해보기
        img = Image.open(image)
        img.load()  # 로드 과정에서 오류 발생 시 비정상적인 이미지

        return True, None
    except Exception:
        return False, "유효한 이미지 파일이 아닙니다."

def validate_zip_file(zip_file, max_size=500 * 1024 * 1024):
    """
    ZIP 파일의 크기 및 형식을 검증하는 함수
    """
    if not zip_file.name.endswith('.zip'):
        return False, "ZIP 파일만 업로드 가능합니다."

    if zip_file.size > max_size:
        return False, f"ZIP 파일 크기는 최대 {max_size / (1024 * 1024)}MB 이어야 합니다."

    try:
        with zipfile.ZipFile(zip_file, 'r') as zf:
            if zf.testzip() is not None:
                return False, "손상된 ZIP 파일입니다."
    except zipfile.BadZipFile:
        return False, "유효한 ZIP 파일이 아닙니다."

    return True, None

def assign_chip_based_on_difficulty(game):
    """
    게임에 난이도 칩 부여 (EASY, NORMAL, HARD)
    난이도 평균을 이용함
    """
    #게임에 대한 평균 난이도
    average_difficulty = game.reviews.filter(is_visible=True).aggregate(
        average_difficulty=Avg('difficulty')
    )['average_difficulty'] or 0

    easy_chip, _ = Chip.objects.get_or_create(name="EASY")
    normal_chip, _ = Chip.objects.get_or_create(name="NORMAL")
    hard_chip, _ = Chip.objects.get_or_create(name="HARD")

    #기존 칩 제거
    game.chip.remove(easy_chip, normal_chip, hard_chip)

    #기준에 맞게 칩 부여
    if average_difficulty < 0.7:
        game.chip.add(easy_chip)
    elif average_difficulty > 1.3:
        game.chip.add(hard_chip)
    else:
        game.chip.add(normal_chip)


def send_discord_notification(game, msg_text="📢 새로운 게임이 업로드되었습니다! 관리자 계정으로 확인해주세요.\n"):
    webhook_url = DISCORD_GAME_UPLOAD_CHANNEL_WEBHOOK_URL

    message = {
        "content": f"""
{msg_text}
🎮 게임명: {game.title}\n"
👤 업로더: {game.maker.nickname}\n
"""
    }

    try:
        resp = requests.post(webhook_url, json=message)
        # resp.raise_for_status()
    except Exception as e:
        # logger 도입하는대로 해당 코드 라인은 살릴 예정
        # 지금은 print 처리
        # raise DiscordAlertException
        # 실패 시 로깅 처리
        print(f"Discord 알림 실패: {e}")
