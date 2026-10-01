from rest_framework.routers import DefaultRouter

from .views import ConversionJobViewSet

router = DefaultRouter()
router.register("conversion-jobs", ConversionJobViewSet, basename="conversion-job")

urlpatterns = router.urls
