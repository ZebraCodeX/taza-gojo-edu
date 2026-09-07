import json

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
    """ICE servers the WebRTC clients should use (TURN matters for NAT in rural regions).

    TURN_SERVERS may be a JSON array of server specs, e.g.
      ["turn:turn.example.edu:3478?user=alice;pass=secret", "stun:stun.example.edu:3478"]
    or shaped entries [{"urls":["turns:..."],"username":"u","credential":"p"}].
    """

    permission_classes = [IsAuthenticated]

    @staticmethod
    def _normalise(spec):
        """Return a WebRTC-style RTCIceServer dict, or None for junk input."""
        if isinstance(spec, dict):
            urls = spec.get("urls") or []
            if not urls:
                return None
            entry = {"urls": [u for u in urls if ":" in str(u)]}
            for key in ("username", "credential"):
                if spec.get(key):
                    entry[key] = spec[key]
            return entry if entry["urls"] else None
        spec = str(spec).strip()
        if not spec.lower().startswith(("turn:", "turns:", "stun:", "stuns:")):
            return None
        urls, _, cred = spec.partition("?")
        entry = {"urls": [urls]}
        if cred.startswith("user="):
            user, _, passw = cred[len("user="):].partition(";pass=")
            if user and passw:
                entry["username"] = user
                entry["credential"] = passw
        return entry

    def list(self, request):
        raw = (settings.TURN_SERVERS or "").strip()
        servers = []
        if raw and raw not in ("[]", "{}", "null"):
            try:
                raw = json.loads(raw) if raw.startswith(("[", "{")) else raw.split(";")
            except json.JSONDecodeError:
                raw = raw.split(";")
            for item in raw or []:
                entry = self._normalise(item)
                if entry:
                    servers.append(entry)
        # Always give clients a working way to gather reflexive candidates;
        # a malformed/empty TURN config must never leave them with no servers.
        stun_present = any(
            "stun:" in u.lower() for entry in servers for u in entry.get("urls", [])
        )
        if not stun_present:
            servers.append({"urls": ["stun:stun.l.google.com:19302"]})
        return Response({"iceServers": servers, "mediaServer": settings.MEDIA_SERVER_URL})