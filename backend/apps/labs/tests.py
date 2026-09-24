from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.labs.models import Lab, LabSubmission

User = get_user_model()


class LabFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ada", password="test1234", role="student")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.lab = Lab.objects.create(
            slug="python-add", title="Add", kind="coding", subject="computing",
            language="python", tests=[{"name": "sum", "expected_output": "12"}],
        )

    def test_list_and_submit_pass(self):
        self.assertEqual(self.client.get("/api/v1/labs/labs/").status_code, 200)
        resp = self.client.post(
            f"/api/v1/labs/labs/{self.lab.slug}/submit/",
            {"code": "print(12)", "results": [{"name": "sum", "passed": True}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(resp.data["passed"])
        self.assertEqual(resp.data["total_tests"], 1)

    def test_submit_partial_fails(self):
        resp = self.client.post(
            f"/api/v1/labs/labs/{self.lab.slug}/submit/",
            {"results": [{"name": "sum", "passed": False}]},
            format="json",
        )
        self.assertFalse(resp.data["passed"])
        self.assertTrue(LabSubmission.objects.filter(user=self.user).exists())
