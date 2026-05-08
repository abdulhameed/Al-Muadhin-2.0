from django.db import models

class NotificationLog(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('summary', 'Daily Summary'),
        ('pre_adhan', 'Pre-Adhan'),
        ('adhan', 'Adhan'),
    ]

    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('call', 'Phone Call'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]

    PRAYER_CHOICES = [
        ('fajr', 'Fajr'),
        ('dhuhr', 'Dhuhr'),
        ('asr', 'Asr'),
        ('maghrib', 'Maghrib'),
        ('isha', 'Isha'),
    ]

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    channel = models.CharField(max_length=50, choices=CHANNEL_CHOICES)
    prayer = models.CharField(max_length=20, choices=PRAYER_CHOICES, blank=True)
    provider = models.ForeignKey('providers.TelcoProvider', on_delete=models.SET_NULL, null=True, blank=True)

    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    external_id = models.CharField(max_length=255, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)

    cost_estimate = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    scheduled_for = models.DateTimeField()
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['notification_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type} ({self.channel}) - {self.status}"
