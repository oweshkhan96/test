import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fuel_management.settings")

app = Celery("fuel_management")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# optional: default queue configuration, retries, etc.
