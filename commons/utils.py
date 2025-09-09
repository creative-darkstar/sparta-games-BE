from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from enum import Enum

from django.contrib.contenttypes.models import ContentType
from .models import Notification


# class NOTI_MESSAGE_TEMPLATES(str, Enum):
class NotificationSubType(str, Enum):
    REGISTER_REQUEST = "검수요청"
    REGISTER_APPROVE = "검수승인"
    REGISTER_REJECT = "검수반려"
    REVIEW_REGISTER = "리뷰등록"
    COMMENT_REGISTER = "댓글등록"
    POPULAR = "인기급상승"


NOTI_MESSAGE_TEMPLATES = {
    NotificationSubType.REGISTER_REQUEST: lambda title: f"[검수요청] '{title}' 게임이 성공적으로 접수되었습니다.",
    NotificationSubType.REGISTER_APPROVE: lambda title: f"[검수승인] '{title}' 게임이 검수를 통과하였습니다.\n‘새로 등록된 게임’ 상단에 30일간 등록됩니다.",
    NotificationSubType.REGISTER_REJECT: lambda title: f"[검수반려] '{title}' 게임이 검수가 반려되었습니다.\n[마이페이지 → 개발목록]에서 확인해주세요.",
    NotificationSubType.REVIEW_REGISTER: lambda title: f"[리뷰등록] '{title}' 게임에 새로운 리뷰가 등록되었습니다.",
    NotificationSubType.COMMENT_REGISTER: lambda _: "[댓글등록] 등록한 게시글에 새로운 댓글이 등록되었습니다.",
    NotificationSubType.POPULAR: lambda title: f"[인기급상승] '{title}' 게임이 인기급상승 게임으로 선정되었습니다.\n메인 홈 ‘인기급상승 게임’ 상단에 등록됩니다.",
}


def create_notification(user, noti_type, noti_sub_type, related_object=None, game_title=None):

    message_func = NOTI_MESSAGE_TEMPLATES.get(noti_sub_type)
    if message_func:
        message = message_func(game_title)
    else:
        message = "새로운 알림이 도착했습니다."

    content_type = None
    content_id = None
    if related_object:
        content_type = ContentType.objects.get_for_model(related_object)
        content_id = related_object.pk

    notif = Notification.objects.create(
        user=user,
        noti_type=noti_type,
        message=message,
        content_type=content_type,
        content_id=content_id
    )

    # 실시간 전송 (Django Channels)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "notify",
            "content": {
                "id": notif.id,
                "noti_type": notif.noti_type,
                "message": notif.message,
                "create_dt": notif.create_dt.isoformat(),
                "is_read": notif.is_read,
            }
        }
    )

    return notif
