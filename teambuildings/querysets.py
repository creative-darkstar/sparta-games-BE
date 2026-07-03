"""
팀빌딩 앱 목록 조회용 queryset 최적화 헬퍼.

시리얼라이저가 author(FK), want_roles/game_genre(M2M), my_role(FK)을 참조하면서
발생하는 N+1 쿼리를 select_related / prefetch_related 로 제거한다.
"""


def with_teambuild_post_list_optimizations(qs):
    """TeamBuildPost 목록: author(FK) + want_roles(M2M)"""
    return qs.select_related("author").prefetch_related("want_roles")


def with_teambuild_profile_list_optimizations(qs):
    """TeamBuildProfile 목록: author/my_role(FK) + game_genre(M2M)"""
    return qs.select_related("author", "my_role").prefetch_related("game_genre")


def with_teambuild_comment_list_optimizations(qs):
    """TeamBuildPostComment 목록: author(FK)"""
    return qs.select_related("author")
