from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

# Load environment variables
load_dotenv()

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Security
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-@e9r=i^wken32@o7$@wu=fuz$az=*m%72qoplrcsoc-b5cm&&_")
DEBUG = True
ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    'rest_framework_simplejwt.token_blacklist',
    'django_celery_beat',
    'djoser',
    'apps.usermanagement',
    'apps.videomanagement',
    'django_rest_passwordreset',
    'corsheaders',
    'drf_yasg',
    'debug_toolbar'
]

# Middleware
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "debug_toolbar.middleware.DebugToolbarMiddleware",

    'corsheaders.middleware.CorsMiddleware',
]

INTERNAL_IPS = ["127.0.0.1", "::1"]

# URL configuration
ROOT_URLCONF = 'video_creator.urls'

# Database
if os.getenv("ENV", "dev") == 'prod':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('MYSQL_DATABASE', 'db'),
            'USER': os.getenv('MYSQL_USER'),
            'PASSWORD': os.getenv('MYSQL_PASSWORD'),
            'HOST': os.getenv('MYSQL_HOST'),
            'PORT': '3307',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Authentication
AUTH_USER_MODEL = 'usermanagement.User'
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# JWT Configuration
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': 'Bearer',
    'AUTH_COOKIE_REFRESH': 'refresh',
    'AUTH_COOKIE_SECURE': True,
    'AUTH_COOKIE_HTTP_ONLY': True,
    'AUTH_COOKIE_SAMESITE': 'Strict'
}

# Djoser Configuration
DJOSER = {
    'LOGIN_FIELD': 'username',
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER", "redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_BACKEND", "redis://127.0.0.1:6379/0")

# Logging
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
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static and Media Files
STATIC_URL = 'static/'
MEDIA_ROOT = os.path.join(BASE_DIR, "")
MEDIA_URL = ""

# Templates
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Email Configuration
EMAIL_BACKEND = os.getenv("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")
EMAIL_PORT = os.getenv("EMAIL_PORT", 587)
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False

# CORS and CSRF
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ORIGIN_ALLOW_ALL = True
CORS_EXPOSE_HEADERS = ["Content-Type", "X-CSRFToken"]
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000', 'http://127.0.0.1:3000']
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTP_ONLY = True
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.FileUploadParser',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': ('apps.usermanagement.authenticate.CustomAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.IsAuthenticated',],
}

# Custom Settings
USER_LIMIT = int(os.getenv("USER_LIMIT", 10))
GPT_OFFICIAL = True
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 3900))
OPEN_API_KEY = os.getenv("OPEN_API_KEY")
DEFAULT_GPT_MODEL = os.getenv("DEFAULT_GPT_MODEL", "gpt-4o")

SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')
API_KEY = os.getenv('API_KEY')
VISION_SELECTION = False

TWITCH_CLIENT = os.getenv('TWITCH_CLIENT')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

XI_API_KEY = os.getenv('XI_API_KEY')
DIFFUSION_KEY = os.getenv('DIFFUSION_KEY')
MIDJOURNEY_KEY = os.getenv('MIDJOURNEY_KEY')
CONFIG_PATH = "apps/videomanagement/utils/SadTalker/src/config"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
