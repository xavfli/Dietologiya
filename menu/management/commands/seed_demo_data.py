import os
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from menu.models import (
    Diet,
    Dish,
    DishIngredient,
    MealTime,
    MenuDay,
    MenuEntry,
    Organization,
    OrganizationMember,
    Product,
    Season,
)


class Command(BaseCommand):
    help = "Create a demo organization, owner account, products, dishes, and menu entries."

    def handle(self, *args, **options):
        user_model = get_user_model()

        username = "soglom_avlod"
        password = "OrgDemo2026!"
        superuser_username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "").strip()

        user, _ = user_model.objects.get_or_create(
            username=username,
            defaults={
                "first_name": "Soglom",
                "last_name": "Avlod",
                "email": "soglom.avlod@example.com",
            },
        )
        user.set_password(password)
        user.save()
        owner_user = user_model.objects.filter(username=superuser_username).first() or user
        Organization.objects.filter(owner=owner_user).exclude(name="Sog'lom Avlod MTT").update(owner=None)

        organization, _ = Organization.objects.get_or_create(
            name="Sog'lom Avlod MTT",
            defaults={
                "address": "Toshkent sh., Yunusobod tumani, 12-mavze",
                "contact": "+998 90 120 45 67",
                "owner": user,
            },
        )
        organization.address = "Toshkent sh., Yunusobod tumani, 12-mavze"
        organization.contact = "+998 90 120 45 67"
        organization.owner = owner_user
        organization.save()
        OrganizationMember.objects.update_or_create(
            user=user,
            defaults={
                "organization": organization,
                "role": OrganizationMember.Role.DIRECTOR,
                "can_manage_menu": True,
                "can_manage_prices": True,
                "can_view_reports": True,
            },
        )
        if owner_user != user:
            OrganizationMember.objects.update_or_create(
                user=owner_user,
                defaults={
                    "organization": organization,
                    "role": OrganizationMember.Role.DIRECTOR,
                    "can_manage_menu": True,
                    "can_manage_prices": True,
                    "can_view_reports": True,
                },
            )

        today = timezone.localdate()
        season_name = self._season_for_month(today.month)
        seasons = {}
        for name in ("winter", "spring", "summer", "autumn"):
            seasons[name], _ = Season.objects.get_or_create(name=name, year=today.year)
        season = seasons[season_name]
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
        diet_standard = diets["STD"]
        diet_lite = diets["LITE"]

        for slot, title, order in [
            ("first_breakfast", "1-nonushta", 1),
            ("second_breakfast", "2-nonushta", 2),
            ("lunch", "Tushlik", 3),
            ("buffet", "Bufet mahsulotlari", 4),
            ("dinner", "Kechki ovqat", 5),
        ]:
            MealTime.objects.update_or_create(slot=slot, defaults={"title": title, "order": order})

        products = {}
        for name, unit, protein, fat, carbs, calories, price in [
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
        ]:
            product, _ = Product.objects.update_or_create(
                organization=organization,
                name=name,
                defaults={
                    "unit": unit,
                    "protein": Decimal(protein),
                    "fat": Decimal(fat),
                    "carbs": Decimal(carbs),
                    "calories": calories,
                    "price_per_kg": Decimal(price),
                },
            )
            products[name] = product

        dishes_data = [
            (
                "Sutli suli bo'tqasi",
                diet_standard,
                "Ertalabki energiya uchun foydali bo'tqa.",
                20,
                [("Suli yormasi", 80), ("Sut", 200)],
            ),
            (
                "Mevali yogurt",
                diet_lite,
                "Yengil ikkinchi nonushta.",
                10,
                [("Yogurt", 180), ("Olma", 70)],
            ),
            (
                "Tovuqli sabzavot sho'rva",
                diet_standard,
                "Muvozanatli tushlik sho'rvasi.",
                45,
                [("Tovuq filesi", 120), ("Kartoshka", 100), ("Sabzi", 50)],
            ),
            (
                "Qaynatilgan guruch",
                diet_standard,
                "Asosiy taom uchun garnir.",
                25,
                [("Guruch", 90)],
            ),
            (
                "Bug'da pishgan baliq va brokkoli",
                diet_lite,
                "Kechki ovqat uchun yengil oqsilli taom.",
                35,
                [("Baliq filesi", 140), ("Brokkoli", 120)],
            ),
            (
                "Grechkali mol go'shti",
                diets["HIGH_PROTEIN"],
                "Oqsil va murakkab uglevodga boy tushlik.",
                50,
                [("Mol go'shti", 120), ("Grechka", 90), ("Sabzi", 40), ("O'simlik yog'i", 8)],
            ),
            (
                "Tuxumli sabzavot salati",
                diet_lite,
                "Yengil oqsilli salat.",
                15,
                [("Tuxum", 60), ("Bodring", 80), ("Pomidor", 80), ("Karam", 60)],
            ),
            (
                "Loviya sho'rva",
                diets["LOW_SALT"],
                "To'yimli va tuzi kamaytirilgan sho'rva.",
                45,
                [("Loviya", 90), ("Kartoshka", 80), ("Sabzi", 50), ("Karam", 50)],
            ),
            (
                "Qatiqli banan",
                diet_lite,
                "Ikkinchi nonushta uchun yengil tamaddi.",
                8,
                [("Qatiq", 180), ("Banan", 80)],
            ),
            (
                "Sabzavotli makaron",
                diet_standard,
                "Bolalar uchun yumshoq garnirli taom.",
                30,
                [("Makaron", 90), ("Pomidor", 60), ("Sabzi", 40), ("O'simlik yog'i", 8)],
            ),
            (
                "Laktosasiz tovuqli salat",
                diets["NO_LACTOSE"],
                "Sut mahsulotlarisiz oqsilli salat.",
                20,
                [("Tovuq filesi", 110), ("Bodring", 80), ("Pomidor", 70), ("Karam", 60)],
            ),
        ]

        meal_lookup = {meal.slot: meal for meal in MealTime.objects.all()}
        dish_lookup = {}
        for dish_name, diet, description, duration_minutes, ingredients in dishes_data:
            dish, _ = Dish.objects.update_or_create(
                organization=organization,
                name=dish_name,
                defaults={"diet": diet, "description": description, "duration_minutes": duration_minutes},
            )
            DishIngredient.objects.filter(dish=dish).delete()
            for product_name, grams in ingredients:
                DishIngredient.objects.create(
                    dish=dish,
                    product=products[product_name],
                    grams=grams,
                )
            dish_lookup[dish_name] = dish

        week_start = today - timedelta(days=today.weekday())
        for day_offset in range(7):
            menu_date = week_start + timedelta(days=day_offset)
            daily_diet = [diet_standard, diet_lite, diets["NO_LACTOSE"], diets["HIGH_PROTEIN"], diets["LOW_SALT"], diet_lite, diet_standard][day_offset]
            people_count = 120 + (day_offset % 3) * 5
            menu_day, _ = MenuDay.objects.update_or_create(
                organization=organization,
                date=menu_date,
                defaults={"season": season, "diet": daily_diet, "people_count": people_count},
            )
            MenuEntry.objects.filter(menu_day=menu_day).delete()
            MenuEntry.objects.create(
                menu_day=menu_day,
                mealtime=meal_lookup["first_breakfast"],
                dish=dish_lookup["Sutli suli bo'tqasi"] if day_offset != 2 else dish_lookup["Tuxumli sabzavot salati"],
                portions=people_count,
                notes="Bolalar uchun standart porsiya",
            )
            MenuEntry.objects.create(
                menu_day=menu_day,
                mealtime=meal_lookup["second_breakfast"],
                dish=dish_lookup["Qatiqli banan"] if day_offset in (1, 4) else dish_lookup["Mevali yogurt"],
                portions=people_count,
                notes="Mevali yengil tamaddi",
            )
            MenuEntry.objects.create(
                menu_day=menu_day,
                mealtime=meal_lookup["lunch"],
                dish=[dish_lookup["Tovuqli sabzavot sho'rva"], dish_lookup["Loviya sho'rva"], dish_lookup["Laktosasiz tovuqli salat"], dish_lookup["Grechkali mol go'shti"], dish_lookup["Loviya sho'rva"], dish_lookup["Tovuqli sabzavot sho'rva"], dish_lookup["Grechkali mol go'shti"]][day_offset],
                portions=people_count,
                notes="Asosiy issiq ovqat",
            )
            MenuEntry.objects.create(
                menu_day=menu_day,
                mealtime=meal_lookup["buffet"],
                dish=dish_lookup["Sabzavotli makaron"] if day_offset in (3, 6) else dish_lookup["Qaynatilgan guruch"],
                portions=people_count,
                notes="Qo'shimcha garnir",
            )
            MenuEntry.objects.create(
                menu_day=menu_day,
                mealtime=meal_lookup["dinner"],
                dish=dish_lookup["Bug'da pishgan baliq va brokkoli"],
                portions=people_count,
                notes="Kechki yengil taom",
            )

        self.stdout.write(self.style.SUCCESS("Demo organization created/updated successfully."))
        self.stdout.write(f"Organization: {organization.name}")
        self.stdout.write(f"Owner: {owner_user.username}")
        self.stdout.write(f"Login: {username}")
        self.stdout.write(f"Password: {password}")

    def _season_for_month(self, month: int) -> str:
        if month in (12, 1, 2):
            return "winter"
        if month in (3, 4, 5):
            return "spring"
        if month in (6, 7, 8):
            return "summer"
        return "autumn"
