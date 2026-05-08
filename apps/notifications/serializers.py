from rest_framework import serializers
from .models import NotificationLog


class NotificationLogSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    provider_name = serializers.CharField(source='provider.name', read_only=True)

    class Meta:
        model = NotificationLog
        fields = [
            'id',
            'user_email',
            'notification_type',
            'channel',
            'prayer',
            'provider_name',
            'status',
            'external_id',
            'error_message',
            'retry_count',
            'cost_estimate',
            'sent_at',
            'delivered_at',
            'created_at',
        ]
        read_only_fields = fields
