from django.db import models

class Country(models.Model):
    code = models.CharField(max_length=5, unique=True)
    name = models.CharField(max_length=100)
    dial_code = models.CharField(max_length=10)
    is_supported = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Countries"

    def __str__(self):
        return f"{self.name} ({self.code})"


class TelcoProvider(models.Model):
    PROVIDER_TYPE_CHOICES = [
        ('sms', 'SMS'),
        ('voice', 'Voice'),
        ('both', 'SMS & Voice'),
    ]

    name = models.CharField(max_length=100)
    provider_type = models.CharField(max_length=50, choices=PROVIDER_TYPE_CHOICES)
    adapter_class = models.CharField(max_length=255, help_text="Full path to adapter class, e.g. apps.providers.adapters.twilio.TwilioAdapter")
    countries = models.ManyToManyField(Country, through='ProviderCountry')

    api_key = models.CharField(max_length=500, blank=True)
    api_secret = models.CharField(max_length=500, blank=True)
    account_sid = models.CharField(max_length=500, blank=True)
    sender_id = models.CharField(max_length=50, blank=True)
    base_url = models.URLField(blank=True)
    auth_token = models.CharField(max_length=500, blank=True)

    is_active = models.BooleanField(default=True)
    supports_voice = models.BooleanField(default=False)
    voice_webhook_url = models.URLField(blank=True)

    cost_per_sms = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    cost_per_minute = models.DecimalField(max_digits=6, decimal_places=4, default=0)
    currency = models.CharField(max_length=3, default='USD')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.provider_type})"


class ProviderCountry(models.Model):
    provider = models.ForeignKey(TelcoProvider, on_delete=models.CASCADE)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    priority = models.IntegerField(default=0, help_text="0 = primary provider, higher = fallback")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('provider', 'country')
        ordering = ['country', 'priority']
        verbose_name_plural = "Provider Countries"

    def __str__(self):
        return f"{self.provider.name} in {self.country.name} (priority: {self.priority})"
