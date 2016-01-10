from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.viewsets import ModelViewSet

from blogposts.filters import BlogpostFilter, CommentFilter
from blogposts.models import Blogpost, Comment
from blogposts.permissions import (
    IsAuthorOrReadOnly, CommentDeleteOrUpdatePermission
)
from blogposts.serializers import BlogpostSerializer, CommentSerializer


class BlogpostViewSet(ModelViewSet):
    serializer_class = BlogpostSerializer
    queryset = Blogpost.objects.all()
    permission_classes = (IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly)
    filter_class = BlogpostFilter

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
    filter_class = CommentFilter
