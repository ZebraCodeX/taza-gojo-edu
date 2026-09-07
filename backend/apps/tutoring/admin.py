from django.contrib import admin
from .models import TutoringSession, CallEvent


class CallEventInline(admin.TabularInline):
    model = CallEvent
    extra = 0


@admin.register(TutoringSession)
class SessionAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "tutor", "course", "topic", "status", "mode", "created_at")
    list_filter = ("status", "mode")
    inlines = [CallEventInline]