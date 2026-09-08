from rest_framework import serializers
from .models import Course, Module, Lesson, LessonProgress, Question


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "slug", "name", "description", "icon", "color", "version"]


class ModuleSerializer(serializers.ModelSerializer):
    lessons = serializers.SerializerMethodField()
    completed = serializers.SerializerMethodField()

    class Meta:
        model = Module
        fields = ["id", "title", "description", "lessons", "completed"]

    def get_lessons(self, obj):
        return LessonListSerializer(obj.lessons.all(), many=True).data

    def get_completed(self, obj):
        try:
            return LessonProgress.objects.filter(
                user=self.context["request"].user,
                lesson__module=obj,
                completed=True,
            ).count()
        except Exception:
            return 0


class LessonListSerializer(serializers.ModelSerializer):
    """Lightweight list row: just enough to render a dashboard / sync manifest."""

    lecture_url = serializers.SerializerMethodField()
    has_lecture = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "title", "kind", "xp", "duration_minutes", "version", "lecture_url", "has_lecture"]

    def get_lecture_url(self, obj):
        return obj.lecture_url()

    def get_has_lecture(self, obj):
        return obj.lecture_status == "ready" and bool(obj.lecture_file)


class LessonDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = [
            "id", "title", "kind", "content", "xp", "duration_minutes", "version",
            "lecture_url", "lecture_status", "lecture_duration",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["lecture_url"] = instance.lecture_url()
        data["questions"] = QuestionSerializer(instance.questions.all(), many=True).data
        return data


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ["id", "kind", "prompt", "options", "hint"]
        # `answer` intentionally excluded from client payload to discourage cheating.


class ProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = ["lesson", "completed", "score", "stars", "attempts", "updated_at"]
        read_only_fields = ["updated_at"]