full_text_search_drf
====================

Introduction
------------

This project was created to provide an example on how to implement full text search in a `Django REST framework <http://www.django-rest-framework.org/>`_ site using only the functionality provided by the `PostgreSQL <http://www.postgresql.org/>`_ database back-end. It is based in a `similar project <https://github.com/abarto/full_text_search_django>`_ that showed how to implement full text search in a `Django <https://www.djangoproject.com/>`_ site using `PostgreSQL <http://www.postgresql.org/>`_ and `MySQL <https://www.mysql.com/>`_.

Although having a specialized indexing solution is what most experts recommend when dealing with large, real word sites, sometimes it can be overkill if we're only working on a simple system with few users and models or if you lack the resources or expertise to manage an additional external dependency.

Combining what we presented in the other project with the functionality of `django-filter <https://github.com/alex/django-filter>`_ you can have a fully functional full text search filter with a PostgreSQL back-end. Adapting the solution for MySQL (`MariaDB <https://mariadb.org/>`_) is quite simple, but notice that Django REST framework already has some `full text search functionality <http://www.django-rest-framework.org/api-guide/filtering/#searchfilter>`_ when working with a MySQL back-end.

The application
---------------

The model is a simplified version of the one introduced in the `learn_drf_nested_resources <https://github.com/abarto/learn_drf_nested_resources>`_:

::

    class UUIDIdMixin(models.Model):
        class Meta:
            abstract = True

        id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)


    class AuthorMixin(models.Model):
        class Meta:
            abstract = True

        author = models.ForeignKey(
            settings.AUTH_USER_MODEL, editable=False, verbose_name=_('author'),
            related_name='%(app_label)s_%(class)s_author'
        )


    class Blogpost(UUIDIdMixin, TimeStampedModel, TitleSlugDescriptionModel, AuthorMixin):
        content = models.TextField(_('content'), blank=True, null=True)

        def __str__(self):
            return self.title


    class Comment(UUIDIdMixin, TimeStampedModel, AuthorMixin):
        blogpost = models.ForeignKey(
            Blogpost, editable=False, verbose_name=_('blogpost'), related_name='comments'
        )
        content = models.TextField(_('content'), max_length=255, blank=False, null=False)

And the viewsets are just typical ModelViewSet implementations:

::

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

Full Text Search with PostgreSQL
--------------------------------

Starting with version `8.3 <http://www.postgresql.org/docs/8.3/static/release-8-3.html>`_ introduced fully featured full text search capabilities. The system is `quite flexible <http://www.postgresql.org/docs/9.4/static/textsearch-intro.html>`_ and easy to use if you just want the default configuration for the English language (which I'll use here).

As shown in the `documentation <http://www.postgresql.org/docs/9.4/static/textsearch-tables.html#TEXTSEARCH-TABLES-SEARCH>`_, searching a table is quite simple:

::

    SELECT title
    FROM pgweb
    WHERE to_tsvector('english', body) @@ to_tsquery('english', 'friend');

In this example, the user is looking for 'friend' on the 'body' column of the 'pgweb' table using the 'english' configuration. We can easily adapt this to query a Django model, but first we can speed things up by creating an index on the columns that we want to query. We'll create our index using a migration:

::

    class Migration(migrations.Migration):

        dependencies = [
            ('blogposts', '0002_remove_blogpost_allow_comments'),
        ]

        operations = [
            migrations.RunSQL(
                "CREATE INDEX blogposts_blogpost_ts_idx ON blogposts_blogpost USING gin(to_tsvector('english', title || ' ' || description || ' ' || content));",
                "DROP INDEX IF EXISTS items_item_name_ts_idx;"
            ),
            migrations.RunSQL(
                "CREATE INDEX blogposts_comment_ts_idx ON blogposts_comment USING gin(to_tsvector('english', content));",
                "DROP INDEX IF EXISTS items_part_name_ts_idx;"
            ),
        ]

We're creating two indexes here: one for the Blogspot title, description and content and one for the Comment content. As mentioned in the PostgreSQL `documentation <http://www.postgresql.org/docs/9.4/static/textsearch-tables.html#TEXTSEARCH-TABLES-INDEX>`_, as long as the queries use the same ``ts_vector`` configuration, the index will be used. Next, we'll write the Django ORM queries for the Blogpost and Comment models as ``QuerySet``:

::

    class BlogpostQueryset(models.QuerySet):
        def full_text_search(self, text):
            return self.extra(
                select={'rank': "ts_rank_cd(to_tsvector('english', blogposts_blogpost.title || ' ' || blogposts_blogpost.description || ' ' || blogposts_blogpost.content), plainto_tsquery(%s), 32)"},
                select_params=(text,),
                where=("to_tsvector('english', blogposts_blogpost.title || ' ' || blogposts_blogpost.description || ' ' || blogposts_blogpost.content) @@ plainto_tsquery(%s)",),
                params=(text,),
                order_by=('-rank',)
            )


    class CommentQueryset(models.QuerySet):
        def full_text_search(self, text):
            return self.extra(
                select={'rank': "ts_rank_cd(to_tsvector('english', blogposts_comment.content), plainto_tsquery(%s), 32)"},
                select_params=(text,),
                where=("to_tsvector('english', blogposts_comment.content) @@ plainto_tsquery(%s)",),
                params=(text,),
                order_by=('-rank',)
            )

We made use of the ``QuerySet`` `extra <https://docs.djangoproject.com/en/1.9/ref/models/querysets/#extra>`_ modifier to express the full text search queries. The ``full_text_search`` methods use a similar query to the one in the example, with a simple modification: We use PostgreSQL's `ts_rank_cd <http://www.postgresql.org/docs/9.4/static/functions-textsearch.html>`_ function to define a ranking between the matches, which allows us to order the results, which is what we want in these cases. Notice that I use the 'english' configuration so the indexes created in the migration are properly used. Be aware that if you use a different configuration **the query won't fail**, but it will not use the index.

Now we need to make sure the ``objects`` manager on our models, use the new QuerySets:

::

    class Blogpost(models.Model):
        ...

        objects = BlogpostQueryset.as_manager()

    class Comment(models.Model):
        ...

        objects = CommentQueryset.as_manager()


What ties the whole thing together are a couple of `django-filter <https://github.com/alex/django-filter>`_ FilterSet which give access to the QuerySet methods using a `MethodFilter <http://django-filter.readthedocs.org/en/latest/ref/filters.html#methodfilter>` field (alongside typical fields one would expose in an API such as this):

::

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

Example
-------

The following shell session shows how to use these filters using `httpie <http://httpie.org>`_. First we'll make a simple request without filtering to make sure everything works as intended:

::

    $ http --auth=reader:reader GET ":8000/api/blogposts/" Accept:'application/json;indent=4'
    HTTP/1.0 200 OK
    Allow: GET, POST, HEAD, OPTIONS
    Content-Type: application/json;indent=4
    Date: Sun, 10 Jan 2016 18:27:14 GMT
    Server: WSGIServer/0.2 CPython/3.4.3
    Vary: Accept, Cookie
    X-Frame-Options: SAMEORIGIN

    [
        {
            "author": "http://localhost:8000/api/users/author/",
            "comments": [
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/e439c223-f98e-4abf-b876-5358f165fd98/",
                    "content": "Mauris enim leo, rhoncus sed, vestibulum sit amet, cursus id, turpis. Integer aliquet, massa id lobortis convallis, tortor risus dapibus augue, vel accumsan tellus nisi eu orci. Mauris lacinia sapien quis libero.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "c1c106b1-0425-4ee1-97a6-ced9df001d62",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/c1c106b1-0425-4ee1-97a6-ced9df001d62/"
                },
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/e439c223-f98e-4abf-b876-5358f165fd98/",
                    "content": "Morbi non lectus. Aliquam sit amet diam in magna bibendum imperdiet. Nullam orci pede, venenatis non, sodales sed, tincidunt eu, felis.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "4c444a3c-4ff9-467c-bc89-73933fe2c519",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/4c444a3c-4ff9-467c-bc89-73933fe2c519/"
                },
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/e439c223-f98e-4abf-b876-5358f165fd98/",
                    "content": "Quisque porta volutpat erat. Quisque erat eros, viverra eget, congue eget, semper rutrum, nulla. Nunc purus.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "6ce42019-a3fc-451d-a55e-f4a5d6186f93",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/6ce42019-a3fc-451d-a55e-f4a5d6186f93/"
                }
            ],
            "content": "In hac habitasse platea dictumst. Etiam faucibus cursus urna. Ut tellus.\n\nNulla ut erat id mauris vulputate elementum. Nullam varius. Nulla facilisi.\n\nCras non velit nec nisi vulputate nonummy. Maecenas tincidunt lacus at velit. Vivamus vel nulla eget eros elementum pellentesque.\n\nQuisque porta volutpat erat. Quisque erat eros, viverra eget, congue eget, semper rutrum, nulla. Nunc purus.\n\nPhasellus in felis. Donec semper sapien a libero. Nam dui.\n\nProin leo odio, porttitor id, consequat in, consequat ut, nulla. Sed accumsan felis. Ut at dolor quis odio consequat varius.",
            "created": "2016-01-10T11:13:06.124297Z",
            "description": "lacus curabitur at ipsum ac tellus semper interdum mauris ullamcorper",
            "id": "e439c223-f98e-4abf-b876-5358f165fd98",
            "modified": "2016-01-10T11:13:06.124297Z",
            "slug": "",
            "title": "elit ac nulla sed vel enim sit",
            "url": "http://localhost:8000/api/blogposts/e439c223-f98e-4abf-b876-5358f165fd98/"
        },
        ...
        {
            "author": "http://localhost:8000/api/users/author/",
            "comments": [
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/b0aecc55-3f28-4bf4-8a6a-2d35305b1a95/",
                    "content": "Praesent blandit. Nam nulla. Integer pede justo, lacinia eget, tincidunt eget, tempus vel, pede.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "df097215-f383-4fad-b7fb-d0d8575e1458",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/df097215-f383-4fad-b7fb-d0d8575e1458/"
                },
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/b0aecc55-3f28-4bf4-8a6a-2d35305b1a95/",
                    "content": "Vestibulum quam sapien, varius ut, blandit non, interdum in, ante. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Duis faucibus accumsan odio. Curabitur convallis.\n\nDuis consequat dui nec nisi volutpat eleifend. Donec ut dolor. Morbi vel lectus in quam fringilla rhoncus.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "956528f7-c15c-41c7-b290-7bc2e0f83933",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/956528f7-c15c-41c7-b290-7bc2e0f83933/"
                },
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/b0aecc55-3f28-4bf4-8a6a-2d35305b1a95/",
                    "content": "Nulla ut erat id mauris vulputate elementum. Nullam varius. Nulla facilisi.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "bd536ef6-6eeb-4d44-bd7f-3debce581d9c",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/bd536ef6-6eeb-4d44-bd7f-3debce581d9c/"
                }
            ],
            "content": "Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Proin risus. Praesent lectus.\n\nVestibulum quam sapien, varius ut, blandit non, interdum in, ante. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Duis faucibus accumsan odio. Curabitur convallis.\n\nDuis consequat dui nec nisi volutpat eleifend. Donec ut dolor. Morbi vel lectus in quam fringilla rhoncus.\n\nMauris enim leo, rhoncus sed, vestibulum sit amet, cursus id, turpis. Integer aliquet, massa id lobortis convallis, tortor risus dapibus augue, vel accumsan tellus nisi eu orci. Mauris lacinia sapien quis libero.\n\nNullam sit amet turpis elementum ligula vehicula consequat. Morbi a ipsum. Integer a nibh.",
            "created": "2016-01-10T11:13:06.124297Z",
            "description": "vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia curae donec pharetra magna vestibulum aliquet ultrices",
            "id": "b0aecc55-3f28-4bf4-8a6a-2d35305b1a95",
            "modified": "2016-01-10T11:13:06.124297Z",
            "slug": "",
            "title": "magna ac consequat metus sapien",
            "url": "http://localhost:8000/api/blogposts/b0aecc55-3f28-4bf4-8a6a-2d35305b1a95/"
        }
    ]

The values for the filters are supplied as request parameters in the URL. If we wanted to know which blogposts match "Ut Dolor" in its title, description, or content, we use the "q" request parameter.

::

    $ http --auth=reader:reader GET ":8000/api/blogposts/?q=Ut+Dolor" Accept:'application/json;indent=4'
    HTTP/1.0 200 OK
    Allow: GET, POST, HEAD, OPTIONS
    Content-Type: application/json;indent=4
    Date: Sun, 10 Jan 2016 18:42:19 GMT
    Server: WSGIServer/0.2 CPython/3.4.3
    Vary: Accept, Cookie
    X-Frame-Options: SAMEORIGIN

    [
        {
            "author": "http://localhost:8000/api/users/author/",
            "comments": [],
            "content": "In hac habitasse platea dictumst. Morbi vestibulum, velit id pretium iaculis, diam erat fermentum justo, nec condimentum neque sapien placerat ante. Nulla justo.\n\nAliquam quis turpis eget elit sodales scelerisque. Mauris sit amet eros. Suspendisse accumsan tortor quis turpis.\n\nSed ante. Vivamus tortor. Duis mattis egestas metus.\n\nAenean fermentum. Donec ut mauris eget massa tempor convallis. Nulla neque libero, convallis eget, eleifend luctus, ultricies eu, nibh.\n\nQuisque id justo sit amet sapien dignissim vestibulum. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Nulla dapibus dolor vel est. Donec odio justo, sollicitudin ut, suscipit a, feugiat et, eros.\n\nVestibulum ac est lacinia nisi venenatis tristique. Fusce congue, diam id ornare imperdiet, sapien urna pretium nisl, ut volutpat sapien arcu sed augue. Aliquam erat volutpat.\n\nIn congue. Etiam justo. Etiam pretium iaculis justo.",
            "created": "2016-01-10T11:13:06.124297Z",
            "description": "accumsan odio curabitur convallis duis consequat dui nec nisi volutpat eleifend donec ut dolor morbi vel lectus in quam",
            "id": "fda6e8cc-0263-4766-bb8e-db796c6472e5",
            "modified": "2016-01-10T11:13:06.124297Z",
            "slug": "",
            "title": "dolor quis odio consequat varius integer ac leo pellentesque ultrices",
            "url": "http://localhost:8000/api/blogposts/fda6e8cc-0263-4766-bb8e-db796c6472e5/"
        },
        ...
        {
            "author": "http://localhost:8000/api/users/author/",
            "comments": [
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/7cf57328-e881-4cfc-81b9-38a099fe9591/",
                    "content": "Nulla ut erat id mauris vulputate elementum. Nullam varius. Nulla facilisi.\n\nCras non velit nec nisi vulputate nonummy. Maecenas tincidunt lacus at velit. Vivamus vel nulla eget eros elementum pellentesque.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "64610d5a-6543-48f3-9f68-b526538b753d",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/64610d5a-6543-48f3-9f68-b526538b753d/"
                },
                {
                    "author": "http://localhost:8000/api/users/reader/",
                    "blogpost": "http://localhost:8000/api/blogposts/7cf57328-e881-4cfc-81b9-38a099fe9591/",
                    "content": "Sed sagittis. Nam congue, risus semper porta volutpat, quam pede lobortis ligula, sit amet eleifend pede libero quis orci. Nullam molestie nibh in lectus.",
                    "created": "2016-01-10T11:13:06.124297Z",
                    "id": "c8ed06dc-9b04-48ff-b416-06f91b45bac4",
                    "modified": "2016-01-10T11:13:06.124297Z",
                    "url": "http://localhost:8000/api/comments/c8ed06dc-9b04-48ff-b416-06f91b45bac4/"
                }
            ],
            "content": "Maecenas tristique, est et tempus semper, est quam pharetra magna, ac consequat metus sapien ut nunc. Vestibulum ante ipsum primis in faucibus orci luctus et ultrices posuere cubilia Curae; Mauris viverra diam vitae quam. Suspendisse potenti.\n\nNullam porttitor lacus at turpis. Donec posuere metus vitae ipsum. Aliquam non mauris.\n\nMorbi non lectus. Aliquam sit amet diam in magna bibendum imperdiet. Nullam orci pede, venenatis non, sodales sed, tincidunt eu, felis.\n\nFusce posuere felis sed lacus. Morbi sem mauris, laoreet ut, rhoncus aliquet, pulvinar sed, nisl. Nunc rhoncus dui vel sem.\n\nSed sagittis. Nam congue, risus semper porta volutpat, quam pede lobortis ligula, sit amet eleifend pede libero quis orci. Nullam molestie nibh in lectus.\n\nPellentesque at nulla. Suspendisse potenti. Cras in purus eu magna vulputate luctus.\n\nCum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Vivamus vestibulum sagittis sapien. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus.\n\nEtiam vel augue. Vestibulum rutrum rutrum neque. Aenean auctor gravida sem.\n\nPraesent id massa id nisl venenatis lacinia. Aenean sit amet justo. Morbi ut odio.\n\nCras mi pede, malesuada in, imperdiet et, commodo vulputate, justo. In blandit ultrices enim. Lorem ipsum dolor sit amet, consectetuer adipiscing elit.",
            "created": "2016-01-10T11:13:06.124297Z",
            "description": "sagittis nam congue risus semper porta volutpat quam pede lobortis ligula sit amet eleifend pede libero quis orci nullam molestie",
            "id": "7cf57328-e881-4cfc-81b9-38a099fe9591",
            "modified": "2016-01-10T11:13:06.124297Z",
            "slug": "",
            "title": "erat curabitur gravida nisi at nibh in",
            "url": "http://localhost:8000/api/blogposts/7cf57328-e881-4cfc-81b9-38a099fe9591/"
        }
    ]

Similarly If we wanted to know which comment on the blogpost with id "eb17b879-cdcc-4c9c-a088-7c9b9f8d63b3" matches "Ut Dolor" in its content, we can combine the "blogpost" and "q" request parameters in the "comments" resource:

::

    $ http --auth=reader:reader GET ":8000/api/comments/?blogpost=eb17b879-cdcc-4c9c-a088-7c9b9f8d63b3&q=Ut+Dolor" Accept:'application/json;indent=4'HTTP/1.0 200 OK
    Allow: GET, POST, HEAD, OPTIONS
    Content-Type: application/json;indent=4
    Date: Sun, 10 Jan 2016 18:56:15 GMT
    Server: WSGIServer/0.2 CPython/3.4.3
    Vary: Accept, Cookie
    X-Frame-Options: SAMEORIGIN

    [
        {
            "author": "http://localhost:8000/api/users/reader/",
            "blogpost": "http://localhost:8000/api/blogposts/eb17b879-cdcc-4c9c-a088-7c9b9f8d63b3/",
            "content": "Proin leo odio, porttitor id, consequat in, consequat ut, nulla. Sed accumsan felis. Ut at dolor quis odio consequat varius.\n\nInteger ac leo. Pellentesque ultrices mattis odio. Donec vitae nisi.",
            "created": "2016-01-10T11:13:06.124297Z",
            "id": "887af8c0-83f0-4ccf-981f-af64370051ca",
            "modified": "2016-01-10T11:13:06.124297Z",
            "url": "http://localhost:8000/api/comments/887af8c0-83f0-4ccf-981f-af64370051ca/"
        },
        {
            "author": "http://localhost:8000/api/users/reader/",
            "blogpost": "http://localhost:8000/api/blogposts/eb17b879-cdcc-4c9c-a088-7c9b9f8d63b3/",
            "content": "Proin leo odio, porttitor id, consequat in, consequat ut, nulla. Sed accumsan felis. Ut at dolor quis odio consequat varius.\n\nInteger ac leo. Pellentesque ultrices mattis odio. Donec vitae nisi.",
            "created": "2016-01-10T11:13:06.124297Z",
            "id": "adf4bb80-385a-4bba-b920-67bd07dd3011",
            "modified": "2016-01-10T11:13:06.124297Z",
            "url": "http://localhost:8000/api/comments/adf4bb80-385a-4bba-b920-67bd07dd3011/"
        }
    ]

Conclusion
----------

Once the full text search indexes and queries have been set, it's all just a matter of simple django-filters wiring. As we mentioned before, this shouldn't be used in large sites with lots of data as we're not really sure the database back-ends full text search capabilities are up to the task, but for medium and small sites, this should work just fine.

Vagrant
-------

A `Vagrant <https://www.vagrantup.com/>`_ configuration file is included if you want to test the solutions.

Feedback
--------

As usual, I welcome comments, suggestions and pull requests.
