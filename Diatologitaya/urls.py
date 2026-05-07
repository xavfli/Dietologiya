from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

from menu.org_admin import organization_admin_site

urlpatterns = [
    path("admin/", admin.site.urls),
    path("organization-admin/", organization_admin_site.urls),
    path("favicon.ico", RedirectView.as_view(url="/static/menu/favicon.svg", permanent=True)),
    path("", include("menu.urls")),
]

handler400 = "menu.error_views.bad_request"
handler403 = "menu.error_views.permission_denied"
handler404 = "menu.error_views.page_not_found"
handler500 = "menu.error_views.server_error"
