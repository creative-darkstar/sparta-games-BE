from rest_framework import serializers
from .models import TeamBuildPost
from .models import TeamBuildProfile


class TeamBuildPostSerializer(serializers.ModelSerializer):
    status_chip = serializers.CharField(read_only=True)
    author_data = serializers.SerializerMethodField(read_only=True)
    want_roles = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = TeamBuildPost
        fields = (
            'id', 'title', 'author_data', 'purpose',
            'duration', 'deadline', 'is_visible',
            'status_chip', 'want_roles', 'thumbnail',
        )
        read_only_fields = ['id', 'author_data', 'is_visible', 'create_dt', 'update_dt', 'status_chip']

    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else None,
        }
    
    def get_want_roles(self, obj):
        roles = list(obj.want_roles.values_list('name', flat=True))
        if len(roles) <= 3:
            return roles
        return roles[:3] + [f"+{len(roles) - 3}"]
    
    def get_thumbnail(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None
    
class TeamBuildPostDetailSerializer(serializers.ModelSerializer):
    author_data = serializers.SerializerMethodField(read_only=True)
    thumbnail = serializers.ImageField(use_url=True)
    want_roles = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamBuildPost
        fields = [
            "id", "title", "want_roles", "purpose", "duration", "meeting_type",
            "deadline", "contact", "content", "thumbnail", "author_data",
            "create_dt"
        ]
        read_only_fields = ["id", "author_data", "create_dt"]

    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else None,
        }
    
    def get_want_roles(self, obj):
        return list(obj.want_roles.values_list("name", flat=True))
    
class RecommendedTeamBuildPostSerializer(serializers.ModelSerializer):
    status_chip = serializers.CharField(read_only=True)
    author_data = serializers.SerializerMethodField(read_only=True)
    want_roles = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = TeamBuildPost
        fields = (
            'id', 'title', 'author_data', 'purpose',
            'duration', 'deadline', 'is_visible',
            'status_chip', 'want_roles', 'thumbnail',
            'content',
        )
        read_only_fields = ['id', 'author_data', 'is_visible', 'create_dt', 'update_dt', 'status_chip']

    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else None,
        }
    
    def get_want_roles(self, obj):
        roles = list(obj.want_roles.values_list('name', flat=True))
        if len(roles) <= 4:
            return roles
        return roles[:4] + [f"+{len(roles) - 4}"]
    
    def get_thumbnail(self, obj):
        return obj.thumbnail.url if obj.thumbnail else None
    

class TeamBuildProfileSerializer(serializers.ModelSerializer):
    author_data = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    game_genre = serializers.SlugRelatedField(
        many=True, read_only=True, slug_field="name"
    )
    my_role = serializers.SlugRelatedField(
        read_only=True, slug_field="name"
    )

    class Meta:
        model = TeamBuildProfile
        fields = (
            'id', 'author_data', 'profile_image', 'career', 'my_role',
            'tech_stack', 'game_genre', 'portfolio',
            'purpose', 'duration', 'meeting_type',
            'contact', 'title', 'content',
        )

    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else None,
        }

    def get_profile_image(self, obj):
        return obj.image.url if obj.image else None