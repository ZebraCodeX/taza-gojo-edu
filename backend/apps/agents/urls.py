from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet, ConversationViewSet, TutorAskView

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("conversations", ConversationViewSet, basename="conversation")

urlpatterns = [
    path("tutor/ask/", TutorAskView.as_view()),
] + router.urls