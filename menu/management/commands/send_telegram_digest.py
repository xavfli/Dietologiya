from django.core.management.base import BaseCommand

from menu.models import MenuDay, TelegramSubscription
from menu.services import send_telegram_message


class Command(BaseCommand):
    help = "Send Telegram daily menu and cost digest to configured organizations."

    def add_arguments(self, parser):
        parser.add_argument("--organization", help="Send only one organization by name.")

    def handle(self, *args, **options):
        subscriptions = TelegramSubscription.objects.filter(is_active=True, daily_digest=True).select_related("organization")
        if options.get("organization"):
            subscriptions = subscriptions.filter(organization__name=options["organization"])

        sent = 0
        for subscription in subscriptions:
            organization = subscription.organization
            menu_day = MenuDay.objects.filter(organization=organization).order_by("-date").first()
            if not menu_day:
                text = f"{organization.name}: menyu ma'lumotlari hali yo'q."
            else:
                text = (
                    f"{organization.name}\n"
                    f"Sana: {menu_day.date:%d.%m.%Y}\n"
                    f"Taomlanuvchilar: {menu_day.people_count}\n"
                    f"Umumiy xarajat: {menu_day.total_cost:.0f} so'm\n"
                    f"Kishi boshiga: {menu_day.per_person_cost:.0f} so'm"
                )
            if send_telegram_message(subscription, text):
                sent += 1
                self.stdout.write(f"Sent: {organization.name}")
            else:
                self.stdout.write(self.style.WARNING(f"Skipped/failed: {organization.name}"))
        self.stdout.write(self.style.SUCCESS(f"Telegram digests sent: {sent}"))
