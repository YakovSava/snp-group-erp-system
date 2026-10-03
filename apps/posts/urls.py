from django.urls import path

from . import views

app_name = "posts"

urlpatterns = [
    path("posts/", views.PostListView.as_view(), name="post_list"),
    path("posts/create/", views.PostCreateView.as_view(), name="post_create"),
    path("posts/<int:pk>/", views.PostDetailView.as_view(), name="post_detail"),
    path("posts/<int:pk>/publish/", views.PostPublishView.as_view(), name="post_publish"),
    path("sales-posts/", views.SalesPostListView.as_view(), name="salespost_list"),
    path("sales-posts/create/", views.SalesPostCreateView.as_view(), name="salespost_create"),
    path("sales-posts/<int:pk>/", views.SalesPostDetailView.as_view(), name="salespost_detail"),
]
