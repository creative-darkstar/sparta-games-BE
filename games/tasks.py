from celery import shared_task
from games.models import Game, Chip
from django.db.models import Count

# 칩을 초기화하고, 상위 4개의 좋아요가 많은 게임에 새 칩을 부여하는 태스크
@shared_task
def assign_chips_to_top_games():
    # Step 1: 모든 게임에서 기존 칩을 초기화 (제거)
    all_games = Game.objects.all()
    for game in all_games:
        game.chip.clear()  # 모든 칩을 제거

    # Step 2: 가장 좋아요가 많은 상위 4개의 게임을 선택
    top_games = Game.objects.annotate(like_count=Count('likes')).order_by('-like_count','created_at')[:4]

    # Step 3: 새로운 칩을 생성하거나 기존 칩을 가져옴
    chip, created = Chip.objects.get_or_create(name='Daily Top')

    # Step 4: 상위 4개의 게임에 새로 칩을 부여
    for game in top_games:
        game.chip.add(chip)

    return f"Assigned 'Daily Top' chip to {len(top_games)} games after resetting all chips."