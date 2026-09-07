from rest_framework import serializers
from .models import TutoringSession, CallEvent


class SessionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.username", read_only=True)
    tutor_name = serializers.SerializerMethodField()
    course_name = serializers.CharField(source="course.name", read_only=True)

    class Meta:
        model = TutoringSession
        fields = [
            "id", "student_name", "tutor_name", "course", "course_name", "topic",
            "status", "mode", "started_at", "ended_at", "rating", "created_at",
        ]
        read_only_fields = ["status", "started_at", "ended_at"]

    def get_tutor_name(self, obj):
        return obj.tutor.username if obj.tutor else None


class CallEventSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = CallEvent
        fields = ["id", "kind", "name", "detail", "created_at"]