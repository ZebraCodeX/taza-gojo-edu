# Taza-Gojo EDU — Project Guide

An offline-first education platform for kids 6–14 in low-resource communities.
React 18 + Vite PWA (frontend/) + Django 5 + DRF + Channels (backend/), plus a
C++ mediaserver. One codebase for web, Android/iOS (Capacitor) and desktop (Tauri).

## Repo map

- `frontend/` — Vite + React 18. PWA shell (service worker), offline IndexedDB store
  (`src/services/offline.js`), game engines (`src/games/GameRenderer.jsx`), lessons,
  labs, library, i18n (`src/i18n/`).
- `backend/` — Django. Apps: `accounts` (JWT), `curriculum` (Framework/Strand/Outcome +
  Mapping), `courses` (lessons, seeds), `assessment` (item bank, Elo adaptive, grading),
  `labs`, `live` (LiveKit), `analytics`, `offline` (idempotent sync), `agents`, `tutoring`.
- `docs/` — architecture.md, offline-first.md, assessment.md, curriculum.md,
  interactive.md, labs.md, live.md, gateway.md, desktop.md.

## Everyday commands

```bash
# Frontend
cd frontend && npm install       # first time
npm run dev                      # http://localhost:5173
npm run build                    # production build (must pass)

# Backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_core && seed_interactive && seed_curriculum && seed_assessment && seed_labs && seed_materials
python manage.py test            # full suite
python manage.py check
```

## Hard rules (do not break)

1. **Offline-first.** The app must open and play with zero signal. Progress is written
   locally first, flushed in batches when online; server sync ops are idempotent and
   ordered (`docs/offline-first.md`).
2. **Low-end friendly.** Shell ≈ 66 KB gzipped. Targets 2G, Android 8+, 1–2 GB RAM,
   4–5" screens. No heavy deps, no autoplay background video, big touch targets.
3. **Child-safe.** No chat with strangers, no ads, minimal personal data, no
   leaderboards that shame. Encouraging, error-tolerant feedback only.
4. **Audio-first.** Instructions always have an audio channel + visual/icon fallback;
   pre-readers must play without reading.
5. **Additive content.** New game engines/lessons/languages ship as data, not app updates.
6. **Never expose answers** in student-facing serializers. No `eval` in graders.
7. **Place by ability, not age/grade.** Use the adaptive (Elo) model.

## Subagents

- `backend` — Django/DRF models, APIs, seeds, tests.
- `frontend` — React/PWA UI, offline store, i18n, Capacitor/Tauri shells.
- `games` — game engines + game lesson scripts + difficulty adaptation.
- `content` — curriculum outcomes, cross-framework mapping, localization packs.
- `qa` — runs the full test/build/guardrail suite before anything is "done".