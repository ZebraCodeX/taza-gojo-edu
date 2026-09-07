# 🎓 Taza-Gojo EDU

An AI-agent-run school for children on low-bandwidth (2G/3G) networks in
Africa. Works as a **web app (PWA)** and as **downloadable mobile apps**
(Google Play + App Store via Capacitor). Game-based courses (English, Math,
Science, Computer Programming) run fully offline, an AI tutor answers questions
between lessons, and students get **face-to-face video tutoring** with teachers
abroad — tuned so the call still works when the mast is congested.

```
React web + mobile app ──► Django (API + WebRTC signaling) ◄── C++ mediaserver (optional SFU)
                 ├─ accounts/auth (JWT)
                 ├─ courses   → JSON "game scripts" (play offline)
                 ├─ agents    → content/tutor/grader/curriculum (mock|openai|ollama)
                 ├─ tutoring  → sessions + WebSocket signaling for media
                 └─ offline   → idempotent sync queue for offline writes
```

## What works right now

- **Backend** — Django 5 + DRF + Channels. Courses, lessons, progress; JWT auth
  (student/teacher/content_creator/admin profiles); tutoring sessions and a
  WebSocket signaling relay for WebRTC; agent task queue with a `mock` AI provider
  (runs with zero keys); offline sync endpoint. `python manage.py test
  apps.tutoring` → 3/3 passing (offer/answer/ICE relay, no self-echo, mode
  broadcast).
- **Frontend (web + native)** — one Vite + React 18 codebase that serves both:
  - the **web app** is a PWA: works offline (service worker + IndexedDB
    queue), four tap-games, AI chat, tutor directory, a **Library** of free
    grade-6→college materials that download for offline reading, and a
    `/call/:sessionId` video page with low/medium/high presets that switch live
    (~70 KB gzipped total);
  - the **native app** is the same UI wrapped by Capacitor (`frontend/android/`,
    `frontend/ios/`) — publishable to Google Play and the App Store with the
    assets in `frontend/resources/`.
- **Library** — 66 curated free resources (OpenStax, Project Gutenberg, Khan
  Academy, MIT OCW, LibreTexts, freeCodeCamp…) plus agent-written study packs,
  filterable by subject + grade (6 → college). **Every material is fully
  downloadably offline** — link-only entries get a generated compact study
  guide (outline + practice plan) at seed time
  (`python manage.py seed_materials`).
- **Smart AI tutor** — grounded in the library: it retrieves the most relevant
  study notes for the question, knows the student's grade + country + recent
  conversation, answers in steps, and returns follow-up suggestions. The built-in
  mock provider actually solves arithmetic (sums, products, percentages) instead
  of faking it, so the demo never sounds robotic.
- **Learning roadmap** — every student profiles their goals, interests and
  weekly time on a short onboarding flow; goals show on the dashboard and drive
  the curriculum planner.
- **In-app admin panel** (`/admin` for teachers/admins) — overview stats,
  material management (create/activate/edit/delete) and user administration,
  on top of Django's `/admin` for deep control.
- **Mediaserver (C++17)** — libdatachannel-based WebRTC SFU with an
  RTCP-loss-driven bitrate controller (`src/bitrate.hpp`, unit-tested). Compiles
  from source with the bundled deps.

## 5-minute dev run

```bash
# terminal 1 — backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py seed_core && python manage.py seed_materials
python manage.py run_agents &            # optional: AI worker (mock AI)
daphne -b 127.0.0.1 -p 8000 config.asgi:application

# terminal 2 — frontend
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Seed users: `ada` (student, Kenya) and `mrkwame` (teacher, Ghana) — password
`test1234`. In production, seed a superuser for the school operator by setting
the `DEMO_ADMIN_USERNAME` / `DEMO_ADMIN_PASSWORD` env vars (Docker/fly secrets).

## Deploying

- **fly.io** — see `docs/DEPLOY.md` (single app: Django serves both the API and
  the built SPA on one origin, so the PWA + WebRTC + WebSockets all stay
  same-origin).
- **Docker** — `docker compose up --build` (postgres + redis + daphne + agents
  + frontend) for self-hosted / school-server installs.
- **Google Play / App Store** — see `docs/STORE-DEPLOY.md` (Capacitor project +
  generated app icons/splash + store listing assets).

Set `AI_PROVIDER=openai` + `AI_API_KEY`, or point `AI_API_URL` at a school-owned
Ollama. Add the mediaserver service when a classroom needs a Wi-Fi hub to
throttle video before it chokes the link (see `docs/architecture.md`).

## Docs

- `docs/architecture.md` — system design, data model, why-each-piece.
- `docs/offline-first.md` — offline cache/sync strategy + pre-seeding schools.
- `docs/ai-agents.md` — agent pipeline, providers, game-script format.
- `docs/DEPLOY.md` — fly.io deployment, step by step.
- `docs/STORE-DEPLOY.md` — shipping the Android/iOS app to the stores.

## License

MIT (see LICENSE). Not yet added — say the word and I'll add it.