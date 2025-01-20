from rest_framework import serializers
from games.models import Game, Like

class MyGameListSerializer(serializers.ModelSerializer):
    maker_name = serializers.CharField(source='maker.nickname')
    chip_names= serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = (
            "pk", "title", "thumbnail", "star", "content", "register_state",
            "maker_name", "chip_names", "is_liked", "category_name"
        )
    
    def get_chip_names(self, obj):
        #칩 우선순위 리스트
        priority_chips = ["Daily Top", "New Game", "Bookmark Top", "Long Play", "Review Top"]
        chips = obj.chip.all()
        difficulty_chips = ["EASY", "NORMAL", "HARD"]
        difficulty_chip = chips.filter(name__in=difficulty_chips).first()
        result = [difficulty_chip.name] if difficulty_chip else []

        for priority_chip in priority_chips:
            if len(result) < 3:  # Limit to a maximum of 3 chips
                chip = chips.filter(name=priority_chip).first()
                if chip:
                    result.append(chip.name)
        # Chip 객체의 name 필드를 리스트로 반환
        return result
    
    def get_is_liked(self, obj):
        user = self.context.get('user')
        # 사용자가 인증된 경우 해당 게임에 대한 좋아요 상태를 확인
        if user and user.is_authenticated:
            return Like.objects.filter(user=user, game=obj).exists()
        return False
    
    def get_category_name(self, obj):
        # 카테고리 이름 리스트를 반환
        return [category.name for category in obj.category.all()]
