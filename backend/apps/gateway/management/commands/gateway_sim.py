"""Simulate a feature-phone learner from the terminal (no SMS account needed).

Usage:
    python manage.py gateway_sim +251900000001 START
    python manage.py gateway_sim +251900000001 1
    python manage.py gateway_sim +251900000001 B
    python manage.py gateway_sim --ussd +251900000001 1
"""

from django.core.management.base import BaseCommand

from apps.gateway import services


class Command(BaseCommand):
    help = "Send a fake SMS/USSD message into the gateway and print the replies."

    def add_arguments(self, parser):
        parser.add_argument("phone")
        parser.add_argument("text", nargs="?", default="")
        parser.add_argument("--ussd", action="store_true", help="Simulate USSD instead of SMS")

    def handle(self, *args, **opts):
        phone, text = opts["phone"], opts["text"]
        if opts["ussd"]:
            cont, message = services.handle_ussd(phone, text)
            self.stdout.write(("CON " if cont else "END ") + message)
            return
        for reply in services.handle_sms(phone, text):
            self.stdout.write(self.style.SUCCESS("← " + reply))
