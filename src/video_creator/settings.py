from pathlib import Path
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()


AUTH_USER_MODEL = 'usermanagement.User'


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-@e9r=i^wken32@o7$@wu=fuz$az=*m%72qoplrcsoc-b5cm&&_"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


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

# Application definition

INSTALLED_APPS = [
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_cleanup.apps.CleanupConfig',
    'rest_framework',
    'django_celery_beat',
    'djoser',
    'apps.usermanagement',
    'apps.videomanagement',
    'django_rest_passwordreset',
    'corsheaders',
    'drf_yasg'


]

MEDIA_ROOT = os.path.join(BASE_DIR, "")
MEDIA_URL = ""


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware'

]

ROOT_URLCONF = 'video_creator.urls'
CSRF_TRUSTED_ORIGINS = ['http://localhost:3000']

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

WSGI_APPLICATION = 'video_creator.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases
if os.getenv("ENV", "dev") == 'prod':
    DATABASES = {'default': {
                    'ENGINE': 'django.db.backends.mysql',
                    'NAME': os.getenv('MYSQL_DATABASE', 'db'),
                    'USER': os.getenv('MYSQL_USER'),
                    'PASSWORD': os.getenv('MYSQL_PASSWORD'),
                    'HOST': os.getenv('MYSQL_HOST'),  # Or an IP Address that your DB is hosted on
                    'PORT': '3307'
                    }
                 }

else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CELERY_BROKER_URL = "redis://127.0.0.1:6379"

AUTHENTICATION_BACKENDS = [

    # Django ModelBackend is the default authentication backend.
    'django.contrib.auth.backends.ModelBackend',
]


SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=100),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': 'Bearer',
}

DJOSER = {
    'LOGIN_FIELD': 'username'
}


EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
EMAIL_PORT = os.environ.get("EMAIL_PORT", 587)
EMAIL_USE_TLS = True
EMAIL_USE_SSL = False


REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.FileUploadParser'
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ['rest_framework.permissions.AllowAny', ]
}

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True


GPT_OFFICIAL = True
MAX_TOKENS = os.getenv("MAX_TOKENS", 3900) # Max Tokens
OPEN_API_KEY = os.getenv("OPEN_API_KEY")    # Open AI api key
DEFAULT_GPT_MODEL = os.getenv("DEFAULT_GPT_MODEL", "gpt-4o")


SEARCH_ENGINE_ID = os.getenv('SEARCH_ENGINE_ID')    # SEARCH ENGINE ID FOR GOOGLE IMAGES
API_KEY = os.getenv('API_KEY')  # GOOGLE API ID
VISION_SELECTION = False

TWITCH_CLIENT = os.getenv('TWITCH_CLIENT')
TWITCH_CLIENT_SECRET = os.getenv('TWITCH_CLIENT_SECRET')

XI_API_KEY = os.getenv('XI_API_KEY')
DIFFUSION_KEY = os.getenv('DIFFUSION_KEY')
MIDJOURNEY_KEY = os.getenv('MIDJOURNEY_KEY')
CONFIG_PATH = "apps/videomanagement/utils/SadTalker/src/config"
