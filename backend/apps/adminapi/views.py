"""apps.adminapi — the in-app school admin panel for teachers/admins.

Not a full CMS: focused on what a school operator actually does daily —
watch counts, manage materials (create/edit/activate/deactivate), and manage
student/teacher accounts. Django's /admin stays the deep-admin fallback.
"""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Course, LessonProgress
from apps.library.models import Download, Material

User = get_user_model()

MANAGE_FIELDS = [
    "slug", "subject", "title", "description", "kind", "provider",
    "license_note", "grade_start", "grade_end", "url", "content",
    "outline", "pages", "active", "order",
]


class IsSchoolAdmin(permissions.BasePermission):
    """Teachers and admins manage the school; students stay read-only."""

    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated
            and (request.user.is_staff or request.user.role in ("teacher", "admin"))
        )


class StatsView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSchoolAdmin]

    def get(self, request):
        users = User.objects.all()
        materials = Material.objects.all()
        return Response({
            "users": users.count(),
            "students": users.filter(role="student").count(),
            "teachers": users.filter(role="teacher").count(),
            "admins": users.filter(role="admin").count(),
            "materials": materials.count(),
            "materials_live": materials.filter(active=True).count(),
            "downloads": Download.objects.count(),
            "download_touches": materials.aggregate(t=Count("downloads_set"))["t"] or 0,
            "courses": Course.objects.count(),
            "lessons_done": LessonProgress.objects.filter(completed=True).count(),
        })


class MaterialListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSchoolAdmin]

    def get(self, request):
        qs = Material.objects.all()
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(provider__icontains=q) | Q(description__icontains=q))
        subject = request.query_params.get("subject")
        if subject:
            qs = qs.filter(subject=subject)
        if request.query_params.get("active") in ("1", "0"):
            qs = qs.filter(active=request.query_params["active"] == "1")
        qs = qs.order_by("subject", "order", "title")
        page = int(request.query_params.get("page", 1))
        size = min(int(request.query_params.get("size", 50)), 200)
        total = qs.count()
        rows = []
        for m in list(qs[(page - 1) * size: page * size]):
            rows.append({
                "id": m.id, "slug": m.slug, "subject": m.subject, "title": m.title,
                "kind": m.kind, "provider": m.provider,
                "grade_start": m.grade_start, "grade_end": m.grade_end,
                "downloadable": m.downloadable, "active": m.active,
                "downloads": m.downloads, "url": m.url,
                "license_note": m.license_note,
            })
        return Response({"total": total, "page": page, "size": size, "results": rows})

    def post(self, request):
        data = {k: request.data.get(k) for k in MANAGE_FIELDS if k in request.data}
        if not data.get("title") or not data.get("subject"):
            return Response({"error": "title and subject are required"}, status=status.HTTP_400_BAD_REQUEST)
        data.setdefault("slug", slugify_title(data["title"]))
        data.setdefault("grade_start", 6)
        data.setdefault("grade_end", 99)
        data.setdefault("active", True)
        if Material.objects.filter(slug=data["slug"]).exists():
            data["slug"] = f"{data['slug']}-{Material.objects.count() + 1}"
        mat = Material.objects.create(**data)
        if not mat.content and not mat.url:
            mat.content = build_guide(mat)
            mat.save(update_fields=["content"])
        return Response({"id": mat.id, "ok": True}, status=status.HTTP_201_CREATED)


class MaterialDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSchoolAdmin]

    def patch(self, request, pk):
        mat = Material.objects.filter(pk=pk).first()
        if not mat:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        data = {k: v for k, v in request.data.items() if k in MANAGE_FIELDS}
        if "content" in request.data and request.data["content"]:
            data["content"] = request.data["content"]
        for k, v in data.items():
            setattr(mat, k, v)
        mat.save()
        return Response({"id": mat.id, "ok": True, "active": mat.active})

    def delete(self, request, pk):
        Material.objects.filter(pk=pk).delete()
        return Response({"ok": True})


class UserListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsSchoolAdmin]

    def get(self, request):
        qs = User.objects.all()
        q = request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(country__icontains=q))
        role = request.query_params.get("role")
        if role:
            qs = qs.filter(role=role)
        rows = []
        for u in qs.order_by("-date_joined")[:300]:
            rows.append({
                "id": u.id,
                "username": u.username,
                "role": u.role,
                "country": u.country,
                "is_active": u.is_active,
                "points": getattr(getattr(u, "profile", None), "points", 0),
                "lessons_done": u.progress.filter(completed=True).count() if hasattr(u, "progress") else 0,
                "agent_tasks": u.agent_tasks.count(),
                "joined": u.date_joined.isoformat() if u.date_joined else None,
            })
        return Response(rows)


class UserDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSchoolAdmin]

    def patch(self, request, pk):
        u = User.objects.filter(pk=pk).first()
        if not u:
            return Response({"error": "not found"}, status=status.HTTP_404_NOT_FOUND)
        if "is_active" in request.data:
            u.is_active = bool(request.data["is_active"])
        if "role" in request.data and request.data["role"] in ("student", "teacher", "admin", "content_creator"):
            u.role = request.data["role"]
        u.save(update_fields=["is_active", "role"] if "role" in request.data else ["is_active"])
        return Response({"ok": True, "id": u.id, "is_active": u.is_active, "role": u.role})


def slugify_title(title):
    import re
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return s or "material"


def build_guide(mat):
    from apps.library.study import build_study_html
    return build_study_html(mat)