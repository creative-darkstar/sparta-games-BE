from rest_framework import serializers
from .models import Game, Review, GameCategory, Screenshot

DIFFICULTY_CHIPS = ["EASY", "NORMAL", "HARD"]
PRIORITY_CHIPS = ["Daily Top", "New Game", "Bookmark Top", "Long Play", "Review Top"]


def build_game_chips(obj):
    chips = list(obj.chip.all())
    result = []

    difficulty_chip = next((c for c in chips if c.name in DIFFICULTY_CHIPS), None)
    if difficulty_chip:
        result.append({"id": difficulty_chip.id, "name": difficulty_chip.name})

    for chip_name in PRIORITY_CHIPS:
        if len(result) >= 3:
            break
        chip = next((c for c in chips if c.name == chip_name), None)
        if chip:
            result.append({"id": chip.id, "name": chip.name})

    return result


class GameListSerializer(serializers.ModelSerializer):
    maker_data = serializers.SerializerMethodField()
    chips= serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()
    star = serializers.SerializerMethodField()
    
    class Meta:
        model = Game
        fields = ("id", "title", "thumbnail",
                  "star", "maker_data", "content", "chips", "is_liked", "category_data")
    
    def get_maker_data(self, obj):
        return {
            "id": obj.maker.id,
            "nickname": obj.maker.nickname,
        }
    
    def get_star(self, obj):
        return round(obj.star, 2) if obj.star is not None else 0
    
    def get_chips(self, obj):
        return build_game_chips(obj)
    
    def get_is_liked(self, obj):
        if hasattr(obj, "is_liked"):
            return bool(obj.is_liked)
        return False
    
    def get_category_data(self, obj):
        return [{"id": category.id, "name": category.name,} for category in obj.category.all()]


class GameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = "__all__"
        read_only_fields = ('maker', 'is_visible', 'view_cnt', 'register_state',)


class GameDetailSerializer(serializers.ModelSerializer):
    maker_data = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    chips= serializers.SerializerMethodField()
    star = serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = ("id", "maker_data", "title", "thumbnail",
                  "star", "content", "chips", "is_liked", "youtube_url",
                  "gamefile", "gamepath", "register_state", "is_visible", "review_cnt")
        read_only_fields = ('maker',)
    
    def get_maker_data(self, obj):
        return {
            "id": obj.maker.id,
            "nickname": obj.maker.nickname,
        }
    
    def get_star(self, obj):
        return round(obj.star, 2) if obj.star is not None else 0

    def get_is_liked(self, obj):
        if hasattr(obj, "is_liked"):
            return bool(obj.is_liked)
        return False
    
    def get_chips(self, obj):
        return build_game_chips(obj)


class ReviewSerializer(serializers.ModelSerializer):
    author_data = serializers.SerializerMethodField()
    game_id = serializers.IntegerField(source='game.id', read_only=True)
    like_count = serializers.SerializerMethodField()
    dislike_count = serializers.SerializerMethodField()
    user_is_like = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id', 'author_data', 'game_id', 'like_count', 'dislike_count', 'user_is_like',
            'content', 'star', 'difficulty', 'is_visible', 'created_at', 'updated_at',
        ]
        read_only_fields = ('is_visible', 'game', 'author',)
    
    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else '',
        }
    
    def get_like_count(self, obj):
        if hasattr(obj, "like_count"):
            return obj.like_count
        return 0

    def get_dislike_count(self, obj):
        if hasattr(obj, "dislike_count"):
            return obj.dislike_count
        return 0

    def get_user_is_like(self, obj):
        if hasattr(obj, "user_is_like"):
            return obj.user_is_like or 0
        return 0


class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ('id', 'src', )


class CategorySerailizer(serializers.ModelSerializer):
    class Meta:
        model = GameCategory
        fields = ('id', 'name')
