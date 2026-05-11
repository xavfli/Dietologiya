from django.contrib import admin

from .models import (
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
    TelegramSubscription,
)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "address", "contact")
    search_fields = ("name", "address", "contact", "owner__username")


@admin.register(OrganizationMember)
class OrganizationMemberAdmin(admin.ModelAdmin):
    list_display = ("user", "organization", "role", "can_manage_menu", "can_manage_prices", "can_view_reports")
    list_filter = ("role", "organization")
    search_fields = ("user__username", "organization__name")


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "year")
    list_filter = ("name", "year")


@admin.register(Diet)
class DietAdmin(admin.ModelAdmin):
    list_display = ("code", "title")
    search_fields = ("code", "title")


@admin.register(MealTime)
class MealTimeAdmin(admin.ModelAdmin):
    list_display = ("title", "slot", "order")
    list_editable = ("order",)
    ordering = ("order",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "unit", "protein", "fat", "carbs", "calories", "price_per_kg")
    search_fields = ("name",)
    list_filter = ("unit", "organization")


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    list_display = ("product", "organization", "old_price", "new_price", "source_type", "confidence", "created_at")
    list_filter = ("source_type", "organization", "created_at")
    search_fields = ("product__name", "source_label")


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ("organization", "job_type", "status", "source", "created_at", "completed_at")
    list_filter = ("job_type", "status", "organization")
    search_fields = ("organization__name", "source", "summary")


class DishIngredientInline(admin.TabularInline):
    model = DishIngredient
    extra = 1


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "diet", "duration_minutes", "total_weight", "total_calories", "total_cost")
    list_filter = ("diet", "organization")
    search_fields = ("name",)
    inlines = [DishIngredientInline]


@admin.register(MenuDay)
class MenuDayAdmin(admin.ModelAdmin):
    list_display = ("organization", "date", "season", "diet", "people_count", "total_cost")
    list_filter = ("season", "diet", "date")
    search_fields = ("organization__name",)
    date_hierarchy = "date"


@admin.register(MenuEntry)
class MenuEntryAdmin(admin.ModelAdmin):
    list_display = ("menu_day", "mealtime", "dish", "portions", "total_cost")
    list_filter = ("mealtime",)
    search_fields = ("dish__name", "menu_day__organization__name")


@admin.register(MenuAlert)
class MenuAlertAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "menu_day", "severity", "is_resolved", "created_at")
    list_filter = ("severity", "is_resolved", "organization")
    search_fields = ("title", "message", "organization__name")


@admin.register(TelegramSubscription)
class TelegramSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("organization", "chat_id", "is_active", "daily_digest")
    list_filter = ("is_active", "daily_digest")
