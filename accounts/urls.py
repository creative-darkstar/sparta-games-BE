from django.urls import path, include
from . import views
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenBlacklistView,
    TokenVerifyView,
)


app_name = "accounts"

urlpatterns = [
    # ---------- API---------- #
    path("api/login/", TokenObtainPairView.as_view(), name='login'),
    path("api/refresh/", TokenRefreshView.as_view(), name='refresh_token'),
    path("api/logout/", TokenBlacklistView.as_view(), name='logout'),
    path("api/signup/", views.SignUpAPIView.as_view(), name='signup'),
    path("api/verify/", TokenVerifyView.as_view(), name='verify'),
    
    # --- Social Login API --- #
    path("api/google/callback/", views.google_login_callback, name='google_callback'),
    path("api/naver/login/", views.NaverLoginAPIView.as_view(), name='naver_login'),
    path("api/naver/callback/", views.NaverCallbackAPIView.as_view(), name='naver_callback'),
    path("api/kakao/callback/", views.kakao_login_callback, name='kakao_callback'),

    # ---------- Web---------- #
    path('login/', views.login_page, name='login_page'),
    path('signup/', views.signup_page, name='signup_page'),
]
