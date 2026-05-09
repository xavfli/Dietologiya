from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _


HUNDRED = Decimal("100")
THOUSAND = Decimal("1000")
User = get_user_model()


class Organization(models.Model):
    name = models.CharField(max_length=200)
    address = models.CharField(max_length=300, blank=True)
    contact = models.CharField(max_length=150, blank=True)
    owner = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="managed_organization")

    class Meta:
        verbose_name = "Tashkilot"
        verbose_name_plural = "Tashkilotlar"

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    class Role(models.TextChoices):
        DIRECTOR = "director", _("Direktor")
        COOK = "cook", _("Oshpaz")
        ACCOUNTANT = "accountant", _("Hisobchi")
        VIEWER = "viewer", _("Kuzatuvchi")

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="organization_membership")
    role = models.CharField(max_length=32, choices=Role.choices, default=Role.VIEWER)
    can_manage_menu = models.BooleanField(default=False)
    can_manage_prices = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=True)

    class Meta:
        ordering = ("organization__name", "user__username")
        verbose_name = "Tashkilot a'zosi"
        verbose_name_plural = "Tashkilot a'zolari"

    def __str__(self):
        return f"{self.user} - {self.organization} ({self.get_role_display()})"


class Season(models.Model):
    class SeasonName(models.TextChoices):
        WINTER = "winter", _("Qish")
        SPRING = "spring", _("Bahor")
        SUMMER = "summer", _("Yoz")
        AUTUMN = "autumn", _("Kuz")

    name = models.CharField(max_length=100, choices=SeasonName.choices)
    year = models.PositiveIntegerField()

    class Meta:
        ordering = ("-year", "name")
        verbose_name = "Mavsum"
        verbose_name_plural = "Mavsumlar"

    def __str__(self):
        return f"{self.get_name_display()} {self.year}"


class Diet(models.Model):
    code = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ("code",)
        verbose_name = "Parhez"
        verbose_name_plural = "Parhezlar"

    def __str__(self):
        return f"{self.code} - {self.title}"


class MealTime(models.Model):
    class Slot(models.TextChoices):
        FIRST_BREAKFAST = "first_breakfast", _("1-nonushta")
        SECOND_BREAKFAST = "second_breakfast", _("2-nonushta")
        LUNCH = "lunch", _("Tushlik")
        BUFFET = "buffet", _("Bufet mahsulotlari")
        DINNER = "dinner", _("Kechki ovqat")

    title = models.CharField(max_length=120, blank=True)
    slot = models.CharField(max_length=32, choices=Slot.choices, unique=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("order", "id")
        verbose_name = "Ovqatlanish vaqti"
        verbose_name_plural = "Ovqatlanish vaqtlari"

    def save(self, *args, **kwargs):
        if not self.title:
            self.title = self.get_slot_display()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Product(models.Model):
    class Unit(models.TextChoices):
        GRAM = "g", _("Gram")
        MILLILITER = "ml", _("Millilitr")

    name = models.CharField(max_length=200)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name="products")
    unit = models.CharField(max_length=8, choices=Unit.choices, default=Unit.GRAM)
    protein = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fat = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carbs = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    calories = models.PositiveIntegerField(default=0)
    price_per_kg = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        ordering = ("name",)
        verbose_name = "Mahsulot"
        verbose_name_plural = "Mahsulotlar"

    def __str__(self):
        return self.name


class PriceHistory(models.Model):
    class SourceType(models.TextChoices):
        MANUAL = "manual", _("Qo'lda")
        EXCEL = "excel", _("Excel")
        URL = "url", _("Internet jadval")
        AI = "ai", _("AI internet qidiruv")

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="price_history")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="price_history")
    old_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    source_type = models.CharField(max_length=16, choices=SourceType.choices, default=SourceType.MANUAL)
    source_label = models.CharField(max_length=300, blank=True)
    confidence = models.PositiveSmallIntegerField(default=100)
    effective_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "product__name")
        verbose_name = "Narx tarixi"
        verbose_name_plural = "Narx tarixi"

    def __str__(self):
        return f"{self.product.name}: {self.old_price} -> {self.new_price}"


class ImportJob(models.Model):
    class JobType(models.TextChoices):
        EXCEL = "excel", _("Excel import")
        PRICE_URL = "price_url", _("Internet narx")
        PRICE_AI = "price_ai", _("AI narx")
        MENU_AI = "menu_ai", _("AI menyu")

    class Status(models.TextChoices):
        PENDING = "pending", _("Kutilmoqda")
        SUCCESS = "success", _("Bajarildi")
        FAILED = "failed", _("Xatolik")

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="import_jobs")
    job_type = models.CharField(max_length=24, choices=JobType.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    source = models.CharField(max_length=500, blank=True)
    summary = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Import vazifasi"
        verbose_name_plural = "Import vazifalari"

    def __str__(self):
        return f"{self.organization} - {self.get_job_type_display()} - {self.get_status_display()}"


class Dish(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name="dishes")
    diet = models.ForeignKey(Diet, on_delete=models.SET_NULL, null=True, blank=True)
    duration_minutes = models.PositiveIntegerField(default=30)

    class Meta:
        ordering = ("name",)
        verbose_name = "Taom"
        verbose_name_plural = "Taomlar"

    def __str__(self):
        return self.name

    def _sum_decimal(self, attr_name):
        total = Decimal("0")
        for ingredient in self.ingredients.select_related("product").all():
            total += getattr(ingredient, attr_name)
        return total

    @property
    def total_weight(self):
        return sum(ingredient.grams for ingredient in self.ingredients.all())

    @property
    def total_protein(self):
        return self._sum_decimal("protein_amount")

    @property
    def total_fat(self):
        return self._sum_decimal("fat_amount")

    @property
    def total_carbs(self):
        return self._sum_decimal("carbs_amount")

    @property
    def total_calories(self):
        return round(
            sum(
                ingredient.calories_amount
                for ingredient in self.ingredients.select_related("product").all()
            )
        )

    @property
    def total_cost(self):
        return self._sum_decimal("cost_amount")


class DishIngredient(models.Model):
    dish = models.ForeignKey(Dish, related_name="ingredients", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    grams = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Taom tarkibi"
        verbose_name_plural = "Taom tarkibi"

    def __str__(self):
        return f"{self.grams}g {self.product.name}"

    def _scaled_value(self, value):
        return (Decimal(self.grams) * Decimal(value)) / HUNDRED

    @property
    def protein_amount(self):
        return self._scaled_value(self.product.protein)

    @property
    def fat_amount(self):
        return self._scaled_value(self.product.fat)

    @property
    def carbs_amount(self):
        return self._scaled_value(self.product.carbs)

    @property
    def calories_amount(self):
        return (Decimal(self.grams) * Decimal(self.product.calories)) / HUNDRED

    @property
    def cost_amount(self):
        return (Decimal(self.grams) * self.product.price_per_kg) / THOUSAND


class MenuDay(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateField()
    diet = models.ForeignKey(Diet, on_delete=models.SET_NULL, null=True, blank=True)
    people_count = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("-date", "organization__name")
        verbose_name = "Menyu kuni"
        verbose_name_plural = "Menyu kunlari"

    def __str__(self):
        return f"{self.organization.name} - {self.date}"

    @property
    def total_cost(self):
        total = Decimal("0")
        for entry in self.entries.select_related("dish").all():
            total += entry.total_cost
        return total

    @property
    def per_person_cost(self):
        if not self.people_count:
            return Decimal("0")
        return self.total_cost / Decimal(self.people_count)

    @property
    def total_calories(self):
        return sum(entry.total_calories for entry in self.entries.select_related("dish").all())


class MenuEntry(models.Model):
    menu_day = models.ForeignKey(MenuDay, related_name="entries", on_delete=models.CASCADE)
    mealtime = models.ForeignKey(MealTime, on_delete=models.PROTECT)
    dish = models.ForeignKey(Dish, on_delete=models.PROTECT)
    portions = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ("mealtime__order", "id")
        verbose_name = "Menyu yozuvi"
        verbose_name_plural = "Menyu yozuvlari"

    def __str__(self):
        return f"{self.menu_day} / {self.mealtime} / {self.dish}"

    @property
    def total_cost(self):
        return self.dish.total_cost * self.portions

    @property
    def total_calories(self):
        return self.dish.total_calories * self.portions

    @property
    def total_protein(self):
        return self.dish.total_protein * self.portions

    @property
    def total_fat(self):
        return self.dish.total_fat * self.portions

    @property
    def total_carbs(self):
        return self.dish.total_carbs * self.portions


class MenuAlert(models.Model):
    class Severity(models.TextChoices):
        INFO = "info", _("Ma'lumot")
        WARNING = "warning", _("Ogohlantirish")
        DANGER = "danger", _("Xavf")

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="menu_alerts")
    menu_day = models.ForeignKey(MenuDay, on_delete=models.CASCADE, related_name="alerts", null=True, blank=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    severity = models.CharField(max_length=16, choices=Severity.choices, default=Severity.WARNING)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("is_resolved", "-created_at")
        verbose_name = "Menyu ogohlantirishi"
        verbose_name_plural = "Menyu ogohlantirishlari"

    def __str__(self):
        return self.title


class AISuggestion(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="ai_suggestions")
    prompt = models.TextField()
    response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "AI menyu tavsiyasi"
        verbose_name_plural = "AI menyu tavsiyalari"

    def __str__(self):
        return f"AI tavsiya - {self.organization} - {self.created_at:%Y-%m-%d}"


class TelegramSubscription(models.Model):
    organization = models.OneToOneField(Organization, on_delete=models.CASCADE, related_name="telegram_subscription")
    chat_id = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    daily_digest = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Telegram sozlama"
        verbose_name_plural = "Telegram sozlamalari"

    def __str__(self):
        return f"{self.organization} - {self.chat_id}"
