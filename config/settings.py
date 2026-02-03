"""
Django settings for config project.
Standard Production-Ready Configuration.
"""

import os
from pathlib import Path
import environ
from datetime import timedelta
from django.templatetags.static import static
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

# 1. تهيئة البيئة
env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent, '.env'))

BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# 🛡️ CORE SECURITY
# ==============================================================================

DEBUG = env.bool('DJANGO_DEBUG', False)
SECRET_KEY = env('DJANGO_SECRET_KEY')
DB_ENCRYPTION_KEY = env('DB_ENCRYPTION_KEY')

# السماح بالدومينات (بما فيها IP الشبكة المحلية للهاتف)
ALLOWED_HOSTS = env.list('DJANGO_ALLOWED_HOSTS', default=['localhost', '127.0.0.1', '*'])

# ==============================================================================
# 🧩 APPS & MIDDLEWARE
# ==============================================================================

INSTALLED_APPS = [
    'daphne',
    
    # UI Theme
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.import_export",

    # Django Core
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    # Third Party
    'channels',
    'csp',
    'axes',
    # unfold
    "import_export",
    # Local Apps
    'apps.accounts',
    'apps.chat',
    'apps.core',
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "csp.middleware.CSPMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "axes.middleware.AxesMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = 'config.asgi.application'



# ==============================================================================
# 🌐 INTERNATIONALIZATION
# ==============================================================================
LANGUAGE_CODE = "en-us"
TIME_ZONE = 'Europe/Oslo'
USE_I18N = True
USE_TZ = True

# ==============================================================================
# 🗄️ DATABASE & CACHE
# ==============================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'camp_medical_db',
        'USER': 'postgres',
        'PASSWORD': env('DB_PASSWORD'), 
        'HOST': 'host.docker.internal',
        'PORT': '5432',
    }
}

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(env('REDIS_HOST', default='redis'), 6379)],
        },
    },
}

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": f"redis://{env('REDIS_HOST', default='redis')}:6379/1",
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"}
    }
}

# ==============================================================================
# 🔒 AUTH & SECURITY
# ==============================================================================

AUTH_USER_MODEL = 'accounts.User'

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# إعدادات الحماية من التخمين
AXES_FAILURE_LIMIT = 5          
AXES_COOLOFF_TIME = timedelta(minutes=10)     
AXES_RESET_ON_SUCCESS = True    
AXES_LOCKOUT_TEMPLATE = 'accounts/lockout.html'
AXES_CLIENT_IP_CALLABLE = 'apps.core.utils.get_client_ip'

# ==============================================================================
# 🧠 AI SERVICES
# ==============================================================================
AZURE_TRANSLATOR_KEY = env('AZURE_TRANSLATOR_KEY')
AZURE_TRANSLATOR_ENDPOINT = env('AZURE_TRANSLATOR_ENDPOINT')
AZURE_TRANSLATOR_REGION = env('AZURE_TRANSLATOR_REGION')

AZURE_OPENAI_ENDPOINT = env('AZURE_OPENAI_ENDPOINT')
AZURE_OPENAI_KEY = env('AZURE_OPENAI_KEY')
AZURE_OPENAI_DEPLOYMENT_NAME = env('AZURE_OPENAI_DEPLOYMENT_NAME', default='gpt-4o')

# ==============================================================================
# 🐇 CELERY
# ==============================================================================
CELERY_BROKER_URL = f"redis://{env('REDIS_HOST', default='redis')}:6379/0"
CELERY_RESULT_BACKEND = f"redis://{env('REDIS_HOST', default='redis')}:6379/0"
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_WORKER_CONCURRENCY = 2

from celery.schedules import crontab
CELERY_BEAT_SCHEDULE = {
    'epidemic-warning-every-15-minutes': {
        'task': 'apps.chat.tasks.check_epidemic_outbreak',
        'schedule': crontab(minute='*/15'), 
    },
}

# ==============================================================================
# 🎨 STATIC & MEDIA & UI
# ==============================================================================
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / 'templates'],
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

# إعدادات Unfold
UNFOLD = {
    "SITE_TITLE": "Medical Support System",
    "SITE_HEADER": "Camp Administration",
    "SITE_URL": "/auth/login/",
    "COLORS": {
        "primary": {
            "50": "240 253 250",
            "100": "204 251 241",
            "200": "153 246 228",
            "300": "94 234 212",
            "400": "45 212 191",
            "500": "20 184 166",
            "600": "13 148 136",
            "700": "15 118 110",
            "800": "17 94 89",
            "900": "19 78 74",
            "950": "4 47 46",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": _("Overview"),
                "separator": False,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("custom_dashboard"),
                    },
                ],
            },
            {
                "title": _("Medical Operations"),
                "separator": True,
                "items": [
                    {
                        "title": _("Live Chat"),
                        "icon": "forum",
                        "link": reverse_lazy("admin:chat_chatsession_changelist"),
                        "permission": lambda request: request.user.is_staff,
                    },
                    {
                        "title": _("Epidemic Alerts"),
                        "icon": "coronavirus",
                        "link": reverse_lazy("admin:chat_epidemicalert_changelist"),
                    },
                    {
                        "title": _("Emergency Keywords"),
                        "icon": "warning",
                        "link": reverse_lazy("admin:chat_dangerkeyword_changelist"),
                    },
                ],
            },
            {
                "title": _("Users & Staff"),
                "separator": True,
                "items": [
                    {
                        "title": _("Refugees & Nurses"),
                        "icon": "group",
                        "link": reverse_lazy("admin:accounts_user_changelist"),
                    },
                ],
            },
        ],
    },
    "STYLES": [lambda request: static("css/admin_sticky.css")],
}



# ==============================================================================
# 🚧 REDIRECTS & EMAIL
# ==============================================================================
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ==============================================================================
# 👮 CSP & Security (Web Focused)
# ==============================================================================

# قائمة المصادر الموثوقة (يجب إضافة العناوين التي تفتح منها الموقع)
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://192.168.1.50:8000", # IP جهازك
]

CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "script-src": ["'self'", "'unsafe-inline'", "'unsafe-eval'"],
        "style-src": ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        "font-src": ["'self'", "data:", "https://fonts.gstatic.com"],
        "img-src": ["'self'", "data:", "https://www.gravatar.com"],
        
        "connect-src": [
            "'self'",
            "ws://localhost:8000",
            "ws://127.0.0.1:8000",
            "ws://host.docker.internal:8000",
            "ws://192.168.1.50:8000", # IP جهازك للموبايل
        ],
    }
}

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True