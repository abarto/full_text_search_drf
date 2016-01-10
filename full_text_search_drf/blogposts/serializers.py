from rest_framework.serializers import HyperlinkedModelSerializer

from .models import Blogpost, Comment


class CommentSerializer(HyperlinkedModelSerializer):
    class Meta:
        model = Comment
        fields = ('url', 'content', 'author', 'created', 'modified', 'blogpost')
        read_only_fields = ('url', 'author', 'created', 'modified', 'blogpost')


class BlogpostSerializer(HyperlinkedModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Blogpost
        fields = ('url', 'title', 'slug', 'description', 'content', 'allow_comments', 'author', 'created', 'modified', 'comments')
        read_only_fields = ('url', 'slug', 'author', 'created', 'modified', 'comments')
