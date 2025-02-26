from datetime import timedelta
from django.utils import timezone
from celery import shared_task
from django.db.models import Count, Q,Sum
from .models import Game, Chip


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
        
        return f"Assigned 'Daily Top' chip to {len(top_games)} games."
    except Exception as e:
        # 예외 발생 시 로그 남기기 (추가적인 로깅 설정 필요 시 설정)
        return f"Error in assigning 'Daily Top' chips: {str(e)}"


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
        
        return f"Removed 'New Game' chip from {len(games_with_new_game)} games."
    except Exception as e:
        return f"Error in cleaning up 'New Game' chips: {str(e)}"


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
        
        return f"Assigned 'Bookmark Top' chip to {len(top_bookmarked_games)} games."
    except Exception as e:
        # 예외 발생 시 로그 남기기 (추가적인 로깅 설정 필요 시 설정)
        return f"Error in assigning 'Bookmark Top' chips: {str(e)}"
    
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
        
        return f"Assigned 'Long Play' chip to {len(top_long_play_games)} games."
    except Exception as e:
        return f"Error in assigning 'Long Play' chips: {str(e)}"
    
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
        
        return f"Assigned 'Review Top' chip to {len(top_reviewed_games)} games."
    except Exception as e:
        return f"Error in assigning 'Review Top' chips: {str(e)}"