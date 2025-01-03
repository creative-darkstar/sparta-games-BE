from django.urls import path
from . import views


# app_name = "qnas" #2024-01-03 API 기능만 있으므로 DTL에서 사용하는 app_name은 주석 처리

urlpatterns = [
    # ---------- API---------- #
    path("api/qna/", views.QnAPostListAPIView.as_view(), name="qna_list"),
    path("api/qna/<int:qna_pk>/", views.QnADetailAPIView.as_view(), name="qna_detail"),
    path('api/qna/categories/', views.CategoryListView.as_view(), name='category_list'),

    # 2025-01-03 관리자 페이지에 있을 기능을 games -> qnas 로 이관
    path("api/admin/stats/", views.get_stats, name="game_stats"),
    path("api/admin/list/", views.game_register_list, name="game_register_list"),
    path("api/admin/list/<int:game_pk>/", views.game_register_logs_all, name="game_register_logs_all"),
    path("api/list/<int:game_pk>/register/", views.game_register, name="game_register"),
    path("api/list/<int:game_pk>/deny/", views.game_register_deny, name="game_register_deny"),
    path("api/denylog/<int:game_pk>/", views.deny_log, name="deny_log"),
    path('api/list/<int:game_pk>/dzip/', views.game_dzip, name='game_dzip'),
    # 작업예정
    # path('api/admin/makers/', views.maker_list, name='maker_list'),
    
    # 2025-01-03 웹 기능 비활성화
    # # ---------- Web---------- #
    # path("", views.qna_main_view, name="qna_main"),
    # path("<int:qna_pk>/", views.qna_detail_view, name="qna_detail_page"),
    # path("create/", views.qna_create_view, name="qna_create"),
    # path("<int:qna_pk>/update/", views.qna_update_view, name="qna_update"),
]
