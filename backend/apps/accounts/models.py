from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone as dj_timezone


class User(AbstractUser):
    """Single user model; role drives everything else."""

    class Role(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        CONTENT_CREATOR = "content_creator", "Content Creator"
        ADMIN = "admin", "Admin"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.STUDENT)
    country = models.CharField(max_length=80, blank=True)
    language = models.CharField(max_length=10, default="en")  # UI language

    # Low-bandwidth friendly: smallest avatar we store.
    avatar = models.URLField(blank=True)

    def subtitle(self):
        return self.get_role_display()

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role in (self.Role.TEACHER, self.Role.ADMIN)


class Profile(models.Model):
    """Extra per-role data."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")

    # Students
    grade_level = models.PositiveSmallIntegerField(null=True, blank=True)
    points = models.IntegerField(default=0)         # gamification score
    streak_days = models.PositiveSmallIntegerField(default=0)

    # Teachers
    subjects = models.JSONField(default=list, blank=True)  # ["english", "math", ...]
    bio = models.TextField(blank=True)
    rating = models.FloatField(default=5.0)
    timezone = models.CharField(max_length=40, blank=True)

    # Bandwidth device profile lets the app pick video quality presets.
    device_bandwidth = models.CharField(
        max_length=10,
        choices=[("low", "Low (2G)"), ("medium", "Medium (3G)"), ("high", "High (4G)")],
        default="medium",
    )

    # Learning roadmap: what the student wants to learn, set at onboarding and
    # editable any time. `goals` is [{subject, goal, target_weeks}, ...].
    interests = models.JSONField(default=list, blank=True)  # ["math", "english", ...]
    goals = models.JSONField(default=list, blank=True)
    weekly_minutes = models.PositiveSmallIntegerField(default=120)
    onboarded = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=dj_timezone.now)