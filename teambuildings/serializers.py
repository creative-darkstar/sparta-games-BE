from rest_framework import serializers
from .models import TeamBuildPost, TeamBuildProfile, TeamBuildPostComment


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
            'status_chip', 'want_roles', 'thumbnail', 'content'
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
    status_chip = serializers.CharField(read_only=True)
    author_data = serializers.SerializerMethodField(read_only=True)
    thumbnail = serializers.ImageField(use_url=True)
    want_roles = serializers.SerializerMethodField()
    thumbnail_basic = serializers.SerializerMethodField(read_only=True)  # 기본 이미지 여부
    
    class Meta:
        model = TeamBuildPost
        fields = [
            "id", "title", "want_roles", "purpose", "duration", "meeting_type",
            "deadline", "contact", "content", "thumbnail", "author_data",
            "create_dt", "status_chip", "thumbnail_basic"
        ]
        read_only_fields = ["id", "author_data", "create_dt", "status_chip", "thumbnail_basic"]

    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else None,
        }
    
    def get_want_roles(self, obj):
        return list(obj.want_roles.values_list("name", flat=True))
    
    def get_thumbnail_basic(self, obj):
        default_path = "images/thumbnail/teambuildings/teambuilding_default.png"
        # obj.thumbnail.name 은 MEDIA_ROOT 하위 경로를 반환
        return obj.thumbnail and obj.thumbnail.name == default_path


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


class TeamBuildPostCommentSerializer(serializers.ModelSerializer):
    author_data = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = TeamBuildPostComment
        fields = [
            'id', 'author_data', 'post_id', 'content', 'is_visible', 'created_at', 'updated_at',
        ]
        read_only_fields = ('is_visible', 'post', 'author',)
    
    def get_author_data(self, obj):
        return {
            "id": obj.author.id,
            "nickname": obj.author.nickname,
            "image": obj.author.image.url if obj.author.image else '',
        }


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