from django.db import models
from django.conf import settings
from django.utils import timezone


class TutoringSession(models.Model):
    """A live face-to-face session between a student and a remote tutor.

    Status flow:
      requested -> the student wants a tutor
      scheduled -> matched to a teacher, waiting to connect
      active    -> signaling started (or in progress)
      ended     -> finished normally
      cancelled
    """

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        SCHEDULED = "scheduled", "Scheduled"
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"
        CANCELLED = "cancelled", "Cancelled"

    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="tutoring_sessions_as_student")
    tutor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                              null=True, blank=True, related_name="tutoring_sessions_as_tutor")
    course = models.ForeignKey("courses.Course", on_delete=models.SET_NULL, null=True,
                               related_name="tutoring_sessions")
    topic = models.CharField(max_length=120, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.REQUESTED)

    # Zoom-style scheduling: when the call window opens and how long it lasts.
    scheduled_at = models.DateTimeField(null=True, blank=True,
                                   help_text="Call window opens this time (participants can join a few minutes early).")
    duration_minutes = models.PositiveSmallIntegerField(
        default=30, help_text="Scheduled call length in minutes.")
    EARLY_JOIN_MINUTES = 5  # how early participants may join before the window

    # Bandwidth hint negotiated at start of call, drives mediaserver encoder presets.
    mode = models.CharField(
        max_length=10,
        choices=[("video", "Video"), ("audio-only", "Audio only"), ("low", "Low (2G video)")],
        default="video",
    )

    device_token_student = models.CharField(max_length=64, blank=True)
    device_token_tutor = models.CharField(max_length=64, blank=True)

    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    rating = models.PositiveSmallIntegerField(null=True, blank=True)  # 1..5 stars
    tutor_feedback = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.student} ↔ {self.tutor or 'unmatched'} [{self.status}]"

    # ---- scheduling helpers (Zoom-style windows) ----

    def starts_in_seconds(self, now=None):
        """Signed seconds until the window opens (negative once it's open)."""
        import datetime

        if not self.scheduled_at:
            return None
        now = now or timezone.now()
        return int((self.scheduled_at - now).total_seconds())

    def window_open(self, now=None):
        """True when participants may join: a few min early, up to the scheduled end."""
        import datetime as dt

        if self.scheduled_at:
            now = now or timezone.now()
            early_ok = self.scheduled_at - dt.timedelta(minutes=self.EARLY_JOIN_MINUTES)
            ends = self.scheduled_at + dt.timedelta(minutes=self.duration_minutes + 15)
            return early_ok <= now <= ends
        return True  # ad-hoc session: join anytime


class CallEvent(models.Model):
    """Audit trail for live calls: joins, leaves, mode switches, signal errors."""

    KIND = [
        ("join", "Join"), ("leave", "Leave"), ("mode", "Mode change"),
        ("signal", "Signal"), ("error", "Error"),
    ]
    session = models.ForeignKey(TutoringSession, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=10, choices=KIND)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_kind_display()} {self.actor} @ {self.created_at:%H:%M}"