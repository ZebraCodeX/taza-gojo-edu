from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import SessionViewSet, AvailableTutorsView, TurnConfigView

router = DefaultRouter()
router.register("sessions", SessionViewSet, basename="session")
router.register("tutors", AvailableTutorsView, basename="tutors")
router.register("ice", TurnConfigView, basename="ice")

urlpatterns = router.urls