from rest_framework.routers import DefaultRouter

from .views import LiveClassViewSet

router = DefaultRouter()
router.register("classes", LiveClassViewSet, basename="live-class")

urlpatterns = router.urls
