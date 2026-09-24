from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.live.models import LiveClass, Attendance

User = get_user_model()


class LiveClassTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("mrkwame", password="test1234", role="teacher")
        self.student = User.objects.create_user("ada", password="test1234", role="student")
        self.client = APIClient()

    def test_teacher_creates_and_student_joins(self):
        self.client.force_authenticate(self.teacher)
        created = self.client.post("/api/v1/live/classes/", {
            "title": "Physics live", "subject": "physics", "max_participants": 15,
        }, format="json")
        self.assertEqual(created.status_code, 201)
        cid = created.data["id"]

        self.client.force_authenticate(self.student)
        join = self.client.post(f"/api/v1/live/classes/{cid}/join/")
        self.assertEqual(join.status_code, 200)
        self.assertEqual(join.data["max_participants"], 15)
        self.assertFalse(join.data["can_publish"])
        self.assertTrue(Attendance.objects.filter(user=self.student).exists())

    @override_settings(LIVEKIT_URL="wss://lk.example", LIVEKIT_API_KEY="k", LIVEKIT_API_SECRET="s" * 32)
    def test_token_generated_when_configured(self):
        live = LiveClass.objects.create(title="T", host=self.teacher, room_name="tg-1")
        self.client.force_authenticate(self.student)
        join = self.client.post(f"/api/v1/live/classes/{live.id}/join/")
        self.assertTrue(join.data["configured"])
        self.assertTrue(join.data["token"])
