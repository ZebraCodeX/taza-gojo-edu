"""Minimal LiveKit access-token minter (HS256 JWT).

No LiveKit server SDK dependency — a LiveKit access token is just a JWT with a
``video`` grant claim, so we sign it with PyJWT (already a project dependency).
"""

import time

import jwt
from django.conf import settings


def is_configured():
    return bool(
        getattr(settings, "LIVEKIT_API_KEY", "")
        and getattr(settings, "LIVEKIT_API_SECRET", "")
    )


def make_token(identity, room, name="", can_publish=True, ttl_seconds=3600):
    api_key = getattr(settings, "LIVEKIT_API_KEY", "")
    api_secret = getattr(settings, "LIVEKIT_API_SECRET", "")
    if not (api_key and api_secret):
        return ""
    now = int(time.time())
    grants = {
        "roomJoin": True,
        "room": room,
        "canPublish": bool(can_publish),
        "canSubscribe": True,
        "canPublishData": True,
    }
    payload = {
        "iss": api_key,
        "sub": str(identity),
        "name": name or str(identity),
        "iat": now,
        "nbf": now - 10,
        "exp": now + int(ttl_seconds),
        "video": grants,
    }
    return jwt.encode(payload, api_secret, algorithm="HS256")
