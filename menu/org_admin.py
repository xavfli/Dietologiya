from django.contrib import admin
from django.contrib.admin import AdminSite
from django.db.models import Q

from .models import Diet, Dish, MealTime, MenuAlert, MenuDay, MenuEntry, PriceHistory, Product, Season
from .services import get_user_organization


class OrganizationAdminSite(AdminSite):
    site_header = "Tashkilot kabineti"
    site_title = "Tashkilot kabineti"
    index_title = "Retsept va natijalarni boshqarish"

    def has_permission(self, request):
        return request.user.is_active and bool(get_user_organization(request.user))


organization_admin_site = OrganizationAdminSite(name="organization_admin")


class OrganizationScopedAdmin(admin.ModelAdmin):
    organization_field = "organization"

    def get_organization(self, request):
        return get_user_organization(request.user)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(**{self.organization_field: self.get_organization(request)})

    def save_model(self, request, obj, form, change):
        setattr(obj, self.organization_field, self.get_organization(request))
        super().save_model(request, obj, form, change)

    def has_module_permission(self, request):
        return bool(get_user_organization(request.user))

    def has_view_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))

    def has_add_permission(self, request):
        return bool(get_user_organization(request.user))

    def has_change_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))

    def has_delete_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))


class OrganizationReadOnlyMixin:
    def has_module_permission(self, request):
        return bool(get_user_organization(request.user))

    def has_view_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        fields = [field.name for field in self.model._meta.fields]
        return fields


@admin.register(Season, site=organization_admin_site)
class OrganizationSeasonAdmin(OrganizationReadOnlyMixin, admin.ModelAdmin):
    list_display = ("name", "year")
    list_filter = ("name", "year")


@admin.register(Diet, site=organization_admin_site)
class OrganizationDietAdmin(OrganizationReadOnlyMixin, admin.ModelAdmin):
    list_display = ("code", "title")
    search_fields = ("code", "title")


@admin.register(MealTime, site=organization_admin_site)
class OrganizationMealTimeAdmin(OrganizationReadOnlyMixin, admin.ModelAdmin):
    list_display = ("title", "slot", "order")
    ordering = ("order",)


@admin.register(Dish, site=organization_admin_site)
class OrganizationDishAdmin(OrganizationReadOnlyMixin, OrganizationScopedAdmin):
    list_display = ("name", "diet", "duration_minutes", "total_calories", "total_cost")
    list_filter = ("diet",)
    fields = ("name", "diet", "duration_minutes", "description")
    search_fields = ("name",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "diet":
            kwargs["queryset"] = Diet.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Product, site=organization_admin_site)
class OrganizationProductAdmin(OrganizationReadOnlyMixin, OrganizationScopedAdmin):
    list_display = ("name", "unit", "protein", "fat", "carbs", "calories", "price_per_kg")
    list_filter = ("unit",)
    search_fields = ("name",)
    fields = ("name", "unit", "protein", "fat", "carbs", "calories", "price_per_kg")


@admin.register(PriceHistory, site=organization_admin_site)
class OrganizationPriceHistoryAdmin(OrganizationReadOnlyMixin, OrganizationScopedAdmin):
    list_display = ("product", "old_price", "new_price", "source_type", "created_at")
    list_filter = ("source_type", "created_at")
    search_fields = ("product__name",)

    fields = ("product", "organization", "old_price", "new_price", "source_type", "source_label", "confidence", "effective_date", "created_at")


@admin.register(MenuAlert, site=organization_admin_site)
class OrganizationMenuAlertAdmin(OrganizationScopedAdmin):
    list_display = ("title", "menu_day", "severity", "is_resolved", "created_at")
    list_filter = ("severity", "is_resolved")
    search_fields = ("title", "message")


@admin.register(MenuDay, site=organization_admin_site)
class OrganizationMenuDayAdmin(OrganizationScopedAdmin):
    list_display = ("date", "season", "diet", "people_count", "total_cost")
    list_filter = ("season", "diet")
    date_hierarchy = "date"
    fields = ("date", "season", "diet", "people_count")


@admin.register(MenuEntry, site=organization_admin_site)
class OrganizationMenuEntryAdmin(admin.ModelAdmin):
    list_display = ("menu_day", "mealtime", "dish", "portions", "total_cost")
    fields = ("menu_day", "mealtime", "dish", "portions", "notes")

    def get_organization(self, request):
        return get_user_organization(request.user)

    def get_queryset(self, request):
        return super().get_queryset(request).filter(menu_day__organization=self.get_organization(request))

    def has_module_permission(self, request):
        return bool(get_user_organization(request.user))

    def has_view_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))

    def has_add_permission(self, request):
        return bool(get_user_organization(request.user))

    def has_change_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))

    def has_delete_permission(self, request, obj=None):
        return bool(get_user_organization(request.user))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = self.get_organization(request)
        if db_field.name == "menu_day":
            kwargs["queryset"] = MenuDay.objects.filter(organization=organization)
        elif db_field.name == "dish":
            kwargs["queryset"] = Dish.objects.filter(Q(organization=organization) | Q(organization__isnull=True))
        elif db_field.name == "mealtime":
            kwargs["queryset"] = MealTime.objects.all()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.menu_day.organization = self.get_organization(request)
        super().save_model(request, obj, form, change)
