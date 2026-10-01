from rest_framework.routers import DefaultRouter

from .views import ConversionHistoryViewSet

router = DefaultRouter()
router.register("conversion-history", ConversionHistoryViewSet, basename="conversion-history")

urlpatterns = router.urls
