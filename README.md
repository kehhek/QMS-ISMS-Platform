# Multi-tenant QMS+ISMS starter (Django)

Minimal starter scaffold using Django + django-tenants.

Setup (macOS / Linux):

1. Create a Python virtualenv and install deps:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Configure Postgres connection via environment variables (see `.env.example`).

3. Run migrations for the public schema and create a public tenant:

```bash
python manage.py migrate_schemas --shared
python manage.py migrate
```

This repo contains a minimal `tenants` app (schema tenant model), an `accounts` app (custom user), and a `core` app with basic models.

Next steps:
- Create a public tenant (Domain) and tenant schema
- Implement onboarding views and API
- Harden settings for production (SECRET_KEY, DEBUG=False, TLS, storage)

Quick start (after installing dependencies):

```bash
# initialize DB and sample tenant
python manage.py init_project

# start development server
python manage.py runserver
```

Docker (recommended for local dev):

```bash
docker-compose up --build
```



Authentication:
- Obtain an auth token: POST `/api/accounts/token/` with `username` and `password` to receive an auth token.
- For tenant-scoped requests, use the tenant's domain (or set the Host header to the tenant domain) when calling APIs.

