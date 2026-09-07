# Taza-Gojo EDU — architecture

**Goal.** A school any child with a $40 Android phone and a 2G connection can
use. AI agents build the courses, an AI tutor answers questions between video
calls, and real teachers tutor face-to-face over WebRTC that survives flaky
networks.

## High-level layout

```
┌────────────┐   HTTPS /api, /ws    ┌──────────────────────────────┐
│  React PWA │ ───────────────────► │  Django (daphne ASGI)        │
│  (browser) │                      │  examples                    │
│            │  WS signaling       │  ├─ accounts (auth+profiles) │
│  WebRTC lev├────────────────────►│  ├─ courses (content+tasks)  │
└───┬────────┘                      │  ├─ agents (AI core)         │
    │ media (DTLS/SRTP-UDP)          │  ├─ tutoring (sessions+signaling)
    ▼                              │  └─ offline (sync queue)     │
┌────────────┐  RTCP loss → mode   └──────────────┬───────────────┘
│ C++ SFU    │ ◄────────────────────             │
│ mediaserver│                                    │  ┌───────────┐  ┌──────┐
└────────────┘   WS to SignalingConsumer          ▼  │  Redis    │  │ Postgres│
                                            run_agents ◄──►  │  (channels)│  └──────┘
                                                              └───────────┘
```

Everything the browser needs is on one origin (the Django host) so the PWA
service worker can intercept it; the mediaserver is optional and only used to
choke video bitrate on congested 3G links.

## Data model (abridged)

- `accounts.User` (`AUTH_USER_MODEL`): `role` in `student|teacher|content_creator|admin`.
- `accounts.Profile`: `country`, `device_bandwidth`, `subjects`, `points`, `streak_days`,
  `timezone` — drives lesson selection, difficulty and video presets.
- `courses.Course` → `Module` → `Lesson` (`content` is a small JSON **game script**
  interpreted by `frontend/src/games/GameRenderer.jsx`) → `Question`.
- `courses.LessonProgress` — per user per lesson (`completed`, `score`, `stars`).
- `agents.AgentTask` — durable queue of jobs written by the API and executed by
  the `run_agents` worker. `Conversation`/`Message` persist AI tutor chat.
- `tutoring.TutoringSession` — state machine `requested → scheduled → active →
  ended|cancelled`; `CallEvent` is a raw JSON log of offer/answer/ICE/mode events.
- `offline.SyncBatch` — audit trail of every offline op the server applied.

## Request flow

- **Auth.** JWT (`djangorestframework-simplejwt`). Access token 15 min, refresh
  silent. `frontend/src/api/client.js` transparently refreshes once and replays.
- **Progress writes** go through `offline.SyncView` (`POST /api/v1/offline/sync/`)
  which is *idempotent*: it applies each op only once (`op_id` log) and returns
  `{ applied, pending }`.
- **Signaling** (`SignalConsumer`, `consumers.py`) joins a group per session and
  relays `offer`/`answer`/`ice`/`mode` frames between the two browser users and,
  when enrolled, a mediaserver leg. It re-broadcasts the last offer/ICE so a
  reconnecting peer can rejoin mid-call.

## Why these components

| Decision | Reason |
|---|---|
| Frames (Django get-on-the-page) | Standard, quick to build the admin-ish ops parts. |
| Small JSON game scripts | A 5 KB lesson plays fully offline; agents can author them. |
| Indexed DB + SW (PWA) | Cache-first shell, network-first API, offline queue. |
| WebSocket signaling via Channels | Survives NAT better than direct WS to a mediaserver; also carries mode/bitrate control. |
| C++ SFU with RTCP-loss-driven bitrate | Cheap surplus phones / Raspberry Pi act as a local "hub" for a classroom share it over Wi-Fi; drop resolution before packet loss compounds. |
| Pluggable AI provider (`mock/openai/ollama`) | Run with zero keys locally; swap in a real model or a school-owned Ollama in-country. |

## Two deployment modes

1. **Peer-to-peer (default).** Browsers connect directly; `MEDIA_SERVER_URL`
   unset. Works for one-on-one tutoring at low/medium quality.
2. **Hub (classroom/2G).** A `mediaserver` instance on a Wi-Fi hotspot carries
   the media. Students join the hub over short-range Wi-Fi; the hub tunnels one
   upstream video stream to the tutor abroad, throttling per RTCP loss.

## Local dev quickstart

```
# Backend (SQLite + in-memory channel layer work for single-process dev)
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate && python manage.py seed_core
python manage.py test apps.tutoring
daphne -b 127.0.0.1 -p 8000 config.asgi:application

# Frontend
cd frontend && npm install && npm run dev   # proxies /api and /ws to :8000

# Optional agent worker
cd backend && python manage.py run_agents

# Mediaserver (libdatachannel is pulled in at configure time)
cd mediaserver && cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  && cmake --build build -j$(nproc) && ./build/tazagojo_mediaserver --help
```

See `docs/offline-first.md` and `docs/ai-agents.md` for those subsystems.