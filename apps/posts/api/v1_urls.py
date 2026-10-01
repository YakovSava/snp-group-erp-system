from rest_framework.routers import DefaultRouter

from .views import PostViewSet, SalesPostViewSet

router = DefaultRouter()
router.register("posts", PostViewSet, basename="post")
router.register("sales-posts", SalesPostViewSet, basename="sales-post")

urlpatterns = router.urls
