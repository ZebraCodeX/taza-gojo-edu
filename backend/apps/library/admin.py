from django.contrib import admin

from .models import Download, Material


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ("title", "subject", "kind", "provider", "grade_start", "grade_end", "downloadable", "downloads", "active")
    list_filter = ("subject", "kind", "provider", "active")
    search_fields = ("title", "description", "provider")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ("user", "material", "device_id", "created_at")