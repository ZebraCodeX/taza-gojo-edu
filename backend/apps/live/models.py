"""Live classes.

Media is carried by a self-hosted LiveKit SFU (open source, SDKs for web,
Android, iOS, desktop). This app owns scheduling, room membership and
attendance; it issues short-lived, scoped access tokens and never handles
media itself.

Set ``LIVEKIT_URL`` / ``LIVEKIT_API_KEY`` / ``LIVEKIT_API_SECRET`` in the
environment. With no keys configured the API still returns a room + URL so the
P2P fallback (the existing tutoring signaling) can be used.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class LiveClass(models.Model):
    STATUS = [
        ("scheduled", "Scheduled"),
        ("live", "Live"),
        ("ended", "Ended"),
        ("cancelled", "Cancelled"),
    ]

    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    host = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="hosted_classes")
    course = models.ForeignKey(
        "courses.Course", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="live_classes",
    )
    subject = models.SlugField(blank=True)
    room_name = models.CharField(max_length=80, unique=True)
    scheduled_at = models.DateTimeField(default=timezone.now)
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    max_participants = models.PositiveSmallIntegerField(default=15)
    status = models.CharField(max_length=12, choices=STATUS, default="scheduled")
    is_recorded = models.BooleanField(default=False)
    recording_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self):
        return f"{self.title} ({self.status})"


class Attendance(models.Model):
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE, related_name="attendance")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attendance")
    role = models.CharField(max_length=12, default="student")
    joined_at = models.DateTimeField(default=timezone.now)
    left_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-joined_at"]

    def __str__(self):
        return f"{self.user} @ {self.live_class_id}"
