from django.contrib.auth import get_user_model

from rest_framework.serializers import HyperlinkedModelSerializer, HyperlinkedRelatedField

from blogposts.models import Blogpost, Comment


class CommentSerializer(HyperlinkedModelSerializer):
    author = HyperlinkedRelatedField(
            queryset=get_user_model().objects.all(),
            view_name='user-detail', lookup_field='username', lookup_url_kwarg='username'
    )

    class Meta:
        model = Comment
        fields = ('url', 'id', 'content', 'author', 'created', 'modified', 'blogpost')
        read_only_fields = ('url', 'id', 'author', 'created', 'modified', 'blogpost')


class BlogpostSerializer(HyperlinkedModelSerializer):
    comments = CommentSerializer(many=True, read_only=True)
    author = HyperlinkedRelatedField(
            queryset=get_user_model().objects.all(),
            view_name='user-detail', lookup_field='username', lookup_url_kwarg='username'
    )

    class Meta:
        model = Blogpost
        fields = ('url', 'id', 'title', 'slug', 'description', 'content', 'author', 'created', 'modified', 'comments')
        read_only_fields = ('url', 'id', 'slug', 'author', 'created', 'modified', 'comments')
