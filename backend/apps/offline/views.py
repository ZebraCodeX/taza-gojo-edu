from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.courses.models import Course, Module, Lesson, LessonProgress

from .models import SyncBatch


class ManifestView(APIView):
    """Tiny sync manifest so clients know what changed without re-downloading everything."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        courses = []
        for c in Course.objects.prefetch_related("modules__lessons").all().order_by("order"):
            lessons = []
            for m in c.modules.all():
                for l in m.lessons.all():
                    lessons.append({"id": l.id, "v": l.version, "module": m.title})
            courses.append({
                "slug": c.slug, "name": c.name, "version": c.version, "lessons": lessons,
            })
        return Response({"courses": courses})


class SyncView(APIView):
    """Device pushes offline activity. Idempotent by op_id (client-generated UUID)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        batch = SyncBatch.objects.create(
            user=request.user,
            device_id=request.data.get("device_id", "unknown"),
            payload=request.data.get("ops", []),
        )
        applied = []
        with transaction.atomic():
            for op in batch.payload:
                op_type = op.get("op")
                did = op.get("id")
                if did in applied:
                    continue
                if op_type == "progress":
                    d = op.get("data", {})
                    lesson = Lesson.objects.filter(id=d.get("lesson")).first()
                    if not lesson:
                        continue
                    prev = LessonProgress.objects.filter(user=request.user, lesson=lesson).first()
                    LessonProgress.objects.update_or_create(
                        user=request.user,
                        lesson=lesson,
                        defaults={
                            "completed": bool(d.get("completed", prev.completed if prev else False)),
                            "score": int(d.get("score", prev.score if prev else 0)),
                            "stars": min(3, max(0, int(d.get("stars", 0)))) or (prev.stars if prev else 0),
                        },
                    )
                    applied.append(did)
                elif op_type == "chat":
                    # chat synced through agents endpoints too; just mark applied
                    applied.append(did)
                elif op_type == "material":
                    from apps.library.models import Download, Material as LibMaterial

                    m = LibMaterial.objects.filter(id=op.get("data", {}).get("id")).first()
                    if m:
                        Download.objects.get_or_create(
                            user=request.user, material=m, defaults={"device_id": did or ""}
                        )
                    applied.append(did)
                elif op_type == "rating":
                    applied.append(did)
        batch.applied = applied
        batch.status = "done"
        batch.save(update_fields=["applied", "status"])
        return Response({"applied": len(applied), "pending": len(batch.payload) - len(applied)})