from rest_framework import serializers
from .models import AgentTask, Conversation, Message


class AgentTaskSerializer(serializers.ModelSerializer):
    kind_display = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = AgentTask
        fields = ["id", "kind", "kind_display", "status", "input_data", "output_data",
                  "error", "created_at", "finished_at"]
        read_only_fields = ["status", "output_data", "error"]


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ["id", "role", "text", "meta", "created_at"]


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ["id", "subject", "course", "messages", "updated_at"]