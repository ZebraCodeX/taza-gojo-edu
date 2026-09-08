"""Link committed lecture videos to lessons in the database.

Lecture MP4s are rendered once (render_lectures) and committed to the repo so
every deploy ships them baked into the container. This command runs at deploy
startup and fills the lesson->video link for any lesson whose video already
exists on disk — including lessons created before the lecture pipeline existed
(their lecture fields still default to "pending").

Usage:  python manage.py seed_lecture_links
"""

import json

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.courses.models import Lesson
from apps.courses.management.commands.render_lectures import lesson_slug_of

LECTURE_MEDIA = settings.MEDIA_ROOT / "lectures"


class Command(BaseCommand):
    help = "Point lessons at committed lecture videos already present in MEDIA_ROOT."

    def handle(self, *args, **options):
        manifest_path = LECTURE_MEDIA / "manifest.json"
        manifest = {}
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        linked = skipped = 0
        lessons = Lesson.objects.select_related("module__course").order_by(
            "module__course__order", "order"
        )
        for lesson in lessons:
            if lesson.lecture_status == "ready" and lesson.lecture_file:
                skipped += 1
                continue
            name = f"{lesson.module.course.slug}-{lesson_slug_of(lesson.title)}.mp4"
            video = LECTURE_MEDIA / name
            if not video.exists():
                continue
            lesson.lecture_file.name = f"lectures/{name}"
            lesson.lecture_status = "ready"
            lesson.lecture_duration = manifest.get(
                name.removesuffix(".mp4"), {}
            ).get("duration", 0)
            lesson.save(update_fields=["lecture_file", "lecture_status", "lecture_duration"])
            linked += 1
            self.stdout.write(f"   → {lesson.module.course.slug}/{lesson.title}: {name}")

        self.stdout.write(self.style.SUCCESS(
            f"Done. Linked {linked} lecture(s); {skipped} already ready."
        ))