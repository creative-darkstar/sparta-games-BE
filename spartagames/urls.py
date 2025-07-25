"""
URL configuration for spartagames project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from games import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # ---------- Include ---------- #
    path('accounts/', include('accounts.urls')),
    path('oauth/', include('allauth.urls')),
    path('users/', include('users.urls')),
    path('games/', include('games.urls')),
    path('directs/', include('qnas.urls')),    #2025-01-03 기존 qnas 앱은 놔두고 url 패턴 수정
    path('teams/', include('teambuildings.urls')),
    path('commons/', include('commons.urls')),

    # ---------- Web ---------- #
    # path('', views.main_view, name='main_view'),
    # path('search/', views.search_view, name='search_view'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
