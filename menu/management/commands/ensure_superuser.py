import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a superuser from environment variables when credentials are provided."

    def handle(self, *args, **options):
        username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "")
        email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "").strip()

        if not username or not password:
            self.stdout.write("Superuser env vars are not set; skipping admin creation.")
            return

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "email": email,
                "is_staff": True,
                "is_superuser": True,
            },
        )

        changed = False
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if email and user.email != email:
            user.email = email
            changed = True

        if created or os.environ.get("DJANGO_SUPERUSER_UPDATE_PASSWORD", "").lower() == "true":
            user.set_password(password)
            changed = True

        if changed:
            user.save()

        action = "created" if created else "already exists"
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' {action}."))
