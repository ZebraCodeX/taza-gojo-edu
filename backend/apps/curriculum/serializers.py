from rest_framework import serializers

from .models import Framework, Strand, Outcome, OutcomeLink, Mapping


class OutcomeSerializer(serializers.ModelSerializer):
    strand_title = serializers.CharField(source="strand.title", read_only=True)
    subject = serializers.CharField(source="strand.subject", read_only=True)
    framework = serializers.CharField(source="strand.framework.slug", read_only=True)

    class Meta:
        model = Outcome
        fields = [
            "id", "code", "reference", "statement", "grade_min", "grade_max",
            "difficulty", "tags", "strand_title", "subject", "framework",
        ]


class StrandSerializer(serializers.ModelSerializer):
    outcomes = OutcomeSerializer(many=True, read_only=True)

    class Meta:
        model = Strand
        fields = ["id", "subject", "code", "title", "description", "order", "outcomes"]


class FrameworkSerializer(serializers.ModelSerializer):
    strands = StrandSerializer(many=True, read_only=True)

    class Meta:
        model = Framework
        fields = [
            "id", "slug", "name", "country", "authority", "version",
            "description", "strands",
        ]


class MappingSerializer(serializers.ModelSerializer):
    from_code = serializers.CharField(source="from_outcome.code", read_only=True)
    to_code = serializers.CharField(source="to_outcome.code", read_only=True)

    class Meta:
        model = Mapping
        fields = ["id", "from_code", "to_code", "relation", "confidence", "note"]


class OutcomeLinkSerializer(serializers.ModelSerializer):
    outcome = OutcomeSerializer(read_only=True)

    class Meta:
        model = OutcomeLink
        fields = ["id", "outcome", "target_model", "target_id", "relation", "weight"]
