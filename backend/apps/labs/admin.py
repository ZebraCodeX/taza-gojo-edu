from django.contrib import admin

from .models import Lab, LabSubmission


@admin.register(Lab)
class LabAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "kind", "subject", "language", "grade_min", "grade_max", "is_published")
    list_filter = ("kind", "language", "subject", "is_published")
    search_fields = ("title", "slug", "prompt")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(LabSubmission)
class LabSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "lab", "passed", "score", "created_at")
    list_filter = ("passed", "lab__kind")
    search_fields = ("user__username", "lab__slug")
