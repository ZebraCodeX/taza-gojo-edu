from rest_framework.routers import DefaultRouter

from .views import LabViewSet, LabSubmissionViewSet

router = DefaultRouter()
router.register("labs", LabViewSet, basename="lab")
router.register("submissions", LabSubmissionViewSet, basename="lab-submission")

urlpatterns = router.urls
