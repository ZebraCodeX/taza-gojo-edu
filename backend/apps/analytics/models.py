"""Lightweight xAPI-style learning events.

Events are written offline-first by clients and flushed in batches through the
existing sync layer (or directly here). They power streaks, mastery trends and
teacher/guardian dashboards without a separate warehouse.
"""

from django.conf import settings
from django.db import models


class LearningEvent(models.Model):
    KINDS = [
        ("lesson_start", "Lesson started"),
        ("lesson_complete", "Lesson completed"),
        ("assessment_start", "Assessment started"),
        ("assessment_submit", "Assessment submitted"),
        ("lab_submit", "Lab submitted"),
        ("live_join", "Live class joined"),
        ("material_open", "Material opened"),
        ("video_watch", "Video watched"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=24, choices=KINDS)
    subject = models.SlugField(blank=True)
    object_type = models.CharField(max_length=60, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    value = models.FloatField(default=0.0, help_text="e.g. seconds watched, percent score")
    metadata = models.JSONField(default=dict, blank=True)
    client_ts = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "kind"]),
            models.Index(fields=["subject", "kind"]),
        ]

    def __str__(self):
        return f"{self.user} {self.kind} {self.subject}"
