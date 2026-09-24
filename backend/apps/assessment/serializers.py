from rest_framework import serializers

from .models import Item, Assessment, AssessmentItem, Attempt, Response, Certificate


class ItemStudentSerializer(serializers.ModelSerializer):
    """Student-safe: never includes the answer or solution."""

    class Meta:
        model = Item
        fields = [
            "id", "kind", "prompt", "body", "options", "hint",
            "grade_min", "grade_max", "language", "tags",
        ]


class ItemStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = "__all__"


class AssessmentSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    course_slug = serializers.CharField(source="course.slug", read_only=True, default=None)

    class Meta:
        model = Assessment
        fields = [
            "id", "slug", "title", "description", "course_slug", "subject",
            "kind", "time_limit_minutes", "pass_score", "max_items", "adaptive",
            "grade_min", "grade_max", "item_count",
        ]

    def get_item_count(self, obj):
        return obj.items.count()


class AssessmentDetailSerializer(AssessmentSerializer):
    class Meta(AssessmentSerializer.Meta):
        fields = AssessmentSerializer.Meta.fields


class ResponseSerializer(serializers.ModelSerializer):
    item = ItemStudentSerializer(read_only=True)

    class Meta:
        model = Response
        fields = ["id", "item", "answer", "correct", "awarded", "max_points", "needs_manual", "feedback", "time_ms"]


class StaffResponseSerializer(serializers.ModelSerializer):
    """For teachers: includes the item key and the learner identity."""

    item = ItemStaffSerializer(read_only=True)
    username = serializers.CharField(source="attempt.user.username", read_only=True)
    attempt_id = serializers.IntegerField(source="attempt.id", read_only=True)
    assessment = serializers.CharField(source="attempt.assessment.title", read_only=True)

    class Meta:
        model = Response
        fields = [
            "id", "attempt_id", "assessment", "username", "item", "answer",
            "correct", "awarded", "max_points", "needs_manual", "feedback", "time_ms",
        ]


class AttemptSerializer(serializers.ModelSerializer):
    assessment_slug = serializers.CharField(source="assessment.slug", read_only=True)
    percent = serializers.FloatField(read_only=True)
    passed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Attempt
        fields = [
            "id", "assessment", "assessment_slug", "status", "score", "max_score",
            "theta", "percent", "passed", "started_at", "submitted_at", "duration_seconds",
        ]


class CertificateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Certificate
        fields = ["id", "title", "subject", "score", "code", "issued_at", "revoked"]
