# 🎓 Taza-Gojo EDU

**Live:** https://taza-edu.onrender.com

An online school for children on low-bandwidth (2G/3G) networks in Africa.
Works as a **web app (PWA)** and as **downloadable mobile apps** (Google Play +
App Store via Capacitor).

Ethiopia-first and **Cambridge/IGCSE-aligned**, with a curriculum layer that maps
flexibly onto any African system. Subjects include English, Mathematics, Science,
**Physics**, **Electricity** (academic and TVET/electrical), and Computing.
Game-based courses run fully offline, each lesson has a **video lecture**,
learners get **adaptive auto-graded assessments**, **in-app coding and circuit
labs**, **live classes** for 1:1 and groups up to 15, and a **free offline
library** — all multilingual (Amharic, Afaan Oromo, Tigrinya, Somali + more).

```
React web + mobile app ──► Django (API + WebRTC signaling + LiveKit tokens)
                 ├─ accounts     → JWT auth, roles, profiles
                 ├─ curriculum   → frameworks · strands · outcomes · mappings
                 ├─ courses      → JSON game scripts + video lectures
                 ├─ assessment   → item bank, adaptive Elo, auto-grading, certs
                 ├─ labs         → coding (browser), circuits, physics, science
                 ├─ live         → LiveKit classes, attendance, recording
                 ├─ analytics    → offline-first learning events
                 ├─ agents       → content/grader/curriculum (mock|openai|ollama)
                 ├─ tutoring     → 1:1 sessions + WebSocket signaling
                 └─ offline      → idempotent sync queue for offline writes
```

## What works right now

- **Backend** — Django 5 + DRF + Channels. Courses, lessons and progress; JWT
  auth (student/teacher/content_creator/admin); tutoring sessions and a
  WebSocket signaling relay for WebRTC calls; a content-agent task queue with a
  `mock` provider; offline sync and a lecture render pipeline.
- **Interactive lessons** — Brilliant-style guided discovery that runs offline:
  sliders, plots, ordering, matching, an embedded circuit simulator, immediate
  feedback with the *reason why*, hints and worked solutions. Seed with
  `python manage.py seed_interactive`.
- **Curriculum** — framework/strand/outcome model seeded with Cambridge Primary,
  Lower Secondary and IGCSE plus Ethiopian MoE and TVET, cross-mapped so one
  lesson serves many countries. See `docs/curriculum.md`.
- **Assessment** — reusable item bank (MCQ, multi-select, numeric-with-units,
  math, code, ordering, matching, short answer, essay); server-side auto-grading;
  adaptive item selection using an Elo ability model; verifiable certificates.
  See `docs/assessment.md`.
- **Labs** — browser-only coding (JavaScript in a sandboxed Web Worker, Python
  via Pyodide), an SVG DC-circuit simulator, pendulum and water-cycle sims, plus
  guided real experiments. See `docs/labs.md`.
- **Live classes** — LiveKit (open source SFU) for 1:1 and groups up to 15, with
  scheduling, attendance and recording hooks; falls back to P2P when unset. See
  `docs/live.md`.
- **Analytics** — offline-first learning events powering progress dashboards.
- **Frontend** — one Vite + React 18 codebase for web and native. The PWA works
  offline (service worker + IndexedDB queue), has four tap-games, adaptive
  assessment runner, labs, live classes, downloadable Library, certificates and a
  `/call/:sessionId` video page. The native app wraps the same UI with Capacitor.
- **Localisation** — dependency-free i18n with Amharic, Afaan Oromo, Tigrinya,
  Somali, French, Kiswahili and Arabic (RTL).
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
python manage.py migrate
python manage.py seed_core && python manage.py seed_materials
python manage.py seed_curriculum && python manage.py seed_assessment && python manage.py seed_labs && python manage.py seed_interactive
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
`docs/curriculum.md`, `docs/assessment.md`, `docs/labs.md`, `docs/live.md`,
`docs/DEPLOY.md`, `docs/STORE-DEPLOY.md`.

## License

MIT (see LICENSE).
