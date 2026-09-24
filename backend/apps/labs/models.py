"""Interactive labs: coding, circuits/electronics, physics and science.

Per the product decision, coding runs **browser-only** (Blockly for primary,
Pyodide for Python, a Web Worker for JavaScript), so ``tests`` are shipped to
the client to run offline. The server stores the authoritative test definition
and the submitted results, and can re-verify deterministic output labs.
"""

from django.conf import settings
from django.db import models

LAB_KINDS = [
    ("coding", "Coding"),
    ("circuit", "Circuit / Electronics"),
    ("physics", "Physics"),
    ("science", "Science"),
]

LAB_LANGS = [
    ("blockly", "Block-based"),
    ("python", "Python (Pyodide)"),
    ("javascript", "JavaScript"),
    ("none", "Not code"),
]


class Lab(models.Model):
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=LAB_KINDS, default="coding")
    subject = models.SlugField(blank=True, help_text="e.g. electricity, physics, computing")
    course = models.ForeignKey(
        "courses.Course", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="labs",
    )
    grade_min = models.PositiveSmallIntegerField(default=1)
    grade_max = models.PositiveSmallIntegerField(default=12)

    prompt = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    language = models.CharField(max_length=12, choices=LAB_LANGS, default="none")
    starter_code = models.TextField(blank=True)
    # Circuit/sim initial state, e.g. {"sim": "dc-circuit", "components": [...]}
    assets = models.JSONField(default=dict, blank=True)
    # Client-run tests: [{"name","expected_output"}] or [{"name","expr","expected"}]
    tests = models.JSONField(default=list, blank=True)
    solution = models.TextField(blank=True)

    xp = models.PositiveIntegerField(default=20)
    difficulty = models.FloatField(default=1000.0)
    is_published = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["order", "title"]
        indexes = [models.Index(fields=["kind", "subject", "is_published"])]

    def __str__(self):
        return f"[{self.kind}] {self.title}"


class LabSubmission(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="lab_submissions")
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, related_name="submissions")
    code = models.TextField(blank=True)
    language = models.CharField(max_length=12, blank=True)
    passed = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)
    results = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} · {self.lab.slug} · {'pass' if self.passed else 'fail'}"
