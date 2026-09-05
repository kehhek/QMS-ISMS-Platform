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

# Encryption at rest for Evidence file uploads (see core/storage.py). Fixed
# dev-only default so encrypted files stay readable across restarts locally;
# real deployments must set their own via env and never commit it.
EVIDENCE_ENCRYPTION_KEY = os.environ.get('EVIDENCE_ENCRYPTION_KEY')
if not EVIDENCE_ENCRYPTION_KEY:
    if DEBUG:
        EVIDENCE_ENCRYPTION_KEY = '0vS7ZvUQPxmAbnXxrrIZReJL8RDq4XcS-SHXE3fZ7ss='
    else:
        raise ImproperlyConfigured('EVIDENCE_ENCRYPTION_KEY must be set when DJANGO_DEBUG=False')

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
    # Must come after TenantMainMiddleware: it reads connection.tenant,
    # which that middleware is what sets.
    'tenants.middleware.TenantSessionScopeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# TLS is expected to be terminated in front of this app (a reverse proxy /
# load balancer) — Django doesn't serve HTTPS itself. These just make sure
# the app *behaves* correctly once it's behind one: trusts the proxy's
# X-Forwarded-Proto header, redirects plain HTTP, and never sends cookies
# unencrypted. Left off in DEBUG since local dev has no TLS in front of it.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

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

# Evidence uploads. Local disk for now (the repo dir is bind-mounted into
# the web container, so files survive restarts); swap for S3/MinIO storage
# before this needs to run anywhere beyond one dev host.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

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
        # Public self-service signup: each call provisions a real Postgres
        # schema, a much heavier operation than a normal anonymous read.
        'registration': '5/hour',
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
    },
    'daily-tenant-backup': {
        'task': 'tenants.tasks.run_daily_backups',
        'schedule': crontab(hour=2, minute=0),
    },
}

# Where backup_tenants writes dumps (see tenants/management/commands/).
# Bind-mounted into the container like everything else, so backups land on
# the host — swap for S3/off-host storage before this runs anywhere that
# isn't disposable.
BACKUP_ROOT = BASE_DIR / 'backups'
BACKUP_RETENTION_COUNT = int(os.environ.get('BACKUP_RETENTION_COUNT', '14'))

# CORS - permissive only in DEBUG; set CORS_ALLOWED_ORIGINS (comma-separated) for production
CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
    ]
