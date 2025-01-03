# pagination.py

from rest_framework.pagination import PageNumberPagination

class GameRegisterListPagination(PageNumberPagination):
    page_size = 8  # 기본 페이지 크기 설정
    page_size_query_param = 'limit'  # 클라이언트가 페이지 크기를 조정할 수 있는 파라미터
    page_query_param = 'page'  # 페이지 번호를 지정하는 쿼리 파라미터
    max_page_size = 100  # 허용되는 최대 페이지 크기
