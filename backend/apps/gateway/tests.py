from django.test import TestCase, override_settings

from apps.assessment.models import Item
from apps.gateway import services
from apps.gateway.models import PhoneUser, Message


def make_item():
    return Item.objects.create(
        subject="math", kind="mcq", prompt="What is 2 + 2?",
        options=[{"id": "a", "text": "3"}, {"id": "b", "text": "4"}, {"id": "c", "text": "5"}],
        answer={"value": "b"}, grade_min=1, grade_max=12, is_active=True,
    )


class SmsFlowTests(TestCase):
    def setUp(self):
        make_item()

    def test_start_choose_and_answer(self):
        replies = services.handle_sms("+251900000001", "START")
        self.assertTrue(any("Reply with a number" in r for r in replies))

        q = services.handle_sms("+251900000001", "1")  # math
        self.assertTrue(any("What is 2 + 2?" in r for r in q))
        self.assertTrue(any("B) 4" in r for r in q))

        fb = services.handle_sms("+251900000001", "B")
        self.assertTrue(any("Correct" in r for r in fb))

        wrong = services.handle_sms("+251900000001", "A")
        self.assertTrue(any("Not quite" in r for r in wrong))

    def test_unknown_reply_prompts(self):
        services.handle_sms("+251900000002", "START")
        services.handle_sms("+251900000002", "1")
        replies = services.handle_sms("+251900000002", "Z")
        self.assertTrue(any("A, B, C or D" in r for r in replies))

    def test_stop(self):
        services.handle_sms("+251900000003", "START")
        replies = services.handle_sms("+251900000003", "STOP")
        self.assertTrue(any("left the quiz" in r for r in replies))
        self.assertTrue(PhoneUser.objects.filter(phone="+251900000003").exists())
        self.assertTrue(Message.objects.filter(phone_user__phone="+251900000003").exists())


class UssdFlowTests(TestCase):
    def setUp(self):
        make_item()

    def test_menu_question_and_end(self):
        cont, msg = services.handle_ussd("+251900000010", "")
        self.assertTrue(cont)
        self.assertIn("Taza-Gojo", msg)

        cont, msg = services.handle_ussd("+251900000010", "1")
        self.assertTrue(cont)
        self.assertIn("Q1", msg)

        cont, msg = services.handle_ussd("+251900000010", "B")
        self.assertIn("Correct", msg)

        cont, msg = services.handle_ussd("+251900000010", "0")
        self.assertFalse(cont)
        self.assertIn("Thanks", msg)


class WebhookTests(TestCase):
    def setUp(self):
        make_item()

    def test_sms_webhook(self):
        res = self.client.post("/api/v1/gateway/sms/", {"from": "+251900000020", "text": "START"})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json()["ok"])

    @override_settings(GATEWAY_WEBHOOK_TOKEN="secret")
    def test_sms_webhook_requires_token(self):
        denied = self.client.post("/api/v1/gateway/sms/", {"from": "+251900000021", "text": "START"})
        self.assertEqual(denied.status_code, 403)
        ok = self.client.post("/api/v1/gateway/sms/?token=secret", {"from": "+251900000021", "text": "START"})
        self.assertEqual(ok.status_code, 200)

    def test_ussd_webhook_format(self):
        res = self.client.post("/api/v1/gateway/ussd/", {"phoneNumber": "+251900000022", "text": ""})
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.content.decode().startswith("CON "))
