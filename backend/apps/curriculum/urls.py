from rest_framework.routers import DefaultRouter

from .views import FrameworkViewSet, StrandViewSet, OutcomeViewSet, MappingViewSet

router = DefaultRouter()
router.register("frameworks", FrameworkViewSet, basename="framework")
router.register("strands", StrandViewSet, basename="strand")
router.register("outcomes", OutcomeViewSet, basename="outcome")
router.register("mappings", MappingViewSet, basename="mapping")

urlpatterns = router.urls
