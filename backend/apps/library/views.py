"""Library API: browse, filter, search, download tracking.

`GET /api/v1/library/materials/`  -> list (compact; cached by the service worker)
`GET /api/v1/library/materials/<id>/` -> detail incl. `content` for offline reads
`POST /api/v1/library/materials/<id>/download/` -> mark cached on a device
"""

from django.db.models import F, Q
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import Download, Material
from .serializers import MaterialBriefSerializer, MaterialDetailSerializer


def filter_query(request):
    qs = Material.objects.filter(active=True)
    q = request.query_params.get("q", "").strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(provider__icontains=q))
    subject = request.query_params.get("subject")
    if subject:
        qs = qs.filter(subject=subject)
    # Grade filter: return materials whose band covers the year.
    grade = request.query_params.get("grade")
    if grade:
        try:
            g = int(grade)
            qs = qs.filter(grade_start__lte=g, grade_end__gte=g)
        except (TypeError, ValueError):
            pass
    kind = request.query_params.get("kind")
    if kind:
        qs = qs.filter(kind=kind)
    downloadable = request.query_params.get("downloadable")
    if downloadable in ("1", "true", "True"):
        qs = qs.filter(content__gt="")
    return qs


class MaterialListView(ListAPIView):
    """Browse the library. Compact payload; the SW caches successful GETs."""

    permission_classes = [IsAuthenticated]
    serializer_class = MaterialBriefSerializer
    pagination_class = None  # catalog is small; send it all so offline caching is complete

    def get_queryset(self):
        return filter_query(self.request)


class MaterialDetailView(RetrieveAPIView):
    """Full material incl. `content` — the body you download for offline reading."""

    permission_classes = [IsAuthenticated]
    queryset = Material.objects.filter(active=True)
    serializer_class = MaterialDetailSerializer
    lookup_field = "id"


class MaterialDownloadView(APIView):
    """Record that this device saved the material. Idempotent per user+material."""

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        material = Material.objects.filter(id=id).first()
        if not material:
            return Response({"error": "material not found"}, status=404)
        _, created = Download.objects.get_or_create(
            user=request.user,
            material=material,
            defaults={"device_id": request.data.get("device_id", "")[:64]},
        )
        if created:
            Material.objects.filter(id=material.id).update(downloads=F("downloads") + 1)
        return Response({"ok": True, "downloads": material.downloads})