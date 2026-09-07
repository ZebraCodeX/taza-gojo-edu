"""Library material serializers."""

from rest_framework import serializers

from .models import Material


class MaterialBriefSerializer(serializers.ModelSerializer):
    grade_band = serializers.SerializerMethodField()
    subject_name = serializers.CharField(source="get_subject_display", read_only=True)

    class Meta:
        model = Material
        fields = [
            "slug", "id", "subject", "subject_name", "title", "description",
            "kind", "provider", "license_note", "grade_start", "grade_end",
            "grade_band", "url", "downloadable", "downloads", "outline", "pages",
        ]

    def get_grade_band(self, obj):
        return grade_band_label(obj.grade_start, obj.grade_end)


class MaterialDetailSerializer(MaterialBriefSerializer):
    class Meta(MaterialBriefSerializer.Meta):
        fields = MaterialBriefSerializer.Meta.fields + ["content"]


def grade_band_label(start, end):
    if start >= 13:
        return "College"
    if end >= 13:
        return f"Grade {start} + (College tracks)"
    if start == end:
        return f"Grade {start}"
    return f"Grades {start}–{end}"