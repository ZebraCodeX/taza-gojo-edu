from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path, re_path
from django.views.static import serve

from .spa import spa


def health(request):
    """Liveness probe for fly.io HTTP checks (no DB, no auth, always fast)."""
    return JsonResponse({"ok": True})


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/curriculum/", include("apps.curriculum.urls")),
    path("api/v1/courses/", include("apps.courses.urls")),
    path("api/v1/assessment/", include("apps.assessment.urls")),
    path("api/v1/labs/", include("apps.labs.urls")),
    path("api/v1/live/", include("apps.live.urls")),
    path("api/v1/gateway/", include("apps.gateway.urls")),
    path("api/v1/analytics/", include("apps.analytics.urls")),
    path("api/v1/agents/", include("apps.agents.urls")),
    path("api/v1/tutoring/", include("apps.tutoring.urls")),
    path("api/v1/offline/", include("apps.offline.urls")),
    path("api/v1/library/", include("apps.library.urls")),
    path("api/v1/admin/", include("apps.adminapi.urls")),
    # Lecture videos live in MEDIA_ROOT (baked into the image at deploy).
    re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}),
    # SPA catch-all — last, so the API/admin/ws take precedence.
    re_path(r"^(?!api/|ws/|admin/|static/|media/|favicon)(?P<path>.*)$", spa),
]