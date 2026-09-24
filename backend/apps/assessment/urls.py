from rest_framework.routers import DefaultRouter

from .views import ItemViewSet, AssessmentViewSet, AttemptViewSet, CertificateViewSet

router = DefaultRouter()
router.register("items", ItemViewSet, basename="item")
router.register("assessments", AssessmentViewSet, basename="assessment")
router.register("attempts", AttemptViewSet, basename="attempt")
router.register("certificates", CertificateViewSet, basename="certificate")

urlpatterns = router.urls
