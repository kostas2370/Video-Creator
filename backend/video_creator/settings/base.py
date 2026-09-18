from pathlib import Path
import base64
import hashlib
import os
from datetime import timedelta

# Paths
# settings/ is a package now, so BASE_DIR is three parents up rather than two.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Security
# `or`, not a getenv default: .env_example ships this blank, and "" would override it.
SECRET_KEY = (
    os.getenv("SECRET_KEY")
    or "django-insecure-@e9r=i^wken32@o7$@wu=fuz$az=*m%72qoplrcsoc-b5cm&&_"
)

FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY") or base64.urlsafe_b64encode(
    hashlib.sha256(SECRET_KEY.encode()).digest()
).decode()

COOKIES_SECURE = False
CROSS_SITE_SAMESITE = "Lax"

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_cleanup.apps.CleanupConfig",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_celery_beat",
    "djoser",
    "apps.usermanagement",
    "apps.videomanagement",
    "apps.apikeysmanagement",
    "encrypted_model_fields",
    "django_rest_passwordreset",
    "corsheaders",
    "drf_yasg",
    "django_filters",
    "django_lifecycle_checks",
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "corsheaders.middleware.CorsMiddleware",
]

INTERNAL_IPS = ["127.0.0.1", "::1"]

# URL configuration
ROOT_URLCONF = "video_creator.urls"

# Authentication
AUTH_USER_MODEL = "usermanagement.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# JWT Configuration
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "AUTH_HEADER_TYPES": "Bearer",
    "AUTH_COOKIE_REFRESH": "refresh",
    "AUTH_COOKIE_SECURE": COOKIES_SECURE,
    "AUTH_COOKIE_HTTP_ONLY": True,
    "AUTH_COOKIE_SAMESITE": "Strict",
}

# Djoser Configuration
DJOSER = {
    "LOGIN_FIELD": "username",
}

CELERY_BROKER_URL = (
    os.getenv("CELERY_BROKER_URL") or "redis://redis-stack-server:6379/0"
)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or CELERY_BROKER_URL

CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True

VIDEO_TASK_STALE_AFTER = int(os.getenv("VIDEO_TASK_STALE_AFTER") or 60 * 60 * 3)

CELERY_BEAT_SCHEDULE = {
    "reap-stalled-videos": {
        "task": "apps.videomanagement.tasks.reap_stalled_videos",
        "schedule": 15 * 60.0,
    },
}

# Logging
# The root level is per-environment; local.py turns it down to INFO.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static and Media Files
STATIC_URL = "static/"
MEDIA_ROOT = os.path.join(BASE_DIR, "")
MEDIA_URL = ""

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

FRONTEND_URL = (os.getenv("FRONTEND_URL") or "http://localhost:3000").rstrip("/")
PASSWORD_RESET_PATH = os.getenv("PASSWORD_RESET_PATH") or "/reset-password"

# CORS and CSRF
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CSRF_COOKIE_SECURE = COOKIES_SECURE
CSRF_COOKIE_HTTP_ONLY = True
CSRF_COOKIE_SAMESITE = CROSS_SITE_SAMESITE
SESSION_COOKIE_SECURE = COOKIES_SECURE
SESSION_COOKIE_SAMESITE = CROSS_SITE_SAMESITE

# Django REST Framework
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.FileUploadParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "apps.usermanagement.authenticate.CustomAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
}

# Custom Settings
USER_LIMIT = int(os.getenv("USER_LIMIT", 10))
MAX_TOKENS = int(os.getenv("MAX_TOKENS") or 3900)
REASONING_TOKEN_ALLOWANCE = int(os.getenv("REASONING_TOKEN_ALLOWANCE") or 8000)
OPEN_API_KEY = os.getenv("OPEN_API_KEY")
DEFAULT_GPT_MODEL = os.getenv("DEFAULT_GPT_MODEL") or "gpt-5.4-mini"

IMAGE_MODEL = os.getenv("IMAGE_MODEL") or "gpt-image-2"
IMAGE_QUALITY = os.getenv("IMAGE_QUALITY") or "high"
IMAGE_SIZE = os.getenv("IMAGE_SIZE") or "1792x1024"

SORA_MODEL = os.getenv("SORA_MODEL") or "sora-2"
SORA_SIZE = os.getenv("SORA_SIZE") or "1280x720"
SILENT_SCENE_SECONDS = int(os.getenv("SILENT_SCENE_SECONDS") or 30)

SORA_STYLE = os.getenv("SORA_STYLE") or (
    "Consistent look across the whole video: natural lighting, shallow depth of field, "
    "warm colour grade, steady camera, photorealistic."
)

# As ImageMagick names it (`convert -list font`). The image carries only DejaVu;
# "Arial" exists on macOS and Windows but not in debian-slims.
SUBTITLE_FONT = os.getenv("SUBTITLE_FONT") or "DejaVu-Sans"

SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
API_KEY = os.getenv("API_KEY")
VISION_SELECTION = False

TWITCH_CLIENT = os.getenv("TWITCH_CLIENT")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")

XI_API_KEY = os.getenv("XI_API_KEY")
SIXTYDB_API_KEY = os.getenv("SIXTYDB_API_KEY")
DIFFUSION_KEY = os.getenv("DIFFUSION_KEY")
MIDJOURNEY_KEY = os.getenv("MIDJOURNEY_KEY")
CONFIG_PATH = "apps/videomanagement/utils/SadTalker/src/config"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
