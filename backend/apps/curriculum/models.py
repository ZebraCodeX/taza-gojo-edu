"""Curriculum framework.

The platform is Ethiopia-first but must map flexibly onto other African
systems. Rather than hard-coding one country's syllabus, content is described
as *outcomes* grouped into *strands* inside a *framework*, and frameworks are
cross-mapped to each other.

    Framework (e.g. Cambridge IGCSE, Ethiopian MoE, TVET)
      └─ Strand (e.g. "Electricity and Magnetism")
           └─ Outcome (a single assessable statement, with a grade band)

Lessons/assessments/labs link to outcomes through ``OutcomeLink`` and can be
re-used across countries. Official syllabus codes are optional (``reference``);
internal codes stay stable even when a syllabus is revised.
"""

from django.db import models


class Framework(models.Model):
    """A national or international curriculum specification."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    # ISO-ish country label; blank means international.
    country = models.CharField(max_length=80, blank=True)
    authority = models.CharField(max_length=160, blank=True, help_text="Exam board / ministry")
    version = models.CharField(max_length=40, blank=True, help_text="Syllabus year/edition")
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "name"]

    def __str__(self):
        return self.name


class Strand(models.Model):
    """A themed group of outcomes within a framework (a 'topic area')."""

    framework = models.ForeignKey(Framework, on_delete=models.CASCADE, related_name="strands")
    subject = models.SlugField(help_text="Subject slug, e.g. physics, electricity, math")
    code = models.CharField(max_length=40, blank=True)
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["subject", "order"]
        unique_together = ("framework", "subject", "code", "title")

    def __str__(self):
        return f"{self.subject} · {self.title}"


class Outcome(models.Model):
    """A single assessable learning outcome, tied to a grade band."""

    strand = models.ForeignKey(Strand, on_delete=models.CASCADE, related_name="outcomes")
    code = models.CharField(max_length=40, help_text="Stable internal code, e.g. PHY-6.1")
    reference = models.CharField(
        max_length=80, blank=True,
        help_text="Optional official syllabus code (kept blank unless verified)",
    )
    statement = models.TextField(help_text="What the learner can do, written as a can-do statement")
    grade_min = models.PositiveSmallIntegerField(default=1)
    grade_max = models.PositiveSmallIntegerField(default=12)
    difficulty = models.FloatField(default=1000.0, help_text="Initial Elo difficulty estimate")
    order = models.PositiveSmallIntegerField(default=0)
    tags = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["strand", "order"]
        unique_together = ("strand", "code")

    def __str__(self):
        return f"{self.code}: {self.statement[:60]}"


class OutcomeLink(models.Model):
    """Links any object (lesson, assessment, lab) to an outcome it teaches/assesses.

    Deliberately generic (content_type/model + id) so new content types don't
    require schema changes and this app never imports the content apps.
    """

    REL = [
        ("teaches", "Teaches"),
        ("assesses", "Assesses"),
        ("prerequisite", "Prerequisite"),
    ]

    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name="links")
    target_model = models.CharField(max_length=60, help_text="e.g. courses.Lesson")
    target_id = models.PositiveIntegerField()
    relation = models.CharField(max_length=16, choices=REL, default="teaches")
    weight = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["target_model", "target_id"])]
        unique_together = ("outcome", "target_model", "target_id", "relation")

    def __str__(self):
        return f"{self.target_model}#{self.target_id} {self.relation} {self.outcome.code}"


class Mapping(models.Model):
    """Cross-framework mapping (Cambridge outcome <-> Ethiopian outcome, etc.)."""

    REL = [
        ("equivalent", "Equivalent"),
        ("partial", "Partial"),
        ("broader", "Broader"),
        ("narrower", "Narrower"),
    ]

    from_outcome = models.ForeignKey(
        Outcome, on_delete=models.CASCADE, related_name="mappings_out"
    )
    to_outcome = models.ForeignKey(
        Outcome, on_delete=models.CASCADE, related_name="mappings_in"
    )
    relation = models.CharField(max_length=12, choices=REL, default="equivalent")
    confidence = models.FloatField(default=0.8)
    note = models.CharField(max_length=240, blank=True)

    class Meta:
        unique_together = ("from_outcome", "to_outcome")

    def __str__(self):
        return f"{self.from_outcome.code} {self.relation} {self.to_outcome.code}"
