import re

from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view, renderer_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from spartagames.utils import std_response
from spartagames.pagination import CustomPagination

from accounts.models import EmailVerification
from games.models import (
    Game,
    GameCategory,
)
from games.serializers import GameListSerializer
from qnas.models import DeleteUsers



