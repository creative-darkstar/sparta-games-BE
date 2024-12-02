from celery import shared_task
from games.models import Game, Chip
from django.db.models import Count

# 칩을 초기화하고, 상위 4개의 좋아요가 많은 게임에 새 칩을 부여하는 태스크
@shared_task
def assign_chips_to_top_games():
    
    # 'Daily Top' 칩 가져오기 (없으면 생성)
    chip, _ = Chip.objects.get_or_create(name='Daily Top')

    # 'Daily Top' 칩이 이미 존재하는 게임만 필터링하여 칩 제거
    games_with_chip = Game.objects.filter(chip=chip)
    for game in games_with_chip:
        game.chip.remove(chip)

    # 좋아요가 가장 많은 상위 4개 게임을 가져옴
    top_games = Game.objects.annotate(like_count=Count('likes')).filter(is_visible=True,register_state=True,like_count__gte=1).order_by('-like_count')[:4]

    # 상위 4개 게임이 없을 경우 메시지 반환
    if not top_games:
        return "현재 상위 게임이 없습니다."

    # 상위 4개 게임에 'Daily Top' 칩 추가
    for game in top_games:
        game.chip.add(chip)
    
    return f"Assigned 'Daily Top' chip to {len(top_games)} games"

@shared_task
def cleanup_new_game_chip():
    # 'New Game' 칩 가져오기
    new_game_chip = Chip.objects.filter(name='New Game').first()
    if not new_game_chip:
        return "새로 생성된 게임 칩이 달린 게임이 없습니다."

    # 현재 존재하는 'New Game' 칩을 제거
    games_with_new_game = Game.objects.filter(chip=new_game_chip)
    for game in games_with_new_game:
        game.chip.remove(new_game_chip)

    return f"Removed 'New Game' chip from {len(games_with_new_game)} games."