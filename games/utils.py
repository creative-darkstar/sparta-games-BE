from django.db.models import Avg
from .models import Chip

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