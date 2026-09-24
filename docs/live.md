# Live classes

Live video for **1:1 tutoring and groups up to 15**, carried by a self-hosted
[LiveKit](https://livekit.io) SFU (open source, SDKs for web, Android, iOS and
desktop). The backend only schedules classes, tracks attendance and mints
scoped access tokens — it never handles media.

## Configuration

```bash
LIVEKIT_URL=wss://livekit.example.org
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
```

With no keys set, `join` returns `configured: false` and the frontend explains
that the built-in **peer-to-peer** tutoring call (the existing
`/call/:sessionId` path) is the fallback. This keeps local dev zero-config.

A dev SFU:

```yaml
# docker-compose.yml (uncomment the livekit block)
livekit:
  image: livekit/livekit-server:latest
  command: --dev --bind 0.0.0.0
  network_mode: host
  environment:
    LIVEKIT_KEYS: "devkey: secret"
```

## Model

- `LiveClass` — title, host, course, subject, `room_name`, schedule, capacity
  (`max_participants`, default 15), status, recording URL.
- `Attendance` — who joined, when, for how long.

## API

```
GET/POST /api/v1/live/classes/            list / schedule (teachers)
POST     /api/v1/live/classes/<id>/join/   -> {url, token, can_publish, max_participants}
POST     /api/v1/live/classes/<id>/leave/  record departure
POST     /api/v1/live/classes/<id>/end/    host ends the class
GET      /api/v1/live/classes/<id>/roster/ attendance list
```

Tokens are HS256 JWTs with a `video` grant (`roomJoin`, `canPublish`,
`canSubscribe`); teachers/admins get `canPublish`, students are subscribe-only
until promoted. See `backend/apps/live/livekit.py`.

## Frontend

`frontend/src/pages/LivePage.jsx` loads the LiveKit client lazily from a
configurable CDN URL (`window.LIVEKIT_CLIENT_URL`), connects with
`adaptiveStream` + `dynacast`, and attaches remote/local video. For fully
offline-capable packaging, vendor `livekit-client` and point the URL at it.

## Bandwidth

LiveKit's simulcast + dynacast plus the existing quality presets keep calls
alive on 2G/3G. Recording uses LiveKit Egress (multi-rendition) when enabled;
`LiveClass.recording_url` stores the result.
