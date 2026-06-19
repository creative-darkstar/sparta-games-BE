from games.serializers import GameListSerializer


class MyGameListSerializer(GameListSerializer):
    """
    GameListSerializer를 상속하여 chips/is_liked/star/maker_data/category_data 로직을 공유한다.
    유저 페이지 개발목록 용도로 register_state 필드만 추가로 노출한다.
    """
    class Meta(GameListSerializer.Meta):
        fields = GameListSerializer.Meta.fields + ("register_state",)
