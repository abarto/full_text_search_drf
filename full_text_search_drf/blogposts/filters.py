import django_filters

from blogposts.models import Blogpost, Comment


class BlogpostFilter(django_filters.FilterSet):
    author = django_filters.CharFilter(name='author__username')

    class Meta:
        model = Blogpost
        fields = {
            'id': ('exact',),
            'created': ('lt', 'gt'),
            'modified': ('lt', 'gt'),
            'title': ('icontains',),
            'description': ('icontains',),
            'content': ('icontains',)
        }


class CommentFilter(django_filters.FilterSet):
    author = django_filters.CharFilter(name='author__username')

    class Meta:
        model = Comment
        fields = {
            'id': ('exact',),
            'created': ('lt', 'gt'),
            'modified': ('lt', 'gt'),
            'content': ('icontains',)
        }
