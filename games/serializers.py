from rest_framework import serializers
from .models import Game, Review, GameCategory, Screenshot


class GameListSerializer(serializers.ModelSerializer):
    star = serializers.FloatField(read_only=True)
    maker_name = serializers.CharField(source='maker.username')

    class Meta:
        model = Game
        fields = ("pk", "title", "maker", "thumbnail",
                  "star", "maker_name", "view_cnt")


class GameCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Game
        fields = "__all__"
        read_only_fields = ('maker', 'is_visible', 'view_cnt', 'register_state')


class GameDetailSerializer(serializers.ModelSerializer):
    maker_name = serializers.CharField(source='maker.username')

    class Meta:
        model = Game
        fields = "__all__"
        read_only_fields = ('maker')


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(
        source='author.username', read_only=True)
    src = serializers.ImageField(source='author.image', read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = "__all__"
        read_only_fields = ('is_visible', 'game', 'author',)

    def get_replies(self, obj):
        if obj.reply.exists():
            return ReviewSerializer(obj.reply, many=True).data
        return []


class ScreenshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = Screenshot
        fields = ('id', 'src', )


class CategorySerailizer(serializers.ModelSerializer):
    class Meta:
        model = GameCategory
        fields = ('pk', 'name')
