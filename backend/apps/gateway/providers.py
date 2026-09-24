"""Outbound channel providers.

SMS goes through a configurable aggregator. Default is a no-op "console"
provider so the whole flow is testable offline. Africa's Talking is supported
out of the box; add others by writing one ``send_sms`` function.
"""

import logging

import requests
from django.conf import settings

log = logging.getLogger("tazagojo.gateway")


def send_sms(phone, text):
    """Send an SMS. Returns True on success (or in mock mode)."""
    provider = getattr(settings, "SMS_PROVIDER", "console")
    if provider == "africastalking":
        return _africastalking(phone, text)
    log.info("[SMS:%s] %s", phone, text)
    return True


def _africastalking(phone, text):
    username = getattr(settings, "AFRICASTALKING_USERNAME", "")
    api_key = getattr(settings, "AFRICASTALKING_API_KEY", "")
    sender = getattr(settings, "AFRICASTALKING_SENDER", "")
    if not (username and api_key):
        log.warning("Africa's Talking not configured; dropping SMS to %s", phone)
        return False
    url = getattr(settings, "AFRICASTALKING_URL", "https://api.africastalking.com/version1/messaging")
    try:
        res = requests.post(
            url,
            data={"username": username, "to": phone, "message": text, "from": sender},
            headers={"apiKey": api_key, "Accept": "application/json"},
            timeout=10,
        )
        return res.status_code < 400
    except requests.RequestException as e:
        log.warning("SMS send failed: %s", e)
        return False


def send_voice(phone, text_or_audio_url):
    """Placeholder for IVR/voice lessons (out of scope for now)."""
    log.info("[VOICE:%s] %s", phone, text_or_audio_url)
    return True
