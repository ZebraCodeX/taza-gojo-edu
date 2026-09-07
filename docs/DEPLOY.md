# Deploying Taza-Gojo EDU to fly.io

One fly.io app hosts the **whole product** (Django API + WebSockets + the built
React PWA) on a single origin, so the service worker, WebRTC signaling and
tokens all stay same-origin. Works for both the web app and the Capacitor apps
(`VITE_API_URL=https://<app>.fly.dev` at native build time).

> Requires a fly.io account (a personal one is fine). Free tier covers a single
> small machine + the demo database.

## 1. Install the CLI

```bash
# macOS
brew install flyctl
# Linux
curl -L https://fly.io/install.sh | sh
# verify
fly version
```

## 2. Log in

```bash
fly auth login
```

## 3. Bootstrap the app (creates fly.toml + machine)

```bash
# from the repo root (uses the existing fly.toml + Dockerfile)
fly launch --name taza-gojo-edu --region iad --no-deploy
fly scale memory 1024        # Django + agents comfortably in 1GB
```

## 4. Postgres database

```bash
fly postgres create --name taza-gojo-pg --region iad --vm-size shared-cpu-1x --memory 512
fly postgres attach taza-gojo-pg
```

`fly postgres attach` sets the `DATABASE_URL` secret automatically; the app
parses it in `config/settings.py`.

## 5. Secrets (never commit these)

```bash
fly secrets set DJANGO_SECRET_KEY="$(openssl rand -hex 32)"
fly secrets set DJANGO_DEBUG="false"

# ~~ optional: real AI instead of the mock provider ~~
fly secrets set AI_PROVIDER=openai AI_MODEL=gpt-4o-mini
fly secrets set AI_API_KEY="sk-..."
#   (or school-owned Ollama: AI_PROVIDER=ollama AI_API_URL=http://localhost:11434)

# ~~ optional: TURN for video calls behind strict NATs ~~
# fly secrets set TURN_SERVERS="turn:turn.example.com:3478?user=u;pass=p"
```

## 6. Redis (only needed if you scale past one instance)

The default fly config uses Channels' **in-memory** layer, which is correct for a
single machine. To scale to multiple daphne workers you need Redis:

```bash
fly redis create
fly redis status <redis-name>        # copy the REDIS_URL
fly secrets set REDIS_URL="rediss://..."
```

## 7. Deploy

```bash
fly deploy --dockerfile Dockerfile
```

First boot: creates a `superuser`-less setup, runs `migrate` + `seed_core` (the
four core courses). Logs:

```bash
fly logs
```

## 8. Sanity check

```bash
# API + seed data
curl https://taza-gojo-edu.fly.dev/api/v1/offline/manifest/ | head

# SPA is served on the same origin
curl -sI https://taza-gojo-edu.fly.dev/ | head -3
curl -sI https://taza-gojo-edu.fly.dev/sw.js | head -3
```

Then open https://taza-gojo-edu.fly.dev and log in as `ada` / `test1234`.

## Day-two ops

| Task | Command |
|---|---|
| Deployment rollback | `fly releases` then `fly releases deploy <id>` |
| View logs | `fly logs` |
| Attach a shared IPv4 (for clients on IPv4-only networks) | `fly ips allocate-v4` |
| Scale to 2 daphne workers | set `REDIS_URL`, then `fly scale count 2` |
| Mobile apps against prod | build native with `VITE_API_URL=https://taza-gojo-edu.fly.dev` (see `docs/STORE-DEPLOY.md`) |

## Notes / gotchas

- WebRTC is **peer-to-peer** by default (no mediaserver) — works for 1:1 calls.
  For a classroom hub throttling video on 2G, run the C++ `tazagojo_mediaserver`
  on a Wi-Fi box and set `MEDIA_SERVER_URL` — see `docs/architecture.md`.
- `DJANGO_DEBUG=true` is fine for a prototype; flip it false with the secret above.
- The `auto_stop_machines = "stop"` setting parks the machine when idle to save
  money; change to `"off"` if you need a warm first page load.