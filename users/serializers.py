from rest_framework import serializers

from games.serializers import GameListSerializer, get_zip_task_id_for


class MyGameListSerializer(GameListSerializer):
    """
    GameListSerializer를 상속하여 chips/is_liked/star/maker_data/category_data 로직을 공유한다.
    유저 페이지 개발목록 용도로 register_state와 ZIP 검증 task_id(본인·관리자 조회 시)를 추가로 노출한다.
    """
    zip_task_id = serializers.SerializerMethodField()

    class Meta(GameListSerializer.Meta):
        fields = GameListSerializer.Meta.fields + ("register_state", "zip_task_id")

    def get_zip_task_id(self, obj):
        # context["user"]는 프로필 주인, context["viewer"]는 실제 요청자
        return get_zip_task_id_for(obj, self.context.get("viewer"))
