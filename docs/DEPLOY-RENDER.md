# Deploying to Render

This repo ships a `render.yaml` Blueprint. Render builds the root `Dockerfile`,
which produces **one image** running Django (daphne) that serves the API,
WebSockets/WebRTC signaling **and** the built React SPA from a single origin —
so the PWA, service worker and live classes all stay same-origin.

## One-click (Blueprint)

1. Push this repo to GitHub (already at `ZebraCodeX/taza-gojo-edu`).
2. In Render: **New → Blueprint** → connect the repo → **Apply**.
3. Render will:
   - create the `taza-db` Postgres database,
   - build the Docker image,
   - run `migrate` + `collectstatic` + all content seeds on first boot,
   - health-check `GET /api/health/`,
   - serve the app at **https://taza-edu.onrender.com**.

That's it. The first boot seeds courses (English, Math, Science, Physics,
Electricity, Computing), the curriculum frameworks, assessments and labs.

## About the URL

`render.yaml` names the service `taza-edu`, so Render assigns
`https://taza-edu.onrender.com`.

> `taza-edu-onrender.com` (with a hyphen before "onrender") is **not** a
> Render-provided hostname — Render only issues `<service-name>.onrender.com`.
> To use a domain you own, add it under **Settings → Custom Domains** and point
> its DNS (CNAME) at Render.

## Manual (no Blueprint)

Create a **Web Service → Docker**:

| Setting | Value |
|---|---|
| Dockerfile path | `./Dockerfile` |
| Health check path | `/api/health/` |
| Start command | *(from the Dockerfile)* |

Environment variables:

```
DEBUG=0
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<generate>
DJANGO_ALLOWED_HOSTS=.onrender.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
DATABASE_URL=<from the Render Postgres>
AI_PROVIDER=mock
```

Then create a **PostgreSQL** instance and link `DATABASE_URL`.

## Optional services

- **Redis / Key Value** → set `REDIS_URL` for multi-instance Channels + agent
  queue (single instance uses the in-memory layer).
- **LiveKit** → set `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` to
  enable group live classes (1:1–15). Without them the P2P call path is used.
- **AI** → set `AI_PROVIDER=openai` + `AI_API_KEY`, or `ollama` + `AI_API_URL`.

## Deploy via API (automation)

If you have a Render API key you can create the service without the dashboard:

```bash
export RENDER_API_KEY=rnd_xxx
curl -s https://api.render.com/v1/blueprints \
  -H "Authorization: Bearer $RENDER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"repo":"https://github.com/ZebraCodeX/taza-gojo-edu","branch":"main","autoDeploy":"yes"}'
```

## Verify

```bash
curl -s https://taza-edu.onrender.com/api/health/        # {"ok": true}
curl -s https://taza-edu.onrender.com/api/v1/courses/    # 401 without a token
```

Sign in with the seeded demo accounts: `ada` / `mrkwame`, password `test1234`
(change these before real use — see `seed_core.py`).

## Notes & limits

- Free instances **sleep when idle** and cold-start in a few seconds; the
  health check keeps them honest but does not prevent sleep.
- Free Postgres has storage/time limits — use a paid plan for production.
- Lecture MP4s are baked into the image (committed under `backend/media/`), so
  no extra object storage is required to start.
