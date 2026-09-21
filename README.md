# 🎓 Taza-Gojo EDU

An online school for children on low-bandwidth (2G/3G) networks in Africa.
Works as a **web app (PWA)** and as **downloadable mobile apps** (Google Play +
App Store via Capacitor).

Game-based courses (English, Math, Science, Computer Programming) run fully
offline, each lesson comes with a **video lecture**, students get **face-to-face
video tutoring** tuned for congested networks, and a **free offline library**
covers grade-6→college material.

```
React web + mobile app ──► Django (API + WebRTC signaling) ◄── C++ mediaserver (optional SFU)
                 ├─ accounts/auth (JWT)
                 ├─ courses   → JSON game scripts + video lectures
                 ├─ agents    → content/grader/curriculum (mock|openai|ollama)
                 ├─ tutoring  → sessions + WebSocket signaling
                 └─ offline   → idempotent sync queue for offline writes
```

## What works right now

- **Backend** — Django 5 + DRF + Channels. Courses, lessons and progress; JWT
  auth (student/teacher/content_creator/admin); tutoring sessions and a
  WebSocket signaling relay for WebRTC calls; a content-agent task queue with a
  `mock` provider; offline sync and a lecture render pipeline.
- **Frontend** — one Vite + React 18 codebase for web and native. The PWA works
  offline (service worker + IndexedDB queue), has four tap-games, a downloadable
  Library and a `/call/:sessionId` video page. The native app wraps the same UI
  with Capacitor.
- **Video lectures** — every lesson ships as a short MP4 rendered from the
  lesson content with HyperFrames; re-render with
  `python manage.py render_lectures`.
- **Live video tutoring** — students book face-to-face calls with real teachers;
  no AI tutor chat.
- **Library** — 66 curated free resources (OpenStax, Gutenberg, Khan Academy,
  MIT OCW, LibreTexts, freeCodeCamp) plus agent-written study packs, filterable
  by subject and grade.
- **Learning roadmap** — onboarding captures goals, interests and weekly time,
  which drive the curriculum planner.
- **In-app admin** — overview stats, material management and user administration
  at `/admin`.
- **Mediaserver (C++17)** — libdatachannel-based WebRTC SFU with an
  RTCP-loss-driven bitrate controller.

## 5-minute dev run

```bash
# terminal 1 — backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py seed_core && python manage.py seed_materials
python manage.py run_agents &
daphne -b 127.0.0.1 -p 8000 config.asgi:application

# terminal 2 — frontend
cd frontend && npm install && npm run dev     # http://localhost:5173
```

Seeded users: `ada` (student) and `mrkwame` (teacher), password `test1234`.

## Deploy

- **fly.io** — see `docs/DEPLOY.md` (Django serves the API and built SPA on one
  origin, keeping PWA + WebRTC + WebSockets same-origin).
- **Docker** — `docker compose up --build` for self-hosted installs.
- **Stores** — see `docs/STORE-DEPLOY.md` for the Capacitor projects.

## Docs

`docs/architecture.md`, `docs/offline-first.md`, `docs/ai-agents.md`,
`docs/DEPLOY.md`, `docs/STORE-DEPLOY.md`.

## License

MIT (see LICENSE).
