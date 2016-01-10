import django_filters

from blogposts.models import Blogpost, Comment


class BlogpostFilter(django_filters.FilterSet):
    author = django_filters.CharFilter(name='author__username')

    q = django_filters.MethodFilter(action='filter_by_q', distinct=True)

    def filter_by_q(self, queryset, value):
        return queryset.full_text_search(value)

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
    blogpost = django_filters.CharFilter()

    q = django_filters.MethodFilter(action='filter_by_q', distinct=True)

    def filter_by_q(self, queryset, value):
        return queryset.full_text_search(value)

    class Meta:
        model = Comment
        fields = {
            'id': ('exact',),
            'created': ('lt', 'gt'),
            'modified': ('lt', 'gt'),
            'content': ('icontains',)
        }
