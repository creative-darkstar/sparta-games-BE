from rest_framework import serializers
from .models import QnA
from games.models import Game


class QnAPostListSerializer(serializers.ModelSerializer):
    class Meta:
        model = QnA
        fields = "__all__"


class CategorySerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()

    def to_representation(self, instance):
        return {
            'code': instance[0],
            'name': instance[1]
        }


class GameRegisterListSerializer(serializers.ModelSerializer):
    maker_data = serializers.SerializerMethodField()
    category_data = serializers.SerializerMethodField()
    game_register_logs = serializers.SerializerMethodField()
    class Meta:
        model = Game
        fields = ("id", "title", "register_state", "maker_data", "category_data", "game_register_logs")
    
    def get_maker_data(self, obj):
        return {
            "id": obj.maker.id,
            "nickname": obj.maker.nickname,
        }
    
    def get_category_data(self, obj):
        # 카테고리 리스트를 반환
        return [{"id": category.id, "name": category.name,} for category in obj.category.all()]
    
    def get_game_register_logs(self, obj):
        # 로그 리스트를 반환
        return [{"created_at": log.created_at, "content": log.content} for log in obj.logs_game.filter(game=obj).order_by("-created_at")][:2]