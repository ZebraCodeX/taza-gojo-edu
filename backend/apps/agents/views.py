from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from rest_framework.response import Response
from rest_framework import status, views
from rest_framework.permissions import IsAuthenticated

import re

from .models import AgentTask, Conversation, Message
from .serializers import AgentTaskSerializer, ConversationSerializer, MessageSerializer


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


class TutorAskView(views.APIView):
    """Blocking chat with the tutor agent.

    Kept synchronous so a student on a spotty connection gets one answer with one
    round-trip; the frontend shows a "thinking..." state.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("message") or "").strip()
        subject = request.data.get("subject", "")
        if not text:
            return Response({"error": "message required"}, status=status.HTTP_400_BAD_REQUEST)

        if subject and not re.match(r"^[a-z_]+$", subject):
            subject = ""
        conversation, _ = Conversation.objects.get_or_create(
            user=request.user,
            subject=subject,
        )
        if subject and not conversation.subject:
            conversation.subject = subject
            conversation.save()

        Message.objects.create(conversation=conversation, role="user", text=text)

        from .agents import run_task
        history = [
            f"{m.role}: {m.text}"
            for m in conversation.messages.order_by("-created_at")[:6]
        ][::-1]
        profile = getattr(request.user, "profile", None)
        task = AgentTask.objects.create(
            kind=AgentTask.Kind.TUTOR_REPLY,
            user=request.user,
            input_data={
                "question": text,
                "subject": subject,
                "grade_level": getattr(profile, "grade_level", None) or None,
                "country": request.user.country or "",
                "history": history,
            },
        )
        run_task(task)
        output = task.output_data or {}
        reply = output.get("reply") or "Sorry, I could not reach my model. Please retry."

        msg = Message.objects.create(conversation=conversation, role="agent", text=reply)
        resp = MessageSerializer(msg).data
        if output.get("follow_ups"):
            resp["follow_ups"] = output["follow_ups"]
        if output.get("context"):
            resp["context"] = output["context"]
        return Response(resp, status=status.HTTP_201_CREATED)