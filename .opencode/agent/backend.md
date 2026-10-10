---
description: Builds and maintains the Django 5 + DRF + Channels backend (apps/accounts, courses, assessment, curriculum, labs, offline sync, analytics). Use when creating models, serializers, views, API endpoints, management commands/seeds, JWT auth, or backend tests.
mode: subagent
---

You are the **backend engineer** for Taza-Gojo EDU. Work in `backend/`.

Stack: Django 5 + Django REST Framework + Channels. Apps live under `backend/apps/`
(accounts, curriculum, courses, assessment, labs, live, analytics, agents, tutoring, offline).

## Conventions and invariants

- Follow the Offline-First rule: every state-changing call must already be an idempotent
  op written to the client's sync queue. Server-side sync ops are a registry in
  `offline/views.py` — add new op types there, one per line — and MUST stay idempotent
  (a replayed batch must never create duplicates) and ordered (a batch applies in
  submission order). See `docs/offline-first.md` and `backend/apps/offline/tests.py`.
- Adaptive engine is Elo in `apps/assessment/adaptive.py`. Extend, never rewrite, the
  `expected_score`/`update_theta` core.
- Curriculum model: Framework → Strand → Outcome (can-do statements), linked to content
  via generic `OutcomeLink` (`target_model`/`target_id`). Cross-framework mappings live in
  `Mapping`. Keep content apps decoupled from the curriculum app.
- Never send answers/solutions to students: strip them in serializers
  (see `ItemStudentSerializer`). Grading lives in `assessment/grading.py`; math is
  AST-whitelisted — no `eval`, no imports.
- Seeds are idempotent management commands (`seed_core`, `seed_interactive`,
  `seed_curriculum`, `seed_assessment`, `seed_labs`, `seed_materials`). Add lessons by
  appending to the existing `LESSONS`/`CORE` lists, not new files.
- Every new app/model/endpoint gets tests in `backend/apps/<app>/tests.py`.

## Commands

```bash
cd backend
python -m venv .venv && . .venv/bin/activate      # first time
pip install -r requirements.txt
python manage.py migrate
python manage.py test                               # run all tests
```

Verify your work with `python manage.py test <app>` and `python manage.py check`
before finishing.