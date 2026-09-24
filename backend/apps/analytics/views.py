from datetime import timedelta

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LearningEvent
from .serializers import LearningEventSerializer


class LearningEventViewSet(viewsets.GenericViewSet):
    serializer_class = LearningEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return LearningEvent.objects.filter(user=self.request.user)

    def list(self, request):
        qs = self.get_queryset()[:500]
        return Response(LearningEventSerializer(qs, many=True).data)

    def create(self, request):
        """Ingest one event or a batch: {events: [...]} / [ ... ] / { ... }."""
        payload = request.data.get("events") if isinstance(request.data, dict) else request.data
        if payload is None:
            payload = [request.data]
        if not isinstance(payload, list):
            return Response({"detail": "Expected a list of events."}, status=status.HTTP_400_BAD_REQUEST)
        rows = []
        for ev in payload[:500]:
            if not isinstance(ev, dict) or not ev.get("kind"):
                continue
            rows.append(LearningEvent(user=request.user, **{
                k: ev[k] for k in ("kind", "subject", "object_type", "object_id", "value", "metadata", "client_ts")
                if k in ev
            }))
        LearningEvent.objects.bulk_create(rows)
        return Response({"ingested": len(rows)}, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        since = timezone.now() - timedelta(days=30)
        qs = self.get_queryset().filter(created_at__gte=since)
        by_kind = list(qs.values("kind").annotate(n=Count("id")).order_by("-n"))
        by_subject = list(
            qs.exclude(subject="").values("subject").annotate(n=Count("id")).order_by("-n")
        )
        minutes = qs.filter(kind="video_watch").aggregate(s=Sum("value"))["s"] or 0
        active_days = qs.dates("created_at", "day").count()
        return Response({
            "window_days": 30,
            "total_events": qs.count(),
            "active_days": active_days,
            "watch_seconds": round(minutes),
            "by_kind": by_kind,
            "by_subject": by_subject,
        })
