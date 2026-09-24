from asgiref.sync import sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import TestCase, override_settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from apps.accounts.models import Profile
from apps.tutoring.models import TutoringSession

User = get_user_model()


@override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer", "CONFIG": {}}})
class SignalConsumerTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", password="x", role="student")
        Profile.objects.create(user=self.student)
        self.teacher = User.objects.create_user(username="tea", password="x", role="teacher")
        Profile.objects.create(user=self.teacher)
        self.session = TutoringSession.objects.create(student=self.student)

    def _comm(self, user):
        from rest_framework_simplejwt.tokens import AccessToken
        tok = str(AccessToken.for_user(user))
        path = f"/ws/tutor/{self.session.pk}/?device=web&token={tok}"
        return WebsocketCommunicator(
            __import__("config.asgi", fromlist=["application"]).application, path
        )

    async def _connect(self, user):
        comm = self._comm(user)
        ok, _ = await comm.connect()
        self.assertTrue(ok)
        welcome = await comm.receive_json_from(timeout=2)
        self.assertEqual(welcome["type"], "welcome")
        return comm


    async def _expect(self, comm, kind):
        """Drain presence frames until the message we care about arrives."""
        while True:
            m = await comm.receive_json_from(timeout=2)
            if m["type"] == kind:
                return m

    async def test_relay_offer_answer_ice(self):
        a = await self._connect(self.student)
        b = await self._connect(self.teacher)

        await b.send_json_to({"type": "offer", "payload": {"sdp": "sdp-teacher"}, "id": "o1"})
        offer = await self._expect(a, "offer")
        self.assertEqual(offer["type"], "offer")
        self.assertEqual(offer["payload"]["sdp"], "sdp-teacher")

        await a.send_json_to({"type": "answer", "payload": {"sdp": "sdp-student"}, "id": "o2"})
        answer = await self._expect(b, "answer")
        self.assertEqual(answer["type"], "answer")

        await b.send_json_to({"type": "ice", "payload": {"candidate": "c1"}, "id": "o3"})
        ice = await self._expect(a, "ice")
        self.assertEqual(ice["type"], "ice")
        self.assertEqual(ice["relay_id"], "o3")

        await a.disconnect()
        await b.disconnect()

    async def test_no_self_echo(self):
        a = await self._connect(self.student)
        b = await self._connect(self.teacher)
        await a.send_json_to({"type": "offer", "payload": {"sdp": "a"}, "id": "o"})
        await b.send_json_to({"type": "ice", "payload": {"candidate": "c"}, "id": "i"})
        seen = []
        for _ in range(2):
            m = await a.receive_json_from(timeout=2)
            seen.append(m["type"])
        # a must have received b's presence + b's ice — never its own offer.
        self.assertNotIn("offer", seen)
        self.assertIn("ice", seen)
        await a.disconnect()
        await b.disconnect()

    async def test_mode_broadcast(self):
        a = await self._connect(self.student)
        b = await self._connect(self.teacher)
        await b.send_json_to({"type": "mode", "mode": "low"})
        mode = await self._expect(a, "mode")
        self.assertEqual(mode["payload"]["mode"], "low")
        await a.disconnect()
        await b.disconnect()


class TurnConfigTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", password="x", role="student")
        Profile.objects.create(user=self.student)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(AccessToken.for_user(self.student)))

    def _ice(self):
        return self.client.get("/api/v1/tutoring/ice/").json()

    @override_settings(TURN_SERVERS="[]")
    def test_empty_json_yields_stun_only(self):
        servers = self._ice()["iceServers"]
        self.assertEqual(servers, [{"urls": ["stun:stun.l.google.com:19302"]}])

    @override_settings(TURN_SERVERS="")
    def test_unset_yields_stun_only(self):
        servers = self._ice()["iceServers"]
        self.assertEqual(servers, [{"urls": ["stun:stun.l.google.com:19302"]}])

    @override_settings(TURN_SERVERS='["turn:turn.example.edu:3478?user=alice;pass=secret"]')
    def test_json_turn_with_credentials(self):
        servers = self._ice()["iceServers"]
        self.assertEqual(servers[0]["urls"], ["turn:turn.example.edu:3478"])
        self.assertEqual(servers[0]["username"], "alice")
        self.assertEqual(servers[0]["credential"], "secret")
        # STUN fallback is still appended.
        self.assertEqual(servers[1]["urls"], ["stun:stun.l.google.com:19302"])

    @override_settings(TURN_SERVERS='[{"urls":["stun:stun.cloudflare.com:3478"]}]')
    def test_shaped_json_passthrough(self):
        servers = self._ice()["iceServers"]
        self.assertEqual(servers[0]["urls"], ["stun:stun.cloudflare.com:3478"])

    @override_settings(TURN_SERVERS="garbage that is not a server")
    def test_junk_never_reaches_clients(self):
        servers = self._ice()["iceServers"]
        self.assertNotIn("turn:[]", [u for e in servers for u in e["urls"]])
        self.assertEqual(servers, [{"urls": ["stun:stun.l.google.com:19302"]}])


class ScheduleTests(TestCase):
    def setUp(self):
        self.student = User.objects.create_user(username="stu", password="x", role="student")
        Profile.objects.create(user=self.student)
        self.teacher = User.objects.create_user(username="tea", password="x", role="teacher")
        Profile.objects.create(user=self.teacher)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION="Bearer " + str(AccessToken.for_user(self.student)))

    def _create(self, **extra):
        body = {"topic": "Algebra bootcamp", "duration_minutes": 30, **extra}
        return self.client.post("/api/v1/tutoring/sessions/", body, format="json")

    def test_create_scheduled_future(self):
        r = self._create(scheduled_at=(timezone.now() + timedelta(hours=2)).isoformat())
        self.assertEqual(r.status_code, 201)
        d = r.json()
        self.assertIsNotNone(d["scheduled_at"])
        self.assertEqual(d["duration_minutes"], 30)
        self.assertEqual(d["status"], "requested")
        self.assertFalse(d["joinable"])
        self.assertGreater(d["starts_in_seconds"], 0)

    def test_create_rejects_past(self):
        r = self._create(scheduled_at=(timezone.now() - timedelta(hours=1)).isoformat())
        self.assertEqual(r.status_code, 400)

    def test_create_rejects_bad_duration(self):
        r = self._create(duration_minutes=23)
        self.assertEqual(r.status_code, 400)

    def test_join_window(self):
        # 2 minutes into the window (early-join) → joinable, signed countdown < 0.
        s = TutoringSession.objects.create(
            student=self.student, tutor=self.teacher,
            status=TutoringSession.Status.SCHEDULED,
            scheduled_at=timezone.now() - timedelta(minutes=2), duration_minutes=30,
        )
        ser = self.client.get(f"/api/v1/tutoring/sessions/{s.pk}/").json()
        self.assertTrue(ser["joinable"])
        self.assertLess(ser["starts_in_seconds"], 0)

    def test_not_joinable_before_window(self):
        s = TutoringSession.objects.create(
            student=self.student, tutor=self.teacher,
            status=TutoringSession.Status.SCHEDULED,
            scheduled_at=timezone.now() + timedelta(hours=3), duration_minutes=30,
        )
        ser = self.client.get(f"/api/v1/tutoring/sessions/{s.pk}/").json()
        self.assertFalse(ser["joinable"])

    def test_cancel_by_participant(self):
        s = TutoringSession.objects.create(student=self.student, status=TutoringSession.Status.SCHEDULED)
        r = self.client.post(f"/api/v1/tutoring/sessions/{s.pk}/cancel/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["status"], "cancelled")

    def test_cancel_by_stranger_forbidden(self):
        other = User.objects.create_user(username="bad", password="x", role="student")
        Profile.objects.create(user=other)
        s = TutoringSession.objects.create(student=self.student, status=TutoringSession.Status.SCHEDULED)
        other_client = APIClient()
        other_client.credentials(HTTP_AUTHORIZATION="Bearer " + str(AccessToken.for_user(other)))
        # The queryset only exposes participant-owned sessions, so strangers get 404.
        r = other_client.post(f"/api/v1/tutoring/sessions/{s.pk}/cancel/")
        self.assertEqual(r.status_code, 404)

    async def test_ws_rejects_ended_session(self):
        def _mk():
            return TutoringSession.objects.create(
                student=self.student, status=TutoringSession.Status.ENDED)
        s = await sync_to_async(_mk)()
        tok = str(AccessToken.for_user(self.student))
        comm = WebsocketCommunicator(
            __import__("config.asgi", fromlist=["application"]).application,
            f"/ws/tutor/{s.pk}/?device=web&token={tok}",
        )
        ok, _ = await comm.connect()
        self.assertFalse(ok)

    async def test_ws_welcome_includes_schedule(self):
        def _mk():
            return TutoringSession.objects.create(
                student=self.student, status=TutoringSession.Status.SCHEDULED,
                scheduled_at=timezone.now() + timedelta(hours=1), duration_minutes=45,
            )
        s = await sync_to_async(_mk)()
        tok = str(AccessToken.for_user(self.student))
        comm = WebsocketCommunicator(
            __import__("config.asgi", fromlist=["application"]).application,
            f"/ws/tutor/{s.pk}/?device=web&token={tok}",
        )
        ok, _ = await comm.connect()
        self.assertTrue(ok)
        welcome = await comm.receive_json_from(timeout=2)
        self.assertIsNotNone(welcome["schedule"])
        self.assertEqual(welcome["schedule"]["duration_minutes"], 45)
        await comm.disconnect()

    async def test_ws_rejects_stranger(self):
        def _mk():
            return TutoringSession.objects.create(
                student=self.student, status=TutoringSession.Status.SCHEDULED)
        s = await sync_to_async(_mk)()
        other = await sync_to_async(User.objects.create_user)(
            username="eve", password="x", role="student")
        await sync_to_async(Profile.objects.create)(user=other)
        tok = str(AccessToken.for_user(other))
        comm = WebsocketCommunicator(
            __import__("config.asgi", fromlist=["application"]).application,
            f"/ws/tutor/{s.pk}/?device=web&token={tok}",
        )
        ok, _ = await comm.connect()
        self.assertFalse(ok)