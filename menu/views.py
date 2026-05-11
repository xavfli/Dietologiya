from collections import defaultdict
from datetime import date
from decimal import Decimal
import json
import os
import re
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db import OperationalError
from django.db.models import Count, Prefetch
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, TemplateView

from .docx_export import build_docx
from .forms import MenuUploadForm, PriceSourceForm, TelegramSettingsForm
from .models import ImportJob, MenuAlert, MenuDay, MenuEntry, Organization, PriceHistory, TelegramSubscription
from .services import (
    build_menu_alerts,
    create_upload_job,
    get_user_organization,
    monthly_cost_chart,
    monthly_cost_total,
    product_requirement_summary,
    send_telegram_chat_message,
    telegram_api_call,
    top_cost_products,
)


MONTH_LABELS = {
    1: "Yanvar",
    2: "Fevral",
    3: "Mart",
    4: "Aprel",
    5: "May",
    6: "Iyun",
    7: "Iyul",
    8: "Avgust",
    9: "Sentabr",
    10: "Oktabr",
    11: "Noyabr",
    12: "Dekabr",
}


HOME_FEATURES = [
    {
        "title": "Balansli ovqatlanish",
        "text": "Dietologiya organizm uchun oqsil, yog', uglevod va energiya muvozanatini saqlashga yordam beradi.",
    },
    {
        "title": "Parhez nazorati",
        "text": "Sog'liq holatiga qarab individual parhezlar tanlanadi va kundalik menyu shu asosda tuziladi.",
    },
    {
        "title": "Sifatli taomnoma",
        "text": "To'g'ri tuzilgan taomnoma immunitet, ish unumdorligi va umumiy salomatlikni qo'llab-quvvatlaydi.",
    },
    {
        "title": "Oziq qiymati",
        "text": "Har bir taomning oziq qiymatini bilish ratsionni ilmiy asosda boshqarishga imkon beradi.",
    },
    {
        "title": "Yosh va ehtiyoj",
        "text": "Bolalar, kattalar yoki maxsus guruhlar uchun ovqatlanish me'yorlari alohida ko'rib chiqiladi.",
    },
    {
        "title": "Amaliy nazorat",
        "text": "Dietologiya faqat tavsiya emas, balki menyu, porsiya va mahsulot sifatini muntazam nazorat qilishdir.",
    },
]

PLATFORM_FEATURES = [
    {
        "index": "01",
        "title": "Mavsumiy taomnoma",
        "text": "Yil va mavsum bo'yicha kunlik menyularni alohida yuritish va nazorat qilish.",
        "icon": "menu/img/icon-1.png",
    },
    {
        "index": "02",
        "title": "Parhez turlari",
        "text": "1-parhez, laktosasiz va boshqa ovqatlanish rejimlarini qo'llab-quvvatlash.",
        "icon": "menu/img/icon-2.png",
    },
    {
        "index": "03",
        "title": "Taom tarkibi",
        "text": "Har bir taom uchun mahsulotlar, grammovka va retsept tarkibini saqlash.",
        "icon": "menu/img/icon-3.png",
    },
    {
        "index": "04",
        "title": "Oziq qiymati",
        "text": "Oqsil, yog', uglevod va kaloriyani avtomatik hisoblash.",
        "icon": "menu/img/icon-4.svg",
    },
    {
        "index": "05",
        "title": "Narx hisob-kitobi",
        "text": "Kishi boshiga va umumiy xarajatlarni real vaqtda ko'rsatish.",
        "icon": "menu/img/icon-5.svg",
    },
    {
        "index": "06",
        "title": "Hisobotlarga tayyor",
        "text": "Excel va PDF eksporti uchun kerakli struktura va jadval ko'rinishi.",
        "icon": "menu/img/icon-6.svg",
    },
]

DIETOLOGY_INFO = [
    {
        "title": "Dietologiya nima?",
        "text": "Dietologiya ovqatlanishning organizmga ta'sirini o'rganadi va sog'liq holatiga mos ratsion tuzishga yordam beradi.",
    },
    {
        "title": "Nega muhim?",
        "text": "To'g'ri ovqatlanish vazn nazorati, ovqat hazm qilish, immunitet va kundalik ish unumdorligini yaxshilaydi.",
    },
    {
        "title": "Asosiy tamoyil",
        "text": "Ratsionda porsiya me'yori, mahsulot sifati, kaloriyaviy muvozanat va individual ehtiyoj birgalikda hisobga olinadi.",
    },
]

DEMO_ORGANIZATIONS = [
    {
        "name": "Sog'lom Avlod MTT",
        "address": "Toshkent sh., Yunusobod tumani, 12-mavze",
        "contact": "+998 90 120 45 67",
        "menu_days_count": 24,
    },
    {
        "name": "Mehribonlik Ta'lim Markazi",
        "address": "Samarqand sh., Amir Temur ko'chasi, 18-uy",
        "contact": "+998 93 510 22 11",
        "menu_days_count": 18,
    },
    {
        "name": "Ishonch Klinik Sanatoriysi",
        "address": "Buxoro vil., G'ijduvon tumani, Mustaqillik ko'chasi",
        "contact": "+998 91 778 30 40",
        "menu_days_count": 31,
    },
    {
        "name": "Baraka Catering Service",
        "address": "Farg'ona sh., Alisher Navoiy ko'chasi, 7-uy",
        "contact": "+998 88 245 88 00",
        "menu_days_count": 15,
    },
    {
        "name": "Nurli Kelajak Maktabi",
        "address": "Namangan sh., Boburshoh ko'chasi, 25-uy",
        "contact": "+998 94 600 14 14",
        "menu_days_count": 27,
    },
    {
        "name": "Sihat Hospital Oshxonasi",
        "address": "Andijon sh., Fitrat ko'chasi, 3-uy",
        "contact": "+998 99 321 50 70",
        "menu_days_count": 22,
    },
]

NEWS_ITEMS = [
    {
        "date": "2026-04-05",
        "title": "Dietologiya platformasida yangi mavsumiy menyu moduli ishga tushdi",
        "text": "Endi tashkilotlar bahor, yoz, kuz va qish mavsumlari bo'yicha alohida taomnoma yurita oladi.",
    },
    {
        "date": "2026-04-02",
        "title": "Parhez bo'limida tezkor filtrlash imkoniyati qo'shildi",
        "text": "Parhez turlarini kod, nom va tavsif bo'yicha qidirish tezligi sezilarli oshirildi.",
    },
    {
        "date": "2026-03-28",
        "title": "Word hisobot eksporti yangilandi",
        "text": "Kunlik mahsulot sarfi va umumiy narx hisoboti endi yanada aniq va tartibli jadvalda eksport qilinadi.",
    },
    {
        "date": "2026-03-22",
        "title": "Tashkilot profili uchun yangi natijalar paneli qo'shildi",
        "text": "Profil sahifasida kunlik kaloriya, umumiy narx va taomlanuvchilar statistikasi vizual bloklarda ko'rsatiladi.",
    },
    {
        "date": "2026-03-15",
        "title": "Xavfsizlik va kirish boshqaruvi yaxshilandi",
        "text": "Tashkilotga biriktirilmagan foydalanuvchilar uchun yopiq bo'limlarga kirish cheklovlari kuchaytirildi.",
    },
]

class HomeView(TemplateView):
    template_name = "menu/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            organizations = list(
                Organization.objects.annotate(menu_days_count=Count("menuday")).order_by("name")[:6]
            )
            stats = self._get_stats()
            db_warning = ""
        except OperationalError:
            organizations = []
            stats = [
                {"label": "Modullar", "value": 11, "suffix": "ta"},
                {"label": "Ovqatlanish vaqti", "value": 5, "suffix": "ta"},
                {"label": "Hisob-kitob", "value": 4, "suffix": "ko'rsatkich"},
                {"label": "Deploy", "value": "Heroku", "suffix": "tayyor"},
            ]
            db_warning = "Ma'lumotlar bazasi hozircha vaqtincha o'qilmadi. Demo ko'rinish chiqarildi."
        if not organizations:
            organizations = DEMO_ORGANIZATIONS
            if not db_warning:
                db_warning = "Sayt demo ma'lumotlar bilan ko'rsatilmoqda."
        context["organizations"] = organizations
        context["stats"] = stats
        context["db_warning"] = db_warning
        context["about_points"] = HOME_FEATURES
        context["dietology_info"] = DIETOLOGY_INFO
        context["platform_features"] = PLATFORM_FEATURES
        return context

    def _get_stats(self):
        latest_day = MenuDay.objects.order_by("-date").first()
        if latest_day:
            return [
                {"label": "Tashkilotlar", "value": Organization.objects.count(), "suffix": "ta"},
                {"label": "Faol menyular", "value": MenuDay.objects.count(), "suffix": "kun"},
                {"label": "Taomlanuvchilar", "value": latest_day.people_count, "suffix": "nafar"},
                {"label": "Kunlik qiymat", "value": f"{latest_day.total_cost:.0f}", "suffix": "so'm"},
            ]

        return [
            {"label": "Modullar", "value": 11, "suffix": "ta"},
            {"label": "Ovqatlanish vaqti", "value": 5, "suffix": "ta"},
            {"label": "Hisob-kitob", "value": 4, "suffix": "ko'rsatkich"},
            {"label": "Deploy", "value": "Heroku", "suffix": "tayyor"},
        ]

class OrganizationListView(ListView):
    model = Organization
    template_name = "menu/organization_list.html"
    context_object_name = "organizations"
    queryset = Organization.objects.annotate(menu_days_count=Count("menuday")).order_by("name")

    def get_queryset(self):
        try:
            queryset = list(super().get_queryset())
            return queryset or DEMO_ORGANIZATIONS
        except OperationalError:
            return DEMO_ORGANIZATIONS


class NewsListView(TemplateView):
    template_name = "menu/news.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["news_items"] = NEWS_ITEMS
        return context


class OrganizationLoginView(LoginView):
    template_name = "menu/login.html"
    redirect_authenticated_user = False

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for field in form.fields.values():
            field.widget.attrs["class"] = "form-control"
        return form

    def get_success_url(self):
        return reverse_lazy("profile")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "menu/profile.html"
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not get_user_organization(request.user):
            return redirect("login")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        organization = get_user_organization(self.request.user)
        menu_days = (
            MenuDay.objects.filter(organization=organization)
            .select_related("season", "diet")
            .prefetch_related(
                Prefetch(
                    "entries",
                    queryset=MenuEntry.objects.select_related("mealtime", "dish"),
                )
            )
            .order_by("-date")
        )

        summaries = []
        summary_by_date = {}
        total_people = 0
        total_cost = Decimal("0")
        total_calories = 0
        for day in menu_days:
            mealtime_groups = defaultdict(list)
            for entry in day.entries.all():
                mealtime_groups[entry.mealtime.title].append(entry)
            day_cost = day.total_cost
            day_calories = day.total_calories
            total_people += day.people_count
            total_cost += day_cost
            total_calories += day_calories
            summary = {
                "day": day,
                "day_key": f"day-{day.id}",
                "groups": list(mealtime_groups.items()),
                "total_cost": day_cost,
                "total_calories": day_calories,
            }
            summaries.append(summary)
            summary_by_date[day.date] = summary

        today = timezone.localdate()
        week_start = today.fromordinal(today.toordinal() - today.weekday())
        week_dates = [week_start.fromordinal(week_start.toordinal() + index) for index in range(7)]
        selected_summary = summary_by_date.get(today)
        if not selected_summary:
            selected_summary = next(
                (
                    summary_by_date[day_date]
                    for day_date in week_dates
                    if day_date in summary_by_date
                ),
                None,
            )

        calendar_days = []
        selected_day_id = selected_summary["day_key"] if selected_summary else "today-empty"
        for day_date in week_dates:
            summary = summary_by_date.get(day_date)
            calendar_days.append(
                {
                    "date": day_date,
                    "summary": summary,
                    "is_current_month": True,
                    "is_today": day_date == today,
                    "is_selected": bool(day_date == today and (not summary or summary["day_key"] == selected_day_id)),
                }
            )
        week_summaries = [summary_by_date[day_date] for day_date in week_dates if day_date in summary_by_date]
        week_label = f"{week_dates[0].day}-{week_dates[-1].day} {MONTH_LABELS[week_dates[-1].month]} {week_dates[-1].year}"

        context["organization"] = organization
        context["menu_summaries"] = summaries
        context["week_menu_summaries"] = week_summaries
        context["calendar_weekdays"] = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Yak"]
        context["calendar_days"] = calendar_days
        context["calendar_month_label"] = week_label
        context["selected_day_id"] = selected_day_id
        context["today_summary"] = summary_by_date.get(today)
        context["profile_overview"] = {
            "days_count": len(summaries),
            "people_total": total_people,
            "cost_total": total_cost,
            "calories_total": total_calories,
        }
        context["price_form"] = PriceSourceForm()
        context["upload_form"] = MenuUploadForm()
        context["telegram_form"] = TelegramSettingsForm(
            initial={
                "chat_id": getattr(getattr(organization, "telegram_subscription", None), "chat_id", ""),
                "daily_digest": getattr(getattr(organization, "telegram_subscription", None), "daily_digest", True),
            }
        )
        context["monthly_cost_chart"] = monthly_cost_chart(organization)
        context["monthly_cost_total"] = monthly_cost_total(organization)
        context["top_products"] = top_cost_products(organization)
        context["requirements"] = product_requirement_summary(organization)[:12]
        context["price_history"] = PriceHistory.objects.filter(organization=organization).select_related("product")[:8]
        context["menu_alerts"] = MenuAlert.objects.filter(organization=organization, is_resolved=False)[:8]
        context["import_jobs"] = ImportJob.objects.filter(organization=organization)[:6]
        return context


class OrganizationActionMixin(LoginRequiredMixin):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        organization = get_user_organization(request.user)
        if not organization:
            return redirect("login")
        self.organization = organization
        return super().dispatch(request, *args, **kwargs)


class PriceUpdateView(OrganizationActionMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        form = PriceSourceForm(request.POST)
        if not form.is_valid():
            messages.error(request, form.errors.as_text())
            return redirect("profile")

        output = StringIO()
        try:
            call_command(
                "update_product_prices",
                "--korzinka",
                "--city",
                form.cleaned_data.get("city") or "Tashkent",
                "--organization",
                self.organization.name,
                stdout=output,
            )
        except CommandError as error:
            messages.error(request, f"Narx yangilashda xato: {error}")
        else:
            output_text = output.getvalue()
            if "Matched products: 0" in output_text:
                messages.warning(
                    request,
                    "Korzinka katalog sahifasida ochiq narx topilmadi. To'liq Korzinka Go qidiruvi uchun OPENAI_API_KEY sozlang.",
                )
            else:
                messages.success(request, "Narxlar Korzinka manbalari asosida avtomatik yangilandi.")
        return redirect("profile")


class MenuUploadView(OrganizationActionMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        form = MenuUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, form.errors.as_text())
            return redirect("profile")

        uploaded = form.cleaned_data["file"]
        suffix = Path(uploaded.name).suffix.lower()
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / uploaded.name
            with temp_path.open("wb") as destination:
                for chunk in uploaded.chunks():
                    destination.write(chunk)
            try:
                if suffix == ".zip":
                    call_command("import_menu_zip", "--zip-path", str(temp_path), "--organization", self.organization.name)
                elif suffix == ".xlsx":
                    call_command("import_menu_zip", "--folder-path", temp_dir, "--organization", self.organization.name)
                else:
                    raise CommandError("Faqat .zip yoki .xlsx fayl yuklang.")
            except CommandError as error:
                ImportJob.objects.create(
                    organization=self.organization,
                    job_type=ImportJob.JobType.EXCEL,
                    status=ImportJob.Status.FAILED,
                    source=uploaded.name,
                    summary=str(error),
                )
                messages.error(request, f"Import xatosi: {error}")
            else:
                create_upload_job(self.organization, uploaded, "Fayl kabinet orqali import qilindi.")
                messages.success(request, "Excel/ZIP import yakunlandi.")
        return redirect("profile")


class AlertBuildView(OrganizationActionMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        count = build_menu_alerts(self.organization)
        messages.success(request, f"{count} ta ogohlantirish yaratildi.")
        return redirect("profile")


class TelegramSettingsView(OrganizationActionMixin, TemplateView):
    def post(self, request, *args, **kwargs):
        form = TelegramSettingsForm(request.POST)
        if not form.is_valid():
            messages.error(request, form.errors.as_text())
            return redirect("profile")
        TelegramSubscription.objects.update_or_create(
            organization=self.organization,
            defaults={
                "chat_id": form.cleaned_data["chat_id"],
                "daily_digest": form.cleaned_data["daily_digest"],
                "is_active": True,
            },
        )
        messages.success(request, "Telegram sozlamasi saqlandi.")
        return redirect("profile")


def _telegram_menu_text(organization):
    menu_day = MenuDay.objects.filter(organization=organization).order_by("-date").first()
    if not menu_day:
        return f"{organization.name}: menyu ma'lumotlari hali yo'q."

    lines = [
        organization.name,
        f"Sana: {menu_day.date:%d.%m.%Y}",
        f"Taomlanuvchilar: {menu_day.people_count}",
        f"Umumiy xarajat: {menu_day.total_cost:.0f} so'm",
        f"Kishi boshiga: {menu_day.per_person_cost:.0f} so'm",
        "",
        "Retseptlar:",
    ]
    for entry in menu_day.entries.select_related("mealtime", "dish").all():
        lines.append(f"- {entry.mealtime.title}: {entry.dish.name} ({entry.portions} porsiya)")
    return "\n".join(lines)


def _parse_telegram_credentials(text: str):
    cleaned = text.strip()
    if not cleaned:
        return None

    command_match = re.match(r"^/?login(?:\s+(.+))?$", cleaned, flags=re.IGNORECASE | re.DOTALL)
    if command_match:
        value = (command_match.group(1) or "").strip()
        parts = value.split(maxsplit=1)
        return tuple(parts) if len(parts) == 2 else None

    login_match = re.search(r"(?:login|username)\s*[:=]\s*(\S+)", cleaned, flags=re.IGNORECASE)
    password_match = re.search(r"(?:parol|password)\s*[:=]\s*(\S+)", cleaned, flags=re.IGNORECASE)
    if login_match and password_match:
        return login_match.group(1), password_match.group(1)

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    if len(lines) == 2 and not any(line.startswith("/") for line in lines):
        return lines[0], lines[1]

    parts = cleaned.split()
    if len(parts) == 2 and not cleaned.startswith("/"):
        return parts[0], parts[1]
    return None


def _connect_telegram_login(chat_id: str, text: str) -> bool:
    credentials = _parse_telegram_credentials(text)
    if not credentials:
        return False
    username, password = credentials
    user = authenticate(username=username, password=password)
    organization = get_user_organization(user) if user else None
    if not organization:
        send_telegram_chat_message(chat_id, "Login yoki parol noto'g'ri, yoki foydalanuvchi tashkilotga bog'lanmagan.")
        return True
    TelegramSubscription.objects.update_or_create(
        organization=organization,
        defaults={"chat_id": chat_id, "is_active": True, "daily_digest": True},
    )
    send_telegram_chat_message(chat_id, f"Ulandi: {organization.name}\nEndi /today yoki /summary yuboring.")
    return True


@method_decorator(csrf_exempt, name="dispatch")
class TelegramWebhookView(TemplateView):
    def post(self, request, *args, **kwargs):
        try:
            payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return JsonResponse({"ok": False}, status=400)

        message = payload.get("message") or payload.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = str(chat.get("id") or "")
        text = (message.get("text") or "").strip()
        if not chat_id:
            return JsonResponse({"ok": True})

        if text.startswith(("/start", "/help")):
            send_telegram_chat_message(
                chat_id,
                "Dietologiya botiga xush kelibsiz.\n"
                "Sayt login/paroli bilan ulanish: /login login parol\n"
                "Yoki login va parolni 2 qatorda yuboring.\n"
                "Oxirgi menyu va xarajat: /today\n"
                "Qisqa xulosa: /summary",
            )
            return JsonResponse({"ok": True})

        if text.startswith("/login"):
            if not _connect_telegram_login(chat_id, text):
                send_telegram_chat_message(chat_id, "Format: /login login parol\nYoki login va parolni 2 qatorda yuboring.")
                return JsonResponse({"ok": True})
            return JsonResponse({"ok": True})

        subscription = TelegramSubscription.objects.filter(chat_id=chat_id, is_active=True).select_related("organization").first()
        if not subscription:
            if _connect_telegram_login(chat_id, text):
                return JsonResponse({"ok": True})
            send_telegram_chat_message(chat_id, "Avval sayt login/paroli bilan ulaning: /login login parol")
            return JsonResponse({"ok": True})

        if text.startswith(("/today", "/summary")):
            send_telegram_chat_message(chat_id, _telegram_menu_text(subscription.organization))
        else:
            send_telegram_chat_message(chat_id, "Buyruqlar: /today, /summary")
        return JsonResponse({"ok": True})


class TelegramWebhookSetupView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponse("Ruxsat yo'q", status=403, content_type="text/plain")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not os.environ.get("TELEGRAM_BOT_TOKEN"):
            return HttpResponse("TELEGRAM_BOT_TOKEN sozlanmagan.", status=400, content_type="text/plain")
        webhook_url = request.build_absolute_uri(reverse("telegram_webhook"))
        output = StringIO()
        try:
            call_command("set_telegram_webhook", "--url", webhook_url, stdout=output)
        except CommandError as error:
            return HttpResponse(f"Webhook sozlashda xato: {error}", status=400, content_type="text/plain")
        status = telegram_api_call("getWebhookInfo")
        return HttpResponse(
            "Telegram webhook tayyor.\n"
            f"URL: {webhook_url}\n\n"
            f"Holat:\n{json.dumps(status, ensure_ascii=False, indent=2)}",
            content_type="text/plain",
        )


class TelegramWebhookStatusView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return HttpResponse("Ruxsat yo'q", status=403, content_type="text/plain")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        bot = telegram_api_call("getMe")
        webhook = telegram_api_call("getWebhookInfo")
        return HttpResponse(
            json.dumps({"bot": bot, "webhook": webhook}, ensure_ascii=False, indent=2),
            content_type="application/json",
        )


class LatestMenuWordExportView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        organization = get_user_organization(request.user)
        if not organization:
            return redirect("login")
        menu_day = (
            MenuDay.objects.filter(organization=organization)
            .prefetch_related("entries__dish__ingredients__product")
            .order_by("-date")
            .first()
        )
        if not menu_day:
            return redirect("profile")

        totals = defaultdict(lambda: {"quantity": Decimal("0"), "cost": Decimal("0"), "unit": "g"})
        for entry in menu_day.entries.all():
            for ingredient in entry.dish.ingredients.select_related("product").all():
                bucket = totals[ingredient.product.name]
                bucket["unit"] = ingredient.product.unit
                bucket["quantity"] += Decimal(ingredient.grams) * Decimal(entry.portions)
                bucket["cost"] += ingredient.cost_amount * Decimal(entry.portions)

        rows = []
        total_cost = Decimal("0")
        for product_name in sorted(totals):
            item = totals[product_name]
            total_cost += item["cost"]
            quantity_kg = (item["quantity"] / Decimal("1000")).quantize(Decimal("0.001"))
            rows.append(
                [
                    product_name,
                    f"{quantity_kg}",
                    "kg",
                    f"{item['cost'].quantize(Decimal('1'))} so'm",
                ]
            )
        rows.append(["Jami", "", "", f"{total_cost.quantize(Decimal('1'))} so'm"])

        file_name = f"{organization.name}-{menu_day.date.isoformat()}-bir-kunlik-xarajatlar.docx"
        content = build_docx(
            title=f"{organization.name} uchun bir kunlik xarajatlar hisoboti",
            subtitle=f"Sana: {menu_day.date.isoformat()}",
            headers=["Mahsulot", "Miqdor", "Birlik", "Jami narx"],
            rows=rows,
        )
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response


class AllMenuWordExportView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        organization = get_user_organization(request.user)
        if not organization:
            return redirect("login")
        menu_days = list(
            MenuDay.objects.filter(organization=organization)
            .prefetch_related("entries__dish__ingredients__product")
            .order_by("date")
        )
        if not menu_days:
            return redirect("profile")

        totals = defaultdict(lambda: {"quantity": Decimal("0"), "cost": Decimal("0"), "unit": "g"})
        for menu_day in menu_days:
            for entry in menu_day.entries.all():
                for ingredient in entry.dish.ingredients.select_related("product").all():
                    bucket = totals[ingredient.product.name]
                    bucket["unit"] = ingredient.product.unit
                    bucket["quantity"] += Decimal(ingredient.grams) * Decimal(entry.portions)
                    bucket["cost"] += ingredient.cost_amount * Decimal(entry.portions)

        rows = []
        total_cost = Decimal("0")
        for product_name in sorted(totals):
            item = totals[product_name]
            total_cost += item["cost"]
            quantity_kg = (item["quantity"] / Decimal("1000")).quantize(Decimal("0.001"))
            rows.append(
                [
                    product_name,
                    f"{quantity_kg}",
                    "kg",
                    f"{item['cost'].quantize(Decimal('1'))} so'm",
                ]
            )
        rows.append(["Jami", "", "", f"{total_cost.quantize(Decimal('1'))} so'm"])

        start_date = menu_days[0].date.isoformat()
        end_date = menu_days[-1].date.isoformat()
        date_range = start_date if start_date == end_date else f"{start_date} - {end_date}"
        file_name = f"{organization.name}-{start_date}-{end_date}-barcha-xarajatlar.docx"
        content = build_docx(
            title=f"{organization.name} uchun barcha xarajatlar hisoboti",
            subtitle=f"Davr: {date_range}. Menyu kunlari: {len(menu_days)}",
            headers=["Mahsulot", "Miqdor", "Birlik", "Jami narx"],
            rows=rows,
        )
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("home"))


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return HttpResponse("unhealthy", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")
