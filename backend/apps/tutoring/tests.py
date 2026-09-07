import asyncio
import json
from channels.testing import WebsocketCommunicator
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
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
        from urllib.parse import quote
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