"""Taza-Gojo EDU Django project settings.

Designed to run in low-resource environments:
- SQLite default (zero-admin), PostgreSQL via env var.
- Configurable AI provider: `openai`, `ollama` (local/offline), or `mock` (no network).
"""

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DEBUG", "1") == "1"
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "channels",
    "apps.accounts",
    "apps.courses",
    "apps.agents",
    "apps.tutoring",
    "apps.offline",
    "apps.library",
    "apps.adminapi",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

ASGI_APPLICATION = "config.asgi.application"
WSGI_APPLICATION = "config.wsgi.application"

# Database: PostgreSQL in production, SQLite served as the offline-friendly default.
# Accepts the standard DATABASE_URL from fly.io/Heroku style platforms, or the
# explicit DB_* env vars used by docker-compose.
_db_url = os.environ.get("DATABASE_URL", "")
if _db_url:
    from urllib.parse import urlparse

    _u = urlparse(_db_url)
    _u = _u._replace(scheme=_u.scheme.replace("postgres", "postgresql"))
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _u.path.lstrip("/"),
            "USER": _u.username,
            "PASSWORD": _u.password,
            "HOST": _u.hostname,
            "PORT": _u.port or 5432,
        }
    }
elif os.environ.get("DB_ENGINE") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("DB_NAME", "tazagojo"),
            "USER": os.environ.get("DB_USER", "tazagojo"),
            "PASSWORD": os.environ.get("DB_PASSWORD", "tazagojo"),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# Built React SPA (frontend/dist). The Django app serves it on the same origin
# so the PWA, service worker, WebSockets and WebRTC signaling share one host —
# no CORS, no mixed content, ideal for low-trust school networks.
FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist")
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- CORS (frontend dev server) ----
CORS_ALLOW_ALL_ORIGINS = DEBUG
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
]

# ---- DRF ----
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

# ---- Channels ----
CHANNEL_LAYERS = {
    "default": {
        # redis available -> use it; otherwise in-memory (dev, single process).
        "BACKEND": ("channels_redis.core.RedisChannelLayer"
                    if os.environ.get("REDIS_URL") else "channels.layers.InMemoryChannelLayer"),
        "CONFIG": ({"hosts": [os.environ.get("REDIS_URL", "redis://127.0.0.1:6379")]}
                   if os.environ.get("REDIS_URL") else {}),
    }
}

# ---- AI agents ----
# Provider is intentionally pluggable. In remote classrooms with no Internet you
# can point this at a local Ollama server; with connectivity use openai.
AI_PROVIDER = os.environ.get("AI_PROVIDER", "mock")  # mock | openai | ollama
AI_MODEL = os.environ.get("AI_MODEL", "llama3")
AI_API_KEY = os.environ.get("AI_API_KEY", "")
AI_API_URL = os.environ.get("AI_API_URL", "http://localhost:11434")
AI_OPENAI_URL = os.environ.get("AI_OPENAI_URL", "https://api.openai.com/v1")

# ---- Video / tutoring ----
# Where the C++ mediaserver (SFU + bitrate adaptation) lives.
MEDIA_SERVER_URL = os.environ.get("MEDIA_SERVER_URL", "wss://mediaserver:8443")
TURN_SERVERS = os.environ.get("TURN_SERVERS", "")  # "turn:host:3478?user=u;pass=p"

# ---- Offline sync ----
SYNC_WINDOW_DAYS = int(os.environ.get("SYNC_WINDOW_DAYS", "30"))