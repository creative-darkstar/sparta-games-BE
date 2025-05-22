from rest_framework import serializers
from games.models import Game, Like

class MyGameListSerializer(serializers.ModelSerializer):
    maker_data = serializers.SerializerMethodField()
    chips= serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = (
            "id", "title", "thumbnail", "star", "content", "register_state",
            "maker_data", "chips", "is_liked", "category_data"
        )
    
    def get_maker_data(self, obj):
        return {
            "id": obj.maker.id,
            "nickname": obj.maker.nickname,
        }
    
    def get_chips(self, obj):
        chips = obj.chip.all()
        difficulty_chips = ["EASY", "NORMAL", "HARD"]
        priority_chips = ["Daily Top", "New Game", "Bookmark Top", "Long Play", "Review Top"]

        result = []

        # 난이도 칩 하나 선택
        difficulty_chip = chips.filter(name__in=difficulty_chips).first()
        if difficulty_chip:
            result.append({"id": difficulty_chip.id, "name": difficulty_chip.name})

        # 우선순위 칩 최대 2개 추가
        for chip_name in priority_chips:
            if len(result) >= 3:
                break
            chip = chips.filter(name=chip_name).first()
            if chip:
                result.append({"id": chip.id, "name": chip.name})

        return result
    
    def get_is_liked(self, obj):
        user = self.context.get('user')
        # 사용자가 인증된 경우 해당 게임에 대한 좋아요 상태를 확인
        if user and user.is_authenticated:
            return Like.objects.filter(user=user, game=obj).exists()
        return False
    
    def get_category_data(self, obj):
        # 카테고리 리스트를 반환
        return [{"id": category.id, "name": category.name,} for category in obj.category.all()]
