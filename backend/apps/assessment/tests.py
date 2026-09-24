from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from apps.assessment.models import Item, Assessment, AssessmentItem, Attempt, Certificate, Response
from apps.assessment import grading, adaptive

User = get_user_model()


class GradingTests(TestCase):
    def _item(self, kind, answer, options=None):
        return Item.objects.create(subject="physics", kind=kind, prompt="q", answer=answer, options=options or [])

    def test_mcq(self):
        it = self._item("mcq", {"value": "b"})
        self.assertTrue(grading.grade_item(it, {"value": "B"})["correct"])
        self.assertFalse(grading.grade_item(it, {"value": "a"})["correct"])

    def test_multi_partial_credit(self):
        it = self._item("multi", {"values": ["a", "b"]})
        full = grading.grade_item(it, {"values": ["a", "b"]})
        self.assertTrue(full["correct"])
        self.assertEqual(full["awarded"], 1.0)
        partial = grading.grade_item(it, {"values": ["a"]})
        self.assertFalse(partial["correct"])
        self.assertGreater(partial["awarded"], 0)

    def test_numeric_with_units(self):
        it = self._item("numeric", {"value": "12", "unit": "V", "tolerance": 0.01})
        self.assertTrue(grading.grade_item(it, {"value": "12", "unit": "V"})["correct"])
        wrong_unit = grading.grade_item(it, {"value": "12", "unit": "A"})
        self.assertFalse(wrong_unit["correct"])
        self.assertEqual(wrong_unit["awarded"], 0.5)

    def test_math_expression(self):
        it = self._item("math", {"value": "2^3", "tolerance": 0.01})
        self.assertTrue(grading.grade_item(it, {"value": "8"})["correct"])  # numeric equivalence
        self.assertFalse(grading.grade_item(it, {"value": "9"})["correct"])

    def test_code_output(self):
        it = self._item("code", {"expected_output": "14"})
        self.assertTrue(grading.grade_item(it, {"output": "14\n"})["correct"])

    def test_order(self):
        it = self._item("order", {"values": ["a", "b", "c"]})
        self.assertTrue(grading.grade_item(it, {"values": ["a", "b", "c"]})["correct"])
        self.assertFalse(grading.grade_item(it, {"values": ["b", "a", "c"]})["correct"])

    def test_match(self):
        it = self._item("match", {"pairs": {"Fuse": "Overload", "RCD": "Leakage"}})
        self.assertTrue(grading.grade_item(it, {"pairs": {"Fuse": "Overload", "RCD": "Leakage"}})["correct"])

    def test_essay_needs_manual(self):
        it = self._item("essay", {})
        self.assertTrue(grading.grade_item(it, {"value": "text"})["needs_manual"])

    def test_safe_eval_rejects_code(self):
        self.assertIsNone(grading.safe_eval("__import__('os').system('echo hi')"))
        self.assertEqual(grading.safe_eval("2+3*4"), 14.0)


class AdaptiveTests(TestCase):
    def test_theta_moves_up_on_success(self):
        t0 = 1000.0
        t1 = adaptive.update_theta(t0, 1000.0, 1.0)
        self.assertGreater(t1, t0)
        t2 = adaptive.update_theta(t0, 1000.0, 0.0)
        self.assertLess(t2, t0)

    def test_select_next_prefers_near_difficulty(self):
        a = Assessment.objects.create(slug="a", title="A", subject="physics", adaptive=True, max_items=1)
        easy = Item.objects.create(subject="physics", kind="mcq", prompt="easy", difficulty=800, answer={"value": "a"})
        hard = Item.objects.create(subject="physics", kind="mcq", prompt="hard", difficulty=1400, answer={"value": "a"})
        AssessmentItem.objects.create(assessment=a, item=easy, order=0)
        AssessmentItem.objects.create(assessment=a, item=hard, order=1)
        chosen = adaptive.select_next(a, theta=1350, answered_ids=set())
        self.assertEqual(chosen.item, hard)


class AssessmentFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("ada", password="test1234", role="student")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.a = Assessment.objects.create(
            slug="phy", title="Physics Quiz", subject="physics", kind="quiz",
            adaptive=False, max_items=2, pass_score=50,
        )
        self.i1 = Item.objects.create(subject="physics", kind="mcq", prompt="1+1?",
                                      options=[{"id": "a", "text": "1"}, {"id": "b", "text": "2"}],
                                      answer={"value": "b"}, difficulty=900)
        self.i2 = Item.objects.create(subject="physics", kind="numeric", prompt="2+2?",
                                      answer={"value": "4", "tolerance": 0.01}, difficulty=1000)
        AssessmentItem.objects.create(assessment=self.a, item=self.i1, order=0)
        AssessmentItem.objects.create(assessment=self.a, item=self.i2, order=1)

    def test_full_attempt_issues_certificate(self):
        start = self.client.post(f"/api/v1/assessment/assessments/{self.a.slug}/start/")
        self.assertEqual(start.status_code, 201)
        attempt = Attempt.objects.get(user=self.user)
        self.assertEqual(attempt.status, "in_progress")

        r1 = self.client.post(f"/api/v1/assessment/attempts/{attempt.id}/answer/",
                              {"item": self.i1.id, "answer": {"value": "b"}}, format="json")
        self.assertEqual(r1.status_code, 200)
        self.assertTrue(r1.data["result"]["correct"])

        r2 = self.client.post(f"/api/v1/assessment/attempts/{attempt.id}/answer/",
                              {"item": self.i2.id, "answer": {"value": "4"}}, format="json")
        self.assertTrue(r2.data["result"]["correct"])

        sub = self.client.post(f"/api/v1/assessment/attempts/{attempt.id}/submit/")
        self.assertEqual(sub.status_code, 200)
        self.assertEqual(sub.data["status"], "graded")
        self.assertTrue(sub.data["passed"])
        self.assertIsNotNone(sub.data["certificate"])
        self.assertTrue(Certificate.objects.filter(user=self.user).exists())

    def test_student_item_payload_hides_answer(self):
        resp = self.client.get("/api/v1/assessment/items/")
        self.assertEqual(resp.status_code, 200)
        rows = resp.data["results"] if isinstance(resp.data, dict) else resp.data
        self.assertTrue(rows)
        self.assertNotIn("answer", rows[0])


class TeacherGradingTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user("mrkwame", password="test1234", role="teacher")
        self.student = User.objects.create_user("ada", password="test1234", role="student")
        self.client = APIClient()

        self.a = Assessment.objects.create(slug="essay-test", title="Essay test", subject="english", pass_score=50, max_items=1)
        self.essay = Item.objects.create(subject="english", kind="essay", prompt="Write about your school.", answer={}, difficulty=1000)
        AssessmentItem.objects.create(assessment=self.a, item=self.essay, order=0)

    def _attempt(self):
        self.client.force_authenticate(self.student)
        start = self.client.post(f"/api/v1/assessment/assessments/{self.a.slug}/start/")
        attempt_id = start.data["attempt_id"]
        self.client.post(
            f"/api/v1/assessment/attempts/{attempt_id}/answer/",
            {"item": self.essay.id, "answer": {"value": "My school is great."}}, format="json",
        )
        self.client.post(f"/api/v1/assessment/attempts/{attempt_id}/submit/")
        return attempt_id

    def test_pending_and_grade_flow(self):
        attempt_id = self._attempt()

        self.client.force_authenticate(self.teacher)
        pending = self.client.get("/api/v1/assessment/attempts/pending/")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(len(pending.data), 1)
        response_id = pending.data[0]["id"]

        graded = self.client.post(
            f"/api/v1/assessment/attempts/{attempt_id}/responses/{response_id}/grade/",
            {"awarded": 1, "feedback": "Good start — add examples."}, format="json",
        )
        self.assertEqual(graded.status_code, 200)
        self.assertEqual(graded.data["status"], "graded")
        self.assertTrue(graded.data["passed"])
        self.assertIsNotNone(graded.data["certificate"])

    def test_student_cannot_grade(self):
        self._attempt()
        self.client.force_authenticate(self.student)
        self.assertEqual(self.client.get("/api/v1/assessment/attempts/pending/").status_code, 403)

    def test_overview(self):
        self._attempt()
        self.client.force_authenticate(self.teacher)
        data = self.client.get("/api/v1/assessment/attempts/overview/").data
        self.assertGreaterEqual(data["attempts"], 1)
        self.assertEqual(data["pending_grading"], 1)


class CalibrationTests(TestCase):
    def test_rasch_calibration_runs(self):
        from django.core.management import call_command
        from io import StringIO

        easy = Item.objects.create(subject="math", kind="mcq", prompt="easy", answer={"value": "a"}, difficulty=1000)
        hard = Item.objects.create(subject="math", kind="mcq", prompt="hard", answer={"value": "a"}, difficulty=1000)
        # 3 learners: everyone gets `easy` right, almost nobody gets `hard` right.
        for i in range(3):
            u = User.objects.create_user(f"cal{i}", password="x")
            a = Attempt.objects.create(user=u, assessment=self._assessment())
            Response.objects.create(attempt=a, item=easy, correct=True)
            Response.objects.create(attempt=a, item=hard, correct=(i == 0))

        out = StringIO()
        call_command("calibrate_items", "--min-responses", "2", stdout=out)
        easy.refresh_from_db()
        hard.refresh_from_db()
        self.assertLess(easy.difficulty, hard.difficulty)
        self.assertIn("Updated", out.getvalue())

    def _assessment(self):
        return Assessment.objects.create(slug=f"cal-{Assessment.objects.count()}", title="Cal", subject="math")
