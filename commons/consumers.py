# notifications/consumers.py
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async

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

        if user.is_authenticated:
            await self.channel_layer.group_add(f"user_{user.id}", self.channel_name)
            await self.accept(subprotocol=self.scope["subprotocols"][0] if self.scope.get("subprotocols") else None)
        else:
            await self.close()

    async def disconnect(self, close_code):
        user = self.scope["user"]
        await self.channel_layer.group_discard(f"user_{user.id}", self.channel_name)

    async def notify(self, event):
        await self.send_json(event["content"])

 # 동기 함수 정의
    def get_user_from_token(self, validated_token):
        from rest_framework_simplejwt.authentication import JWTAuthentication

        auth = JWTAuthentication()
        user, _ = auth.get_user(validated_token), validated_token
        return user