from rest_framework import serializers
from .models import Game, Review, GameCategory, Screenshot, ReviewsLike, Like


class GameListSerializer(serializers.ModelSerializer):
    maker_name = serializers.CharField(source='maker.nickname')
    chip_names= serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    category_name = serializers.SerializerMethodField()
    class Meta:
        model = Game
        fields = ("pk", "title", "thumbnail",
                  "star", "maker_name","content","chip_names","is_liked","category_name")
    
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


class GameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = "__all__"
        read_only_fields = ('maker', 'is_visible', 'view_cnt', 'register_state',)


class GameDetailSerializer(serializers.ModelSerializer):
    maker_name = serializers.CharField(source='maker.nickname')
    is_liked = serializers.SerializerMethodField()
    chip_names= serializers.SerializerMethodField()

    class Meta:
        model = Game
        fields = "__all__"
        read_only_fields = ('maker',)

    def get_is_liked(self, obj):
        user = self.context.get('user')
        if user and user.is_authenticated:
            return Like.objects.filter(user=user, game=obj).exists()
        return False
    
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


class ReviewSerializer(serializers.ModelSerializer):
    author_id = serializers.IntegerField(source='author.id', read_only=True)
    game_id = serializers.IntegerField(source='game.id', read_only=True)
    author_name = serializers.CharField(
        source='author.nickname', read_only=True)
    like_count = serializers.SerializerMethodField()
    dislike_count = serializers.SerializerMethodField()
    user_is_like = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            'id','author_name','like_count','dislike_count','user_is_like',
            'content','star','difficulty','is_visible','created_at','updated_at',
            'author_id','game_id',
        ]
        read_only_fields = ('is_visible', 'game', 'author',)
    
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
        fields = ('pk', 'name')
