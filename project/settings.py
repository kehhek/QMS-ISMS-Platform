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

# 21 CFR Part 11 §11.300(a)/(b): unique ID/password combinations and
# periodic password revision. No validators were configured at all before
# this — Django applied none, so any password (however weak) was accepted.
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Part 11 §11.300(b) (periodic password revision) and §11.300(d) (transaction
# safeguards against unauthorized use, e.g. account lockout after repeated
# failed attempts). See accounts/security.py for where these are enforced —
# settings only, not self-enforcing.
PART11_PASSWORD_MAX_AGE_DAYS = int(os.environ.get('PART11_PASSWORD_MAX_AGE_DAYS', '90'))
PART11_MAX_FAILED_LOGINS = int(os.environ.get('PART11_MAX_FAILED_LOGINS', '5'))
PART11_LOCKOUT_MINUTES = int(os.environ.get('PART11_LOCKOUT_MINUTES', '15'))

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

# Evidence uploads. Local disk by default (fine for one dev host, or one
# app server replica) — set AWS_STORAGE_BUCKET_NAME (+ AWS creds) to
# switch to S3 instead, needed as soon as there's more than one app
# server replica, since local disk isn't shared between them. See
# core/storage.py get_evidence_storage() for the actual switch.
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', '')
if AWS_STORAGE_BUCKET_NAME:
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', '')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', '')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-1')
    # Optional: point at an S3-compatible service (MinIO, R2, etc.)
    # instead of AWS itself.
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', '') or None
    # Evidence is already Fernet-encrypted before it reaches S3 and is
    # meant to be fetched only through the API (which streams it back
    # authenticated), never linked to directly — private objects, no
    # public querystring auth URLs.
    AWS_DEFAULT_ACL = 'private'
    AWS_QUERYSTRING_AUTH = False

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
        # Public "request a demo" lead form — cheap to process, but still
        # throttled harder than general anon reads to deter spam/scraping.
        'demo-request': '10/hour',
        # Forgot-password request/confirm — throttled to slow down both
        # inbox-flooding (repeated requests) and token-guessing (repeated
        # confirm attempts), same reasoning as 'registration'.
        'password-reset': '10/hour',
        # Public supplier questionnaire response page — the access_token
        # IS the credential, so this also slows down token-guessing.
        'questionnaire-public': '30/hour',
        # Public supplier agreement e-signature page — same
        # token-is-the-credential reasoning as questionnaire-public.
        'agreement-public': '30/hour',
        # Public Trust Center page — cheap aggregate read, but still worth
        # a floor above the general anon rate to deter scraping.
        'trust-center-public': '60/hour',
        # Public auditor-access link — real evidence/policy files behind
        # this one, so it's throttled the same as the other token-is-the-
        # credential public links even though the auditor may load it
        # (and each control's evidence) repeatedly over an audit.
        'auditor-access-public': '120/hour',
    },
}

# Celery
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)

from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Replaces the old 'run-audit-every-minute' placeholder (which just
    # printed a string every 60 seconds and did nothing) — this actually
    # scans every tenant for overdue ISMS Calendar items and emails a
    # digest to that tenant's admins/auditors. Once a day, not once a
    # minute: overdue-ness doesn't change fast enough to justify more.
    'isms-overdue-digest': {
        'task': 'core.tasks.send_overdue_isms_digest',
        'schedule': crontab(hour=7, minute=0),
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

# Email — console backend in DEBUG (prints to the web container's stdout,
# no external credentials needed for local dev); real SMTP in production
# via env vars. Every call site treats sending as best-effort (caught and
# logged, never raised) — a broken SMTP config shouldn't block inviting a
# member or submitting a demo request.
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'no-reply@example.com')

# Where "someone submitted a demo request" notifications go — your team's
# inbox, not the requester's. Left blank, demo requests still land in
# Django admin; they just won't page anyone.
DEMO_REQUEST_NOTIFY_EMAIL = os.environ.get('DEMO_REQUEST_NOTIFY_EMAIL', '')

# The origin the React app is actually served from — used to build the
# password-reset link emailed to users (accounts/views.py
# PasswordResetRequestView). Left blank, that view falls back to the
# API's own request origin, which works but won't point at the frontend
# in a setup where they're on different hosts/ports (e.g. local dev).
FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', '').rstrip('/')

# CORS - permissive only in DEBUG; set CORS_ALLOWED_ORIGINS (comma-separated) for production
CORS_ALLOW_ALL_ORIGINS = DEBUG
if not DEBUG:
    CORS_ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if o.strip()
    ]
