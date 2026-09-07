from django.urls import re_path
from .consumers import SignalConsumer

websocket_urlpatterns = [
    re_path(r"ws/tutor/(?P<session_id>\d+)/$", SignalConsumer.as_asgi()),
]