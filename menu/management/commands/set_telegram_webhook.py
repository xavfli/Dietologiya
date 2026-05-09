import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError


BOT_COMMANDS = [
    {"command": "start", "description": "Botni boshlash va ko'rsatma olish"},
    {"command": "login", "description": "Sayt login/paroli bilan ulanish"},
    {"command": "today", "description": "Oxirgi menyu va xarajatlarni olish"},
    {"command": "summary", "description": "Tashkilot bo'yicha qisqa xulosa"},
    {"command": "help", "description": "Yordam"},
]


class Command(BaseCommand):
    help = "Register this site's Telegram webhook URL."

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True, help="Full webhook URL, for example https://site.onrender.com/telegram/webhook/")

    def handle(self, *args, **options):
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        if not token:
            raise CommandError("TELEGRAM_BOT_TOKEN is not configured.")

        self._telegram_request(token, "setWebhook", {"url": options["url"]})
        self._telegram_request(token, "setMyCommands", {"commands": BOT_COMMANDS})
        self.stdout.write(self.style.SUCCESS(f"Webhook set: {options['url']}"))
        self.stdout.write(self.style.SUCCESS("Bot commands set."))

    def _telegram_request(self, token: str, method: str, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            f"https://api.telegram.org/bot{token}/{method}",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise CommandError(error.read().decode("utf-8", errors="replace")) from error
        except URLError as error:
            raise CommandError(f"Telegram {method} request failed: {error}") from error

        if not response_payload.get("ok"):
            raise CommandError(response_payload)
        return response_payload
