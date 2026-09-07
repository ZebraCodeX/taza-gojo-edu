from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CourseViewSet, LessonViewSet, ProgressViewSet

router = DefaultRouter()
router.register("", CourseViewSet, basename="course")

# Nested under /api/v1/courses/ but kept out of the course router so a lesson
# id is never mistaken for a course slug.
extra = [
    path("lessons/<int:pk>/", LessonViewSet.as_view({"get": "retrieve"})),
    path("lessons/", LessonViewSet.as_view({"get": "list"})),
    path("progress/", ProgressViewSet.as_view({"get": "list", "post": "create"})),
]

urlpatterns = router.urls + extra