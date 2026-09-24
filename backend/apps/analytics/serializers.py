from rest_framework import serializers

from .models import LearningEvent


class LearningEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningEvent
        fields = ["id", "kind", "subject", "object_type", "object_id", "value", "metadata", "client_ts", "created_at"]
        read_only_fields = ["id", "created_at"]
