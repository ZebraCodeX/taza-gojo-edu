"""Serve the built React SPA from the same origin as the API.

Django handles /api/, /ws/ and /admin/; everything else falls through to the
frontend (index.html or a real hashed asset under FRONTEND_DIST). This keeps
the PWA, service worker, WebSockets and WebRTC signaling on a single host.
"""

from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.static import serve
from django.views.decorators.http import require_GET

DIST = Path(settings.FRONTEND_DIST)


@require_GET
def spa(request, path=""):
    # Resolve strictly inside dist so `../../` cannot escape.
    if path:
        candidate = (DIST / path).resolve()
        if candidate.is_relative_to(DIST.resolve()) and candidate.is_file():
            return serve(request, str(candidate.relative_to(DIST)), document_root=DIST)

    index = DIST / "index.html"
    if not index.is_file():
        return HttpResponseNotFound(
            "Frontend not built. From the repo root run: cd frontend && npm run build"
        )
    html = index.read_bytes()
    return HttpResponse(html, content_type="text/html; charset=utf-8")