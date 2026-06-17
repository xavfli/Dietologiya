import os
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from menu.models import (
    Diet,
    Dish,
    DishIngredient,
    ImportJob,
    MealTime,
    MenuAlert,
    MenuDay,
    MenuEntry,
    Organization,
    OrganizationMember,
    PriceHistory,
    Product,
    Season,
)


DEMO_PASSWORD = "OrgDemo2026!"

DEMO_ORGANIZATIONS = [
    {
        "name": "Sog'lom Avlod MTT",
        "username": "soglom_avlod",
        "first_name": "Soglom",
        "last_name": "Avlod",
        "email": "soglom.avlod@example.com",
        "address": "Toshkent sh., Yunusobod tumani, 12-mavze",
        "contact": "+998 90 120 45 67",
        "people_base": 120,
        "menu_days": 28,
    },
    {
        "name": "Mehribonlik Ta'lim Markazi",
        "username": "mehribonlik_talim",
        "first_name": "Mehribonlik",
        "last_name": "Markazi",
        "email": "mehribonlik@example.com",
        "address": "Samarqand sh., Amir Temur ko'chasi, 18-uy",
        "contact": "+998 93 510 22 11",
        "people_base": 180,
        "menu_days": 18,
    },
    {
        "name": "Ishonch Klinik Sanatoriysi",
        "username": "ishonch_sanatoriy",
        "first_name": "Ishonch",
        "last_name": "Sanatoriy",
        "email": "ishonch@example.com",
        "address": "Buxoro vil., G'ijduvon tumani, Mustaqillik ko'chasi",
        "contact": "+998 91 778 30 40",
        "people_base": 95,
        "menu_days": 31,
    },
    {
        "name": "Baraka Catering Service",
        "username": "baraka_catering",
        "first_name": "Baraka",
        "last_name": "Catering",
        "email": "baraka@example.com",
        "address": "Farg'ona sh., Alisher Navoiy ko'chasi, 7-uy",
        "contact": "+998 88 245 88 00",
        "people_base": 260,
        "menu_days": 15,
    },
    {
        "name": "Nurli Kelajak Maktabi",
        "username": "nurli_kelajak",
        "first_name": "Nurli",
        "last_name": "Kelajak",
        "email": "nurli@example.com",
        "address": "Namangan sh., Boburshoh ko'chasi, 25-uy",
        "contact": "+998 94 600 14 14",
        "people_base": 210,
        "menu_days": 27,
    },
    {
        "name": "Sihat Hospital Oshxonasi",
        "username": "sihat_hospital",
        "first_name": "Sihat",
        "last_name": "Hospital",
        "email": "sihat@example.com",
        "address": "Andijon sh., Fitrat ko'chasi, 3-uy",
        "contact": "+998 99 321 50 70",
        "people_base": 140,
        "menu_days": 22,
    },
]

ROLE_USERS = [
    {
        "username": "soglom_oshpaz",
        "first_name": "Oshpaz",
        "last_name": "Demo",
        "email": "oshpaz@example.com",
        "role": OrganizationMember.Role.COOK,
        "can_manage_menu": True,
        "can_manage_prices": False,
        "can_view_reports": True,
    },
    {
        "username": "soglom_hisobchi",
        "first_name": "Hisobchi",
        "last_name": "Demo",
        "email": "hisobchi@example.com",
        "role": OrganizationMember.Role.ACCOUNTANT,
        "can_manage_menu": False,
        "can_manage_prices": True,
        "can_view_reports": True,
    },
    {
        "username": "soglom_kuzatuvchi",
        "first_name": "Kuzatuvchi",
        "last_name": "Demo",
        "email": "kuzatuvchi@example.com",
        "role": OrganizationMember.Role.VIEWER,
        "can_manage_menu": False,
        "can_manage_prices": False,
        "can_view_reports": True,
    },
]

PRODUCT_DATA = [
    ("Suli yormasi", "g", "12.00", "6.00", "60.00", 360, "28000.00"),
    ("Sut", "ml", "3.20", "3.60", "4.70", 64, "12000.00"),
    ("Tovuq filesi", "g", "23.00", "2.00", "0.00", 110, "58000.00"),
    ("Kartoshka", "g", "2.00", "0.40", "17.00", 77, "9000.00"),
    ("Sabzi", "g", "1.30", "0.10", "7.00", 35, "7000.00"),
    ("Guruch", "g", "7.00", "0.60", "78.00", 344, "21000.00"),
    ("Olma", "g", "0.40", "0.40", "11.00", 47, "18000.00"),
    ("Yogurt", "g", "4.50", "3.20", "6.00", 75, "26000.00"),
    ("Baliq filesi", "g", "19.00", "5.00", "0.00", 120, "76000.00"),
    ("Brokkoli", "g", "3.00", "0.40", "5.00", 34, "24000.00"),
    ("Mol go'shti", "g", "20.00", "12.00", "0.00", 190, "88000.00"),
    ("Tuxum", "g", "13.00", "11.00", "1.00", 155, "22000.00"),
    ("Grechka", "g", "13.00", "3.00", "72.00", 343, "26000.00"),
    ("Makaron", "g", "11.00", "1.50", "72.00", 350, "18000.00"),
    ("Karam", "g", "1.30", "0.10", "6.00", 27, "6000.00"),
    ("Bodring", "g", "0.80", "0.10", "3.00", 16, "12000.00"),
    ("Pomidor", "g", "0.90", "0.20", "4.00", 18, "16000.00"),
    ("Banan", "g", "1.10", "0.30", "23.00", 89, "24000.00"),
    ("Non", "g", "8.00", "2.00", "49.00", 250, "7000.00"),
    ("O'simlik yog'i", "ml", "0.00", "100.00", "0.00", 884, "24000.00"),
    ("Qatiq", "ml", "3.00", "2.50", "4.00", 56, "13000.00"),
    ("Loviya", "g", "21.00", "1.00", "63.00", 333, "30000.00"),
    ("Qovoq", "g", "1.00", "0.10", "6.50", 26, "8500.00"),
    ("Lavlagi", "g", "1.60", "0.20", "10.00", 43, "9000.00"),
    ("Nok", "g", "0.40", "0.10", "15.00", 57, "19000.00"),
    ("Ko'kat", "g", "3.00", "0.80", "6.00", 40, "18000.00"),
    ("Mosh", "g", "24.00", "1.20", "63.00", 347, "32000.00"),
    ("Shaftoli", "g", "0.90", "0.30", "10.00", 39, "22000.00"),
    ("Tarvuz", "g", "0.60", "0.20", "8.00", 30, "6500.00"),
]

MEAL_TIMES = [
    ("first_breakfast", "1-nonushta", 1),
    ("second_breakfast", "2-nonushta", 2),
    ("lunch", "Tushlik", 3),
    ("buffet", "Bufet mahsulotlari", 4),
    ("dinner", "Kechki ovqat", 5),
]

SOGLOM_SEASONAL_MENU_DATES = {
    "winter": [(1, 12), (1, 13), (1, 14), (1, 15), (1, 16)],
    "spring": [(3, 16), (3, 17), (3, 18), (3, 19), (3, 20)],
    "summer": [(6, 15), (6, 16), (6, 17), (6, 18), (6, 19)],
    "autumn": [(9, 14), (9, 15), (9, 16), (9, 17), (9, 18)],
}

SOGLOM_SEASONAL_MENU_PLANS = {
    "winter": [
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Qovoqli sutli suli bo'tqasi", "Issiq va to'yimli nonushta"),
                ("second_breakfast", "Olma va nokli qatiq", "Vitaminli yengil tamaddi"),
                ("lunch", "Mol go'shtli qishki dimlama", "Issiq asosiy taom"),
                ("buffet", "Grechkali sabzi garniri", "Murakkab uglevodli garnir"),
                ("dinner", "Baliqli karam salati", "Yengil oqsilli kechki ovqat"),
            ],
        },
        {
            "diet": "HIGH_PROTEIN",
            "entries": [
                ("first_breakfast", "Tuxumli sabzavot salati", "Oqsilga boy nonushta"),
                ("second_breakfast", "Qatiqli banan", "Yumshoq tamaddi"),
                ("lunch", "Grechkali mol go'shti", "Oqsil va temirga boy tushlik"),
                ("buffet", "Qaynatilgan guruch", "Qo'shimcha garnir"),
                ("dinner", "Qovoqli tovuq sho'rva", "Hazmi yengil issiq taom"),
            ],
        },
        {
            "diet": "LOW_SALT",
            "entries": [
                ("first_breakfast", "Qovoqli sutli suli bo'tqasi", "Tuzsizroq nonushta"),
                ("second_breakfast", "Olma va nokli qatiq", "Mevali tamaddi"),
                ("lunch", "Moshli qishki sho'rva", "To'yimli dukkakli sho'rva"),
                ("buffet", "Lavlagili karam salati", "Rangli sabzavotli qo'shimcha"),
                ("dinner", "Bug'da pishgan baliq va brokkoli", "Yengil oqsilli ovqat"),
            ],
        },
        {
            "diet": "LITE",
            "entries": [
                ("first_breakfast", "Sutli suli bo'tqasi", "Yengil nonushta"),
                ("second_breakfast", "Mevali yogurt", "Mevali tamaddi"),
                ("lunch", "Tovuqli sabzavot sho'rva", "Issiq tushlik"),
                ("buffet", "Grechkali sabzi garniri", "Qo'shimcha garnir"),
                ("dinner", "Baliqli karam salati", "Kechki yengil taom"),
            ],
        },
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Qovoqli sutli suli bo'tqasi", "Hafta yakuni nonushtasi"),
                ("second_breakfast", "Olma va nokli qatiq", "Vitaminli tamaddi"),
                ("lunch", "Mol go'shtli qishki dimlama", "Asosiy issiq ovqat"),
                ("buffet", "Qaynatilgan guruch", "Qo'shimcha energiya"),
                ("dinner", "Qovoqli tovuq sho'rva", "Yengil kechki ovqat"),
            ],
        },
    ],
    "spring": [
        {
            "diet": "LITE",
            "entries": [
                ("first_breakfast", "Ko'katli tuxum salati", "Bahorgi oqsilli nonushta"),
                ("second_breakfast", "Qatiqli bodring", "Yengil tamaddi"),
                ("lunch", "Moshli bahor sho'rva", "Ko'katli tushlik"),
                ("buffet", "Tovuqli ko'katli guruch", "Asosiy garnir"),
                ("dinner", "Laktosasiz bahor salati", "Yengil sabzavotli ovqat"),
            ],
        },
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Sutli suli bo'tqasi", "Klassik nonushta"),
                ("second_breakfast", "Olma va nokli qatiq", "Mevali tamaddi"),
                ("lunch", "Tovuqli ko'katli guruch", "Ko'katli asosiy taom"),
                ("buffet", "Yozgi sabzavot salati", "Yangi sabzavotlar"),
                ("dinner", "Bug'da pishgan baliq va brokkoli", "Kechki yengil ovqat"),
            ],
        },
        {
            "diet": "NO_LACTOSE",
            "entries": [
                ("first_breakfast", "Ko'katli tuxum salati", "Sut mahsulotsiz nonushta"),
                ("second_breakfast", "Olma-nok salati", "Laktosasiz tamaddi"),
                ("lunch", "Laktosasiz bahor salati", "Sut mahsulotsiz asosiy salat"),
                ("buffet", "Qaynatilgan guruch", "Qo'shimcha garnir"),
                ("dinner", "Baliqli karam salati", "Yengil kechki taom"),
            ],
        },
        {
            "diet": "LOW_SALT",
            "entries": [
                ("first_breakfast", "Qovoqli sutli suli bo'tqasi", "Yumshoq nonushta"),
                ("second_breakfast", "Qatiqli bodring", "Salqin tamaddi"),
                ("lunch", "Moshli bahor sho'rva", "Tuz kamaytirilgan sho'rva"),
                ("buffet", "Lavlagili karam salati", "Sabzavotli qo'shimcha"),
                ("dinner", "Laktosasiz bahor salati", "Kechki yengil taom"),
            ],
        },
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Ko'katli tuxum salati", "Hafta yakuni nonushtasi"),
                ("second_breakfast", "Mevali yogurt", "Mevali tamaddi"),
                ("lunch", "Tovuqli sabzavot sho'rva", "Issiq tushlik"),
                ("buffet", "Tovuqli ko'katli guruch", "Qo'shimcha asosiy taom"),
                ("dinner", "Bug'da pishgan baliq va brokkoli", "Yengil kechki ovqat"),
            ],
        },
    ],
    "summer": [
        {
            "diet": "LITE",
            "entries": [
                ("first_breakfast", "Shaftolili suli bo'tqasi", "Yozgi mevali nonushta"),
                ("second_breakfast", "Tarvuzli meva tamaddi", "Salqin tamaddi"),
                ("lunch", "Yozgi tovuqli salat", "Yengil asosiy taom"),
                ("buffet", "Sabzavotli makaron", "Qo'shimcha garnir"),
                ("dinner", "Baliqli yozgi sabzavotlar", "Kechki oqsilli ovqat"),
            ],
        },
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Shaftolili suli bo'tqasi", "Mevali nonushta"),
                ("second_breakfast", "Qatiqli bodring", "Salqin tamaddi"),
                ("lunch", "Tovuqli ko'katli guruch", "Asosiy tushlik"),
                ("buffet", "Yozgi sabzavot salati", "Yangi sabzavotlar"),
                ("dinner", "Baliqli yozgi sabzavotlar", "Kechki yengil taom"),
            ],
        },
        {
            "diet": "NO_LACTOSE",
            "entries": [
                ("first_breakfast", "Ko'katli tuxum salati", "Sut mahsulotsiz nonushta"),
                ("second_breakfast", "Tarvuzli meva tamaddi", "Salqin laktosasiz tamaddi"),
                ("lunch", "Yozgi tovuqli salat", "Sut mahsulotsiz tushlik"),
                ("buffet", "Qaynatilgan guruch", "Qo'shimcha garnir"),
                ("dinner", "Baliqli karam salati", "Yengil kechki taom"),
            ],
        },
        {
            "diet": "LITE",
            "entries": [
                ("first_breakfast", "Sutli suli bo'tqasi", "Yumshoq nonushta"),
                ("second_breakfast", "Shaftoli va yogurt", "Mevali tamaddi"),
                ("lunch", "Tovuqli sabzavot sho'rva", "Yengil issiq tushlik"),
                ("buffet", "Yozgi sabzavot salati", "Yangi sabzavotlar"),
                ("dinner", "Baliqli yozgi sabzavotlar", "Kechki oqsilli ovqat"),
            ],
        },
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Shaftolili suli bo'tqasi", "Hafta yakuni nonushtasi"),
                ("second_breakfast", "Tarvuzli meva tamaddi", "Salqin tamaddi"),
                ("lunch", "Yozgi tovuqli salat", "Yengil asosiy ovqat"),
                ("buffet", "Sabzavotli makaron", "Qo'shimcha garnir"),
                ("dinner", "Bug'da pishgan baliq va brokkoli", "Kechki yengil taom"),
            ],
        },
    ],
    "autumn": [
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Qovoqli grechka bo'tqasi", "Kuzgi to'yimli nonushta"),
                ("second_breakfast", "Nokli qatiq", "Mevali tamaddi"),
                ("lunch", "Tovuqli kuzgi dimlama", "Sabzavotli asosiy taom"),
                ("buffet", "Lavlagili karam salati", "Rangli qo'shimcha"),
                ("dinner", "Moshli yengil sho'rva", "Yengil kechki sho'rva"),
            ],
        },
        {
            "diet": "HIGH_PROTEIN",
            "entries": [
                ("first_breakfast", "Ko'katli tuxum salati", "Oqsilga boy nonushta"),
                ("second_breakfast", "Olma va nokli qatiq", "Mevali tamaddi"),
                ("lunch", "Mol go'shtli qishki dimlama", "Asosiy oqsilli taom"),
                ("buffet", "Qovoqli grechka bo'tqasi", "Qo'shimcha garnir"),
                ("dinner", "Baliqli karam salati", "Kechki oqsilli ovqat"),
            ],
        },
        {
            "diet": "LOW_SALT",
            "entries": [
                ("first_breakfast", "Qovoqli grechka bo'tqasi", "Tuzsizroq nonushta"),
                ("second_breakfast", "Nokli qatiq", "Yengil tamaddi"),
                ("lunch", "Moshli yengil sho'rva", "Dukkakli tushlik"),
                ("buffet", "Lavlagili karam salati", "Sabzavotli qo'shimcha"),
                ("dinner", "Tovuqli kuzgi dimlama", "Yengil asosiy taom"),
            ],
        },
        {
            "diet": "NO_LACTOSE",
            "entries": [
                ("first_breakfast", "Ko'katli tuxum salati", "Sut mahsulotsiz nonushta"),
                ("second_breakfast", "Olma-nok salati", "Laktosasiz tamaddi"),
                ("lunch", "Tovuqli kuzgi dimlama", "Sut mahsulotsiz tushlik"),
                ("buffet", "Qaynatilgan guruch", "Qo'shimcha garnir"),
                ("dinner", "Moshli yengil sho'rva", "Kechki yengil sho'rva"),
            ],
        },
        {
            "diet": "STD",
            "entries": [
                ("first_breakfast", "Qovoqli grechka bo'tqasi", "Hafta yakuni nonushtasi"),
                ("second_breakfast", "Nokli qatiq", "Mevali tamaddi"),
                ("lunch", "Tovuqli kuzgi dimlama", "Asosiy issiq ovqat"),
                ("buffet", "Lavlagili karam salati", "Rangli qo'shimcha"),
                ("dinner", "Bug'da pishgan baliq va brokkoli", "Kechki yengil taom"),
            ],
        },
    ],
}


class Command(BaseCommand):
    help = "Create demo users, organizations, products, dishes, menus, reports, and activity data."

    def handle(self, *args, **options):
        self.user_model = get_user_model()

        today = timezone.localdate()
        seasons = self._seed_seasons(today.year)
        diets = self._seed_diets()
        meal_lookup = self._seed_meal_times()

        users = {}
        organizations = {}
        main_demo = DEMO_ORGANIZATIONS[0]
        main_user = self._ensure_user(main_demo)
        superuser_username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()
        owner_user = self.user_model.objects.filter(username=superuser_username).first() or main_user

        for org_index, org_data in enumerate(DEMO_ORGANIZATIONS):
            user = main_user if org_data["username"] == main_demo["username"] else self._ensure_user(org_data)
            users[org_data["username"]] = user

            organization = self._ensure_organization(
                org_data,
                owner_user if org_index == 0 else user,
            )
            organizations[organization.name] = organization
            self._ensure_membership(
                user=user,
                organization=organization,
                role=OrganizationMember.Role.DIRECTOR,
                can_manage_menu=True,
                can_manage_prices=True,
                can_view_reports=True,
            )

            products = self._seed_products(organization, org_index)
            dishes = self._seed_dishes(organization, diets, products)
            self._seed_menus(
                organization=organization,
                seasons=seasons,
                diets=diets,
                meal_lookup=meal_lookup,
                dish_lookup=dishes,
                today=today,
                days_count=org_data["menu_days"],
                people_base=org_data["people_base"],
                variant=org_index,
            )

            if org_index == 0:
                self._seed_soglom_seasonal_menus(
                    organization=organization,
                    seasons=seasons,
                    diets=diets,
                    meal_lookup=meal_lookup,
                    dish_lookup=dishes,
                    year=today.year,
                    people_base=org_data["people_base"],
                )
                main_products = products
                main_organization = organization

        if owner_user != main_user:
            self._ensure_membership(
                user=owner_user,
                organization=main_organization,
                role=OrganizationMember.Role.DIRECTOR,
                can_manage_menu=True,
                can_manage_prices=True,
                can_view_reports=True,
            )

        for role_user in ROLE_USERS:
            user = self._ensure_user(role_user)
            self._ensure_membership(
                user=user,
                organization=main_organization,
                role=role_user["role"],
                can_manage_menu=role_user["can_manage_menu"],
                can_manage_prices=role_user["can_manage_prices"],
                can_view_reports=role_user["can_view_reports"],
            )

        self._seed_profile_activity(main_organization, main_user, main_products)

        self.stdout.write(self.style.SUCCESS("Demo ma'lumotlar bazaga yozildi."))
        self.stdout.write(f"Asosiy tashkilot: {main_organization.name}")
        self.stdout.write("Sog'lom Avlod MTT uchun qish, bahor, yoz va kuz menyulari to'ldirildi.")
        self.stdout.write("Demo loginlar:")
        for username in [org["username"] for org in DEMO_ORGANIZATIONS] + [user["username"] for user in ROLE_USERS]:
            self.stdout.write(f"  {username} / {DEMO_PASSWORD}")

    def _ensure_user(self, data):
        user, _ = self.user_model.objects.get_or_create(
            username=data["username"],
            defaults={
                "first_name": data.get("first_name", ""),
                "last_name": data.get("last_name", ""),
                "email": data.get("email", ""),
            },
        )
        user.first_name = data.get("first_name", user.first_name)
        user.last_name = data.get("last_name", user.last_name)
        user.email = data.get("email", user.email)
        user.set_password(DEMO_PASSWORD)
        user.save()
        return user

    def _ensure_organization(self, data, owner):
        Organization.objects.filter(owner=owner).exclude(name=data["name"]).update(owner=None)
        organization, _ = Organization.objects.get_or_create(name=data["name"])
        organization.address = data["address"]
        organization.contact = data["contact"]
        organization.owner = owner
        organization.save()
        return organization

    def _ensure_membership(
        self,
        user,
        organization,
        role,
        can_manage_menu,
        can_manage_prices,
        can_view_reports,
    ):
        OrganizationMember.objects.update_or_create(
            user=user,
            defaults={
                "organization": organization,
                "role": role,
                "can_manage_menu": can_manage_menu,
                "can_manage_prices": can_manage_prices,
                "can_view_reports": can_view_reports,
            },
        )

    def _seed_seasons(self, year):
        seasons = {}
        for name in ("winter", "spring", "summer", "autumn"):
            seasons[name], _ = Season.objects.get_or_create(name=name, year=year)
        return seasons

    def _seed_diets(self):
        diets = {}
        for code, title, description in [
            ("STD", "Standart parhez", "Muvozanatli kundalik ovqatlanish"),
            ("LITE", "Yengil parhez", "Hazmi yengil ratsion"),
            ("NO_LACTOSE", "Laktosasiz parhez", "Sut mahsulotlariga sezgirlar uchun ratsion"),
            ("HIGH_PROTEIN", "Oqsilga boy parhez", "Faol o'sish va tiklanish uchun oqsil miqdori yuqori menyu"),
            ("LOW_SALT", "Tuz kamaytirilgan parhez", "Yurak-qon tomir nazorati uchun tuzi me'yorlangan ratsion"),
        ]:
            diets[code], _ = Diet.objects.update_or_create(
                code=code,
                defaults={"title": title, "description": description},
            )
        return diets

    def _seed_meal_times(self):
        meal_lookup = {}
        for slot, title, order in MEAL_TIMES:
            meal, _ = MealTime.objects.update_or_create(
                slot=slot,
                defaults={"title": title, "order": order},
            )
            meal_lookup[slot] = meal
        return meal_lookup

    def _seed_products(self, organization, variant):
        products = {}
        price_factor = Decimal("1.00") + (Decimal(variant) * Decimal("0.035"))
        for name, unit, protein, fat, carbs, calories, price in PRODUCT_DATA:
            product, _ = Product.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={
                    "unit": unit,
                    "protein": Decimal(protein),
                    "fat": Decimal(fat),
                    "carbs": Decimal(carbs),
                    "calories": calories,
                    "price_per_kg": (Decimal(price) * price_factor).quantize(Decimal("0.01")),
                },
            )
            products[name] = product
        return products

    def _seed_dishes(self, organization, diets, products):
        dishes_data = [
            ("Sutli suli bo'tqasi", "STD", "Ertalabki energiya uchun foydali bo'tqa.", 20, [("Suli yormasi", 80), ("Sut", 200)]),
            ("Mevali yogurt", "LITE", "Yengil ikkinchi nonushta.", 10, [("Yogurt", 180), ("Olma", 70)]),
            ("Tovuqli sabzavot sho'rva", "STD", "Muvozanatli tushlik sho'rvasi.", 45, [("Tovuq filesi", 120), ("Kartoshka", 100), ("Sabzi", 50)]),
            ("Qaynatilgan guruch", "STD", "Asosiy taom uchun garnir.", 25, [("Guruch", 90)]),
            ("Bug'da pishgan baliq va brokkoli", "LITE", "Kechki ovqat uchun yengil oqsilli taom.", 35, [("Baliq filesi", 140), ("Brokkoli", 120)]),
            ("Grechkali mol go'shti", "HIGH_PROTEIN", "Oqsil va murakkab uglevodga boy tushlik.", 50, [("Mol go'shti", 120), ("Grechka", 90), ("Sabzi", 40), ("O'simlik yog'i", 8)]),
            ("Tuxumli sabzavot salati", "LITE", "Yengil oqsilli salat.", 15, [("Tuxum", 60), ("Bodring", 80), ("Pomidor", 80), ("Karam", 60)]),
            ("Loviya sho'rva", "LOW_SALT", "To'yimli va tuzi kamaytirilgan sho'rva.", 45, [("Loviya", 90), ("Kartoshka", 80), ("Sabzi", 50), ("Karam", 50)]),
            ("Qatiqli banan", "LITE", "Ikkinchi nonushta uchun yengil tamaddi.", 8, [("Qatiq", 180), ("Banan", 80)]),
            ("Sabzavotli makaron", "STD", "Bolalar uchun yumshoq garnirli taom.", 30, [("Makaron", 90), ("Pomidor", 60), ("Sabzi", 40), ("O'simlik yog'i", 8)]),
            ("Laktosasiz tovuqli salat", "NO_LACTOSE", "Sut mahsulotlarisiz oqsilli salat.", 20, [("Tovuq filesi", 110), ("Bodring", 80), ("Pomidor", 70), ("Karam", 60)]),
            ("Qovoqli sutli suli bo'tqasi", "STD", "Qish va kuz uchun A vitaminiga boy iliq nonushta.", 25, [("Suli yormasi", 70), ("Sut", 180), ("Qovoq", 80)]),
            ("Olma va nokli qatiq", "LITE", "Meva va qatiq asosidagi yengil tamaddi.", 8, [("Qatiq", 170), ("Olma", 60), ("Nok", 60)]),
            ("Mol go'shtli qishki dimlama", "HIGH_PROTEIN", "Sovuq mavsum uchun oqsil va sabzavotga boy issiq taom.", 55, [("Mol go'shti", 120), ("Kartoshka", 90), ("Sabzi", 60), ("Karam", 70), ("O'simlik yog'i", 8)]),
            ("Grechkali sabzi garniri", "STD", "Tushlikka mos murakkab uglevodli garnir.", 25, [("Grechka", 85), ("Sabzi", 70), ("O'simlik yog'i", 6)]),
            ("Baliqli karam salati", "LITE", "Yengil oqsil va tolaga boy kechki ovqat.", 25, [("Baliq filesi", 120), ("Karam", 90), ("Bodring", 60), ("Ko'kat", 10)]),
            ("Qovoqli tovuq sho'rva", "LITE", "Hazmi yengil qovoqli tovuq sho'rvasi.", 40, [("Tovuq filesi", 110), ("Qovoq", 100), ("Sabzi", 45), ("Kartoshka", 70)]),
            ("Moshli qishki sho'rva", "LOW_SALT", "Dukkakli mahsulotlar bilan to'yimli sho'rva.", 50, [("Mosh", 85), ("Kartoshka", 75), ("Sabzi", 45), ("Ko'kat", 10)]),
            ("Lavlagili karam salati", "LOW_SALT", "Tuz miqdori past, rangli sabzavotli salat.", 15, [("Lavlagi", 90), ("Karam", 80), ("Sabzi", 35), ("O'simlik yog'i", 5)]),
            ("Ko'katli tuxum salati", "LITE", "Bahor uchun ko'katli oqsilli nonushta.", 15, [("Tuxum", 70), ("Bodring", 70), ("Ko'kat", 20), ("Pomidor", 60)]),
            ("Qatiqli bodring", "LITE", "Salqin va yengil ikkinchi nonushta.", 7, [("Qatiq", 170), ("Bodring", 100), ("Ko'kat", 10)]),
            ("Moshli bahor sho'rva", "LOW_SALT", "Ko'kat va mosh bilan yengil bahorgi sho'rva.", 45, [("Mosh", 75), ("Kartoshka", 65), ("Sabzi", 45), ("Ko'kat", 18)]),
            ("Tovuqli ko'katli guruch", "STD", "Ko'katli guruch va tovuq filesidan iborat tushlik.", 35, [("Tovuq filesi", 105), ("Guruch", 85), ("Ko'kat", 15), ("Sabzi", 35)]),
            ("Laktosasiz bahor salati", "NO_LACTOSE", "Sut mahsulotlarisiz bahorgi sabzavotli salat.", 18, [("Tovuq filesi", 100), ("Bodring", 85), ("Pomidor", 75), ("Ko'kat", 15)]),
            ("Olma-nok salati", "NO_LACTOSE", "Laktosasiz mevali tamaddi.", 8, [("Olma", 80), ("Nok", 80)]),
            ("Yozgi sabzavot salati", "LITE", "Issiq kunlar uchun yengil sabzavotli qo'shimcha.", 12, [("Bodring", 90), ("Pomidor", 90), ("Ko'kat", 15), ("O'simlik yog'i", 5)]),
            ("Shaftolili suli bo'tqasi", "STD", "Yozgi meva bilan boyitilgan suli bo'tqasi.", 20, [("Suli yormasi", 70), ("Sut", 170), ("Shaftoli", 80)]),
            ("Tarvuzli meva tamaddi", "LITE", "Suyuqlikka boy yozgi tamaddi.", 5, [("Tarvuz", 180), ("Shaftoli", 50)]),
            ("Yozgi tovuqli salat", "NO_LACTOSE", "Yoz uchun yengil, laktosasiz oqsilli salat.", 20, [("Tovuq filesi", 110), ("Bodring", 85), ("Pomidor", 85), ("Ko'kat", 15)]),
            ("Baliqli yozgi sabzavotlar", "LITE", "Baliq va yangi sabzavotlardan iborat kechki ovqat.", 28, [("Baliq filesi", 130), ("Bodring", 60), ("Pomidor", 70), ("Brokkoli", 70)]),
            ("Shaftoli va yogurt", "LITE", "Yozgi mevali yogurt.", 6, [("Yogurt", 170), ("Shaftoli", 90)]),
            ("Qovoqli grechka bo'tqasi", "STD", "Kuz uchun qovoq bilan boyitilgan grechka.", 30, [("Grechka", 85), ("Qovoq", 100), ("Sabzi", 40)]),
            ("Nokli qatiq", "LITE", "Kuzgi mevali qatiq.", 6, [("Qatiq", 180), ("Nok", 90)]),
            ("Tovuqli kuzgi dimlama", "STD", "Kuzgi sabzavotlar bilan tovuqli issiq taom.", 45, [("Tovuq filesi", 115), ("Kartoshka", 80), ("Qovoq", 90), ("Sabzi", 45), ("O'simlik yog'i", 7)]),
            ("Moshli yengil sho'rva", "LOW_SALT", "Kuz uchun moshli, tuzi kamaytirilgan sho'rva.", 45, [("Mosh", 75), ("Karam", 60), ("Sabzi", 45), ("Ko'kat", 12)]),
        ]

        dish_lookup = {}
        for dish_name, diet_code, description, duration_minutes, ingredients in dishes_data:
            dish, _ = Dish.objects.update_or_create(
                organization=organization,
                name=dish_name,
                defaults={
                    "diet": diets[diet_code],
                    "description": description,
                    "duration_minutes": duration_minutes,
                },
            )
            DishIngredient.objects.filter(dish=dish).delete()
            for product_name, grams in ingredients:
                DishIngredient.objects.create(
                    dish=dish,
                    product=products[product_name],
                    grams=grams,
                )
            dish_lookup[dish_name] = dish
        return dish_lookup

    def _seed_menus(
        self,
        organization,
        seasons,
        diets,
        meal_lookup,
        dish_lookup,
        today,
        days_count,
        people_base,
        variant,
    ):
        week_start = today - timedelta(days=today.weekday())
        start_date = week_start - timedelta(days=max(days_count - 7, 0))
        lunch_cycle = [
            "Tovuqli sabzavot sho'rva",
            "Loviya sho'rva",
            "Laktosasiz tovuqli salat",
            "Grechkali mol go'shti",
            "Loviya sho'rva",
            "Tovuqli sabzavot sho'rva",
            "Grechkali mol go'shti",
        ]
        diet_cycle = ["STD", "LITE", "NO_LACTOSE", "HIGH_PROTEIN", "LOW_SALT", "LITE", "STD"]

        for day_index in range(days_count):
            menu_date = start_date + timedelta(days=day_index)
            day_offset = (day_index + variant) % 7
            people_count = people_base + (day_offset % 4) * 7
            menu_day, _ = MenuDay.objects.update_or_create(
                organization=organization,
                date=menu_date,
                defaults={
                    "season": seasons[self._season_for_month(menu_date.month)],
                    "diet": diets[diet_cycle[day_offset]],
                    "people_count": people_count,
                },
            )
            MenuEntry.objects.filter(menu_day=menu_day).delete()
            self._create_entry(
                menu_day,
                meal_lookup["first_breakfast"],
                dish_lookup["Sutli suli bo'tqasi"] if day_offset != 2 else dish_lookup["Tuxumli sabzavot salati"],
                people_count,
                "Bolalar uchun standart porsiya",
            )
            self._create_entry(
                menu_day,
                meal_lookup["second_breakfast"],
                dish_lookup["Qatiqli banan"] if day_offset in (1, 4) else dish_lookup["Mevali yogurt"],
                people_count,
                "Mevali yengil tamaddi",
            )
            self._create_entry(
                menu_day,
                meal_lookup["lunch"],
                dish_lookup[lunch_cycle[day_offset]],
                people_count,
                "Asosiy issiq ovqat",
            )
            self._create_entry(
                menu_day,
                meal_lookup["buffet"],
                dish_lookup["Sabzavotli makaron"] if day_offset in (3, 6) else dish_lookup["Qaynatilgan guruch"],
                people_count,
                "Qo'shimcha garnir",
            )
            self._create_entry(
                menu_day,
                meal_lookup["dinner"],
                dish_lookup["Bug'da pishgan baliq va brokkoli"],
                people_count,
                "Kechki yengil taom",
            )

    def _create_entry(self, menu_day, mealtime, dish, portions, notes):
        MenuEntry.objects.create(
            menu_day=menu_day,
            mealtime=mealtime,
            dish=dish,
            portions=portions,
            notes=notes,
        )

    def _seed_soglom_seasonal_menus(
        self,
        organization,
        seasons,
        diets,
        meal_lookup,
        dish_lookup,
        year,
        people_base,
    ):
        season_people_offset = {
            "winter": 0,
            "spring": 6,
            "summer": 12,
            "autumn": 8,
        }
        for season_key, date_parts in SOGLOM_SEASONAL_MENU_DATES.items():
            plans = SOGLOM_SEASONAL_MENU_PLANS[season_key]
            for day_index, (month, day) in enumerate(date_parts):
                plan = plans[day_index % len(plans)]
                menu_date = date(year, month, day)
                people_count = people_base + season_people_offset[season_key] + (day_index * 4)
                menu_day, _ = MenuDay.objects.update_or_create(
                    organization=organization,
                    date=menu_date,
                    defaults={
                        "season": seasons[season_key],
                        "diet": diets[plan["diet"]],
                        "people_count": people_count,
                    },
                )
                MenuEntry.objects.filter(menu_day=menu_day).delete()
                for slot, dish_name, notes in plan["entries"]:
                    self._create_entry(
                        menu_day,
                        meal_lookup[slot],
                        dish_lookup[dish_name],
                        people_count,
                        notes,
                    )

    def _seed_profile_activity(self, organization, user, products):
        now = timezone.now()

        PriceHistory.objects.filter(organization=organization, source_label__startswith="Demo").delete()
        price_rows = [
            ("Sut", "10500.00", "12000.00", "Demo Korzinka katalogi", 94),
            ("Tovuq filesi", "52000.00", "58000.00", "Demo Korzinka Go", 91),
            ("Mol go'shti", "78000.00", "88000.00", "Demo bozor monitoringi", 88),
            ("Guruch", "19000.00", "21000.00", "Demo Excel import", 97),
            ("Baliq filesi", "69000.00", "76000.00", "Demo AI narx qidiruvi", 84),
            ("Yogurt", "23000.00", "26000.00", "Demo yetkazib beruvchi", 90),
        ]
        for index, (name, old_price, new_price, source_label, confidence) in enumerate(price_rows):
            history = PriceHistory.objects.create(
                product=products[name],
                organization=organization,
                old_price=Decimal(old_price),
                new_price=Decimal(new_price),
                source_type=PriceHistory.SourceType.MANUAL if index % 2 else PriceHistory.SourceType.EXCEL,
                source_label=source_label,
                confidence=confidence,
                effective_date=timezone.localdate() - timedelta(days=index + 1),
            )
            PriceHistory.objects.filter(pk=history.pk).update(created_at=now - timedelta(hours=index + 2))

        ImportJob.objects.filter(organization=organization, source__startswith="demo-").delete()
        import_rows = [
            ("demo-menyu-haftalik.xlsx", "28 kunlik menyu va mahsulotlar import qilindi."),
            ("demo-narxlar-may.xlsx", "Mahsulot narxlari va narx tarixi yangilandi."),
            ("demo-taomnoma-archive.zip", "ZIP arxivdan taom tarkibi va porsiyalar olindi."),
        ]
        for index, (source, summary) in enumerate(import_rows):
            job = ImportJob.objects.create(
                organization=organization,
                job_type=ImportJob.JobType.EXCEL,
                status=ImportJob.Status.SUCCESS,
                source=source,
                summary=summary,
                completed_at=now - timedelta(days=index + 1),
            )
            ImportJob.objects.filter(pk=job.pk).update(created_at=now - timedelta(days=index + 1, hours=1))

        demo_alert_titles = [
            "Laktosiz menyuda sut mahsuloti bor",
            "Sut mahsulotlari narxi oshdi",
            "Ertangi menyuda guruch ehtiyoji yuqori",
        ]
        MenuAlert.objects.filter(organization=organization, title__in=demo_alert_titles).delete()
        lactose_day = (
            MenuDay.objects.filter(organization=organization, diet__code="NO_LACTOSE")
            .order_by("-date")
            .first()
        )
        MenuAlert.objects.create(
            organization=organization,
            menu_day=lactose_day,
            severity=MenuAlert.Severity.DANGER,
            title="Laktosiz menyuda sut mahsuloti bor",
            message="Laktosasiz parhez kunida yogurt yoki sut mahsuloti qatnashgan retsept tekshiruvga chiqarildi.",
        )
        MenuAlert.objects.create(
            organization=organization,
            severity=MenuAlert.Severity.WARNING,
            title="Sut mahsulotlari narxi oshdi",
            message="Sut va yogurt narxlari oxirgi monitoringda 12-14% oralig'ida oshgan.",
        )
        MenuAlert.objects.create(
            organization=organization,
            severity=MenuAlert.Severity.INFO,
            title="Ertangi menyuda guruch ehtiyoji yuqori",
            message="Mahsulot ehtiyoji ro'yxatida guruch miqdori haftalik o'rtachadan yuqori ko'rindi.",
        )

    def _season_for_month(self, month):
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"
