"""Seed the library with the curated catalog of free materials + study packs.

Idempotent: re-running updates rows, regenerates downloadable study-guide bodies
and re-enables entries. Usage: python manage.py seed_materials
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.library.models import Material
from apps.library.study import build_study_html, outline_for

CATALOG = Path(__file__).resolve().parent.parent.parent / "catalog.json"


class Command(BaseCommand):
    help = "Load the curated free-materials catalog into the library."

    def handle(self, *args, **options):
        with open(CATALOG) as f:
            entries = json.load(f)

        count = 0
        for e in entries:
            outline = e.get("outline", [])
            defaults = {
                "subject": e["subject"],
                "title": e["title"],
                "description": e.get("description", ""),
                "kind": e.get("kind", "book"),
                "provider": e.get("provider", ""),
                "license_note": e.get("license_note", ""),
                "grade_start": e.get("grade_start", 6),
                "grade_end": e.get("grade_end", 99),
                "url": e.get("url", ""),
                "outline": outline,
                "pages": e.get("pages"),
                "order": e.get("order", 0),
                "active": True,
            }
            Material.objects.update_or_create(slug=e["slug"], defaults=defaults)

            # Every material gets a downloadable offline body: real study packs
            # keep their authored content; everything else becomes a compact
            # study guide (see apps/library/study.py).
            mat = Material.objects.get(slug=e["slug"])
            if e.get("content"):
                fields = []
                if mat.content != e["content"]:
                    mat.content = e["content"]
                    fields.append("content")
                if not mat.outline:
                    mat.outline = outline_for(mat)
                    fields.append("outline")
                if fields:
                    mat.save(update_fields=fields)
            elif not mat.content:
                mat.content = build_study_html(mat)
                mat.outline = outline_for(mat)
                mat.save(update_fields=["content", "outline"])
            elif not mat.outline:
                mat.outline = outline_for(mat)
                mat.save(update_fields=["outline"])
            count += 1

        # Anything that dropped out of the catalog goes quiet (keeps old rows,
        # never deletes download history).
        still = [e["slug"] for e in entries]
        Material.objects.exclude(slug__in=still).update(active=False)

        self.stdout.write(self.style.SUCCESS(f"Library seeded with {count} materials."))