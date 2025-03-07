# pagination.py

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CategoryGamesPagination(PageNumberPagination):
    page_size = 16  # 기본 페이지 크기 설정
    page_size_query_param = 'limit'  # 클라이언트가 페이지 크기를 조정할 수 있는 파라미터
    page_query_param = 'page'  # 페이지 번호를 지정하는 쿼리 파라미터
    max_page_size = 100  # 허용되는 최대 페이지 크기

class ReviewPagination(PageNumberPagination):
    page_size = 6  # 기본 페이지 크기 설정
    page_size_query_param = 'limit'  # 클라이언트가 페이지 크기를 조정할 수 있는 파라미터
    page_query_param = 'page'  # 페이지 번호를 지정하는 쿼리 파라미터
    max_page_size = 100  # 허용되는 최대 페이지 크기

    def get_paginated_response(self, data):
        """
        전체 리뷰 개수를 정확히 반환.
        """
        return Response({
            "count": self.page.paginator.count-1,
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": {
                "all_reviews": data,
            },
        })