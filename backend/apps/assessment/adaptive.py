"""Adaptive item selection using a simple Elo ability model.

The learner's ability ``theta`` starts at 1000 and is updated after each graded
response. The next item is the unanswered bank item whose difficulty is closest
to the current ability, which keeps challenge near ~50-70% success — the sweet
spot for learning. This is deliberately dependency-free; it can be upgraded to
2PL IRT once the bank has enough response volume for calibration.
"""

K_FACTOR = 24.0


def expected_score(theta, difficulty):
    return 1.0 / (1.0 + 10 ** ((difficulty - theta) / 400.0))


def update_theta(theta, difficulty, score):
    """``score`` in 0..1 (fraction of points awarded)."""
    return theta + K_FACTOR * (score - expected_score(theta, difficulty))


def candidate_items(assessment, exclude_ids=None):
    from .models import AssessmentItem

    qs = AssessmentItem.objects.filter(assessment=assessment).select_related("item")
    qs = qs.filter(item__is_active=True)
    if exclude_ids:
        qs = qs.exclude(item_id__in=list(exclude_ids))
    return qs


def select_next(assessment, theta, answered_ids):
    """Return the AssessmentItem to serve next, or None if exhausted."""
    if assessment.adaptive:
        qs = candidate_items(assessment, answered_ids)
        best = None
        best_gap = None
        for ai in qs:
            gap = abs(ai.item.difficulty - theta)
            if best_gap is None or gap < best_gap:
                best, best_gap = ai, gap
        return best
    # Fixed form: serve in authored order, skipping answered.
    qs = candidate_items(assessment, answered_ids).order_by("order", "id")
    return qs.first()
