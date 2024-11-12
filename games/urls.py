from django.urls import path
from . import views


app_name = "games"

urlpatterns = [
    # ---------- API---------- #
    path("api/list/", views.GameListAPIView.as_view(), name="game_list"),
    path("api/list/<int:game_pk>/", views.GameDetailAPIView.as_view(), name="game_detail"),
    path("api/list/<int:game_pk>/like/", views.GameLikeAPIView.as_view(), name="game_like"),
    # path("api/list/<int:game_pk>/star/", views.GameStarAPIView.as_view(), name="game_star"),
    path("api/list/<int:game_pk>/reviews/", views.ReviewAPIView.as_view(), name="reviews"),
    path('api/review/<int:review_id>/', views.ReviewDetailAPIView.as_view(), name='review_detail'),
    path('api/review/<int:review_id>/like/', views.toggle_review_like, name='toggle_review_like'),
    path("api/categories/", views.CategoryAPIView.as_view(), name="categories"),
    path("api/list/<int:game_pk>/playtimeenter/", views.game_playtime_enter, name="game_playtime_enter"),
    path("api/list/<int:game_pk>/playtimeexit/", views.game_playtime_exit, name="game_playtime_exit"),
    path("api/list/<int:game_pk>/register/", views.game_register, name="game_register"),
    path("api/list/<int:game_pk>/deny/", views.game_register_deny, name="game_register_deny"),
    path('api/list/<int:game_pk>/dzip/', views.game_dzip, name='game_dzip'),
    path('api/chatbot/', views.ChatbotAPIView, name='chatbot'),

    # ---------- Web ---------- #
    # path("list/<int:game_pk>/", views.game_detail_view, name="game_detail_page"),
    # path("list/<int:game_pk>/update/", views.game_update_view, name="game_update_page"),
    # path("list/create/", views.game_create_view, name="game_create_page"),
    # path("admin/list/", views.admin_list, name="admin_list"),
    # path("admin/categories/", views.admin_category, name="admin_categories"),
    # path("chatbot/",views.chatbot_view,name="chatbot_view"),
]
