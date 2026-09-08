from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import AgentTask, Conversation
from .serializers import AgentTaskSerializer, ConversationSerializer


class TaskViewSet(ModelViewSet):
    """Create tasks (async, processed by run_agents worker) and poll results."""

    serializer_class = AgentTaskSerializer
    http_method_names = ["get", "post"]

    def get_queryset(self):
        return AgentTask.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ConversationViewSet(ReadOnlyModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).prefetch_related("messages")