"""Offline-first infrastructure.

Design goal: a child with patchy 2G/3G should keep learning with zero downtime.

1. Content manifests: one small JSON listing every lesson + its version. The
   PWA refreshes it whenever online (cheap), but otherwise plays cached lessons.

2. SyncQueue: every offline action (lesson complete, chat snippet, rating) is
   written to localStorage first and pushed here in batches when connectivity
   returns — the server applies them idempotently.
"""

from django.db import models
from django.conf import settings


class SyncBatch(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    device_id = models.CharField(max_length=64)
    payload = models.JSONField(default=list)  # [{"op": "progress", "data": {...}}, ...]
    applied = models.JSONField(default=list, blank=True)  # ids of applied ops
    status = models.CharField(max_length=10, default="pending",
                              choices=[("pending", "Pending"), ("done", "Done"), ("error", "Error")])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]