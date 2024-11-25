from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    page_size = 20  # 기본 페이지 크기
    page_size_query_param = 'limit'  # 클라이언트가 페이지 크기를 제어
    page_query_param = 'page'  # 페이지 번호 쿼리 파라미터
    max_page_size = 100  # 최대 허용 페이지 크기