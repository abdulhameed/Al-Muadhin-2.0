import logging
from django.conf import settings
from django.utils import timezone
from apps.providers.models import TelcoProvider, ProviderCountry
from apps.providers.registry import get_adapter

logger = logging.getLogger(__name__)


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
        """Make phone call with fallback to secondary providers."""
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
            try:
                adapter = get_adapter(provider)
                result = adapter.make_call(user.phone_number, audio_url)

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
