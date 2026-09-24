"""Assessment: item bank, adaptive attempts, auto-grading and certificates.

Answers never leave the server through the student API — the student serializer
strips ``answer``/``solution`` so the client can render an item without knowing
the key. Grading happens server-side (``grading.py``); adaptive item selection
lives in ``adaptive.py``.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


ITEM_KINDS = [
    ("mcq", "Multiple choice"),
    ("multi", "Multiple select"),
    ("numeric", "Numeric (with units)"),
    ("math", "Math expression"),
    ("code", "Code output"),
    ("order", "Ordering"),
    ("match", "Matching"),
    ("short", "Short answer"),
    ("essay", "Essay (manual)"),
]

# Kinds that cannot be auto-graded and need a human.
MANUAL_KINDS = {"essay"}


class Item(models.Model):
    """A single reusable question in the bank."""

    course = models.ForeignKey(
        "courses.Course", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="items",
    )
    subject = models.SlugField(blank=True, help_text="e.g. physics, electricity, math")
    kind = models.CharField(max_length=12, choices=ITEM_KINDS, default="mcq")
    prompt = models.TextField()
    # Optional structured body: code snippet, passage, graph spec, image url.
    body = models.JSONField(default=dict, blank=True)
    # For mcq/multi/order/match: list of options. Shape depends on kind.
    options = models.JSONField(default=list, blank=True)
    # Canonical answer. Never exposed to students.
    answer = models.JSONField(default=dict, blank=True)
    solution = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    explanation = models.TextField(blank=True)

    # Calibration (adaptive engine reads these).
    difficulty = models.FloatField(default=1000.0, help_text="Elo difficulty")
    discrimination = models.FloatField(default=1.0)

    grade_min = models.PositiveSmallIntegerField(default=1)
    grade_max = models.PositiveSmallIntegerField(default=12)
    language = models.CharField(max_length=10, default="en")
    source = models.CharField(max_length=200, blank=True, help_text="Attribution / origin")
    tags = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]
        indexes = [
            models.Index(fields=["subject", "kind", "is_active"]),
            models.Index(fields=["difficulty"]),
        ]

    def __str__(self):
        return f"[{self.kind}] {self.prompt[:60]}"


class Assessment(models.Model):
    KINDS = [
        ("quiz", "Quiz"),
        ("practice", "Practice"),
        ("diagnostic", "Diagnostic"),
        ("exam", "Exam"),
    ]

    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    course = models.ForeignKey(
        "courses.Course", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assessments",
    )
    framework = models.ForeignKey(
        "curriculum.Framework", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assessments",
    )
    subject = models.SlugField(blank=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="quiz")
    time_limit_minutes = models.PositiveSmallIntegerField(default=0, help_text="0 = untimed")
    pass_score = models.PositiveSmallIntegerField(default=60, help_text="Percent needed to pass")
    max_items = models.PositiveSmallIntegerField(default=10, help_text="Items served per attempt")
    adaptive = models.BooleanField(default=False)
    grade_min = models.PositiveSmallIntegerField(default=1)
    grade_max = models.PositiveSmallIntegerField(default=12)
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "title"]

    def __str__(self):
        return self.title


class AssessmentItem(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name="assessments")
    order = models.PositiveSmallIntegerField(default=0)
    points = models.FloatField(default=1.0)

    class Meta:
        ordering = ["order"]
        unique_together = ("assessment", "item")

    def __str__(self):
        return f"{self.assessment.slug} · {self.item_id}"


class Attempt(models.Model):
    STATUS = [
        ("in_progress", "In progress"),
        ("submitted", "Submitted"),
        ("graded", "Graded"),
        ("expired", "Expired"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name="attempts")
    status = models.CharField(max_length=12, choices=STATUS, default="in_progress")
    score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=0.0)
    # Current ability estimate (Elo); updated after each graded response.
    theta = models.FloatField(default=1000.0)
    served = models.JSONField(default=list, blank=True, help_text="Item ids served, in order")
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user} · {self.assessment.slug} · {self.status}"

    @property
    def percent(self):
        return round(100.0 * self.score / self.max_score, 1) if self.max_score else 0.0

    @property
    def passed(self):
        return self.percent >= self.assessment.pass_score


class Response(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="responses")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    answer = models.JSONField(default=dict, blank=True)
    correct = models.BooleanField(default=False)
    awarded = models.FloatField(default=0.0)
    max_points = models.FloatField(default=1.0)
    needs_manual = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    time_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        unique_together = ("attempt", "item")

    def __str__(self):
        return f"{self.attempt_id}/{self.item_id} {'✓' if self.correct else '✗'}"


class Certificate(models.Model):
    """Issued when a learner passes an assessment (or completes a track)."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates")
    assessment = models.ForeignKey(
        Assessment, null=True, blank=True, on_delete=models.SET_NULL, related_name="certificates"
    )
    title = models.CharField(max_length=200)
    subject = models.CharField(max_length=80, blank=True)
    score = models.FloatField(default=0.0)
    code = models.CharField(max_length=24, unique=True)
    verify_hash = models.CharField(max_length=64, blank=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self):
        return f"{self.code} · {self.title}"
