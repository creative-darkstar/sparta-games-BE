import uuid
import logging

from spartagames.logging_context import set_request_context, clear_request_context


logger = logging.getLogger("sparta_games")

class WebSocketLoggingMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # HTTP는 그냥 통과시켜서 중복 방지
        if scope.get("type") != "websocket":
            return await self.app(scope, receive, send)

        # request_id 생성
        request_id = str(uuid.uuid4())
        scope["request_id"] = request_id

        path = scope.get("path", "-")

        # WebSocket용 request context 임시 세팅 (consumers.py 의 NotificationConsumer.connect 메서드에서 제대로 세팅)
        set_request_context(
            request_id=request_id,
            user_id="anonymous",
            path=path,
            method="WEBSOCKET",
        )

        async def send_wrapper(message):
            # 필요하면 여기서 close / 에러 관련 로그 추가 가능
            return await send(message)

        try:
            return await self.app(scope, receive, send_wrapper)
        finally:
            logger.info("websocket_disconnect")
            clear_request_context()
