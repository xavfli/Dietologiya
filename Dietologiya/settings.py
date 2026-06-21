import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import dj_database_url
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or os.environ.get("SECRET_KEY", "replace-this-in-production")
if not DEBUG and SECRET_KEY == "replace-this-in-production":
    raise ImproperlyConfigured("DJANGO_SECRET_KEY production muhitida majburiy.")
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost,sihatmenyu.local,dietologiya.local").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]
RENDER_EXTERNAL_HOSTNAME = os.environ.get("RENDER_EXTERNAL_HOSTNAME")
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)
    CSRF_TRUSTED_ORIGINS.append(f"https://{RENDER_EXTERNAL_HOSTNAME}")
ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "secure-admin/").strip("/")
ADMIN_PATH = f"{ADMIN_PATH}/"

if os.name == "nt":
    default_sqlite_dir = Path(os.environ.get("LOCALAPPDATA", BASE_DIR)) / "Dietologiya"
else:
    default_sqlite_dir = BASE_DIR
default_sqlite_dir.mkdir(parents=True, exist_ok=True)
default_sqlite_path = Path(os.environ.get("DJANGO_SQLITE_PATH", str(default_sqlite_dir / "db.sqlite3")))
default_database_url = f"sqlite:///{default_sqlite_path.as_posix()}"
database_url = os.environ.get("DATABASE_URL", "").strip().strip("\"'")
if not DEBUG and not database_url:
    raise ImproperlyConfigured("DATABASE_URL production muhitida majburiy.")
known_database_schemes = {
    "cockroach",
    "mssql",
    "mssqlms",
    "mysql",
    "mysql-connector",
    "mysql2",
    "mysqlgis",
    "oracle",
    "oraclegis",
    "pgsql",
    "postgis",
    "postgres",
    "postgresql",
    "redshift",
    "spatialite",
    "sqlite",
    "timescale",
    "timescalegis",
}
if database_url.startswith("://"):
    database_url = f"postgresql{database_url}"
elif database_url and "://" in database_url:
    split_database_url = urlsplit(database_url)
    if split_database_url.scheme.lower() not in known_database_schemes:
        database_url = urlunsplit(("postgresql", split_database_url.netloc, split_database_url.path, split_database_url.query, split_database_url.fragment))

try:
    default_database_config = dj_database_url.parse(
        database_url or default_database_url,
        conn_max_age=600,
    )
    if (
        default_database_config["ENGINE"] == "django.db.backends.postgresql"
        and (not default_database_config.get("HOST") or not default_database_config.get("NAME"))
    ):
        raise ValueError("Incomplete PostgreSQL DATABASE_URL")
except Exception:
    if not DEBUG:
        raise ImproperlyConfigured("Production DATABASE_URL noto'g'ri yoki to'liq emas.")
    default_database_config = dj_database_url.parse(
        default_database_url,
        conn_max_age=600,
    )

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "menu",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "Dietologiya.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "Dietologiya.wsgi.application"

DATABASES = {
    "default": default_database_config
}
if env_bool("DJANGO_REQUIRE_POSTGRES", not DEBUG) and default_database_config["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production muhitida PostgreSQL DATABASE_URL talab qilinadi.")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
MENU_IMPORT_MAX_BYTES = int(os.environ.get("MENU_IMPORT_MAX_BYTES", str(25 * 1024 * 1024)))
MENU_IMPORT_MAX_ARCHIVE_BYTES = int(os.environ.get("MENU_IMPORT_MAX_ARCHIVE_BYTES", str(100 * 1024 * 1024)))
MENU_IMPORT_MAX_ARCHIVE_FILES = int(os.environ.get("MENU_IMPORT_MAX_ARCHIVE_FILES", "100"))

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = env_bool("DJANGO_SECURE_HSTS_PRELOAD", not DEBUG)
X_FRAME_OPTIONS = "DENY"

JAZZMIN_SETTINGS = {
    "site_title": "Dietologiya Admin",
    "site_header": "Dietologiya",
    "site_brand": "Dietologiya",
    "welcome_sign": "Ovqatlanish tizimi boshqaruvi",
    "site_logo": "menu/favicon.svg",
    "site_icon": "menu/favicon.svg",
    "site_logo_classes": "img-circle",
    "show_sidebar": True,
    "navigation_expanded": True,
    "custom_css": "menu/css/admin-custom.css",
    "custom_js": "menu/js/admin-custom.js",
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "menu.Organization": "fas fa-building",
        "menu.Season": "fas fa-cloud-sun",
        "menu.Diet": "fas fa-notes-medical",
        "menu.MealTime": "fas fa-clock",
        "menu.Product": "fas fa-apple-alt",
        "menu.Dish": "fas fa-utensils",
        "menu.MenuDay": "fas fa-calendar-day",
        "menu.MenuEntry": "fas fa-list-check",
    },
}

