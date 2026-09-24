# Taza-Gojo EDU — architecture

**Goal.** A school any child with a low-cost phone and a 2G connection can use.
The platform is **Ethiopia-first and Cambridge/IGCSE-aligned**, with a curriculum
layer that maps onto other African systems. Content spans primary → junior
secondary → vocational/adult, and includes Physics and Electricity alongside
English, Mathematics, Science and Computing.

## High-level layout

```
┌───────────────────┐  HTTPS /api, /ws   ┌──────────────────────────────────┐
│ React PWA         │ ─────────────────► │ Django (daphne, ASGI)            │
│ (web · Android ·  │                    │  ├─ accounts    auth + profiles  │
│  iOS · desktop ·  │  WS signaling      │  ├─ curriculum  frameworks/outcomes
│  TV)              │ ─────────────────► │  ├─ courses     game scripts + lectures
│                   │                    │  ├─ assessment  item bank + adaptive
│  WebRTC (1:1)     │                    │  ├─ labs        coding/circuit/science
└─────────┬─────────┘                    │  ├─ live        LiveKit classes
          │ media (DTLS/SRTP-UDP)        │  ├─ analytics   learning events
          ▼                              │  ├─ agents      AI (mock|openai|ollama)
┌───────────────────┐  SFU               │  ├─ tutoring    1:1 signaling
│ LiveKit (groups)  │ ◄────────────────► │  └─ offline     idempotent sync
│ C++ SFU (LAN hub) │                    └──────────────┬───────────────────┘
└───────────────────┘                                   │
                                    PostgreSQL · Redis (channels/queue) · media
```

Everything the browser needs is served from **one origin** (the Django host) so
the PWA service worker can intercept it. Live group classes use a self-hosted
**LiveKit** SFU; the C++ mediaserver remains an optional LAN hub.

## Apps

| App | Responsibility |
|---|---|
| `accounts` | JWT auth, roles (`student/teacher/content_creator/admin`), profiles, roadmap |
| `curriculum` | Frameworks → strands → outcomes, cross-framework mappings, `OutcomeLink` |
| `courses` | Courses → modules → lessons (JSON game scripts), progress, lecture video |
| `assessment` | Item bank, auto-grading, adaptive Elo, attempts, certificates, manual grading |
| `labs` | Coding/circuit/physics/science labs + submissions (browser-graded) |
| `live` | LiveKit class scheduling, scoped tokens, attendance, recording hooks |
| `gateway` | SMS/USSD/voice quizzes for feature phones (aggregator-agnostic) |
| `analytics` | Offline-first learning events + summaries |
| `agents` | Durable task queue + pluggable providers (`mock/openai/ollama`) |
| `tutoring` | 1:1 session state machine + WebSocket signaling relay |
| `offline` | Idempotent sync of offline writes |
| `library` | Curated free resources + downloadable study packs |
| `adminapi` | In-app school admin (counts, materials, users) |

## Data model (abridged)

- `accounts.User` / `accounts.Profile` — role, country, device bandwidth, points,
  streak, goals/interests.
- `curriculum.Framework/Strand/Outcome` + `Mapping` + `OutcomeLink` — the
  country-agnostic curriculum layer.
- `courses.Course → Module → Lesson` (`content` is a small JSON game script) → `Question`.
- `assessment.Item` → `AssessmentItem` → `Assessment`; `Attempt` → `Response`;
  `Certificate`. `Item.answer` is never exposed to students.
- `labs.Lab` → `LabSubmission`.
- `live.LiveClass` → `Attendance`.
- `analytics.LearningEvent`.
- `offline.SyncBatch` — audit trail of applied offline ops.
- `tutoring.TutoringSession` + `CallEvent`.

## Request flow

- **Auth.** JWT (`djangorestframework-simplejwt`); the client refreshes once and
  replays the request.
- **Progress writes** go through `POST /api/v1/offline/sync/`, idempotent by
  `(device_id, op_id)`.
- **Assessment.** `start` serves an item (adaptive: nearest difficulty to the
  learner's Elo `theta`); `answer` grades server-side and updates `theta`;
  `submit` finalises and issues a certificate on pass.
- **Signaling** (`SignalConsumer`) relays `offer`/`answer`/`ice`/`mode` between
  peers (and a mediaserver leg when enrolled), re-broadcasting the last offer so
  a reconnecting peer can rejoin.
- **Live classes.** The client asks the API to `join`, receives a scoped LiveKit
  token, and connects to the SFU with simulcast/dynacast.

## Why these components

| Decision | Reason |
|---|---|
| Small JSON game scripts | A few KB per lesson plays fully offline. |
| IndexedDB + service worker | Cache-first shell, network-first API, offline write queue. |
| Browser-only labs | Coding (JS worker / Pyodide) and SVG sims run with zero signal. |
| Elo adaptive testing | Dependency-free and effective; upgrade path to 2PL IRT. |
| LiveKit for groups | Open-source SFU with SDKs for every target platform. |
| Pluggable AI provider | Run with zero keys locally; swap in OpenAI or a school Ollama. |

## Deployment modes

1. **PaaS / single container (default).** Render/Fly/Docker: Django serves the
   API, WebSocket signaling and the built SPA on one origin.
2. **LAN hub.** A mediaserver on a Wi-Fi hotspot carries media for a classroom
   that shares one upstream link.

See `docs/offline-first.md`, `docs/curriculum.md`, `docs/assessment.md`,
`docs/interactive.md`, `docs/labs.md`, `docs/live.md`, `docs/gateway.md`,
`docs/desktop.md`, `docs/ai-agents.md`, `docs/DEPLOY.md`, `docs/DEPLOY-RENDER.md`.

## Local dev quickstart

```bash
# Backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_core && python manage.py seed_materials
python manage.py seed_curriculum && python manage.py seed_assessment && python manage.py seed_labs
python manage.py run_agents &
daphne -b 127.0.0.1 -p 8000 config.asgi:application

# Frontend
cd frontend && npm install && npm run dev     # http://localhost:5173
```
