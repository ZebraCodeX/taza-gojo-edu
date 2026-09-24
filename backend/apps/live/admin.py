from django.contrib import admin

from .models import LiveClass, Attendance


class AttendanceInline(admin.TabularInline):
    model = Attendance
    extra = 0
    readonly_fields = ("user", "role", "joined_at", "left_at", "duration_seconds")


@admin.register(LiveClass)
class LiveClassAdmin(admin.ModelAdmin):
    list_display = ("title", "host", "subject", "scheduled_at", "status", "max_participants", "is_recorded")
    list_filter = ("status", "subject", "is_recorded")
    search_fields = ("title", "room_name", "host__username")
    inlines = [AttendanceInline]
