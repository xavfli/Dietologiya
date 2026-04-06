from django.contrib import admin

from .models import Diet, Dish, DishIngredient, MealTime, MenuDay, MenuEntry, Organization, Product, Season


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "address", "contact")
    search_fields = ("name", "address", "contact", "owner__username")


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
