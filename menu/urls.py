from django.urls import path
from .views import (
    AllMenuWordExportView,
    HomeView,
    LatestMenuWordExportView,
    NewsListView,
    OrganizationListView,
    OrganizationLoginView,
    ProfileView,
    health_check,
    logout_view,
)

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("organizations/", OrganizationListView.as_view(), name="organization_list"),
    path("news/", NewsListView.as_view(), name="news"),
    path("login/", OrganizationLoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/export-word/", LatestMenuWordExportView.as_view(), name="profile_export_word"),
    path("profile/export-all-word/", AllMenuWordExportView.as_view(), name="profile_export_all_word"),
    path("healthz", health_check, name="health_check"),
    path("logout/", logout_view, name="logout"),
]
