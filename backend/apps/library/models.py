"""apps.library — downloadable learning materials (grade 6 → college).

Every subject has two kinds of material:
  * `content`-based "study packs" written by an agent teacher (fully
    downloadable, read fully offline);
  * `url`-based links to free online sources (OpenStax, Project Gutenberg,
    Khan Academy, MIT OpenCourseWare, LibreTexts, ...).

Clients download materials into IndexedDB while online, then read them on 2G
or with no signal. The API list endpoint is cached by the service worker, so
browsing the library costs zero bytes once you've opened it.
"""

from django.db import models


class Material(models.Model):
    SUBJECTS = [
        ("math", "Mathematics"),
        ("english", "English"),
        ("science", "Science"),
        ("computing", "Computer Programming"),
        ("general", "General"),
    ]
    KINDS = [
        ("book", "Book / textbook"),
        ("article", "Article / notes"),
        ("worksheet", "Worksheet / practice"),
        ("course", "Full course"),
        ("video", "Video series"),
        ("study_pack", "Agent-written study pack"),
    ]

    slug = models.SlugField(unique=True)
    subject = models.CharField(max_length=12, choices=SUBJECTS)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=12, choices=KINDS, default="book")
    provider = models.CharField(max_length=80, blank=True)  # OpenStax, Gutenberg, "Agent teacher", ...
    license_note = models.CharField(max_length=60, blank=True)  # "CC BY 4.0", "Public domain", ...

    # Grade band this material suits. 6..12 for school, then 13..99 = college+.
    grade_start = models.PositiveSmallIntegerField(default=6)
    grade_end = models.PositiveSmallIntegerField(default=99)

    url = models.URLField(blank=True)          # external source (opens in a new tab)
    content = models.TextField(blank=True)     # offline-readable body (HTML) when present
    outline = models.JSONField(default=list, blank=True)  # ["1. key topic", ...] for the guide
    pages = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    downloads = models.PositiveIntegerField(default=0)  # best-effort popularity stat
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["subject", "order", "grade_start", "title"]

    def __str__(self):
        return f"[{self.subject}] {self.title}"

    @property
    def downloadable(self):
        return bool(self.content)


class Download(models.Model):
    """One client's decision to cache a material (idempotent per client)."""

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    material = models.ForeignKey(Material, on_delete=models.CASCADE, related_name="downloads_set")
    device_id = models.CharField(max_length=64, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "material"], name="uniq_user_material_download")
        ]