from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework.mixins import (
    RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, ListModelMixin,
    CreateModelMixin
)
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, GenericViewSet

from blogposts.models import Blogpost, Comment
from blogposts.permissions import (
    IsAuthorOrReadOnly, CommentDeleteOrUpdatePermission, CommentsAllowed
)
from blogposts.serializers import BlogpostSerializer, CommentSerializer


class BlogpostViewSet(ModelViewSet):
    serializer_class = BlogpostSerializer
    queryset = Blogpost.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class CommentViewSet(
    ModelViewSet
):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = (
        IsAuthenticatedOrReadOnly, CommentDeleteOrUpdatePermission
    )
