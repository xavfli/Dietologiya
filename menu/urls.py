from django.urls import path
from .views import (
    AllMenuWordExportView,
    HomeView,
    LatestMenuWordExportView,
    NewsListView,
    OrganizationListView,
    OrganizationLoginView,
    ProfileView,
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
    path("logout/", logout_view, name="logout"),
]
