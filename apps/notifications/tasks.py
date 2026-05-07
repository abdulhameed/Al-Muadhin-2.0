from celery import shared_task

@shared_task
def dispatch_daily_summaries():
    pass

@shared_task
def dispatch_pre_adhan_notifications():
    pass

@shared_task
def dispatch_adhan_notifications():
    pass
