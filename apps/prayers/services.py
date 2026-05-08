import logging
import requests
import pytz
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from .models import PrayerTimeCache

logger = logging.getLogger(__name__)


class AladhanAPIClient:
    """Client for fetching prayer times from Aladhan API."""

    BASE_URL = "https://api.aladhan.com/v1"
    CACHE_TTL = 86400  # 24 hours
    ALADHAN_METHOD_MAP = {
        'MWL': 3,
        'ISNA': 2,
        'Egypt': 5,
        'Makkah': 4,
        'Karachi': 1,
        'Tehran': 7,
    }

    def fetch_prayer_times(self, latitude, longitude, date, method):
        """Fetch prayer times from Aladhan API with caching."""
        # Try Redis cache first
        cache_key = f"prayers:{latitude}:{longitude}:{date}:{method}"
        cached = cache.get(cache_key)
        if cached:
            return cached

        # Check database
        try:
            pt = PrayerTimeCache.objects.get(
                latitude=latitude,
                longitude=longitude,
                date=date,
                method=method
            )
            return {
                'fajr': pt.fajr,
                'sunrise': pt.sunrise,
                'dhuhr': pt.dhuhr,
                'asr': pt.asr,
                'maghrib': pt.maghrib,
                'isha': pt.isha,
            }
        except PrayerTimeCache.DoesNotExist:
            pass

        # Fetch from API
        try:
            aladhan_method = self.ALADHAN_METHOD_MAP.get(method, 3)
            date_str = date.strftime('%d-%m-%Y')
            url = f"{self.BASE_URL}/timings/{date_str}"

            response = requests.get(
                url,
                params={
                    'latitude': latitude,
                    'longitude': longitude,
                    'method': aladhan_method,
                },
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            timings = data['data']['timings']

            # Parse times
            prayer_times = {
                'fajr': datetime.strptime(timings['Fajr'], '%H:%M').time(),
                'sunrise': datetime.strptime(timings['Sunrise'], '%H:%M').time(),
                'dhuhr': datetime.strptime(timings['Dhuhr'], '%H:%M').time(),
                'asr': datetime.strptime(timings['Asr'], '%H:%M').time(),
                'maghrib': datetime.strptime(timings['Maghrib'], '%H:%M').time(),
                'isha': datetime.strptime(timings['Isha'], '%H:%M').time(),
            }

            # Store in database (find or create country)
            from apps.providers.models import Country
            country, _ = Country.objects.get_or_create(
                code='XX',  # Placeholder
                defaults={'name': 'Unknown', 'dial_code': '+00'}
            )

            PrayerTimeCache.objects.create(
                city='Unknown',
                country=country,
                latitude=latitude,
                longitude=longitude,
                date=date,
                method=method,
                fajr=prayer_times['fajr'],
                sunrise=prayer_times['sunrise'],
                dhuhr=prayer_times['dhuhr'],
                asr=prayer_times['asr'],
                maghrib=prayer_times['maghrib'],
                isha=prayer_times['isha'],
            )

            # Cache in Redis
            cache.set(cache_key, prayer_times, self.CACHE_TTL)

            return prayer_times

        except Exception as e:
            logger.error(f"Error fetching prayer times: {e}")
            return None

    def get_prayer_times_for_user(self, user, date=None):
        """Get prayer times for a user's location."""
        if date is None:
            date = timezone.now().date()

        if not user.latitude or not user.longitude:
            logger.warning(f"User {user.id} missing coordinates")
            return None

        return self.fetch_prayer_times(
            float(user.latitude),
            float(user.longitude),
            date,
            user.calculation_method
        )

    def get_next_prayer_for_user(self, user):
        """Get the next upcoming prayer for a user."""
        now = timezone.now()
        current_time = now.time()
        today_date = now.date()

        prayer_times = self.get_prayer_times_for_user(user, today_date)
        if not prayer_times:
            return None

        # Prayer order
        prayer_order = ['fajr', 'sunrise', 'dhuhr', 'asr', 'maghrib', 'isha']

        # Find next prayer today
        for prayer in prayer_order:
            if prayer == 'sunrise':
                continue  # Skip sunrise, it's not a prayer
            prayer_time = prayer_times.get(prayer)
            if prayer_time and prayer_time > current_time:
                # Convert to datetime with user's timezone
                user_tz = pytz.timezone(user.timezone)
                prayer_dt = datetime.combine(today_date, prayer_time)
                prayer_dt = user_tz.localize(prayer_dt)
                countdown = (prayer_dt - now).total_seconds()
                return {
                    'prayer': prayer,
                    'time': prayer_time,
                    'countdown_seconds': countdown,
                }

        # If no prayer found today, get first prayer tomorrow
        tomorrow = today_date + timedelta(days=1)
        prayer_times = self.get_prayer_times_for_user(user, tomorrow)
        if prayer_times:
            prayer_time = prayer_times['fajr']
            user_tz = pytz.timezone(user.timezone)
            prayer_dt = datetime.combine(tomorrow, prayer_time)
            prayer_dt = user_tz.localize(prayer_dt)
            countdown = (prayer_dt - now).total_seconds()
            return {
                'prayer': 'fajr',
                'time': prayer_time,
                'countdown_seconds': countdown,
            }

        return None
