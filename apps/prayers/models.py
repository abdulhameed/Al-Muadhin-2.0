from django.db import models

class PrayerTimeCache(models.Model):
    CALCULATION_METHODS = [
        ('MWL', 'Muslim World League'),
        ('ISNA', 'Islamic Society of North America'),
        ('Egypt', 'Egyptian General Authority'),
        ('Makkah', 'Umm Al-Qura University'),
        ('Karachi', 'University of Islamic Sciences'),
        ('Tehran', 'Institute of Geophysics'),
    ]

    city = models.CharField(max_length=100)
    country = models.ForeignKey('providers.Country', on_delete=models.CASCADE)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    date = models.DateField()
    method = models.CharField(max_length=50, choices=CALCULATION_METHODS)

    fajr = models.TimeField()
    sunrise = models.TimeField()
    dhuhr = models.TimeField()
    asr = models.TimeField()
    maghrib = models.TimeField()
    isha = models.TimeField()

    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('latitude', 'longitude', 'date', 'method')
        indexes = [
            models.Index(fields=['date', 'method', 'latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.city} - {self.date} ({self.method})"
