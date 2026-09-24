"""Seed Brilliant-style interactive lessons.

Usage:  python manage.py seed_interactive

Idempotent: re-running updates the lesson content in place.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.courses.models import Course, Module, Lesson
from apps.courses.interactive_content import LESSONS


class Command(BaseCommand):
    help = "Create interactive guided-discovery lessons (physics, electricity, math, computing)."

    @transaction.atomic
    def handle(self, *args, **options):
        n = 0
        for spec in LESSONS:
            course = Course.objects.filter(slug=spec["course_slug"]).first()
            if not course:
                self.stderr.write(f"  ! course '{spec['course_slug']}' not found — run seed_core first")
                continue
            module, _ = Module.objects.get_or_create(
                course=course, title=spec["module_title"],
                defaults={"description": "Interactive guided lessons."},
            )
            lesson, _ = Lesson.objects.update_or_create(
                module=module, title=spec["lesson_title"],
                defaults={
                    "kind": "interactive",
                    "xp": spec.get("xp", 40),
                    "duration_minutes": spec.get("duration_minutes", 8),
                    "content": {"engine": "interactive", "steps": spec["steps"]},
                },
            )
            n += 1
        self.stdout.write(self.style.SUCCESS(f"Interactive lessons ready: {n}."))
