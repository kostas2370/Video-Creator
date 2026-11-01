from pathlib import Path
import base64
import hashlib
import json
import os
from datetime import timedelta
from urllib.parse import unquote, urlparse

from video_creator.model_catalog import current_script_model

# Paths
# settings/ is a package now, so BASE_DIR is three parents up rather than two.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SPEECH_TRANSCRIPTION_PROVIDER = os.getenv("SPEECH_TRANSCRIPTION_PROVIDER") or "openai"
LOCAL_WHISPER_URL = os.getenv("LOCAL_WHISPER_URL") or "http://whisper:9000"
AI_COST_RATES = json.loads(os.getenv("AI_COST_RATES") or "{}")
LOCAL_WHISPER_TIMEOUT = int(os.getenv("LOCAL_WHISPER_TIMEOUT") or 1800)
YOUTUBE_CAPTIONS_ENABLED = (os.getenv("YOUTUBE_CAPTIONS_ENABLED") or "true").lower() == "true"

# Security
# `or`, not a getenv default: .env_example ships this blank, and "" would override it.
SECRET_KEY = (
    os.getenv("SECRET_KEY")
    or "REMOVED_EXPOSED_CREDENTIAL"
)

FIELD_ENCRYPTION_KEY = (
    os.getenv("FIELD_ENCRYPTION_KEY")
    or base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest()).decode()
)

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
    "django_eventstream",
    "rest_framework_simplejwt.token_blacklist",
    "django_celery_beat",
    "apps.usermanagement",
    "apps.videomanagement",
    "apps.usage",
    "apps.series",
    "apps.clips",
    "apps.news",
    "apps.publishing",
    "apps.apikeysmanagement",
    "encrypted_model_fields",
    "django_rest_passwordreset",
    "corsheaders",
    "drf_yasg",
    "django_filters",
    "django_lifecycle_checks",
]

# Domain extensions run explicitly without importing feature apps into video models.
VIDEO_WORKFLOW_HOOKS = {
    "storyboard_generated": ["apps.series.hooks.prepare_episode_storyboard"],
    "video_saved": ["apps.series.hooks.mark_episode_canon"],
}

# Middleware
MIDDLEWARE = [
    "video_creator.observability.request_logging",
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

REMEMBER_ME_REFRESH_LIFETIME = timedelta(days=int(os.getenv("REMEMBER_ME_DAYS") or 30))

CELERY_BROKER_URL = (
    os.getenv("CELERY_BROKER_URL") or "redis://redis-stack-server:6379/0"
)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND") or CELERY_BROKER_URL

VIDEO_EVENTS_REDIS_URL = os.getenv("VIDEO_EVENTS_REDIS_URL") or CELERY_BROKER_URL
event_redis_url = urlparse(VIDEO_EVENTS_REDIS_URL)
EVENTSTREAM_REDIS = {
    "host": event_redis_url.hostname or "localhost",
    "port": event_redis_url.port or 6379,
    "db": int(event_redis_url.path.strip("/") or "0"),
    "username": unquote(event_redis_url.username) if event_redis_url.username else None,
    "password": unquote(event_redis_url.password) if event_redis_url.password else None,
    "ssl": event_redis_url.scheme == "rediss",
    "socket_connect_timeout": 1,
}

CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TRACK_STARTED = True

# Keep CPU-heavy exports away from scene edits, generation and maintenance jobs.
CELERY_TASK_ROUTES = {
    "apps.clips.tasks.export_clip_task": {"queue": "renders"},
    "apps.videomanagement.tasks.render_video_task": {"queue": "renders"},
}

VIDEO_TASK_STALE_AFTER = int(os.getenv("VIDEO_TASK_STALE_AFTER") or 60 * 60 * 3)

CELERY_BEAT_SCHEDULE = {
    "purge-expired-deleted-scenes": {
        "task": "apps.videomanagement.tasks.purge_deleted_scenes",
        "schedule": 24 * 60 * 60.0,
    },
    "reap-stalled-clip-exports": {
        "task": "apps.clips.tasks.reap_stalled_clip_exports",
        "schedule": 60.0,
    },
    "reap-stalled-videos": {
        "task": "apps.videomanagement.tasks.reap_stalled_videos",
        "schedule": 15 * 60.0,
    },
}

# Logging
# JSON console output is shared by the API and Celery workers.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"json": {"()": "video_creator.observability.JsonFormatter"}},
    "handlers": {
        "console": {
            "formatter": "json",
            "level": os.getenv("LOG_LEVEL") or "INFO",
            "class": "logging.StreamHandler",
        },
    },
    "loggers": {
        "django": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "celery.app.trace": {"level": "WARNING"},
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL") or "INFO",
    },
}

# Keep the same JSON formatter in Celery instead of replacing root handlers.
CELERY_WORKER_HIJACK_ROOT_LOGGER = False

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

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "kostas2372@gmail.com")

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
CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken", "X-Request-ID"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]
CSRF_COOKIE_SECURE = COOKIES_SECURE
CSRF_COOKIE_HTTP_ONLY = True
CSRF_COOKIE_SAMESITE = CROSS_SITE_SAMESITE
SESSION_COOKIE_SECURE = COOKIES_SECURE
SESSION_COOKIE_SAMESITE = CROSS_SITE_SAMESITE

# Django REST Framework
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "video_creator.exceptions.api_exception_handler",
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
TRUSTED_PROXY_HOPS = int(os.getenv("TRUSTED_PROXY_HOPS") or 0)
TEST_RUNNER = "video_creator.test_runner.ServiceKeysRunner"

MAX_TOKENS = int(os.getenv("MAX_TOKENS") or 3900)
REASONING_TOKEN_ALLOWANCE = int(os.getenv("REASONING_TOKEN_ALLOWANCE") or 8000)
OPEN_API_KEY = os.getenv("OPEN_API_KEY")
DEFAULT_GPT_MODEL = current_script_model(os.getenv("DEFAULT_GPT_MODEL") or "gpt-5.4-mini")

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

SUBTITLE_FONT = os.getenv("SUBTITLE_FONT") or "DejaVu Sans"

SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID")
API_KEY = os.getenv("API_KEY")
VISION_SELECTION = False


XI_API_KEY = os.getenv("XI_API_KEY")
SIXTYDB_API_KEY = os.getenv("SIXTYDB_API_KEY")
DIFFUSION_KEY = os.getenv("DIFFUSION_KEY")
MIDJOURNEY_KEY = os.getenv("MIDJOURNEY_KEY")
CONFIG_PATH = "vendor/sadtalker/src/config"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


ACCEPTED_MODELS = [
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4-turbo",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4.1",
    "gpt-4.1-mini",
    "gpt-4.1-nano",
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "gpt-5-chat-latest",
    "gpt-5.1",
    "gpt-5.1-chat-latest",
    "gpt-5.2",
    "gpt-5.2-chat-latest",
    "gpt-5.3-chat-latest",
    "gpt-5.4",
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.5",
    "gpt-5.6-luna",
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-6-astra",
    "o1",
    "o3",
    "o3-mini",
    "o4-mini",
    "claude-sonnet-5-5",
    "gemini-4-argon",
    "gemini-3.8-flash",
    "gemini-3.5-flash-lite",
]

FFMPEG_RENDER_TIMEOUT = int(os.getenv("FFMPEG_RENDER_TIMEOUT") or "3600")
FFMPEG_DIRECT_RENDER = (os.getenv("FFMPEG_DIRECT_RENDER") or "true").lower() not in (
    "false",
    "0",
    "no",
)
FFMPEG_SCENE_CACHE_ROOT = (
    os.getenv("FFMPEG_SCENE_CACHE_ROOT") or BASE_DIR / "private-render-cache"
)
FFMPEG_SCENE_CACHE_BYTES = int(os.getenv("FFMPEG_SCENE_CACHE_BYTES") or 512 * 1024 * 1024)
FFMPEG_SCENE_CACHE_TTL = int(os.getenv("FFMPEG_SCENE_CACHE_TTL") or 24 * 60 * 60)

# Creator account connections. Secrets stay on the server; register the callback URLs
# documented in docs/social-publishing.md with each developer application.
SOCIAL_PUBLIC_BASE_URL = (os.getenv("SOCIAL_PUBLIC_BASE_URL") or "").rstrip("/")
SOCIAL_PUBLISHING = {
    platform: {
        "client_id": os.getenv(prefix + "_CLIENT_ID", ""),
        "client_secret": os.getenv(prefix + "_CLIENT_SECRET", ""),
        "api_version": os.getenv("SOCIAL_META_API_VERSION", ""),
    }
    for platform, prefix in (
        ("youtube", "SOCIAL_YOUTUBE"), ("tiktok", "SOCIAL_TIKTOK"),
        ("instagram", "SOCIAL_INSTAGRAM"),
    )
}

# Keep publishing snapshots outside the public MEDIA_ROOT.
PUBLISHING_SNAPSHOT_ROOT = os.getenv("PUBLISHING_SNAPSHOT_ROOT") or BASE_DIR / "private-publishing"

# Built-in video providers use the existing service/personal key selection.
FAL_KEY = os.getenv("FAL_KEY")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY")
VIDEO_GENERATION_TIMEOUT = 900
VIDEO_POLL_INTERVAL = 5

CLIP_STORAGE_ROOT = os.getenv("CLIP_STORAGE_ROOT") or None
