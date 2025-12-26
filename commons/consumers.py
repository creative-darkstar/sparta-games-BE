# notifications/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async
import logging

from spartagames.logging_context import set_request_context


logger = logging.getLogger("sparta_games")


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        from django.contrib.auth.models import AnonymousUser
        from rest_framework_simplejwt.tokens import UntypedToken
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from urllib.parse import parse_qs

        # 쿼리스트링에서 token 가져오기
        # 보안 이슈로 주석 처리
        # query_string = self.scope["query_string"].decode()
        # qs = parse_qs(query_string)
        # token = qs.get("token", [None])[0]

        user = AnonymousUser()
         # subprotocol에서 토큰 가져오기
        if self.scope.get("subprotocols"):
            token = self.scope["subprotocols"][1]  # ["access_token", "<JWT>"]
            try:
                validated_token = UntypedToken(token)
                user = await sync_to_async(self.get_user_from_token)(validated_token)
            except Exception as e:
                print("JWT 인증 실패:", e)

        self.scope["user"] = user

        request_id = self.scope.get("request_id", None)
        path = self.scope.get("path", "/ws/notifications/")

        set_request_context(
            request_id=request_id or "ws-no-request-id",
            user_id=(user.id if getattr(user, "is_authenticated", False) else "anonymous"),
            path=path,
            method="WEBSOCKET",
        )

        if user.is_authenticated:
            await self.channel_layer.group_add(f"user_{user.id}", self.channel_name)
            await self.accept(subprotocol=self.scope["subprotocols"][0] if self.scope.get("subprotocols") else None)
            logger.info("notification_websocket connect")
        else:
            await self.close()
            logger.info("notification_websocket close because of anonymous user")

    async def disconnect(self, close_code):
        user = self.scope["user"]
        await self.channel_layer.group_discard(f"user_{user.id}", self.channel_name)
        logger.info(f"notification_websocket disconnect: {close_code}")

    async def notify(self, event):
        logger.info(f"notification_websocket event received: {event}")
        await self.send_json(event["content"])
        logger.info(f"notification_websocket sent: {event['content']}")

 # 동기 함수 정의
    def get_user_from_token(self, validated_token):
        from rest_framework_simplejwt.authentication import JWTAuthentication

        auth = JWTAuthentication()
        user, _ = auth.get_user(validated_token), validated_token
        return user