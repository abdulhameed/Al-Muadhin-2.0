import logging
import time
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from apps.providers.models import TelcoProvider, ProviderCountry
from apps.providers.registry import get_adapter

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for concurrent API calls to providers."""

    # Per-provider rate limits (calls per minute)
    RATE_LIMITS = {
        'twilio': 100,
        'vonage': 60,
        'termii': 50,
        'sendgrid': 200,
    }

    @staticmethod
    def get_rate_limit_key(provider_name):
        """Get Redis key for tracking call count."""
        return f"rate_limit:{provider_name}:{int(time.time() // 60)}"

    @staticmethod
    def can_send(provider_name):
        """Check if a call can be sent without exceeding rate limit."""
        limit = RateLimiter.RATE_LIMITS.get(provider_name.lower(), 100)
        key = RateLimiter.get_rate_limit_key(provider_name)

        current_count = cache.get(key, 0)
        if current_count >= limit:
            logger.warning(f"Rate limit exceeded for {provider_name}")
            return False

        return True

    @staticmethod
    def record_send(provider_name):
        """Record a successful send to increment the call counter."""
        key = RateLimiter.get_rate_limit_key(provider_name)
        current_count = cache.get(key, 0)
        cache.set(key, current_count + 1, 60)


class ProviderDispatcher:
    """Routes notifications to appropriate providers with fallback logic."""

    @staticmethod
    def resolve_providers(country, channel):
        """Get ordered list of providers for a country and channel."""
        providers = ProviderCountry.objects.filter(
            country=country,
            provider__is_active=True,
            is_active=True
        ).select_related('provider').order_by('priority')

        result = []
        for pc in providers:
            provider = pc.provider
            # Filter by channel capability
            if channel == 'sms':
                if provider.provider_type in ['sms', 'both']:
                    result.append(provider)
            elif channel == 'voice':
                if provider.provider_type in ['voice', 'both']:
                    result.append(provider)
            elif channel == 'email':
                if provider.provider_type == 'email':
                    result.append(provider)

        return result

    @staticmethod
    def dispatch_sms(user, message, prayer=None):
        """Send SMS with fallback to secondary providers."""
        from .models import NotificationLog

        if not user.phone_number:
            logger.warning(f"User {user.id} has no phone number for SMS")
            return False

        country = user.country
        providers = ProviderDispatcher.resolve_providers(country, 'sms')

        if not providers:
            logger.error(f"No SMS providers available for {country.name}")
            return False

        for provider in providers:
            try:
                adapter = get_adapter(provider)
                result = adapter.send_sms(user.phone_number, message)

                notification = NotificationLog.objects.create(
                    user=user,
                    notification_type='sms',
                    channel='sms',
                    prayer=prayer,
                    provider=provider,
                    status='sent' if result.success else 'failed',
                    external_id=result.external_id,
                    error_message=result.error_message,
                    cost_estimate=result.cost,
                    scheduled_for=timezone.now()
                )

                if result.success:
                    logger.info(f"SMS sent to {user.phone_number} via {provider.name}")
                    return True
                else:
                    logger.warning(f"SMS failed via {provider.name}: {result.error_message}")
            except Exception as e:
                logger.error(f"Error dispatching SMS via {provider.name}: {e}")
                continue

        logger.error(f"SMS dispatch failed for user {user.id} after all providers")
        return False

    @staticmethod
    def dispatch_email(user, subject, html, text=None):
        """Send email via SendGrid."""
        from .models import NotificationLog

        if not user.email:
            logger.warning(f"User {user.id} has no email")
            return False

        try:
            # Find SendGrid provider
            provider = TelcoProvider.objects.get(
                provider_type='email',
                name__icontains='sendgrid',
                is_active=True
            )
        except TelcoProvider.DoesNotExist:
            logger.error("SendGrid provider not configured")
            return False

        try:
            adapter = get_adapter(provider)
            result = adapter.send_email(user.email, subject, html, text)

            notification = NotificationLog.objects.create(
                user=user,
                notification_type='email',
                channel='email',
                provider=provider,
                status='sent' if result.success else 'failed',
                external_id=result.external_id,
                error_message=result.error_message,
                cost_estimate=result.cost,
                scheduled_for=timezone.now()
            )

            if result.success:
                logger.info(f"Email sent to {user.email}")
                return True
            else:
                logger.warning(f"Email failed: {result.error_message}")
                return False
        except Exception as e:
            logger.error(f"Error dispatching email: {e}")
            return False

    @staticmethod
    def dispatch_call(user, audio_url, prayer=None):
        """Make phone call with fallback to secondary providers and rate limiting."""
        from .models import NotificationLog

        if not user.phone_number:
            logger.warning(f"User {user.id} has no phone number for call")
            return False

        country = user.country
        providers = ProviderDispatcher.resolve_providers(country, 'voice')

        if not providers:
            logger.error(f"No voice providers available for {country.name}")
            return False

        for provider in providers:
            # Check rate limit before attempting call
            if not RateLimiter.can_send(provider.name):
                logger.info(f"Rate limit preventing call via {provider.name}, trying next provider")
                continue

            try:
                adapter = get_adapter(provider)
                result = adapter.make_call(user.phone_number, audio_url)

                # Record the send attempt
                RateLimiter.record_send(provider.name)

                notification = NotificationLog.objects.create(
                    user=user,
                    notification_type='call',
                    channel='call',
                    prayer=prayer,
                    provider=provider,
                    status='pending' if result.success else 'failed',
                    external_id=result.external_id,
                    error_message=result.error_message,
                    cost_estimate=result.cost,
                    scheduled_for=timezone.now()
                )

                if result.success:
                    logger.info(f"Call initiated to {user.phone_number} via {provider.name}")
                    return True
                else:
                    logger.warning(f"Call failed via {provider.name}: {result.error_message}")
            except Exception as e:
                logger.error(f"Error dispatching call via {provider.name}: {e}")
                continue

        logger.error(f"Call dispatch failed for user {user.id} after all providers")
        return False
