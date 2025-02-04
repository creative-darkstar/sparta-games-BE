from django.db.models import Avg
from .models import Chip

from PIL import Image
import zipfile

def validate_image(image, max_width=1000, max_height=800, max_size=5 * 1024 * 1024):
    """
    이미지 파일의 크기 및 해상도를 검증하는 함수
    """
    try:
        img = Image.open(image)
        width, height = img.size

        if width > max_width or height > max_height:
            return False, f"이미지 크기는 최대 {max_width}x{max_height}px 이어야 합니다. 현재: {width}x{height}px"
        
        if image.size > max_size:
            return False, f"이미지 파일 크기는 최대 {max_size / (1024 * 1024)}MB 이어야 합니다."
        
        return True, None
    except Exception:
        return False, "유효한 이미지 파일이 아닙니다."

def validate_zip_file(zip_file, max_size=200 * 1024 * 1024):
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