from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class CustomPagination(PageNumberPagination):
    page_size = 4  # 기본 페이지 크기
    page_size_query_param = 'limit'  # 클라이언트가 페이지 크기를 제어
    page_query_param = 'page'  # 페이지 번호 쿼리 파라미터
    max_page_size = 100  # 최대 허용 페이지 크기

    def paginate_queryset(self, queryset, request, view=None):
        """
        빈 값을 추가하고 총 개수를 조정합니다.
        """
        # 데이터가 리스트인지 QuerySet인지 확인
        if not hasattr(queryset, 'count'):
            queryset = list(queryset)

        # 총 개수 계산 (빈 값 포함)
        self.total_count = len(queryset)
        
        # 부모 클래스의 paginate_queryset 호출
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        """
        페이지네이션된 응답을 반환.
        """
        return Response({
            "count": self.total_count,  # 총 개수 (빈 값 포함)
            "next": self.get_next_link(),
            "previous": self.get_previous_link(),
            "results": {
                "all_games": data,  # 페이지네이션된 데이터
            },
        })