import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')

app = Celery('al_muadhin')

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'dispatch-daily-summaries': {
        'task': 'apps.notifications.tasks.dispatch_daily_summaries',
        'schedule': 300.0,
    },
    'dispatch-pre-adhan-notifications': {
        'task': 'apps.notifications.tasks.dispatch_pre_adhan_notifications',
        'schedule': 60.0,
    },
    'dispatch-adhan-notifications': {
        'task': 'apps.notifications.tasks.dispatch_adhan_notifications',
        'schedule': 60.0,
    },
    'monitor-provider-health': {
        'task': 'apps.notifications.tasks.monitor_provider_health',
        'schedule': 600.0,  # Every 10 minutes
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
