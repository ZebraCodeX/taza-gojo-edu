from django.core.management import call_command
from django.test import TestCase

from apps.curriculum.models import Framework, Outcome, Mapping


class SeedCurriculumTests(TestCase):
    def test_seed_creates_physics_and_electricity(self):
        call_command("seed_curriculum")
        self.assertTrue(Framework.objects.filter(slug="cambridge-igcse").exists())
        self.assertTrue(Framework.objects.filter(slug="ethiopia-tvet").exists())
        self.assertTrue(Outcome.objects.filter(code="PHY-6.1").exists())
        self.assertTrue(Outcome.objects.filter(code="ELE-6.3").exists())
        self.assertTrue(Outcome.objects.filter(code="ELE-T7").exists())
        self.assertGreaterEqual(Mapping.objects.count(), 5)

    def test_seed_is_idempotent(self):
        call_command("seed_curriculum")
        n = Outcome.objects.count()
        call_command("seed_curriculum")
        self.assertEqual(Outcome.objects.count(), n)
