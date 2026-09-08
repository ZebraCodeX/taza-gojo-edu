from rest_framework import serializers
from .models import TutoringSession, CallEvent


class SessionSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source="student.username", read_only=True)
    tutor_name = serializers.SerializerMethodField()
    course_name = serializers.CharField(source="course.name", read_only=True)
    joinable = serializers.SerializerMethodField()
    starts_in_seconds = serializers.SerializerMethodField()

    class Meta:
        model = TutoringSession
        fields = [
            "id", "student_name", "tutor_name", "course", "course_name", "topic",
            "status", "mode", "scheduled_at", "duration_minutes", "joinable",
            "starts_in_seconds", "started_at", "ended_at", "rating", "created_at",
        ]
        read_only_fields = ["status", "started_at", "ended_at"]

    def validate_duration_minutes(self, value):
        if value not in (15, 30, 45, 60):
            raise serializers.ValidationError("Pick 15, 30, 45 or 60 minutes.")
        return value

    def get_tutor_name(self, obj):
        return obj.tutor.username if obj.tutor else None

    def get_joinable(self, obj):
        return obj.status in ("scheduled", "active") and obj.window_open()

    def get_starts_in_seconds(self, obj):
        return obj.starts_in_seconds()


class CallEventSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="actor.username", read_only=True)

    class Meta:
        model = CallEvent
        fields = ["id", "kind", "name", "detail", "created_at"]