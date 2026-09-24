from rest_framework.routers import DefaultRouter

from .views import LearningEventViewSet

router = DefaultRouter()
router.register("events", LearningEventViewSet, basename="learning-event")

urlpatterns = router.urls
