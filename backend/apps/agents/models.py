from django.db import models
from django.conf import settings


class AgentTask(models.Model):
    """A unit of work given to one of the AI agents.

    Queued tasks are picked up by `python manage.py run_agents` which runs them
    against the configured provider (openai / ollama / mock).
    """

    class Kind(models.TextChoices):
        GENERATE_LESSON = "generate_lesson", "Generate lesson"
        TUTOR_REPLY = "tutor_reply", "Tutor reply"
        GRADE = "grade", "Grade answer"
        PLAN_CURRICULUM = "plan_curriculum", "Plan curriculum"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    kind = models.CharField(max_length=30, choices=Kind.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)

    # The digital student / classroom this belongs to.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="agent_tasks",
    )
    course = models.ForeignKey("courses.Course", on_delete=models.SET_NULL, null=True,
                               blank=True, related_name="agent_tasks")

    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)

    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} #{self.pk} [{self.status}]"


class Conversation(models.Model):
    """Thread between a student and the AI tutor agent."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="tutor_conversations")
    course = models.ForeignKey("courses.Course", on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=10, choices=[("user", "User"), ("agent", "Agent")])
    text = models.TextField()
    meta = models.JSONField(default=dict, blank=True)  # hints, corrections, xp awarded
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]