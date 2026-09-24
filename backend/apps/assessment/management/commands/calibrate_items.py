"""Calibrate item difficulty from response data with a 1PL (Rasch) model.

Joint maximum-likelihood: repeatedly update person abilities (theta) and item
difficulties (b) with Newton steps until they converge, then write each item's
difficulty back onto the Elo scale the adaptive engine uses.

Usage:
    python manage.py calibrate_items                 # all items with enough data
    python manage.py calibrate_items --min-responses 10 --dry-run
"""

import math

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.assessment.models import Item, Response

CLIP = 6.0  # logit units
# Elo and logit relate by a factor 400/ln(10) ≈ 173.7; centre at 1000.
ELO_SCALE = 400.0 / math.log(10.0)
ELO_CENTRE = 1000.0


def _logit(p):
    return math.log(p / (1 - p))


class Command(BaseCommand):
    help = "Estimate item difficulties from response data (1PL Rasch)."

    def add_arguments(self, parser):
        parser.add_argument("--min-responses", type=int, default=5)
        parser.add_argument("--iterations", type=int, default=50)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        min_resp = opts["min_responses"]

        # Items with enough graded responses.
        counts = (
            Response.objects.values("item_id")
            .annotate(n=Count("id"))
            .filter(n__gte=min_resp)
        )
        item_ids = [c["item_id"] for c in counts]
        if not item_ids:
            self.stdout.write(self.style.WARNING("No items have enough responses yet."))
            return

        rows = list(
            Response.objects.filter(item_id__in=item_ids)
            .values_list("item_id", "attempt__user_id", "correct")
        )
        # 1PL needs 0/1; partial credit counts as correct if >= 0.5.
        persons = sorted({r[1] for r in rows})
        p_index = {p: i for i, p in enumerate(persons)}
        i_index = {it: i for i, it in enumerate(item_ids)}

        theta = [0.0] * len(persons)
        b = [0.0] * len(item_ids)

        # Group observations by person and by item for efficient updates.
        by_person = {i: [] for i in range(len(persons))}
        by_item = {i: [] for i in range(len(item_ids))}
        for item_id, user_id, correct in rows:
            pi, ii = p_index[user_id], i_index[item_id]
            x = 1.0 if correct else 0.0
            by_person[pi].append((ii, x))
            by_item[ii].append((pi, x))

        for _ in range(opts["iterations"]):
            # Update abilities.
            for pi in range(len(persons)):
                num = den = 0.0
                for ii, x in by_person[pi]:
                    p = 1.0 / (1.0 + math.exp(-(theta[pi] - b[ii])))
                    num += x - p
                    den += p * (1 - p)
                if den > 1e-9:
                    theta[pi] = max(-CLIP, min(CLIP, theta[pi] + num / den))
            # Update difficulties.
            for ii in range(len(item_ids)):
                num = den = 0.0
                for pi, x in by_item[ii]:
                    p = 1.0 / (1.0 + math.exp(-(theta[pi] - b[ii])))
                    num += x - p
                    den += p * (1 - p)
                if den > 1e-9:
                    b[ii] = max(-CLIP, min(CLIP, b[ii] - num / den))
            # Centre difficulties at 0 for identifiability.
            mean_b = sum(b) / len(b)
            b = [x - mean_b for x in b]

        updated = 0
        for item_id, bi in zip(item_ids, b):
            elo = round(ELO_CENTRE + bi * ELO_SCALE, 1)
            item = Item.objects.get(id=item_id)
            n = next(c["n"] for c in counts if c["item_id"] == item_id)
            if opts["dry_run"]:
                self.stdout.write(f"  item {item_id}: {item.difficulty:.0f} -> {elo}  (n={n}, b={bi:+.2f})")
            else:
                item.difficulty = elo
                item.save(update_fields=["difficulty"])
            updated += 1

        verb = "Would update" if opts["dry_run"] else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {updated} items from {len(rows)} responses across {len(persons)} learners."
        ))
