import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get('DJANGO_DEBUG', 'True') == 'True'

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'dev-insecure-secret-key-do-not-use-in-production'
    else:
        raise ImproperlyConfigured('DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=False')

# Multi-tenancy means subdomains aren't known in advance, so the wildcard
# default only applies in DEBUG. Set DJANGO_ALLOWED_HOSTS (comma-separated)
# for production; a leading dot matches the bare domain and all subdomains.
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('DJANGO_ALLOWED_HOSTS', '*' if DEBUG else '.localhost,localhost,127.0.0.1').split(',')
    if h.strip()
]

# Tenants configuration (django-tenants)
TENANT_MODEL = 'tenants.Client'  # app.Model
TENANT_DOMAIN_MODEL = 'tenants.Domain'

# Shared apps (public schema)
SHARED_APPS = (
    'django_tenants',
    'corsheaders',
    'accounts',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tenants',
    'rest_framework.authtoken',
)

# Apps that will be created per-tenant
TENANT_APPS = (
    'django.contrib.admin',
    'rest_framework',
    'core',
)

INSTALLED_APPS = list(SHARED_APPS) + list(TENANT_APPS)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django_tenants.middleware.main.TenantMainMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

ROOT_URLCONF = 'project.urls'
PUBLIC_SCHEMA_URLCONF = 'project.urls'

DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.environ.get('POSTGRES_DB', 'multi_tenant_db'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'postgres'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

# django-tenants requires a database router to manage tenant syncs
DATABASE_ROUTERS = ['django_tenants.routers.TenantSyncRouter']

AUTH_USER_MODEL = 'accounts.User'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Minimal templates setting required for admin and other template rendering
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

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ),
    'DEFAULT_THROTTLE_RATES': {
        'anon': '20/minute',
        'user': '120/minute',
    },
}

# Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'run-audit-every-minute': {
        'task': 'core.tasks.run_audit',
        'schedule': 60.0,
    }
}

# CORS - permissive only in DEBUG; set CORS_ALLOWED_ORIGINS (comma-separated) for production
CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
    ]
