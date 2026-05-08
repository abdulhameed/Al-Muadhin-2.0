import logging
from django.template.loader import render_to_string
from django.utils import timezone
from apps.prayers.services import AladhanAPIClient
from apps.accounts.models import User, NotificationPreference
from .dispatcher import ProviderDispatcher
from .models import NotificationLog
from .timezone_utils import (
    get_users_for_local_hour,
    get_users_with_prayer_in_minutes,
    get_users_with_prayer_now
)

logger = logging.getLogger(__name__)


class NotificationService:
    """High-level service for sending notifications to users."""

    @staticmethod
    def send_daily_summary(user, date=None):
        """Send daily prayer summary to a user via email and SMS."""
        if date is None:
            date = timezone.now().date()

        try:
            # Fetch prayer times
            client = AladhanAPIClient()
            prayer_times = client.get_prayer_times_for_user(user, date)

            if not prayer_times:
                logger.warning(f"Could not fetch prayer times for user {user.id} on {date}")
                return False

            # Render email template
            context = {
                'user': user,
                'prayer_times': prayer_times,
                'date': date,
            }

            html = render_to_string('emails/daily_summary.html', context)
            text = render_to_string('emails/daily_summary.txt', context)

            # Send email to all users
            ProviderDispatcher.dispatch_email(
                user=user,
                subject=f'Daily Prayer Times for {date.strftime("%A, %B %d")}',
                html=html,
                text=text
            )

            # Send SMS to premium users if opted in
            if user.tier == 'premium':
                prefs = NotificationPreference.objects.filter(user=user, summary_sms=True)
                if prefs.exists():
                    sms_text = render_to_string('sms/daily_summary.txt', {
                        'prayer_times': prayer_times,
                    })
                    ProviderDispatcher.dispatch_sms(user=user, message=sms_text)

            return True

        except Exception as e:
            logger.error(f"Error sending daily summary to user {user.id}: {e}")
            return False

    @staticmethod
    def send_pre_adhan_notification(user, prayer, minutes_before=15):
        """Send pre-adhan SMS notification."""
        try:
            prefs = NotificationPreference.objects.get(user=user, prayer=prayer)
            if not prefs.pre_adhan_sms:
                return False
        except NotificationPreference.DoesNotExist:
            return False

        try:
            # Get next occurrence of this prayer
            date = timezone.now().date()
            client = AladhanAPIClient()
            prayer_times = client.get_prayer_times_for_user(user, date)

            if not prayer_times or prayer not in prayer_times:
                logger.warning(f"Prayer time not found for {prayer}")
                return False

            prayer_time = prayer_times[prayer]
            context = {
                'prayer': prayer.capitalize(),
                'minutes': minutes_before,
                'time': prayer_time.strftime('%H:%M'),
            }

            message = render_to_string('sms/pre_adhan.txt', context).strip()
            ProviderDispatcher.dispatch_sms(user=user, message=message, prayer=prayer)

            return True

        except Exception as e:
            logger.error(f"Error sending pre-adhan SMS to user {user.id}: {e}")
            return False

    @staticmethod
    def send_adhan_notification(user, prayer):
        """Send adhan SMS and/or phone call."""
        try:
            prefs = NotificationPreference.objects.get(user=user, prayer=prayer)
        except NotificationPreference.DoesNotExist:
            return False

        try:
            # Get prayer time
            date = timezone.now().date()
            client = AladhanAPIClient()
            prayer_times = client.get_prayer_times_for_user(user, date)

            if not prayer_times or prayer not in prayer_times:
                return False

            prayer_time = prayer_times[prayer]

            # Send SMS if opted in
            if prefs.adhan_sms and user.tier == 'premium':
                context = {
                    'prayer': prayer.capitalize(),
                    'time': prayer_time.strftime('%H:%M'),
                }
                message = render_to_string('sms/adhan.txt', context).strip()
                ProviderDispatcher.dispatch_sms(user=user, message=message, prayer=prayer)

            # Send call if opted in
            if prefs.adhan_call and user.tier == 'premium':
                audio_url = f"{__import__('django.conf').settings.ADHAN_AUDIO_BASE_URL}{user.preferred_muezzin}.mp3"
                ProviderDispatcher.dispatch_call(user=user, audio_url=audio_url, prayer=prayer)

            return True

        except Exception as e:
            logger.error(f"Error sending adhan notification to user {user.id}: {e}")
            return False

    @staticmethod
    def get_notification_stats(user):
        """Get notification statistics for a user."""
        logs = NotificationLog.objects.filter(user=user)

        return {
            'total': logs.count(),
            'sent': logs.filter(status='sent').count(),
            'delivered': logs.filter(status='delivered').count(),
            'failed': logs.filter(status='failed').count(),
            'pending': logs.filter(status='pending').count(),
        }
