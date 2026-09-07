from django.contrib import admin
from .models import Course, Module, Lesson, Question, LessonProgress


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_core", "version", "order")
    list_editable = ("is_core", "order")


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "order")


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "kind", "xp", "version")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "lesson", "kind")


@admin.register(LessonProgress)
class ProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "lesson", "completed", "stars", "updated_at")