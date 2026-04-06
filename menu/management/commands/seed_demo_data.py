from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from menu.models import (
    Diet,
    Dish,
    DishIngredient,
    MealTime,
    MenuDay,
    MenuEntry,
    Organization,
    Product,
    Season,
)


class Command(BaseCommand):
    help = "Create a demo organization, owner account, products, dishes, and menu entries."

    def handle(self, *args, **options):
        user_model = get_user_model()

        username = "soglom_avlod"
        password = "OrgDemo2026!"

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
        organization.owner = user
        organization.save()

        season, _ = Season.objects.get_or_create(name="spring", year=2026)
        diet_standard, _ = Diet.objects.get_or_create(
            code="STD",
            defaults={
                "title": "Standart parhez",
                "description": "Muvozanatli kundalik ovqatlanish",
            },
        )
        diet_lite, _ = Diet.objects.get_or_create(
            code="LITE",
            defaults={
                "title": "Yengil parhez",
                "description": "Hazmi yengil ratsion",
            },
        )

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

        menu_day, _ = MenuDay.objects.update_or_create(
            organization=organization,
            date=date(2026, 4, 4),
            defaults={"season": season, "diet": diet_standard, "people_count": 120},
        )
        MenuEntry.objects.filter(menu_day=menu_day).delete()
        MenuEntry.objects.create(
            menu_day=menu_day,
            mealtime=meal_lookup["first_breakfast"],
            dish=dish_lookup["Sutli suli bo'tqasi"],
            portions=120,
            notes="Bolalar uchun standart porsiya",
        )
        MenuEntry.objects.create(
            menu_day=menu_day,
            mealtime=meal_lookup["second_breakfast"],
            dish=dish_lookup["Mevali yogurt"],
            portions=120,
            notes="Mevali yengil tamaddi",
        )
        MenuEntry.objects.create(
            menu_day=menu_day,
            mealtime=meal_lookup["lunch"],
            dish=dish_lookup["Tovuqli sabzavot sho'rva"],
            portions=120,
            notes="Asosiy issiq ovqat",
        )
        MenuEntry.objects.create(
            menu_day=menu_day,
            mealtime=meal_lookup["buffet"],
            dish=dish_lookup["Qaynatilgan guruch"],
            portions=120,
            notes="Qo'shimcha garnir",
        )
        MenuEntry.objects.create(
            menu_day=menu_day,
            mealtime=meal_lookup["dinner"],
            dish=dish_lookup["Bug'da pishgan baliq va brokkoli"],
            portions=120,
            notes="Kechki yengil taom",
        )

        self.stdout.write(self.style.SUCCESS("Demo organization created/updated successfully."))
        self.stdout.write(f"Organization: {organization.name}")
        self.stdout.write(f"Login: {username}")
        self.stdout.write(f"Password: {password}")
