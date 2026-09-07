# Taza-Gojo EDU — single fly.io app.
# Stage 1: build the React web app (= PWA shell + Capacitor web assets).
# Stage 2: Django (daphne) serving BOTH the API/WebSockets AND the built SPA
# from one origin — service worker, WebRTC signaling and PWA stay same-origin,
# no CORS, no mixed content.

# ---------- web build ----------
FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build
# Keep output minimal: dist + native shells are not needed on the server.
RUN rm -rf node_modules android ios resources capacitor.config.json

# ---------- backend + runtime ----------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=web /web/dist ./frontend_dist
ENV FRONTEND_DIST="/app/frontend_dist"

EXPOSE 8000
# migrate + seed content, start the AI worker in the background, then daphne.
CMD ["sh", "-c", "python manage.py migrate --noinput && \
    python manage.py seed_core && \
    python manage.py seed_materials && \
    python manage.py run_agents & \
    exec daphne -b 0.0.0.0 -p 8000 config.asgi:application"]