"""Feature-phone gateway: SMS, USSD and voice (IVR) access.

Many learners have no smartphone at all. This app lets them take quizzes and
receive feedback over plain SMS or USSD, and (later) hear lessons by voice. It
reuses the same item bank and grading as the app, so one curriculum serves every
channel.
"""

from django.conf import settings
from django.db import models


class PhoneUser(models.Model):
    """A learner reachable by phone, optionally linked to an app account."""

    phone = models.CharField(max_length=24, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="phone_profiles",
    )
    name = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=10, default="en")
    grade_level = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.phone


class Channel(models.TextChoices):
    SMS = "sms", "SMS"
    USSD = "ussd", "USSD"
    VOICE = "voice", "Voice"


class QuizSession(models.Model):
    """State for one phone learner's quiz across messages/calls."""

    STATE = [
        ("idle", "Idle"),
        ("choosing_subject", "Choosing subject"),
        ("answering", "Answering"),
    ]

    phone_user = models.ForeignKey(PhoneUser, on_delete=models.CASCADE, related_name="sessions")
    channel = models.CharField(max_length=8, choices=Channel.choices, default=Channel.SMS)
    state = models.CharField(max_length=20, choices=STATE, default="idle")
    subject = models.SlugField(blank=True)
    current_item = models.ForeignKey(
        "assessment.Item", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    asked = models.JSONField(default=list, blank=True, help_text="Item ids already served")
    score = models.PositiveIntegerField(default=0)
    answered = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.phone_user.phone} · {self.state}"


class Message(models.Model):
    """Audit log of every inbound/outbound message (and USSD screen)."""

    phone_user = models.ForeignKey(
        PhoneUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages"
    )
    channel = models.CharField(max_length=8, choices=Channel.choices, default=Channel.SMS)
    direction = models.CharField(max_length=3, choices=[("in", "In"), ("out", "Out")])
    body = models.TextField(blank=True)
    provider = models.CharField(max_length=40, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel} {self.direction} {self.phone_user_id}"
