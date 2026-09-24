from django.contrib import admin

from .models import PhoneUser, QuizSession, Message


@admin.register(PhoneUser)
class PhoneUserAdmin(admin.ModelAdmin):
    list_display = ("phone", "name", "language", "grade_level", "user", "created_at")
    search_fields = ("phone", "name")
    list_filter = ("language",)


@admin.register(QuizSession)
class QuizSessionAdmin(admin.ModelAdmin):
    list_display = ("phone_user", "channel", "state", "subject", "score", "answered", "updated_at")
    list_filter = ("channel", "state", "subject")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("phone_user", "channel", "direction", "created_at", "short_body")
    list_filter = ("channel", "direction")
    search_fields = ("phone_user__phone", "body")

    @admin.display(description="Body")
    def short_body(self, obj):
        return obj.body[:70]
