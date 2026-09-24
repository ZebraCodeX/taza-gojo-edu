import hashlib
import secrets

from django.conf import settings
from django.db.models import Count
from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response as DRFResponse

from .models import Item, Assessment, AssessmentItem, Attempt, Response, Certificate
from .serializers import (
    ItemStudentSerializer,
    ItemStaffSerializer,
    AssessmentSerializer,
    ResponseSerializer,
    StaffResponseSerializer,
    AttemptSerializer,
    CertificateSerializer,
)
from . import grading, adaptive


def _is_staff(user):
    return bool(user and (user.is_staff or getattr(user, "role", "") in ("teacher", "content_creator", "admin")))


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = Item.objects.filter(is_active=True)
        subject = self.request.query_params.get("subject")
        kind = self.request.query_params.get("kind")
        grade = self.request.query_params.get("grade")
        if subject:
            qs = qs.filter(subject=subject)
        if kind:
            qs = qs.filter(kind=kind)
        if grade:
            qs = qs.filter(grade_min__lte=grade, grade_max__gte=grade)
        return qs

    def get_serializer_class(self):
        return ItemStaffSerializer if _is_staff(self.request.user) else ItemStudentSerializer


class AssessmentViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssessmentSerializer
    lookup_field = "slug"

    def get_queryset(self):
        qs = Assessment.objects.filter(is_published=True).annotate(item_count=Count("items"))
        subject = self.request.query_params.get("subject")
        course = self.request.query_params.get("course")
        grade = self.request.query_params.get("grade")
        if subject:
            qs = qs.filter(subject=subject)
        if course:
            qs = qs.filter(course__slug=course)
        if grade:
            qs = qs.filter(grade_min__lte=grade, grade_max__gte=grade)
        return qs

    @action(detail=True, methods=["post"])
    def start(self, request, slug=None):
        assessment = self.get_object()
        attempt = Attempt.objects.create(
            user=request.user,
            assessment=assessment,
            max_score=0.0,
            theta=1000.0,
        )
        return DRFResponse(_serve(attempt), status=status.HTTP_201_CREATED)


class AttemptViewSet(viewsets.GenericViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AttemptSerializer

    def get_queryset(self):
        # Teachers/content creators see every learner's attempt (grading queue,
        # class overview); students only their own.
        qs = Attempt.objects.select_related("assessment", "user")
        if not _is_staff(self.request.user):
            qs = qs.filter(user=self.request.user)
        assessment = self.request.query_params.get("assessment")
        status = self.request.query_params.get("status")
        if assessment:
            qs = qs.filter(assessment__slug=assessment)
        if status:
            qs = qs.filter(status=status)
        return qs

    @action(detail=False, methods=["get"])
    def pending(self, request):
        """Responses awaiting manual grading (teachers only)."""
        if not _is_staff(request.user):
            return DRFResponse({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        qs = (
            Response.objects.filter(needs_manual=True)
            .select_related("item", "attempt__user", "attempt__assessment")
            .order_by("created_at")
        )
        return DRFResponse(StaffResponseSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """Class-level stats for a teacher's dashboard."""
        if not _is_staff(request.user):
            return DRFResponse({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        attempts = Attempt.objects.all()
        graded = attempts.exclude(status="in_progress")
        return DRFResponse({
            "attempts": attempts.count(),
            "in_progress": attempts.filter(status="in_progress").count(),
            "graded": graded.count(),
            "pending_grading": Response.objects.filter(needs_manual=True).count(),
            "pass_rate": _pass_rate(graded),
            "certificates": Certificate.objects.filter(revoked=False).count(),
            "by_subject": list(
                attempts.values("assessment__subject")
                .annotate(n=Count("id"))
                .order_by("-n")
            ),
        })

    @action(detail=True, methods=["post"], url_path=r"responses/(?P<response_id>[0-9]+)/grade")
    def grade_response(self, request, pk=None, response_id=None):
        """Teacher grades a manual (essay) response, then the attempt is finalised."""
        if not _is_staff(request.user):
            return DRFResponse({"detail": "Not permitted."}, status=status.HTTP_403_FORBIDDEN)
        attempt = self.get_object()
        resp = Response.objects.filter(id=response_id, attempt=attempt).first()
        if not resp:
            return DRFResponse({"detail": "Response not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            awarded = float(request.data.get("awarded", 0))
        except (TypeError, ValueError):
            awarded = 0.0
        awarded = max(0.0, min(awarded, resp.max_points))
        resp.awarded = awarded
        resp.correct = awarded >= resp.max_points * 0.6
        resp.needs_manual = False
        resp.feedback = str(request.data.get("feedback", ""))[:2000]
        resp.save(update_fields=["awarded", "correct", "needs_manual", "feedback"])

        cert = _recompute_attempt(attempt)
        data = AttemptSerializer(attempt).data
        data["certificate"] = CertificateSerializer(cert).data if cert else None
        return DRFResponse(data)

    def retrieve(self, request, pk=None):
        attempt = self.get_object()
        data = AttemptSerializer(attempt).data
        data["responses"] = ResponseSerializer(attempt.responses.select_related("item"), many=True).data
        return DRFResponse(data)

    @action(detail=True, methods=["post"])
    def answer(self, request, pk=None):
        attempt = self.get_object()
        if attempt.status != "in_progress":
            return DRFResponse({"detail": "This attempt is already closed."}, status=400)

        item_id = request.data.get("item")
        item = Item.objects.filter(id=item_id, is_active=True).first()
        if not item:
            return DRFResponse({"detail": "Unknown item."}, status=400)

        link = AssessmentItem.objects.filter(assessment=attempt.assessment, item=item).first()
        points = link.points if link else 1.0
        result = grading.grade_item(item, request.data.get("answer") or {})

        resp, _ = Response.objects.update_or_create(
            attempt=attempt, item=item,
            defaults={
                "answer": request.data.get("answer") or {},
                "correct": result["correct"],
                "awarded": round(points * result["awarded"], 3),
                "max_points": points,
                "needs_manual": result["needs_manual"],
                "feedback": result["feedback"],
                "time_ms": int(request.data.get("time_ms") or 0),
            },
        )
        attempt.theta = adaptive.update_theta(attempt.theta, item.difficulty, result["awarded"])
        if item.id not in attempt.served:
            attempt.served.append(item.id)
        attempt.score = sum(r.awarded for r in attempt.responses.all())
        attempt.max_score = sum(r.max_points for r in attempt.responses.all())
        attempt.save(update_fields=["theta", "served", "score", "max_score"])

        payload = {
            "result": {
                "correct": result["correct"],
                "awarded": resp.awarded,
                "max_points": resp.max_points,
                "needs_manual": result["needs_manual"],
                "feedback": result["feedback"],
                "explanation": item.explanation,
            },
            "score": attempt.score,
            "max_score": attempt.max_score,
        }
        payload.update(_serve(attempt))
        return DRFResponse(payload)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        attempt = self.get_object()
        if attempt.status == "in_progress":
            attempt.status = "submitted"
            attempt.submitted_at = timezone.now()
            if attempt.started_at:
                attempt.duration_seconds = int((attempt.submitted_at - attempt.started_at).total_seconds())
            manual = attempt.responses.filter(needs_manual=True).exists()
            attempt.status = "submitted" if manual else "graded"
            attempt.save(update_fields=["status", "submitted_at", "duration_seconds"])

        cert = None
        if attempt.passed and attempt.status == "graded":
            cert = _issue_certificate(attempt)

        data = AttemptSerializer(attempt).data
        data["certificate"] = CertificateSerializer(cert).data if cert else None
        return DRFResponse(data)


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "code"

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)

    @action(detail=False, methods=["get"], permission_classes=[permissions.AllowAny], url_path=r"verify/(?P<code>[A-Za-z0-9\-]+)")
    def verify(self, request, code=None):
        """Public verification: proves a certificate code is genuine."""
        cert = Certificate.objects.filter(code=code, revoked=False).first()
        if not cert:
            return DRFResponse({"valid": False}, status=404)
        expected = _hash_code(cert.code, cert.score)
        return DRFResponse({
            "valid": cert.verify_hash == expected,
            "title": cert.title,
            "subject": cert.subject,
            "score": cert.score,
            "issued_at": cert.issued_at,
        })


def _serve(attempt):
    """Return the next item payload for an attempt (answered items are skipped)."""
    total = attempt.assessment.max_items or attempt.assessment.items.count()
    base = {"attempt": attempt.id, "attempt_id": attempt.id}
    if len(attempt.served) >= total:
        return {**base, "item": None, "index": len(attempt.served), "total": total, "done": True}
    next_ai = adaptive.select_next(attempt.assessment, attempt.theta, set(attempt.served))
    if not next_ai:
        return {**base, "item": None, "index": len(attempt.served), "total": total, "done": True}
    item = next_ai.item
    return {
        **base,
        "item": ItemStudentSerializer(item).data,
        "points": next_ai.points,
        "index": len(attempt.served),
        "total": total,
        "done": False,
    }


def _pass_rate(qs):
    total = qs.count()
    if not total:
        return 0.0
    passed = 0
    for attempt in qs.prefetch_related("responses"):
        if attempt.passed:
            passed += 1
    return round(100.0 * passed / total, 1)


def _recompute_attempt(attempt):
    """Recompute score/max/status after manual grading; issue a certificate on pass."""
    attempt.score = sum(r.awarded for r in attempt.responses.all())
    attempt.max_score = sum(r.max_points for r in attempt.responses.all())
    still_manual = attempt.responses.filter(needs_manual=True).exists()
    if attempt.status != "in_progress":
        attempt.status = "submitted" if still_manual else "graded"
    attempt.save(update_fields=["score", "max_score", "status"])
    if attempt.status == "graded" and attempt.passed:
        return _issue_certificate(attempt)
    return None


def _hash_code(code, score):
    secret = getattr(settings, "SECRET_KEY", "dev")
    return hashlib.sha256(f"{code}:{score}:{secret}".encode()).hexdigest()


def _issue_certificate(attempt):
    existing = Certificate.objects.filter(user=attempt.user, assessment=attempt.assessment).first()
    if existing:
        return existing
    code = "TG-" + secrets.token_hex(5).upper()
    return Certificate.objects.create(
        user=attempt.user,
        assessment=attempt.assessment,
        title=attempt.assessment.title,
        subject=attempt.assessment.subject,
        score=attempt.percent,
        code=code,
        verify_hash=_hash_code(code, attempt.percent),
    )
