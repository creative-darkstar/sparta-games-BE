from rest_framework.pagination import CursorPagination

class NotificationPagination(CursorPagination):
    page_size = 6  # 기본 페이지 크기 설정
    ordering = '-create_dt'
