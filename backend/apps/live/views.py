import secrets

from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LiveClass, Attendance
from .serializers import LiveClassSerializer, AttendanceSerializer
from . import livekit


def _can_host(user):
    return bool(user and (user.is_staff or getattr(user, "role", "") in ("teacher", "admin")))


class LiveClassViewSet(viewsets.ModelViewSet):
    serializer_class = LiveClassSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = LiveClass.objects.select_related("host", "course")
        course = self.request.query_params.get("course")
        subject = self.request.query_params.get("subject")
        if course:
            qs = qs.filter(course__slug=course)
        if subject:
            qs = qs.filter(subject=subject)
        return qs

    def perform_create(self, serializer):
        room = serializer.validated_data.get("room_name") or f"tg-{secrets.token_hex(4)}"
        serializer.save(host=self.request.user, room_name=room)

    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """Return the LiveKit URL + a scoped token for this learner."""
        live = self.get_object()
        can_publish = _can_host(request.user)
        token = livekit.make_token(
            identity=f"u{request.user.id}",
            room=live.room_name,
            name=request.user.get_full_name() or request.user.username,
            can_publish=can_publish,
        )
        Attendance.objects.create(live_class=live, user=request.user, role="host" if can_publish else "student")
        if live.status == "scheduled" and can_publish:
            live.status = "live"
            live.save(update_fields=["status"])
        return Response({
            "room": live.room_name,
            "url": getattr(settings, "LIVEKIT_URL", ""),
            "token": token,
            "configured": livekit.is_configured(),
            "can_publish": can_publish,
            "max_participants": live.max_participants,
            "recorded": live.is_recorded,
        })

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        live = self.get_object()
        att = live.attendance.filter(user=request.user, left_at__isnull=True).order_by("-joined_at").first()
        if att:
            att.left_at = timezone.now()
            att.duration_seconds = int((att.left_at - att.joined_at).total_seconds())
            att.save(update_fields=["left_at", "duration_seconds"])
        return Response({"ok": True})

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        live = self.get_object()
        if not (_can_host(request.user) or live.host_id == request.user.id):
            return Response({"detail": "Only the host can end this class."}, status=status.HTTP_403_FORBIDDEN)
        live.status = "ended"
        live.save(update_fields=["status"])
        return Response(LiveClassSerializer(live).data)

    @action(detail=True, methods=["get"])
    def roster(self, request, pk=None):
        live = self.get_object()
        return Response(AttendanceSerializer(live.attendance.select_related("user"), many=True).data)
