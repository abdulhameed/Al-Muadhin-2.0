import logging
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import NotificationLog
from .dispatcher import ProviderDispatcher
from apps.accounts.models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def retry_failed_sms(self, notification_id):
    """Retry a failed SMS notification."""
    try:
        notification = NotificationLog.objects.get(id=notification_id)

        if notification.status == 'delivered':
            logger.info(f"Notification {notification_id} already delivered")
            return

        if notification.retry_count >= 3:
            logger.warning(f"Max retries exceeded for SMS {notification_id}")
            notification.status = 'failed'
            notification.error_message = 'Max retries exceeded'
            notification.save()
            return

        # Increment retry count
        notification.retry_count += 1
        notification.status = 'retrying'
        notification.save()

        user = notification.user
        message = "Retrying SMS notification"

        # Try to resend
        result = ProviderDispatcher.dispatch_sms(
            user=user,
            message=message,
            prayer=notification.prayer
        )

        logger.info(f"Retried SMS {notification_id} (attempt {notification.retry_count})")

    except NotificationLog.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as exc:
        logger.error(f"Error retrying SMS: {exc}")
        raise self.retry(exc=exc, countdown=120)


@shared_task(bind=True, max_retries=1)
def retry_failed_call(self, notification_id):
    """Retry a failed phone call notification."""
    try:
        notification = NotificationLog.objects.get(id=notification_id)

        if notification.status == 'delivered':
            logger.info(f"Call notification {notification_id} already delivered")
            return

        if notification.retry_count >= 2:
            logger.warning(f"Max retries exceeded for call {notification_id}")
            notification.status = 'failed'
            notification.error_message = 'Max retries exceeded'
            notification.save()
            return

        # Increment retry count
        notification.retry_count += 1
        notification.status = 'retrying'
        notification.save()

        user = notification.user
        audio_url = f"{__import__('django.conf').settings.ADHAN_AUDIO_BASE_URL}{user.preferred_muezzin}.mp3"

        # Try to resend call
        result = ProviderDispatcher.dispatch_call(
            user=user,
            audio_url=audio_url,
            prayer=notification.prayer
        )

        logger.info(f"Retried call {notification_id} (attempt {notification.retry_count})")

    except NotificationLog.DoesNotExist:
        logger.error(f"Notification {notification_id} not found")
    except Exception as exc:
        logger.error(f"Error retrying call: {exc}")
        raise self.retry(exc=exc, countdown=180)


@shared_task
def clean_failed_notifications():
    """Mark old failed notifications as archived."""
    cutoff_date = timezone.now() - timedelta(days=30)
    old_failed = NotificationLog.objects.filter(
        status='failed',
        created_at__lt=cutoff_date
    )
    count = old_failed.count()
    old_failed.update(status='archived')
    logger.info(f"Archived {count} old failed notifications")
    return count
