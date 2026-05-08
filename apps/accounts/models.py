from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    TIER_CHOICES = [
        ('free', 'Free'),
        ('premium', 'Premium'),
    ]

    CALCULATION_METHOD_CHOICES = [
        ('MWL', 'Muslim World League'),
        ('ISNA', 'Islamic Society of North America'),
        ('Egypt', 'Egyptian General Authority'),
        ('Makkah', 'Umm Al-Qura University'),
        ('Karachi', 'University of Islamic Sciences'),
        ('Tehran', 'Institute of Geophysics'),
    ]

    MUEZZIN_CHOICES = [
        ('mishary_rashid', 'Mishary Rashid'),
        ('abdul_basit', 'Abdul Basit'),
    ]

    phone_number = models.CharField(max_length=20, blank=True)
    country = models.ForeignKey('providers.Country', on_delete=models.SET_NULL, null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    calculation_method = models.CharField(max_length=50, choices=CALCULATION_METHOD_CHOICES, default='MWL')
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='free')
    summary_hour = models.IntegerField(default=5)
    pre_adhan_minutes = models.IntegerField(default=15)
    preferred_muezzin = models.CharField(max_length=50, choices=MUEZZIN_CHOICES, default='mishary_rashid')
    is_active_subscriber = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.username} ({self.email})"


class NotificationPreference(models.Model):
    PRAYER_CHOICES = [
        ('fajr', 'Fajr'),
        ('dhuhr', 'Dhuhr'),
        ('asr', 'Asr'),
        ('maghrib', 'Maghrib'),
        ('isha', 'Isha'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    prayer = models.CharField(max_length=20, choices=PRAYER_CHOICES)
    summary_email = models.BooleanField(default=True)
    summary_sms = models.BooleanField(default=False)
    pre_adhan_sms = models.BooleanField(default=False)
    adhan_sms = models.BooleanField(default=False)
    adhan_call = models.BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'prayer')
        verbose_name_plural = "Notification Preferences"

    def __str__(self):
        return f"{self.user.username} - {self.prayer}"
