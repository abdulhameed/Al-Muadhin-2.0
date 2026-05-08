import logging
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from apps.accounts.models import NotificationPreference
from .models import NotificationLog
from .serializers import NotificationLogSerializer
from .services import NotificationService
from apps.providers.services import CostAnalytics

logger = logging.getLogger(__name__)


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class NotificationsViewSet(viewsets.ViewSet):
    """API endpoints for notifications and preferences."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get paginated notification history."""
        logs = NotificationLog.objects.filter(user=request.user).order_by('-created_at')

        # Apply filters
        notification_type = request.query_params.get('type')
        if notification_type:
            logs = logs.filter(notification_type=notification_type)

        channel = request.query_params.get('channel')
        if channel:
            logs = logs.filter(channel=channel)

        status_filter = request.query_params.get('status')
        if status_filter:
            logs = logs.filter(status=status_filter)

        paginator = NotificationPagination()
        paginated_logs = paginator.paginate_queryset(logs, request)
        serializer = NotificationLogSerializer(paginated_logs, many=True)

        return paginator.get_paginated_response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get notification statistics for current user."""
        stats = NotificationService.get_notification_stats(request.user)
        return Response(stats)

    @action(detail=False, methods=['post'])
    def pause(self, request):
        """Pause all notifications for current user."""
        request.user.is_active_subscriber = False
        request.user.save()
        logger.info(f"User {request.user.id} paused notifications")
        return Response({'status': 'paused'})

    @action(detail=False, methods=['post'])
    def resume(self, request):
        """Resume all notifications for current user."""
        request.user.is_active_subscriber = True
        request.user.save()
        logger.info(f"User {request.user.id} resumed notifications")
        return Response({'status': 'resumed'})

    @action(detail=False, methods=['get', 'put', 'patch'])
    def preferences(self, request):
        """Get or update per-prayer notification preferences."""
        if request.method == 'GET':
            prefs = NotificationPreference.objects.filter(user=request.user)
            data = {}
            for pref in prefs:
                data[pref.prayer] = {
                    'summary_email': pref.summary_email,
                    'summary_sms': pref.summary_sms,
                    'pre_adhan_sms': pref.pre_adhan_sms,
                    'adhan_sms': pref.adhan_sms,
                    'adhan_call': pref.adhan_call,
                }
            return Response(data)

        elif request.method in ['PUT', 'PATCH']:
            # Update preferences
            data = request.data
            for prayer, prefs_data in data.items():
                pref, _ = NotificationPreference.objects.get_or_create(
                    user=request.user,
                    prayer=prayer
                )
                # Enforce premium tier restrictions
                if request.user.tier == 'free':
                    prefs_data['summary_sms'] = False
                    prefs_data['pre_adhan_sms'] = False
                    prefs_data['adhan_sms'] = False
                    prefs_data['adhan_call'] = False

                for key, value in prefs_data.items():
                    if hasattr(pref, key):
                        setattr(pref, key, value)
                pref.save()

            logger.info(f"User {request.user.id} updated notification preferences")
            return Response({'status': 'updated'})

    @action(detail=False, methods=['get', 'patch'], url_path='preferences/(?P<prayer>[a-z]+)')
    def preference_detail(self, request, prayer=None):
        """Get or update preferences for a specific prayer."""
        try:
            pref = NotificationPreference.objects.get(user=request.user, prayer=prayer)
        except NotificationPreference.DoesNotExist:
            return Response({'error': 'Preference not found'}, status=status.HTTP_404_NOT_FOUND)

        if request.method == 'GET':
            data = {
                'prayer': pref.prayer,
                'summary_email': pref.summary_email,
                'summary_sms': pref.summary_sms,
                'pre_adhan_sms': pref.pre_adhan_sms,
                'adhan_sms': pref.adhan_sms,
                'adhan_call': pref.adhan_call,
            }
            return Response(data)

        elif request.method == 'PATCH':
            # Enforce premium tier restrictions
            if request.user.tier == 'free':
                for field in ['summary_sms', 'pre_adhan_sms', 'adhan_sms', 'adhan_call']:
                    if field in request.data:
                        request.data[field] = False

            for key, value in request.data.items():
                if hasattr(pref, key):
                    setattr(pref, key, value)
            pref.save()

            logger.info(f"User {request.user.id} updated {prayer} preferences")
            return Response({'status': 'updated'})

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def cost_summary(self, request):
        """Get cost breakdown by provider, country, and channel (admin only)."""
        days = request.query_params.get('days', 30)
        try:
            days = int(days)
        except ValueError:
            days = 30

        from django.utils import timezone
        from datetime import timedelta

        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)

        summary = CostAnalytics.get_cost_summary(start_date, end_date)
        return Response(summary)

    @action(detail=False, methods=['get'], permission_classes=[IsAdminUser])
    def cost_by_provider(self, request):
        """Get cost breakdown by provider (admin only)."""
        from apps.providers.models import TelcoProvider

        providers = TelcoProvider.objects.filter(is_active=True)
        data = []

        for provider in providers:
            costs = CostAnalytics.get_provider_costs(provider)
            data.append(costs)

        return Response(data)


def notification_list(request):
    """Legacy view for notification list page."""
    return render(request, 'notifications/list.html')
