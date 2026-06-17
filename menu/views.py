from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import tempfile
from io import StringIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.db import OperationalError
from django.db.models import Count, Prefetch
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import ListView, TemplateView

from .docx_export import build_docx
from .forms import AIAgentForm, MenuUploadForm, PriceSourceForm
from .models import AISuggestion, ImportJob, MenuAlert, MenuDay, MenuEntry, Organization, PriceHistory
from .spreadsheet_export import build_xlsx
from .services import (
    AIAgentError,
    build_menu_alerts,
    create_upload_job,
    generate_ai_agent_response,
    get_ai_agent_config,
    get_user_organization,
    inspect_menu_upload,
    monthly_cost_chart,
    monthly_cost_total,
    product_requirement_summary,
    top_cost_products,
    user_has_org_permission,
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

SEASON_PROFILE_ORDER = ("winter", "spring", "summer", "autumn")


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
        "text": "Yil va mavsum bo'yicha menyularni rejalang. Har bir fasl uchun alohida taom ro'yxati.",
        "icon": "seasonal-menu",
    },
    {
        "index": "02",
        "title": "Parhez turlari",
        "text": "Standart, laktosasiz va boshqa maxsus parhez rejalarini boshqaring.",
        "icon": "diet",
    },
    {
        "index": "03",
        "title": "Taom tarkibi",
        "text": "Har bir taom uchun retsept, ingredientlar va grammovkani kiriting.",
        "icon": "recipe",
    },
    {
        "index": "04",
        "title": "Oziq qiymati",
        "text": "Oqsil, yog', uglevod va kaloriyani avtomatik hisoblang. Norma bilan solishtiring.",
        "icon": "nutrition",
    },
    {
        "index": "05",
        "title": "Narx hisob-kitobi",
        "text": "Umumiy va kishi boshiga xarajatni real vaqtda ko'ring. Oylik dinamika grafigi.",
        "icon": "cost",
    },
    {
        "index": "06",
        "title": "Word hisobotlar",
        "text": "Bir kunlik yoki butun davr uchun xarajat hisobotini Word formatida yuklab oling.",
        "icon": "word-report",
    },
    {
        "index": "07",
        "title": "Excel/ZIP import",
        "text": "Menyu va mahsulot ma'lumotlarini Excel yoki ZIP arxivdan tezda import qiling.",
        "icon": "import",
    },
    {
        "index": "08",
        "title": "Menyu ogohlantirishlari",
        "text": "Laktosiz menyuda sut mahsuloti yoki yuqori xarajat holatlari haqida ogohlantirish.",
        "icon": "alerts",
    },
    {
        "index": "09",
        "title": "Narxlar tarixi",
        "text": "Har bir mahsulot uchun narx o'zgarishlarini kuzating va Korzinka orqali yangilang.",
        "icon": "price-history",
    },
    {
        "index": "10",
        "title": "Mahsulot ehtiyoji",
        "text": "Menyu asosida kerakli mahsulotlar ro'yxatini avtomatik hisoblang.",
        "icon": "requirements",
    },
    {
        "index": "11",
        "title": "Admin panel",
        "text": "Global administrator barcha tashkilotlar, foydalanuvchilar va tizim sozlamalarini boshqaradi.",
        "icon": "admin",
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
        context["organizations"] = organizations[:4]
        context["stats"] = stats
        context["db_warning"] = db_warning
        context["about_points"] = HOME_FEATURES
        context["dietology_info"] = DIETOLOGY_INFO
        context["platform_features"] = PLATFORM_FEATURES
        context["news_items"] = NEWS_ITEMS[:6]
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
        menu_days = list(
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
        season_buckets = {}
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
            if day.season_id:
                season_key = day.season.name
                bucket = season_buckets.setdefault(
                    season_key,
                    {
                        "key": season_key,
                        "label": day.season.get_name_display(),
                        "days_count": 0,
                        "people_total": 0,
                        "cost_total": Decimal("0"),
                        "calories_total": 0,
                        "latest_date": day.date,
                    },
                )
                bucket["days_count"] += 1
                bucket["people_total"] += day.people_count
                bucket["cost_total"] += day_cost
                bucket["calories_total"] += day_calories
                if day.date > bucket["latest_date"]:
                    bucket["latest_date"] = day.date

        today = timezone.localdate()
        requested_week = self.request.GET.get("week", "")
        try:
            requested_reference = date.fromisoformat(requested_week)
        except ValueError:
            current_week_start = today - timedelta(days=today.weekday())
            current_week_end = current_week_start + timedelta(days=6)
            has_current_week_menu = any(
                current_week_start <= day.date <= current_week_end
                for day in menu_days
            )
            requested_reference = today if has_current_week_menu or not menu_days else menu_days[0].date

        week_start = requested_reference - timedelta(days=requested_reference.weekday())
        week_end = week_start + timedelta(days=6)
        calendar_dates = [week_start + timedelta(days=index) for index in range(7)]
        week_summaries = sorted(
            (
                summary
                for summary in summaries
                if week_start <= summary["day"].date <= week_end
            ),
            key=lambda summary: summary["day"].date,
        )

        selected_summary = None
        requested_day = self.request.GET.get("day", "")
        try:
            requested_date = date.fromisoformat(requested_day)
        except ValueError:
            requested_date = None
        if requested_date in calendar_dates:
            selected_summary = summary_by_date.get(requested_date)
        if not selected_summary and week_start <= today <= week_end:
            selected_summary = summary_by_date.get(today)
        if not selected_summary and week_summaries:
            selected_summary = week_summaries[0]

        selected_day_id = selected_summary["day_key"] if selected_summary else ""
        calendar_days = []
        for day_date in calendar_dates:
            summary = summary_by_date.get(day_date)
            calendar_days.append(
                {
                    "date": day_date,
                    "summary": summary,
                    "is_today": day_date == today,
                    "is_selected": bool(summary and summary["day_key"] == selected_day_id),
                }
            )

        ordered_season_keys = [
            key for key in SEASON_PROFILE_ORDER if key in season_buckets
        ] + sorted(key for key in season_buckets if key not in SEASON_PROFILE_ORDER)
        season_summaries = []
        for season_key in ordered_season_keys:
            season = season_buckets[season_key]
            season["week_reference"] = season["latest_date"].isoformat()
            season["day_reference"] = season["latest_date"].isoformat()
            season_summaries.append(season)

        context["organization"] = organization
        context["menu_summaries"] = summaries
        context["season_summaries"] = season_summaries
        context["calendar_menu_summaries"] = week_summaries
        context["calendar_weekdays"] = ["Du", "Se", "Cho", "Pa", "Ju", "Sha", "Yak"]
        context["calendar_days"] = calendar_days
        context["calendar_month_label"] = (
            f"{week_start.day} {MONTH_LABELS[week_start.month]} - "
            f"{week_end.day} {MONTH_LABELS[week_end.month]} {week_end.year}"
        )
        context["calendar_prev_week"] = (week_start - timedelta(days=7)).isoformat()
        context["calendar_next_week"] = (week_start + timedelta(days=7)).isoformat()
        context["selected_day_id"] = selected_day_id
        context["selected_summary"] = selected_summary
        context["profile_overview"] = {
            "days_count": len(summaries),
            "people_total": total_people,
            "cost_total": total_cost,
            "calories_total": total_calories,
        }
        context["price_form"] = PriceSourceForm()
        context["upload_form"] = MenuUploadForm()
        context["ai_agent_form"] = AIAgentForm()
        context["ai_agent_config"] = get_ai_agent_config()
        context["ai_suggestions"] = AISuggestion.objects.filter(organization=organization)[:5]
        context["monthly_cost_chart"] = monthly_cost_chart(organization)
        context["monthly_cost_total"] = monthly_cost_total(organization)
        context["top_products"] = top_cost_products(organization)
        context["requirements"] = product_requirement_summary(organization)[:12]
        context["price_history"] = PriceHistory.objects.filter(organization=organization).select_related("product")[:8]
        context["menu_alerts"] = MenuAlert.objects.filter(organization=organization, is_resolved=False)[:8]
        context["can_manage_menu"] = user_has_org_permission(self.request.user, "manage_menu", organization)
        context["can_manage_prices"] = user_has_org_permission(self.request.user, "manage_prices", organization)
        context["can_view_reports"] = user_has_org_permission(self.request.user, "view_reports", organization)
        return context


class OrganizationActionMixin(LoginRequiredMixin):
    login_url = reverse_lazy("login")
    required_permission = None

    def dispatch(self, request, *args, **kwargs):
        organization = get_user_organization(request.user)
        if not organization:
            return redirect("login")
        self.organization = organization
        if self.required_permission and not user_has_org_permission(request.user, self.required_permission, organization):
            messages.error(request, "Bu amal uchun rolingizda ruxsat yo'q.")
            return redirect("profile")
        return super().dispatch(request, *args, **kwargs)


class PriceUpdateView(OrganizationActionMixin, TemplateView):
    required_permission = "manage_prices"

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


class MenuUploadPreviewView(OrganizationActionMixin, TemplateView):
    required_permission = "manage_menu"
    template_name = "menu/import_preview.html"

    def post(self, request, *args, **kwargs):
        form = MenuUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            messages.error(request, form.errors.as_text())
            return redirect("profile")

        uploaded = form.cleaned_data["file"]
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / uploaded.name
            with temp_path.open("wb") as destination:
                for chunk in uploaded.chunks():
                    destination.write(chunk)
            preview = inspect_menu_upload(temp_path)

        return self.render_to_response({"preview": preview, "organization": self.organization})


class MenuUploadView(OrganizationActionMixin, TemplateView):
    required_permission = "manage_menu"

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
    required_permission = "manage_menu"

    def post(self, request, *args, **kwargs):
        count = build_menu_alerts(self.organization)
        messages.success(request, f"{count} ta ogohlantirish yaratildi.")
        return redirect("profile")


class AIAgentView(OrganizationActionMixin, TemplateView):
    required_permission = "view_reports"

    def post(self, request, *args, **kwargs):
        form = AIAgentForm(request.POST)
        if not form.is_valid():
            messages.error(request, "AI agent savoli 5 dan 2000 belgigacha bo'lishi kerak.")
            return redirect("profile")

        try:
            generate_ai_agent_response(self.organization, form.cleaned_data["prompt"])
        except AIAgentError as error:
            messages.error(request, f"AI agent xatosi: {error}")
        else:
            messages.success(request, "AI agent javobi tayyorlandi.")
        return redirect("profile")


class LatestMenuWordExportView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        organization = get_user_organization(request.user)
        if not organization:
            return redirect("login")
        if not user_has_org_permission(request.user, "view_reports", organization):
            messages.error(request, "Hisobotlarni ko'rish uchun ruxsat yo'q.")
            return redirect("profile")
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
        if not user_has_org_permission(request.user, "view_reports", organization):
            messages.error(request, "Hisobotlarni ko'rish uchun ruxsat yo'q.")
            return redirect("profile")
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


class AllMenuExcelExportView(LoginRequiredMixin, TemplateView):
    login_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        organization = get_user_organization(request.user)
        if not organization:
            return redirect("login")
        if not user_has_org_permission(request.user, "view_reports", organization):
            messages.error(request, "Hisobotlarni ko'rish uchun ruxsat yo'q.")
            return redirect("profile")

        menu_days = list(
            MenuDay.objects.filter(organization=organization)
            .prefetch_related("entries__dish__ingredients__product")
            .order_by("date")
        )
        if not menu_days:
            return redirect("profile")

        rows = [["Sana", "Ovqatlanish vaqti", "Taom", "Porsiya", "Kaloriya", "Narx"]]
        total_cost = Decimal("0")
        total_calories = 0
        for menu_day in menu_days:
            for entry in menu_day.entries.select_related("mealtime", "dish").all():
                total_cost += entry.total_cost
                total_calories += entry.total_calories
                rows.append(
                    [
                        menu_day.date.isoformat(),
                        entry.mealtime.title,
                        entry.dish.name,
                        entry.portions,
                        entry.total_calories,
                        f"{entry.total_cost.quantize(Decimal('1'))}",
                    ]
                )
        rows.append(["Jami", "", "", "", total_calories, f"{total_cost.quantize(Decimal('1'))}"])

        start_date = menu_days[0].date.isoformat()
        end_date = menu_days[-1].date.isoformat()
        file_name = f"{organization.name}-{start_date}-{end_date}-barcha-xarajatlar.xlsx"
        content = build_xlsx(rows, "Xarajatlar")
        response = HttpResponse(
            content,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
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
