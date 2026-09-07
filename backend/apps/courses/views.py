from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q

from .models import Course, Module, Lesson, LessonProgress, Question
from .serializers import (
    CourseSerializer,
    ModuleSerializer,
    LessonListSerializer,
    LessonDetailSerializer,
    ProgressSerializer,
)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    lookup_field = "slug"

    @action(detail=True)
    def catalog(self, request, slug=None):
        """Full tree for one course — downloads once, then the app works offline."""
        course = self.get_object()
        return Response(ModuleSerializer(course.modules.all(), many=True, context={"request": request}).data)


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Lesson.objects.all()

    def get_serializer_class(self):
        return LessonDetailSerializer if self.action == "retrieve" else LessonListSerializer


class ProgressViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def list(self, request):
        rows = LessonProgress.objects.filter(user=request.user)
        return Response(ProgressSerializer(rows, many=True).data)

    def create(self, request):
        """Batch upsert from offline device sync: [{lesson, completed, score, stars, attempts}, ...]"""
        rows = request.data if isinstance(request.data, list) else [request.data]
        created = 0
        with transaction.atomic():
            for row in rows:
                lesson_id = row.get("lesson")
                if not lesson_id:
                    continue
                lesson = Lesson.objects.filter(id=lesson_id).first()
                if not lesson:
                    continue
                obj, was_created = LessonProgress.objects.update_or_create(
                    user=request.user,
                    lesson=lesson,
                    defaults={
                        "completed": bool(row.get("completed", False)),
                        "score": int(row.get("score", 0)),
                        "stars": min(3, max(0, int(row.get("stars", 0)))),
                        "attempts": obj_attempts(lesson, request.user) + 1,
                    },
                )
                created += 1
        return Response({"synced": created, "ok": True}, status=status.HTTP_201_CREATED)


def obj_attempts(lesson, user):
    p = LessonProgress.objects.filter(user=user, lesson=lesson).first()
    return p.attempts if p else 0