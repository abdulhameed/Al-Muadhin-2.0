import logging
from celery import shared_task
from django.utils import timezone
from .services import NotificationService
from .timezone_utils import (
    get_users_for_local_hour,
    get_users_with_prayer_in_minutes,
    get_users_with_prayer_now
)
from apps.accounts.models import User, NotificationPreference

logger = logging.getLogger(__name__)


@shared_task
def dispatch_daily_summaries():
    """Send daily prayer summaries to users at their configured hour."""
    from django.conf import settings

    summary_hour = int(settings.SUMMARY_HOUR)
    users = get_users_for_local_hour(summary_hour)

    sent_count = 0
    for user in users:
        if NotificationService.send_daily_summary(user):
            sent_count += 1

    logger.info(f"Sent daily summaries to {sent_count} users")
    return sent_count


@shared_task
def dispatch_pre_adhan_notifications():
    """Send SMS notifications before adhan time."""
    from django.conf import settings

    pre_adhan_minutes = int(settings.DEFAULT_PRE_ADHAN_MINUTES)
    prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']

    total_sent = 0
    for prayer in prayers:
        users = get_users_with_prayer_in_minutes(prayer, pre_adhan_minutes)
        for user in users:
            try:
                prefs = NotificationPreference.objects.get(user=user, prayer=prayer)
                if prefs.pre_adhan_sms and user.tier == 'premium':
                    NotificationService.send_pre_adhan_notification(user, prayer)
                    total_sent += 1
            except NotificationPreference.DoesNotExist:
                pass
            except Exception as e:
                logger.error(f"Error sending pre-adhan SMS: {e}")

    logger.info(f"Sent pre-adhan SMS to {total_sent} users")
    return total_sent


@shared_task
def dispatch_adhan_notifications():
    """Send SMS and phone call notifications at adhan time."""
    prayers = ['fajr', 'dhuhr', 'asr', 'maghrib', 'isha']

    total_sent = 0
    for prayer in prayers:
        users = get_users_with_prayer_now(prayer)
        for user in users:
            try:
                NotificationService.send_adhan_notification(user, prayer)
                total_sent += 1
            except Exception as e:
                logger.error(f"Error sending adhan notification: {e}")

    logger.info(f"Sent adhan notifications to {total_sent} users")
    return total_sent
