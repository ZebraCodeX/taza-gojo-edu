"""Render video lectures for lessons with the HyperFrames CLI (HTML -> MP4).

Pipeline: lesson -> composition HTML (apps.courses.lecture_video) -> rendered
MP4 in MEDIA_ROOT/lectures/. Rendered files are committed to the repo so every
deploy ships the videos baked into the container.

Usage:
    python manage.py render_lectures                    # all pending lessons
    python manage.py render_lectures --course math      # one course
    python manage.py render_lectures --only-listing     # fresh, not pending
    python manage.py render_lectures --dry-run          # show what would render
    python manage.py render_lectures --force            # re-render ready ones too

Requires Node.js >= 22 + the `hyperframes` npm package installed in the
`lectures/` project at the repo root, plus FFmpeg and a headless Chrome/Chromium.
"""

import shutil
import subprocess
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.courses.lecture_video import build_lecture_html, duration_for_probe
from apps.courses.models import Course, Lesson

REPO_ROOT = Path(settings.BASE_DIR).parent
LECTURES_DIR = REPO_ROOT / "lectures"
OUT_DIR = REPO_ROOT / "lectures" / "out"
LECTURE_MEDIA = settings.MEDIA_ROOT / "lectures"


def lesson_slug_of(title):
    """Stable file slug for a lesson title (independent of DB primary keys)."""
    import re
    from django.utils.text import slugify

    slug = slugify(title)
    return re.sub(r"[^a-z0-9-]", "", slug)[:60] or "lesson"


class Command(BaseCommand):
    help = "Render lesson video lectures to MP4 with HyperFrames (HTML -> video)."

    def add_arguments(self, parser):
        parser.add_argument("--course", help="Only lessons in this course slug")
        parser.add_argument("--lesson", type=int, help="Only this lesson id")
        parser.add_argument("--force", action="store_true", help="Re-render ready lessons too")
        parser.add_argument("--limit", type=int, help="Stop after N lessons")
        parser.add_argument("--dry-run", action="store_true",
                            help="Plan + build compositions but do not render")
        parser.add_argument("--keep-frames", action="store_true",
                            help="Keep extracted frames cache (default: cleaned after render)")

    def _prereqs(self):
        if not shutil.which("ffmpeg"):
            raise CommandError("ffmpeg is required to render lectures")
        if not (LECTURES_DIR / "node_modules" / "hyperframes").exists():
            raise CommandError(
                "HyperFrames is not installed. Run: cd lectures && npm install"
            )
        cli = shutil.which("npx") or shutil.which("hyperframes")
        if cli is None:
            raise CommandError("Node.js (npx) is required to render lectures")
        return cli

    def handle(self, *args, **opts):
        cli = self._prereqs()
        LECTURE_MEDIA.mkdir(parents=True, exist_ok=True)
        OUT_DIR.mkdir(parents=True, exist_ok=True)

        lessons = Lesson.objects.select_related("module__course").all()
        if opts.get("course"):
            lessons = lessons.filter(module__course__slug=opts["course"])
        if opts.get("lesson"):
            lessons = lessons.filter(pk=opts["lesson"])
        if not opts.get("force"):
            lessons = lessons.exclude(lecture_status="ready")

        lessons = lessons.order_by("module__course__order", "order")
        if opts.get("limit"):
            lessons = lessons[: opts["limit"]]

        for lesson in lessons:
            self.render_one(lesson, dry_run=opts["dry_run"], cli=cli, keep_frames=opts["keep_frames"])

        if opts["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry run complete — nothing rendered."))

    def render_one(self, lesson, dry_run, cli, keep_frames):
        course = lesson.module.course
        lesson_slug = lesson_slug_of(lesson.title)
        label = f"{course.slug}/{lesson.title}"
        self.stdout.write(f"\n▶ {label}")

        html_doc, duration = build_lecture_html(
            lesson, lesson.module.title, course
        )
        job = OUT_DIR / f"lesson-{lesson.pk}"
        job.mkdir(parents=True, exist_ok=True)
        comp = job / "composition.html"
        comp.write_text(html_doc, encoding="utf-8")
        self.stdout.write(f"   composition: {comp} ({duration:.0f}s planned)")

        if dry_run:
            return

        target = LECTURE_MEDIA / f"{course.slug}-{lesson_slug}.mp4"
        tmp = job / "render.mp4"
        tmp.unlink(missing_ok=True)

        lesson.lecture_status = "rendering"
        lesson.save(update_fields=["lecture_status"])

        cmd = [
            cli,
            "hyperframes",
            "render",
            "-c",
            str(comp.relative_to(LECTURES_DIR)),
            "-o",
            f"out/lesson-{lesson.pk}/render.mp4",
        ]
        self.stdout.write(f"   running: {' '.join(cmd)}  (this can take a minute…)")
        try:
            proc = subprocess.run(
                cmd, cwd=str(LECTURES_DIR), capture_output=True, text=True, timeout=1800
            )
        except Exception as exc:  # noqa: BLE001
            lesson.lecture_status = "error"
            lesson.save(update_fields=["lecture_status"])
            raise CommandError(f"render failed to start for {label}: {exc}")
        if proc.returncode != 0:
            lesson.lecture_status = "error"
            lesson.save(update_fields=["lecture_status"])
            self.stderr.write(proc.stdout[-4000:])
            self.stderr.write(proc.stderr[-4000:])
            raise CommandError(f"render failed for {label} (returncode {proc.returncode})")

        if not tmp.exists():
            lesson.lecture_status = "error"
            lesson.save(update_fields=["lecture_status"])
            raise CommandError(f"render produced no file for {label}")

        shutil.move(str(tmp), str(target))
        lesson.lecture_file.name = f"lectures/{target.name}"
        lesson.lecture_duration = duration_for_probe(target, int(duration))
        lesson.lecture_status = "ready"
        lesson.save(update_fields=["lecture_file", "lecture_duration", "lecture_status"])
        self.stdout.write(self.style.SUCCESS(f"   ✓ saved {target} ({lesson.lecture_duration}s)"))

        if not keep_frames:
            cache = Path("/tmp/hyperframes-extract-cache-1000")
            if cache.exists():
                shutil.rmtree(cache, ignore_errors=True)