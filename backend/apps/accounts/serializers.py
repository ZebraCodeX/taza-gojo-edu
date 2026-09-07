from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password

from .models import Profile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "role", "country", "language", "avatar"]
        read_only_fields = ["id"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    grade_level = serializers.IntegerField(required=False, min_value=1, max_value=99)
    interests = serializers.ListField(child=serializers.CharField(), required=False)
    goals = serializers.ListField(child=serializers.DictField(), required=False)
    weekly_minutes = serializers.IntegerField(required=False, min_value=0, max_value=60 * 24)

    class Meta:
        model = User
        fields = [
            "id", "username", "password", "email", "role", "country", "language",
            "grade_level", "interests", "goals", "weekly_minutes",
        ]

    def create(self, validated_data):
        profile_fields = {
            k: validated_data.pop(k)
            for k in ("grade_level", "interests", "goals", "weekly_minutes")
            if k in validated_data
        }
        validated_data["password"] = make_password(validated_data.pop("password"))
        user = super().create(validated_data)
        profile, _ = Profile.objects.get_or_create(user=user)
        for k, v in profile_fields.items():
            setattr(profile, k, v)
        profile.save()
        return user


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Profile
        fields = [
            "user", "grade_level", "points", "streak_days",
            "subjects", "bio", "rating", "timezone", "device_bandwidth",
            "interests", "goals", "weekly_minutes", "onboarded", "created_at",
        ]
        read_only_fields = ["points", "streak_days", "created_at", "user"]