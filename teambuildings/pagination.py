# pagination.py

from rest_framework.pagination import PageNumberPagination


class TeamBuildPostPagination(PageNumberPagination):
    page_size = 12  # 기본 페이지 크기 설정
    page_size_query_param = 'limit'  # 클라이언트가 페이지 크기를 조정할 수 있는 파라미터
    page_query_param = 'page'  # 페이지 번호를 지정하는 쿼리 파라미터
    max_page_size = 100  # 허용되는 최대 페이지 크기


class TeamBuildProfileListPagination(PageNumberPagination):
    page_size = 12
    page_size_query_param = 'limit'
    page_query_param = 'page'
    max_page_size = 100


class TeamBuildPostCommentPagination(PageNumberPagination):
    page_size = 7
    page_size_query_param = 'limit'
    page_query_param = 'page'
    max_page_size = 100
