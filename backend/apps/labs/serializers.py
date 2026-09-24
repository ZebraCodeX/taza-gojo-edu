from rest_framework import serializers

from .models import Lab, LabSubmission


class LabSerializer(serializers.ModelSerializer):
    course_slug = serializers.CharField(source="course.slug", read_only=True, default=None)

    class Meta:
        model = Lab
        fields = [
            "id", "slug", "title", "kind", "subject", "course_slug",
            "grade_min", "grade_max", "prompt", "instructions", "language",
            "starter_code", "assets", "tests", "xp", "difficulty",
        ]


class LabSubmissionSerializer(serializers.ModelSerializer):
    lab_slug = serializers.CharField(source="lab.slug", read_only=True)

    class Meta:
        model = LabSubmission
        fields = ["id", "lab", "lab_slug", "code", "language", "passed", "score", "results", "created_at"]
