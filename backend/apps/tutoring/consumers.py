"""WebRTC signaling over WebSocket (Django Channels).

The browser (or the C++ mediaserver for relayed sessions) opens one socket per
room and exchanges SDP offers/answers and ICE candidates with the peer. Django
acts as a tiny, reliable message bus — resilient to flaky mobile networks, and
each message carries an `id` so clients can retransmit lost ones.
"""

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.conf import settings
from urllib.parse import parse_qs

from .models import TutoringSession

GROUP_PREFIX = "tutor"


def _session_token_from(query, user):
    """device_token tied to a user+session authorizes the call without cookies."""
    return (query.get("device_token") or [""])[0]


class SignalConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.session_id = self.scope["url_route"]["kwargs"].get("session_id")
        # Auth: JWT passed as ?token= (simple for constrained clients) or session.
        query = parse_qs(self.scope["query_string"].decode())
        self.token = (query.get("token") or [""])[0]
        self.device = (query.get("device") or ["web"])[0]  # "web" | "mediaserver"

        ok, self.user = await self._authorize()
        if not ok or not self.session_id:
            await self.close(code=4001)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({
            "type": "welcome",
            "session": self.session_id,
            "device": self.device,
            "role": "student" if self.user.is_student else "teacher",
            "mode": await self._session_mode(),
            "schedule": await self._session_schedule(),
            "mediaserver": settings.MEDIA_SERVER_URL,
        })
        # Tell the group someone is here (for presence/join detection).
        await self.channel_layer.group_send(self.group_name, {
            "type": "signal.message",
            "from_id": self.user.id,
            "kind": "peer_joined",
            "device": self.device,
        })

    async def disconnect(self, code):
        if self.session_id:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_send(self.group_name, {
                "type": "signal.message",
                "kind": "peer_left",
                "from_id": getattr(self, "user", None).id if hasattr(self, "user") else None,
            })

    async def receive_json(self, content, **kwargs):
        kind = content.get("type")

        # Media server can ask the web clients to switch bitrate/preset.
        if kind == "register_media_server" and self.device == "mediaserver":
            self.is_media_server = True
            return

        if kind in ("offer", "answer", "ice"):
            # Relay to the other participant(s), tagged with relay id for retransmit.
            await self.channel_layer.group_send(self.group_name, {
                "type": "signal.message",
                "from_id": self.user.id,
                "kind": kind,
                "payload": content.get("payload"),
                "relay_id": content.get("id") or "",
            })
        elif kind == "mode":
            await self._set_mode(content.get("mode"))
            await self.channel_layer.group_send(self.group_name, {
                "type": "signal.message", "kind": "mode", "from_id": self.user.id,
                "payload": {"mode": content.get("mode")},
            })
        elif kind == "presence":
            await self.channel_layer.group_send(self.group_name, {
                "type": "signal.message", "kind": "presence", "from_id": self.user.id,
                "payload": {"online": bool(content.get("online"))},
            })

    async def signal_message(self, event):
        if event.get("from_id") == getattr(self, "user", None).id:
            return  # don't echo to sender
        await self.send_json({
            "type": event.get("kind"),
            "from": event.get("from_id"),
            "payload": event.get("payload"),
            "relay_id": event.get("relay_id", ""),
        })

    # ---------------- helpers ----------------

    @property
    def group_name(self):
        return f"{GROUP_PREFIX}_{self.session_id}"

    @database_sync_to_async
    def _authorize(self):
        from rest_framework_simplejwt.tokens import AccessToken

        User = get_user_model()
        try:
            if self.token:
                payload = AccessToken(self.token)
                user = User.objects.get(pk=payload["user_id"])
            else:
                user = self.scope.get("user")
        except Exception:
            return False, None
        session = TutoringSession.objects.filter(pk=self.session_id).first()
        if not session:
            return False, None
        if session.status in (TutoringSession.Status.ENDED, TutoringSession.Status.CANCELLED):
            return False, None
        is_student = user == session.student
        is_tutor = user == session.tutor
        # A teacher may connect to an open request too (claiming it on the wire);
        # students may always watch their own session's lobby.
        if is_student or (is_tutor and session.status != TutoringSession.Status.REQUESTED):
            return True, user
        # Unassigned open request: any teacher may join the lobby to claim it.
        if user.is_teacher and session.status == TutoringSession.Status.REQUESTED:
            return True, user
        return False, None

    @database_sync_to_async
    def _session_mode(self):
        sess = TutoringSession.objects.filter(pk=self.session_id).first()
        return sess.mode if sess else "video"

    @database_sync_to_async
    def _session_schedule(self):
        sess = TutoringSession.objects.filter(pk=self.session_id).first()
        if not sess or not sess.scheduled_at:
            return None
        return {
            "scheduled_at": sess.scheduled_at.isoformat(),
            "duration_minutes": sess.duration_minutes,
        }

    @database_sync_to_async
    def _set_mode(self, mode):
        TutoringSession.objects.filter(pk=self.session_id).update(mode=mode)