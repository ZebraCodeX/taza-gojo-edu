from rest_framework import serializers

from .models import LiveClass, Attendance


class LiveClassSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source="host.username", read_only=True)
    course_slug = serializers.CharField(source="course.slug", read_only=True, default=None)
    attendee_count = serializers.SerializerMethodField()

    class Meta:
        model = LiveClass
        fields = [
            "id", "title", "description", "host_name", "course_slug", "subject",
            "room_name", "scheduled_at", "duration_minutes", "max_participants",
            "status", "is_recorded", "recording_url", "attendee_count",
        ]
        extra_kwargs = {"room_name": {"required": False}}

    def get_attendee_count(self, obj):
        return obj.attendance.count()


class AttendanceSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Attendance
        fields = ["id", "user_name", "role", "joined_at", "left_at", "duration_seconds"]
