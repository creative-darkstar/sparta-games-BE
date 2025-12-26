"""
ASGI config for spartagames project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# from django.core.asgi import get_asgi_application

import spartagames.routing
from spartagames.custom_ws_middleware import WebSocketLoggingMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'spartagames.settings')

# application = get_asgi_application()

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    # WebSocket 연결 라우팅을 여기에 추가
    "websocket": WebSocketLoggingMiddleware(
        # AuthMiddlewareStack(
        #     URLRouter(
        #         spartagames.routing.websocket_urlpatterns
        #     )
        # )
        URLRouter(
            spartagames.routing.websocket_urlpatterns
        )
    ),
})