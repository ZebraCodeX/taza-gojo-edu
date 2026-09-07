from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile


@admin.register(User)
class TazaGojoUserAdmin(UserAdmin):
    list_display = ("username", "role", "country", "is_staff")


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "grade_level", "points", "streak_days", "rating", "device_bandwidth")