import json
from datetime import date
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from .forms import MenuUploadForm
from .models import AISuggestion, MenuDay, MenuEntry, Organization, Product, Season
from .org_admin import OrganizationProductAdmin, organization_admin_site
from .services import generate_ai_agent_response


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class AIAgentServiceTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="director", password="test-pass-123")
        self.organization = Organization.objects.create(name="Birinchi tashkilot", owner=self.user)
        self.other_organization = Organization.objects.create(name="Ikkinchi tashkilot")
        Product.objects.create(name="Guruch", organization=self.organization)
        Product.objects.create(name="Maxfiy mahsulot", organization=self.other_organization)

    @patch.dict(
        "os.environ",
        {
            "AI_AGENT_PROVIDER": "gemini",
            "GEMINI_API_KEY": "test-key",
            "GEMINI_AGENT_MODEL": "gemini-test",
        },
        clear=False,
    )
    @patch("menu.services.urlopen")
    def test_gemini_agent_only_receives_current_organization_context(self, mocked_urlopen):
        mocked_urlopen.return_value = FakeHTTPResponse(
            {"candidates": [{"content": {"parts": [{"text": "Tahlil tayyor."}]}}]}
        )

        suggestion = generate_ai_agent_response(self.organization, "Xarajatlarni tahlil qil")

        self.assertEqual(suggestion.response, "Tahlil tayyor.")
        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data.decode("utf-8"))
        request_text = payload["contents"][0]["parts"][0]["text"]
        self.assertIn("Birinchi tashkilot", request_text)
        self.assertIn("Guruch", request_text)
        self.assertNotIn("Ikkinchi tashkilot", request_text)
        self.assertNotIn("Maxfiy mahsulot", request_text)


class AIAgentViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="owner", password="test-pass-123")
        self.organization = Organization.objects.create(name="Test tashkilot", owner=self.user)
        self.client.force_login(self.user)

    @patch("menu.views.generate_ai_agent_response")
    def test_agent_endpoint_uses_logged_in_users_organization(self, generate_response):
        generate_response.return_value = Mock(spec=AISuggestion)

        response = self.client.post(
            reverse("profile_ai_agent"),
            {"prompt": "Menyuni qisqacha tahlil qil"},
        )

        self.assertRedirects(response, reverse("profile"))
        generate_response.assert_called_once_with(
            self.organization,
            "Menyuni qisqacha tahlil qil",
        )

    def test_agent_endpoint_rejects_short_prompt(self):
        response = self.client.post(reverse("profile_ai_agent"), {"prompt": "yoq"})

        self.assertRedirects(response, reverse("profile"))
        self.assertFalse(AISuggestion.objects.exists())


class OrganizationCabinetTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="cabinet-owner", password="test-pass-123")
        self.organization = Organization.objects.create(name="Kabinet tashkiloti", owner=self.user)
        self.other_organization = Organization.objects.create(name="Boshqa tashkilot")
        self.own_product = Product.objects.create(name="Own product", organization=self.organization)
        Product.objects.create(name="Other product", organization=self.other_organization)
        self.client.force_login(self.user)

    def test_organization_admin_url_opens_real_cabinet(self):
        response = self.client.get(reverse("organization_admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.resolver_match.namespace, "organization_admin")
        self.assertTemplateUsed(response, "admin/index.html")

    def test_organization_admin_queryset_is_tenant_scoped(self):
        request = RequestFactory().get(reverse("organization_admin:menu_product_changelist"))
        request.user = self.user
        model_admin = OrganizationProductAdmin(Product, organization_admin_site)

        products = list(model_admin.get_queryset(request))

        self.assertEqual(products, [self.own_product])


class ProfileCalendarTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="calendar-owner", password="test-pass-123")
        self.organization = Organization.objects.create(name="Kalendar tashkiloti", owner=self.user)
        self.season = Season.objects.create(name=Season.SeasonName.SPRING, year=2026)
        self.first_day = MenuDay.objects.create(
            organization=self.organization,
            season=self.season,
            date=date(2026, 5, 2),
            people_count=10,
        )
        self.second_day = MenuDay.objects.create(
            organization=self.organization,
            season=self.season,
            date=date(2026, 5, 5),
            people_count=12,
        )
        self.client.force_login(self.user)

    def test_profile_defaults_to_latest_menu_week(self):
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["calendar_month_label"], "4 May - 10 May 2026")
        self.assertEqual(len(response.context["calendar_days"]), 7)
        self.assertEqual(response.context["selected_day_id"], f"day-{self.second_day.id}")
        self.assertContains(response, f'data-day-trigger="day-{self.second_day.id}"')
        self.assertContains(response, f'data-day-panel="day-{self.second_day.id}"')
        self.assertNotContains(response, f'data-day-trigger="day-{self.first_day.id}"')

    def test_requested_calendar_day_is_selected(self):
        response = self.client.get(
            reverse("profile"),
            {"week": "2026-05-04", "day": "2026-05-05"},
        )

        self.assertEqual(response.context["selected_day_id"], f"day-{self.second_day.id}")

    def test_previous_week_can_be_opened(self):
        response = self.client.get(
            reverse("profile"),
            {"week": "2026-04-27", "day": "2026-05-02"},
        )

        self.assertEqual(response.context["selected_day_id"], f"day-{self.first_day.id}")
        self.assertContains(response, f'data-day-trigger="day-{self.first_day.id}"')


class DemoSeedDataTests(TestCase):
    def test_soglom_avlod_demo_contains_all_four_seasons(self):
        call_command("seed_demo_data", stdout=StringIO())

        organization = Organization.objects.get(name="Sog'lom Avlod MTT")
        expected_seasons = {"winter", "spring", "summer", "autumn"}
        actual_seasons = set(
            MenuDay.objects.filter(organization=organization).values_list("season__name", flat=True)
        )
        self.assertTrue(expected_seasons.issubset(actual_seasons))
        for season_name in expected_seasons:
            self.assertGreaterEqual(
                MenuDay.objects.filter(organization=organization, season__name=season_name).count(),
                5,
            )

        dish_names = set(
            MenuEntry.objects.filter(menu_day__organization=organization).values_list("dish__name", flat=True)
        )
        self.assertTrue(
            {
                "Qovoqli sutli suli bo'tqasi",
                "Moshli bahor sho'rva",
                "Yozgi tovuqli salat",
                "Tovuqli kuzgi dimlama",
            }.issubset(dish_names)
        )


class MenuUploadFormTests(TestCase):
    @override_settings(MENU_IMPORT_MAX_BYTES=4)
    def test_rejects_oversized_upload(self):
        form = MenuUploadForm(
            files={"file": SimpleUploadedFile("menu.xlsx", b"12345")}
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Fayl hajmi", form.errors["file"][0])
