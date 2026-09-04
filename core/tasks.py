from project.celery import app


@app.task
def run_audit():
    # placeholder scheduled task: scans tenants or scheduled audits
    print('Running scheduled audits...')
    return True
