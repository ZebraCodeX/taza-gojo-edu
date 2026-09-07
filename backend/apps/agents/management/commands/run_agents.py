"""Run queued agent tasks in the background.

Usage:  python manage.py run_agents [--once]
"""

import time

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.agents.models import AgentTask
from apps.agents.agents import run_task


class Command(BaseCommand):
    help = "Poll the AgentTask queue and run agents against the configured AI provider."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process one batch, then exit.")
        parser.add_argument("--sleep", type=int, default=2, help="Seconds between polls.")

    def handle(self, *args, **options):
        once = options["once"]
        self.stdout.write("Agent worker started.")
        while True:
            task = (
                AgentTask.objects.exclude(status=AgentTask.Status.DONE)
                .filter(status=AgentTask.Status.QUEUED)
                .order_by("created_at")
                .first()
            )
            if task:
                run_task(task)
                self.stdout.write(f"  → task #{task.pk} [{task.get_kind_display()}] -> {task.status}")
                continue
            if once:
                break
            # Retry stale RUNNING tasks (crashed worker).
            AgentTask.objects.filter(
                status=AgentTask.Status.RUNNING,
                created_at__lt=timezone.now() - timedelta(minutes=5),
            ).update(status=AgentTask.Status.QUEUED)
            time.sleep(options["sleep"])