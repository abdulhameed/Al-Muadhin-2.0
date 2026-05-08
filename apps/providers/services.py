import logging
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import TelcoProvider
from apps.notifications.models import NotificationLog

logger = logging.getLogger(__name__)


class ProviderHealthMonitor:
    """Monitor and manage provider health status."""

    # Health thresholds
    HEALTH_THRESHOLD_UNHEALTHY = 50  # % success rate below this is unhealthy
    HEALTH_THRESHOLD_RECOVERY = 80   # % success rate above this allows recovery

    # Minimum attempts before making health decision
    MIN_ATTEMPTS = 10

    @staticmethod
    def get_provider_health(provider):
        """
        Calculate provider health percentage based on recent notifications.
        Returns health percentage (0-100).
        """
        key = f"provider_health:{provider.id}"
        cached = cache.get(key)
        if cached is not None:
            return cached

        # Check last 100 notifications (or last hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent = NotificationLog.objects.filter(
            provider=provider,
            created_at__gte=one_hour_ago
        ).order_by('-created_at')[:100]

        if recent.count() < ProviderHealthMonitor.MIN_ATTEMPTS:
            # Not enough data, return neutral
            return 80

        delivered = recent.filter(status='delivered').count()
        sent = recent.filter(status='sent').count()
        successful = delivered + sent
        health = (successful / recent.count()) * 100

        # Cache for 5 minutes
        cache.set(key, int(health), 300)
        return int(health)

    @staticmethod
    def mark_unhealthy(provider):
        """Mark provider as unhealthy."""
        key = f"provider_health:{provider.id}"
        cache.set(key, 0, 86400)  # 0% health for 24 hours
        provider.is_active = False
        provider.save()
        logger.warning(f"Provider {provider.name} marked as unhealthy")

    @staticmethod
    def mark_healthy(provider):
        """Mark provider as healthy."""
        key = f"provider_health:{provider.id}"
        cache.set(key, 95, 86400)  # 95% health for 24 hours
        provider.is_active = True
        provider.save()
        logger.info(f"Provider {provider.name} marked as healthy")

    @staticmethod
    def check_all_providers():
        """Check health of all providers and update status."""
        providers = TelcoProvider.objects.filter(is_active=True)
        changes = {'unhealthy': [], 'recovered': []}

        for provider in providers:
            health = ProviderHealthMonitor.get_provider_health(provider)

            if health < ProviderHealthMonitor.HEALTH_THRESHOLD_UNHEALTHY:
                if provider.is_active:
                    ProviderHealthMonitor.mark_unhealthy(provider)
                    changes['unhealthy'].append(provider.name)

        # Check for recovery
        inactive_providers = TelcoProvider.objects.filter(is_active=False)
        for provider in inactive_providers:
            health = ProviderHealthMonitor.get_provider_health(provider)

            if health >= ProviderHealthMonitor.HEALTH_THRESHOLD_RECOVERY:
                # Check if minimum time has passed (30 minutes)
                key = f"provider_recovery_time:{provider.id}"
                last_check = cache.get(key)

                if last_check is None:
                    # First recovery attempt, mark time
                    cache.set(key, timezone.now(), 1800)  # 30 minutes
                else:
                    # Recovery window passed, mark healthy
                    ProviderHealthMonitor.mark_healthy(provider)
                    changes['recovered'].append(provider.name)
                    cache.delete(key)

        return changes


class CostAnalytics:
    """Analytics for notification costs."""

    @staticmethod
    def get_cost_summary(start_date=None, end_date=None):
        """
        Get cost breakdown by provider, country, and channel.
        """
        if start_date is None:
            start_date = timezone.now() - timedelta(days=30)
        if end_date is None:
            end_date = timezone.now()

        logs = NotificationLog.objects.filter(
            created_at__range=[start_date, end_date],
            status__in=['sent', 'delivered']
        )

        summary = {
            'total_cost': 0,
            'by_provider': {},
            'by_country': {},
            'by_channel': {},
            'by_type': {},
        }

        for log in logs:
            cost = float(log.cost_estimate or 0)
            summary['total_cost'] += cost

            # By provider
            provider_name = log.provider.name if log.provider else 'Unknown'
            if provider_name not in summary['by_provider']:
                summary['by_provider'][provider_name] = {
                    'cost': 0,
                    'count': 0,
                    'avg_cost': 0,
                }
            summary['by_provider'][provider_name]['cost'] += cost
            summary['by_provider'][provider_name]['count'] += 1

            # By country
            country_name = log.user.country.name if log.user.country else 'Unknown'
            if country_name not in summary['by_country']:
                summary['by_country'][country_name] = {
                    'cost': 0,
                    'count': 0,
                    'avg_cost': 0,
                }
            summary['by_country'][country_name]['cost'] += cost
            summary['by_country'][country_name]['count'] += 1

            # By channel
            channel = log.channel
            if channel not in summary['by_channel']:
                summary['by_channel'][channel] = {
                    'cost': 0,
                    'count': 0,
                    'avg_cost': 0,
                }
            summary['by_channel'][channel]['cost'] += cost
            summary['by_channel'][channel]['count'] += 1

            # By type
            msg_type = log.notification_type
            if msg_type not in summary['by_type']:
                summary['by_type'][msg_type] = {
                    'cost': 0,
                    'count': 0,
                    'avg_cost': 0,
                }
            summary['by_type'][msg_type]['cost'] += cost
            summary['by_type'][msg_type]['count'] += 1

        # Calculate averages
        for category in summary.get('by_provider', {}).values():
            category['avg_cost'] = round(category['cost'] / category['count'], 4) if category['count'] > 0 else 0

        for category in summary.get('by_country', {}).values():
            category['avg_cost'] = round(category['cost'] / category['count'], 4) if category['count'] > 0 else 0

        for category in summary.get('by_channel', {}).values():
            category['avg_cost'] = round(category['cost'] / category['count'], 4) if category['count'] > 0 else 0

        for category in summary.get('by_type', {}).values():
            category['avg_cost'] = round(category['cost'] / category['count'], 4) if category['count'] > 0 else 0

        return summary

    @staticmethod
    def get_provider_costs(provider, days=30):
        """Get cost statistics for a specific provider."""
        start_date = timezone.now() - timedelta(days=days)

        logs = NotificationLog.objects.filter(
            provider=provider,
            created_at__gte=start_date,
            status__in=['sent', 'delivered']
        )

        total_cost = sum(float(log.cost_estimate or 0) for log in logs)
        count = logs.count()
        avg_cost = total_cost / count if count > 0 else 0

        return {
            'provider': provider.name,
            'total_cost': round(total_cost, 4),
            'count': count,
            'avg_cost': round(avg_cost, 4),
            'currency': provider.currency,
        }
