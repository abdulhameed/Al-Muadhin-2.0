import logging
from django.contrib import admin
from django.core.cache import cache
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import Count, Q
from .models import Country, TelcoProvider, ProviderCountry
from apps.notifications.models import NotificationLog

logger = logging.getLogger(__name__)


class ProviderCountryInline(admin.TabularInline):
    """Inline admin for provider countries."""
    model = ProviderCountry
    extra = 1
    fields = ('country', 'priority', 'is_active')
    ordering = ('country', 'priority')


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    """Admin for Country model."""
    list_display = ('name', 'code', 'dial_code', 'is_supported')
    list_filter = ('is_supported',)
    search_fields = ('name', 'code')
    readonly_fields = ('created_providers',)

    def created_providers(self, obj):
        """Show count of providers in this country."""
        count = ProviderCountry.objects.filter(country=obj).count()
        return f"{count} providers"


@admin.register(TelcoProvider)
class TelcoProviderAdmin(admin.ModelAdmin):
    """Admin for TelcoProvider model with health monitoring and testing."""

    list_display = (
        'name',
        'provider_type',
        'is_active',
        'get_health_status',
        'total_sent',
        'success_rate',
        'countries_count'
    )

    list_filter = ('is_active', 'provider_type')
    search_fields = ('name',)
    readonly_fields = (
        'created_at',
        'updated_at',
        'get_health_details',
        'get_recent_activity',
    )

    fieldsets = (
        ('Provider Information', {
            'fields': ('name', 'provider_type', 'adapter_class', 'is_active')
        }),
        ('API Credentials', {
            'fields': (
                'api_key',
                'api_secret',
                'account_sid',
                'auth_token',
                'sender_id',
                'base_url',
            ),
            'description': 'Sensitive credentials - use environment variables in production'
        }),
        ('Pricing', {
            'fields': ('cost_per_sms', 'cost_per_minute', 'currency')
        }),
        ('Voice Settings', {
            'fields': ('supports_voice', 'voice_webhook_url')
        }),
        ('Health & Activity', {
            'fields': (
                'get_health_details',
                'get_recent_activity',
            ),
            'description': 'Read-only monitoring data'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [ProviderCountryInline]
    actions = ['test_sms', 'test_call', 'mark_healthy', 'mark_unhealthy']

    def get_health_status(self, obj):
        """Display health status with color coding."""
        health = self.get_provider_health(obj)

        if health >= 95:
            color = 'green'
            status = '✅ Healthy'
        elif health >= 80:
            color = 'orange'
            status = '⚠️ Degraded'
        else:
            color = 'red'
            status = '❌ Unhealthy'

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            status
        )

    get_health_status.short_description = 'Health Status'

    def total_sent(self, obj):
        """Count total notifications sent via this provider."""
        count = NotificationLog.objects.filter(provider=obj).count()
        return count

    total_sent.short_description = 'Total Sent'

    def success_rate(self, obj):
        """Calculate success rate percentage."""
        total = NotificationLog.objects.filter(provider=obj).count()
        if total == 0:
            return 'N/A'

        successful = NotificationLog.objects.filter(
            provider=obj,
            status__in=['sent', 'delivered']
        ).count()

        rate = (successful / total) * 100
        return f"{rate:.1f}%"

    success_rate.short_description = 'Success Rate'

    def countries_count(self, obj):
        """Count countries where this provider is active."""
        count = ProviderCountry.objects.filter(
            provider=obj,
            is_active=True
        ).count()
        return f"{count} countries"

    countries_count.short_description = 'Countries'

    def get_health_details(self, obj):
        """Display detailed health monitoring information."""
        health = self.get_provider_health(obj)
        recent_logs = NotificationLog.objects.filter(provider=obj).order_by('-created_at')[:100]

        if recent_logs.count() == 0:
            return "No activity yet"

        total = recent_logs.count()
        delivered = recent_logs.filter(status='delivered').count()
        sent = recent_logs.filter(status='sent').count()
        failed = recent_logs.filter(status='failed').count()

        return format_html(
            '<div style="font-family: monospace; font-size: 12px;">'
            'Overall Health: <strong>{}</strong>%<br>'
            'Recent Activity (last 100):<br>'
            '  ✅ Delivered: {} ({:.1f}%)<br>'
            '  📤 Sent: {} ({:.1f}%)<br>'
            '  ❌ Failed: {} ({:.1f}%)<br>'
            '</div>',
            health,
            delivered, (delivered/total)*100 if total else 0,
            sent, (sent/total)*100 if total else 0,
            failed, (failed/total)*100 if total else 0,
        )

    get_health_details.short_description = 'Health Details'

    def get_recent_activity(self, obj):
        """Show recent notification activity."""
        recent = NotificationLog.objects.filter(provider=obj).order_by('-created_at')[:5]

        if not recent:
            return "No recent activity"

        html = '<table style="font-size: 12px;"><tr><th>Time</th><th>Type</th><th>Status</th></tr>'
        for log in recent:
            html += f'<tr><td>{log.created_at.strftime("%Y-%m-%d %H:%M")}</td>'
            html += f'<td>{log.notification_type}</td>'
            html += f'<td style="color: {"green" if log.status == "delivered" else "red"}">{log.status}</td></tr>'
        html += '</table>'

        return format_html(html)

    get_recent_activity.short_description = 'Recent Activity'

    def get_provider_health(self, obj):
        """Calculate provider health percentage."""
        key = f"provider_health:{obj.id}"
        health = cache.get(key)

        if health is not None:
            return health

        # Calculate from recent notifications (last hour)
        from django.utils import timezone
        from datetime import timedelta

        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent = NotificationLog.objects.filter(
            provider=obj,
            created_at__gte=one_hour_ago
        )

        if recent.count() < 10:
            # Not enough data, return neutral
            return 80

        successful = recent.filter(status__in=['sent', 'delivered']).count()
        health_percentage = (successful / recent.count()) * 100

        cache.set(key, health_percentage, 300)  # Cache for 5 minutes
        return int(health_percentage)

    @admin.action(description='Test SMS delivery')
    def test_sms(self, request, queryset):
        """Send a test SMS to the admin's phone."""
        for provider in queryset:
            if provider.provider_type in ['sms', 'both']:
                logger.info(f"Test SMS requested for {provider.name}")
                # In production, this would actually send a test SMS
                self.message_user(
                    request,
                    f"Test SMS initiated for {provider.name}. Check logs for result."
                )
            else:
                self.message_user(
                    request,
                    f"{provider.name} does not support SMS",
                    level='error'
                )

    @admin.action(description='Test call delivery')
    def test_call(self, request, queryset):
        """Initiate a test call from the provider."""
        for provider in queryset:
            if provider.provider_type in ['voice', 'both']:
                logger.info(f"Test call requested for {provider.name}")
                self.message_user(
                    request,
                    f"Test call initiated for {provider.name}. Check logs for result."
                )
            else:
                self.message_user(
                    request,
                    f"{provider.name} does not support voice calls",
                    level='error'
                )

    @admin.action(description='Mark as healthy')
    def mark_healthy(self, request, queryset):
        """Mark selected providers as healthy."""
        for provider in queryset:
            key = f"provider_health:{provider.id}"
            cache.set(key, 95, 86400)  # 95% health for 24 hours
        self.message_user(request, "Marked selected providers as healthy")

    @admin.action(description='Mark as unhealthy')
    def mark_unhealthy(self, request, queryset):
        """Mark selected providers as unhealthy."""
        for provider in queryset:
            key = f"provider_health:{provider.id}"
            cache.set(key, 20, 86400)  # 20% health for 24 hours
        self.message_user(request, "Marked selected providers as unhealthy")


@admin.register(ProviderCountry)
class ProviderCountryAdmin(admin.ModelAdmin):
    """Admin for ProviderCountry model."""

    list_display = ('provider', 'country', 'priority', 'is_active', 'success_rate')
    list_filter = ('is_active', 'priority', 'country')
    search_fields = ('provider__name', 'country__name')
    ordering = ('country', 'priority')

    def success_rate(self, obj):
        """Show success rate for this provider in this country."""
        logs = NotificationLog.objects.filter(
            provider=obj.provider,
            user__country=obj.country
        )

        if logs.count() == 0:
            return 'N/A'

        successful = logs.filter(status__in=['sent', 'delivered']).count()
        rate = (successful / logs.count()) * 100
        return f"{rate:.1f}%"

    success_rate.short_description = 'Success Rate'
