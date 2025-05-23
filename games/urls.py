from django.urls import path
from . import views


app_name = "games"

urlpatterns = [
    # ---------- API---------- #
    path("api/list/", views.GameListAPIView.as_view(), name="game_list"),
    path("api/list/search/", views.game_list_search, name="search"),
    path('api/list/categories/', views.category_games_list, name='category_games_list'),
    path("api/list/<int:game_id>/", views.GameDetailAPIView.as_view(), name="game_detail"),
    path("api/list/<int:game_id>/like/", views.GameLikeAPIView.as_view(), name="game_like"),
    # path("api/list/<int:game_pk>/star/", views.GameStarAPIView.as_view(), name="game_star"),
    path("api/list/<int:game_id>/reviews/", views.ReviewAPIView.as_view(), name="reviews"),
    path('api/review/<int:review_id>/', views.ReviewDetailAPIView.as_view(), name='review_detail'),
    path('api/review/<int:review_id>/like/', views.toggle_review_like, name='toggle_review_like'),
    path("api/categories/", views.CategoryAPIView.as_view(), name="categories"),
    path("api/list/<int:game_id>/playlog/", views.GamePlaytimeAPIView.as_view(), name="playlog"),
    path('api/chatbot/', views.ChatbotAPIView, name='chatbot'),

    # ---------- Web ---------- #
    # path("list/<int:game_pk>/", views.game_detail_view, name="game_detail_page"),
    # path("list/<int:game_pk>/update/", views.game_update_view, name="game_update_page"),
    # path("list/create/", views.game_create_view, name="game_create_page"),
    # path("admin/list/", views.admin_list, name="admin_list"),
    # path("admin/categories/", views.admin_category, name="admin_categories"),
    # path("chatbot/",views.chatbot_view,name="chatbot_view"),
]
