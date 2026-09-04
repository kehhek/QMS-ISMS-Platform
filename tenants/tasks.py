from project.celery import app
from django.core.management import call_command


@app.task
def run_daily_backups():
    call_command('backup_tenants')
    return True
