"""
qnas 앱 목록 조회용 queryset 최적화 헬퍼.
"""
from django.db.models import Prefetch

from .models import GameRegisterLog


def with_game_register_list_optimizations(qs):
    """
    관리자 게임 등록 목록(GameRegisterListSerializer)용 최적화.
    - maker(FK) select_related
    - category(M2M) prefetch_related
    - logs_game(역참조)는 최신순으로 Prefetch (시리얼라이저에서 상위 2개만 사용)
    """
    return qs.select_related("maker").prefetch_related(
        "category",
        Prefetch(
            "logs_game",
            queryset=GameRegisterLog.objects.order_by("-created_at"),
        ),
    )
