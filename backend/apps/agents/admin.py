from django.contrib import admin
from .models import AgentTask, Conversation, Message


@admin.register(AgentTask)
class AgentTaskAdmin(admin.ModelAdmin):
    list_display = ("kind", "status", "user", "course", "created_at", "finished_at")
    list_filter = ("status", "kind")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("user", "subject", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "role", "created_at")