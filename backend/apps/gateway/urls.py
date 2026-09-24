from django.urls import path

from .views import sms_webhook, ussd_webhook, gateway_health

urlpatterns = [
    path("sms/", sms_webhook),
    path("ussd/", ussd_webhook),
    path("health/", gateway_health),
]
