from django.contrib import admin

from .models import Item, Assessment, AssessmentItem, Attempt, Response, Certificate


class AssessmentItemInline(admin.TabularInline):
    model = AssessmentItem
    extra = 0
    autocomplete_fields = ["item"]


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "kind", "subject", "short_prompt", "difficulty", "grade_min", "grade_max", "is_active")
    list_filter = ("kind", "subject", "is_active", "language")
    search_fields = ("prompt", "tags", "source")

    @admin.display(description="Prompt")
    def short_prompt(self, obj):
        return obj.prompt[:70]


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ("title", "slug", "subject", "kind", "adaptive", "max_items", "pass_score", "is_published")
    list_filter = ("kind", "adaptive", "is_published", "subject")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [AssessmentItemInline]


class ResponseInline(admin.TabularInline):
    model = Response
    extra = 0
    readonly_fields = ("item", "correct", "awarded", "feedback")


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "assessment", "status", "score", "max_score", "theta", "started_at")
    list_filter = ("status", "assessment")
    search_fields = ("user__username",)
    inlines = [ResponseInline]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("code", "user", "title", "subject", "score", "issued_at", "revoked")
    list_filter = ("revoked", "subject")
    search_fields = ("code", "user__username", "title")
