import pytz
from django.utils import timezone
from datetime import datetime, timedelta
from apps.accounts.models import User


def get_users_for_local_hour(hour):
    """Get users whose local time is currently the given hour."""
    current_utc = timezone.now()
    users = []

    for user in User.objects.filter(is_active_subscriber=True).select_related('country'):
        local_tz = pytz.timezone(user.timezone)
        local_time = current_utc.astimezone(local_tz)

        if local_time.hour == hour:
            users.append(user)

    return users


def get_timezone_groups():
    """Get all unique timezone groups from users."""
    users = User.objects.filter(is_active_subscriber=True).values_list('timezone', flat=True).distinct()
    return list(set(users))


def get_local_time_in_timezone(tz_name):
    """Get current time in a specific timezone."""
    tz = pytz.timezone(tz_name)
    return timezone.now().astimezone(tz)


def get_users_with_prayer_in_minutes(prayer_time, minutes_before):
    """Get users who have a prayer in exactly N minutes from now."""
    from apps.prayers.services import AladhanAPIClient

    client = AladhanAPIClient()
    target_time = timezone.now() + timedelta(minutes=minutes_before)
    target_date = target_time.date()

    users_with_prayer = []

    for user in User.objects.filter(is_active_subscriber=True, tier='premium'):
        try:
            prayer_times = client.get_prayer_times_for_user(user, target_date)
            if prayer_time in prayer_times:
                pt = prayer_times[prayer_time]
                # Check if prayer is within the window (±2 minutes)
                if abs((pt - target_time).total_seconds()) <= 120:
                    users_with_prayer.append(user)
        except Exception as e:
            continue

    return users_with_prayer


def get_users_with_prayer_now(prayer_time, window_seconds=60):
    """Get users who have a prayer happening right now (within window)."""
    from apps.prayers.services import AladhanAPIClient

    client = AladhanAPIClient()
    current_time = timezone.now()
    current_date = current_time.date()

    users_with_prayer = []

    for user in User.objects.filter(is_active_subscriber=True, tier='premium'):
        try:
            prayer_times = client.get_prayer_times_for_user(user, current_date)
            if prayer_time in prayer_times:
                pt = prayer_times[prayer_time]
                # Check if prayer is within the window
                if abs((pt - current_time).total_seconds()) <= window_seconds:
                    users_with_prayer.append(user)
        except Exception as e:
            continue

    return users_with_prayer
