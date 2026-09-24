"""Webhook endpoints for SMS/USSD aggregators (Africa's Talking compatible)."""

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from . import providers, services


def _authorized(request):
    token = getattr(settings, "GATEWAY_WEBHOOK_TOKEN", "")
    if not token:
        return True
    supplied = request.headers.get("X-Gateway-Token") or request.GET.get("token") or ""
    return supplied == token


def _field(request, *names):
    data = request.POST if request.POST else {}
    if not data and request.body:
        import json
        try:
            data = json.loads(request.body.decode() or "{}")
        except (ValueError, UnicodeDecodeError):
            data = {}
    for n in names:
        if data.get(n):
            return str(data[n])
    return ""


@csrf_exempt
@require_POST
def sms_webhook(request):
    if not _authorized(request):
        return JsonResponse({"detail": "forbidden"}, status=403)
    phone = _field(request, "from", "phone", "msisdn", "sender")
    text = _field(request, "text", "message", "body")
    if not phone:
        return JsonResponse({"detail": "missing phone"}, status=400)
    replies = services.handle_sms(phone, text)
    for r in replies:
        providers.send_sms(phone, r)
    return JsonResponse({"ok": True, "replies": len(replies)})


@csrf_exempt
@require_POST
def ussd_webhook(request):
    if not _authorized(request):
        return HttpResponse("END Unauthorised.", content_type="text/plain")
    phone = _field(request, "phoneNumber", "phone", "from", "msisdn")
    text = _field(request, "text", "input")
    if not phone:
        return HttpResponse("END Missing phone number.", content_type="text/plain")
    cont, message = services.handle_ussd(phone, text)
    prefix = "CON " if cont else "END "
    return HttpResponse(prefix + message, content_type="text/plain")


def gateway_health(request):
    return JsonResponse({"ok": True, "sms_provider": getattr(settings, "SMS_PROVIDER", "console")})
