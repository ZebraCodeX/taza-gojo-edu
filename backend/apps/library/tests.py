from django.test import TestCase
from rest_framework.test import APIClient

from .models import Download, Material

import json
from pathlib import Path


class MaterialApiTests(TestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model

        self.user = get_user_model().objects.create_user(
            username="stu", password="test1234", role=get_user_model().Role.STUDENT
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        Material.objects.create(
            slug="mk-frac",
            subject="math",
            title="Fractions",
            grade_start=6,
            grade_end=7,
            content="<h2>Fractions</h2>",
        )
        Material.objects.create(
            slug="mk-calc",
            subject="math",
            title="Calculus I",
            grade_start=13,
            grade_end=99,
            url="https://openstax.org/details/books/calculus-volume-1",
        )
        Material.objects.create(
            slug="mk-novel",
            subject="english",
            title="Novel reading",
            grade_start=9,
            grade_end=12,
        )

    def test_list_all_and_filters(self):
        r = self.client.get("/api/v1/library/materials/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 3)

        r = self.client.get("/api/v1/library/materials/?subject=math")
        self.assertEqual(len(r.data), 2)

        r = self.client.get("/api/v1/library/materials/?grade=7")
        self.assertEqual([m["slug"] for m in r.data], ["mk-frac"])

        r = self.client.get("/api/v1/library/materials/?grade=13")
        self.assertEqual([m["slug"] for m in r.data], ["mk-calc"])

        r = self.client.get("/api/v1/library/materials/?q=calculus")
        self.assertEqual([m["slug"] for m in r.data], ["mk-calc"])

        r = self.client.get("/api/v1/library/materials/?downloadable=1")
        self.assertEqual([m["slug"] for m in r.data], ["mk-frac"])

    def test_detail_has_content_when_present(self):
        r = self.client.get("/api/v1/library/materials/1/")
        self.assertEqual(r.status_code, 200)
        self.assertNotEqual(r.data.get("content"), "")
        self.assertTrue(r.data["downloadable"])

    def test_download_idempotent(self):
        r = self.client.post("/api/v1/library/materials/1/download/", {"device_id": "d1"}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/api/v1/library/materials/1/download/", {"device_id": "d1"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Download.objects.filter(user=self.user, material_id=1).count(), 1)

    def test_anon_blocked(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/v1/library/materials/").status_code, 401)


class CatalogIntegrityTests(TestCase):
    """The shipped catalog must reference the exact model fields."""

    def test_catalog_schema(self):
        cat = Path(__file__).resolve().parent / "catalog.json"
        entries = json.loads(cat.read_text())
        self.assertGreater(len(entries), 40)
        for e in entries:
            self.assertIn(e["subject"], [s[0] for s in Material.SUBJECTS])
            self.assertIn(e["kind"], [k[0] for k in Material.KINDS])
            self.assertTrue(e["slug"])
            self.assertTrue(e["title"])
            self.assertTrue(6 <= e.get("grade_start", 6))
            self.assertTrue(e.get("url") or e.get("content"), f"{e['slug']} needs url or content")