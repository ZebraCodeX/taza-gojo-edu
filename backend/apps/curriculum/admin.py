from django.contrib import admin

from .models import Framework, Strand, Outcome, OutcomeLink, Mapping


class StrandInline(admin.TabularInline):
    model = Strand
    extra = 0


@admin.register(Framework)
class FrameworkAdmin(admin.ModelAdmin):
    list_display = ("name", "country", "authority", "version", "is_active", "order")
    list_filter = ("country", "is_active")
    search_fields = ("name", "authority")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [StrandInline]


@admin.register(Strand)
class StrandAdmin(admin.ModelAdmin):
    list_display = ("title", "framework", "subject", "code", "order")
    list_filter = ("framework", "subject")
    search_fields = ("title", "code")


@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    list_display = ("code", "short_statement", "strand", "grade_min", "grade_max", "difficulty")
    list_filter = ("strand__framework", "strand__subject")
    search_fields = ("code", "statement")

    @admin.display(description="Statement")
    def short_statement(self, obj):
        return obj.statement[:70]


@admin.register(OutcomeLink)
class OutcomeLinkAdmin(admin.ModelAdmin):
    list_display = ("outcome", "target_model", "target_id", "relation")
    list_filter = ("target_model", "relation")


@admin.register(Mapping)
class MappingAdmin(admin.ModelAdmin):
    list_display = ("from_outcome", "relation", "to_outcome", "confidence")
    list_filter = ("relation",)
