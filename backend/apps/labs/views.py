from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Lab, LabSubmission
from .serializers import LabSerializer, LabSubmissionSerializer


class LabViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LabSerializer
    lookup_field = "slug"

    def get_queryset(self):
        qs = Lab.objects.filter(is_published=True)
        kind = self.request.query_params.get("kind")
        subject = self.request.query_params.get("subject")
        course = self.request.query_params.get("course")
        grade = self.request.query_params.get("grade")
        if kind:
            qs = qs.filter(kind=kind)
        if subject:
            qs = qs.filter(subject=subject)
        if course:
            qs = qs.filter(course__slug=course)
        if grade:
            qs = qs.filter(grade_min__lte=grade, grade_max__gte=grade)
        return qs

    @action(detail=True, methods=["post"])
    def submit(self, request, slug=None):
        """Record a lab attempt.

        Coding labs are graded in the browser (offline-first); the client sends
        its per-test results. The server keeps the authoritative definition and
        derives ``passed`` from the reported results so a client cannot simply
        assert success without test evidence.
        """
        lab = self.get_object()
        results = request.data.get("results") or []
        if not isinstance(results, list):
            return Response({"detail": "results must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        total = len(lab.tests) or len(results) or 1
        passed_tests = sum(1 for r in results if isinstance(r, dict) and r.get("passed"))
        score = round(100.0 * passed_tests / total, 1)
        passed = passed_tests == total and total > 0

        submission = LabSubmission.objects.create(
            user=request.user,
            lab=lab,
            code=(request.data.get("code") or "")[:20000],
            language=request.data.get("language") or lab.language,
            passed=passed,
            score=score,
            results=results[:200],
        )
        data = LabSubmissionSerializer(submission).data
        data["passed_tests"] = passed_tests
        data["total_tests"] = total
        return Response(data, status=status.HTTP_201_CREATED)


class LabSubmissionViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = LabSubmissionSerializer

    def get_queryset(self):
        return LabSubmission.objects.filter(user=self.request.user).select_related("lab")
