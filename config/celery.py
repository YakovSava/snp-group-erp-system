import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("snp_esb")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "cleanup-expired-conversion-jobs": {
        "task": "apps.utilities.tasks.cleanup_expired_conversion_jobs",
        "schedule": crontab(minute="*/5"),
    },
}
