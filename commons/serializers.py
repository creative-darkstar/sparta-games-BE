from rest_framework import serializers
from .models import Notification


class ChoiceDisplayField(serializers.ChoiceField):
    def to_representation(self, value):
        # 라벨로 변환해서 응답
        if value in ('', None):
            return value
        return self._choices.get(value, value)


class NotificationSerializer(serializers.ModelSerializer):
    noti_type = ChoiceDisplayField(choices=Notification.NotificationType.choices)

    class Meta:
        model = Notification
        fields = [
            "id", "noti_type", "content_id", "message",
            "is_read", "create_dt"
        ]
