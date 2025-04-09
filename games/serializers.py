from rest_framework import serializers
from .models import Game, Review, GameCategory, Screenshot, ReviewsLike, Like


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
        user = self.context.get('user')
        if user and user.is_authenticated:
            return Like.objects.filter(user=user, game=obj).exists()
        return False
    
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
        return ReviewsLike.objects.filter(review=obj, is_like=1).count()

    def get_dislike_count(self, obj):
        return ReviewsLike.objects.filter(review=obj, is_like=2).count()

    def get_user_is_like(self, obj):
        # 현재 요청을 보낸 사용자 확인
        user = self.context.get('user', None)
        # 사용자가 인증되지 않은 경우 0 반환
        if not user or not user.is_authenticated:
            return 0

        # 사용자가 인증된 경우, 해당 리뷰에 남긴 상태를 조회
        review_like = ReviewsLike.objects.filter(review=obj, user=user).first()
        # 리뷰 상태가 존재하면 그 값을 반환, 없으면 0을 반환
        return review_like.is_like if review_like else 0


class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ('id', 'src', )


class CategorySerailizer(serializers.ModelSerializer):
    class Meta:
        model = GameCategory
        fields = ('id', 'name')
