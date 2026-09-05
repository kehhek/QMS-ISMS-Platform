FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# postgresql-client provides pg_dump/pg_restore/psql, used by the
# backup_tenants / restore_tenant_test management commands.
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . /app

EXPOSE 8000

# --workers 3 is a starting point, not a tuned number — override per
# deployment with the GUNICORN_CMD_ARGS env var (gunicorn reads it
# automatically, e.g. GUNICORN_CMD_ARGS="--workers 8 --timeout 90"),
# no image rebuild needed. A single worker (the old default) meant one
# slow request — e.g. registration provisioning a whole Postgres schema —
# blocked every other request on the same container.
CMD ["gunicorn", "project.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
