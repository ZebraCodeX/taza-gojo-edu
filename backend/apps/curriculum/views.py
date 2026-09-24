from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Framework, Strand, Outcome, Mapping
from .serializers import (
    FrameworkSerializer,
    StrandSerializer,
    OutcomeSerializer,
    MappingSerializer,
)


class FrameworkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Framework.objects.filter(is_active=True).prefetch_related("strands__outcomes")
    serializer_class = FrameworkSerializer
    lookup_field = "slug"
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    @action(detail=True, methods=["get"])
    def outcomes(self, request, slug=None):
        """Flat outcome list for a framework, filterable by subject/grade."""
        qs = Outcome.objects.filter(strand__framework=self.get_object())
        subject = request.query_params.get("subject")
        grade = request.query_params.get("grade")
        if subject:
            qs = qs.filter(strand__subject=subject)
        if grade:
            qs = qs.filter(grade_min__lte=grade, grade_max__gte=grade)
        return Response(OutcomeSerializer(qs.select_related("strand"), many=True).data)


class StrandViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = StrandSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Strand.objects.prefetch_related("outcomes")
        subject = self.request.query_params.get("subject")
        framework = self.request.query_params.get("framework")
        if subject:
            qs = qs.filter(subject=subject)
        if framework:
            qs = qs.filter(framework__slug=framework)
        return qs


class OutcomeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OutcomeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Outcome.objects.select_related("strand")
        subject = self.request.query_params.get("subject")
        grade = self.request.query_params.get("grade")
        if subject:
            qs = qs.filter(strand__subject=subject)
        if grade:
            qs = qs.filter(grade_min__lte=grade, grade_max__gte=grade)
        return qs


class MappingViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = MappingSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Mapping.objects.select_related("from_outcome", "to_outcome")
        code = self.request.query_params.get("outcome")
        if code:
            qs = qs.filter(from_outcome__code=code) | qs.filter(to_outcome__code=code)
        return qs
