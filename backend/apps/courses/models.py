from django.db import models
from django.conf import settings


class Course(models.Model):
    """Top-level subject. Core set: English, Math, Science, Computer Programming."""

    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=40, default="📚")
    color = models.CharField(max_length=7, default="#1f6feb")  # brand accent
    order = models.PositiveSmallIntegerField(default=0)
    is_core = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)  # bumped to force client re-sync

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name


class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="modules")
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.course.name} · {self.title}"


class Lesson(models.Model):
    """A single playable unit. `content` is a JSON game script shared with the
    frontend renderer and designed to be tiny (KBs) for slow networks."""

    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name="lessons")
    title = models.CharField(max_length=160)
    kind = models.CharField(
        max_length=20,
        choices=[
            ("game", "Game"),
            ("video", "Video"),
            ("quiz", "Quiz"),
            ("reading", "Reading"),
        ],
        default="game",
    )
    # GameScript v1: list of steps the renderer interprets.
    content = models.JSONField(default=dict, blank=True)
    xp = models.PositiveIntegerField(default=10)
    duration_minutes = models.PositiveSmallIntegerField(default=5)
    version = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=0)

    # Video lecture (rendered offline from the lesson content with HyperFrames).
    # `lecture_file` holds the finished MP4 preview, `lecture_status` tracks the
    # render pipeline (pending -> rendering -> ready | error).
    lecture_file = models.FileField(upload_to="lectures/", blank=True, null=True)
    lecture_status = models.CharField(
        max_length=12,
        choices=[
            ("pending", "Pending"),
            ("rendering", "Rendering"),
            ("ready", "Ready"),
            ("error", "Error"),
        ],
        default="pending",
    )
    lecture_duration = models.PositiveIntegerField(default=0, help_text="Lecture length in seconds")

    class Meta:
        ordering = ["order"]

    def lecture_url(self):
        if not self.lecture_file:
            return ""
        from django.conf import settings

        return f"/{settings.MEDIA_URL.strip('/')}/{self.lecture_file.name}"

    def __str__(self):
        return self.title


class Question(models.Model):
    """Quiz items. Kept separate so grading + hint agents can inspect them."""

    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="questions")
    kind = models.CharField(max_length=12, choices=[
        ("mcq", "Multiple choice"), ("fill", "Fill in blank"), ("code", "Code output"),
    ], default="mcq")
    prompt = models.CharField(max_length=400)
    options = models.JSONField(default=list, blank=True)  # for mcq
    answer = models.CharField(max_length=200)
    hint = models.TextField(blank=True)  # AI-tutor hint text
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.prompt


class LessonProgress(models.Model):
    """Offline-friendly progress. Updated via batched sync from devices."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progress")
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name="progress")
    completed = models.BooleanField(default=False)
    score = models.IntegerField(default=0)
    stars = models.PositiveSmallIntegerField(default=0)  # 0..3
    attempts = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "lesson")

    def __str__(self):
        return f"{self.user} → {self.lesson}"