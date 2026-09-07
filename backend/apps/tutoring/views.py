from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django.conf import settings

from .models import TutoringSession, CallEvent
from .serializers import SessionSerializer, CallEventSerializer


class SessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = SessionSerializer
    http_method_names = ["get", "post", "patch"]

    def get_queryset(self):
        user = self.request.user
        if user.is_teacher:
            # Teachers see their own sessions PLUS open tutoring requests.
            return TutoringSession.objects.filter(
                Q(student=user) | Q(tutor=user) | Q(status=TutoringSession.Status.REQUESTED)
            )
        return TutoringSession.objects.filter(Q(student=user) | Q(tutor=user))

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        """A teacher claims an available request and opens the call window."""
        session = self.get_object()
        if request.user.is_teacher and session.status == TutoringSession.Status.REQUESTED:
            session.tutor = request.user
            session.status = TutoringSession.Status.SCHEDULED
            session.save()
            CallEvent.objects.create(session=session, kind="join", actor=request.user,
                                     detail={"event": "tutor accepted"})
            return Response(SessionSerializer(session).data)
        return Response({"error": "cannot accept"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        """Both parties present → active call."""
        session = self.get_object()
        if request.user not in (session.student, session.tutor):
            return Response({"error": "not a participant"}, status=status.HTTP_403_FORBIDDEN)
        session.status = TutoringSession.Status.ACTIVE
        session.started_at = timezone.now()
        session.mode = request.data.get("mode", session.mode)
        session.save()
        CallEvent.objects.create(session=session, kind="mode", actor=request.user,
                                 detail={"mode": session.mode})
        return Response(SessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        session = self.get_object()
        if request.user not in (session.student, session.tutor):
            return Response({"error": "not a participant"}, status=status.HTTP_403_FORBIDDEN)
        session.status = TutoringSession.Status.ENDED
        session.ended_at = timezone.now()
        session.rating = request.data.get("rating") or session.rating
        session.tutor_feedback = request.data.get("feedback", "")
        session.save()
        CallEvent.objects.create(session=session, kind="leave", actor=request.user,
                                 detail={"reason": "ended"})
        return Response(SessionSerializer(session).data)


class AvailableTutorsView(viewsets.ViewSet):
    """Students browse nearby-in-time teachers for the requested subject."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        from apps.accounts.models import Profile
        course_id = request.query_params.get("course")
        teachers = Profile.objects.filter(user__role__in=["teacher", "admin"])
        if course_id:
            teachers = teachers.filter(subjects__contains=[course_id]) | teachers.filter(subjects=[])
        rows = [
            {
                "id": p.user.id,
                "name": p.user.username,
                "country": p.user.country,
                "rating": p.rating,
                "subjects": p.subjects,
                "bio": p.bio[:160],
            }
            for p in teachers.distinct()[:25]
        ]
        return Response(rows)


class TurnConfigView(viewsets.ViewSet):
    """ICE servers the WebRTC clients should use (TURN matters for NAT in rural regions)."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        servers = []
        raw = settings.TURN_SERVERS
        if raw:
            for part in raw.split(";"):
                host, _, cred = part.partition("?")
                entry = {"urls": []}
                if cred:
                    u, _, p = cred.partition(";pass=")
                    user, _, passw = u.partition("=")
                    entry["username"] = user
                    entry["credential"] = passw
                entry["urls"].append("turn:" + host)
                servers.append(entry)
        if not servers:
            servers = [
                {"urls": ["stun:stun.l.google.com:19302"]},
            ]
        return Response({"iceServers": servers, "mediaServer": settings.MEDIA_SERVER_URL})