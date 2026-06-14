from django.db.models import (
    BooleanField,
    Count,
    Exists,
    IntegerField,
    OuterRef,
    Q,
    Subquery,
    Value,
)

from .models import Game, Like, Review, ReviewsLike


def annotate_game_is_liked(qs, user):
    if user and getattr(user, "is_authenticated", False):
        liked_exists = Like.objects.filter(user=user, game_id=OuterRef("pk"))
        return qs.annotate(is_liked=Exists(liked_exists))
    return qs.annotate(is_liked=Value(False, output_field=BooleanField()))


def with_game_list_optimizations(qs, user):
    qs = qs.select_related("maker").prefetch_related("chip", "category")
    return annotate_game_is_liked(qs, user)


def with_game_detail_optimizations(qs, user):
    qs = qs.select_related("maker").prefetch_related("chip", "category", "screenshots")
    return annotate_game_is_liked(qs, user)


def with_review_optimizations(qs, user):
    qs = qs.select_related("author", "game")
    qs = qs.annotate(
        like_count=Count("reviews", filter=Q(reviews__is_like=1)),
        dislike_count=Count("reviews", filter=Q(reviews__is_like=2)),
    )
    if user and getattr(user, "is_authenticated", False):
        user_like_subq = ReviewsLike.objects.filter(
            review_id=OuterRef("pk"),
            user=user,
        ).values("is_like")[:1]
        return qs.annotate(
            user_is_like=Subquery(user_like_subq, output_field=IntegerField())
        )
    return qs.annotate(user_is_like=Value(0, output_field=IntegerField()))
