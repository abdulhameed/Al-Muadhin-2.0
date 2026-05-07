# Al-Muadhin — Product Requirements Document

## Prayer Notification Service

**Version:** 1.0
**Last Updated:** April 14, 2026
**Status:** Planning

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [User Personas & Tiers](#3-user-personas--tiers)
4. [Tech Stack](#4-tech-stack)
5. [Project Structure](#5-project-structure)
6. [Data Models](#6-data-models)
7. [Notification System Design](#7-notification-system-design)
8. [Provider Adapter Architecture](#8-provider-adapter-architecture)
9. [Milestone 1 — Foundation](#milestone-1--foundation)
10. [Milestone 2 — Prayer Engine & Scheduling](#milestone-2--prayer-engine--scheduling)
11. [Milestone 3 — Notification Channels](#milestone-3--notification-channels)
12. [Milestone 4 — User Dashboard](#milestone-4--user-dashboard)
13. [Milestone 5 — Phone Call Channel & Premium Tier](#milestone-5--phone-call-channel--premium-tier)
14. [Milestone 6 — Multi-Country Provider Registry](#milestone-6--multi-country-provider-registry)
15. [Milestone 7 — Hardening, Monitoring & Deployment](#milestone-7--hardening-monitoring--deployment)
16. [API Endpoints](#api-endpoints)
17. [Environment Variables](#environment-variables)
18. [Deployment Architecture](#deployment-architecture)
19. [Future Considerations](#future-considerations)

---

## 1. Product Overview

**Al-Muadhin** is a web service that notifies Muslims of salah (prayer) times through email, SMS, and phone calls. It supports multiple countries, each potentially using a different telephony provider to minimize cost. Providers and their credentials are managed entirely through the Django admin panel — no code changes or redeployment needed to add a new country or swap a provider.

### Core Value Proposition

- Reliable, timely prayer notifications across 3 channels (email, SMS, phone call).
- Beautiful adhan recitation delivered via phone call for premium users.
- Worldwide support starting with Nigeria, UK, US, Canada, and UAE.
- Cost-optimized by using local telephony providers per country instead of a single expensive global provider.

### Notification Types

| Type | Trigger | Description |
|---|---|---|
| **Daily Summary** | Beginning of day (user's local time) | All 5 prayer times for the day in one message. |
| **Pre-Adhan** | Configurable minutes before prayer (default: 15) | Heads-up that prayer time is approaching. |
| **Adhan** | Exact prayer time | Notification or phone call at the moment of prayer. |

### Channel × Tier Matrix

| Notification Type | Free Tier | Premium Tier |
|---|---|---|
| Daily Summary | ✅ Email | ✅ Email + SMS |
| Pre-Adhan | ❌ | ✅ SMS |
| Adhan | ❌ | ✅ SMS + Phone Call |

---

## 2. Goals & Success Metrics

| Goal | Metric | Target |
|---|---|---|
| Notification reliability | % of notifications delivered on time (within 60s of target) | ≥ 99% |
| Prayer time accuracy | Deviation from verified prayer time sources | ≤ 1 minute |
| Provider flexibility | Time to add a new country provider | < 10 minutes (admin UI only) |
| User satisfaction | Daily summary open rate (email) | ≥ 40% |
| System uptime | Service availability | ≥ 99.5% |

---

## 3. User Personas & Tiers

### Free Tier User

- Receives daily prayer time summary via email each morning.
- Can configure: city/location, timezone, prayer calculation method, summary delivery time.
- Cannot receive SMS, pre-adhan, or phone call notifications.

### Premium Tier User

- Everything in Free, plus:
- SMS notifications (daily summary, pre-adhan, and/or at adhan time).
- Phone call at adhan time with a recitation of the adhan.
- Can choose preferred muezzin voice (from a curated library of recordings).
- Configurable pre-adhan lead time (5, 10, 15, 20, or 30 minutes).
- Per-prayer notification preferences (e.g., phone call for Fajr only, SMS for others).

---

## 4. Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | Django 5.x + Django REST Framework |
| **Database** | PostgreSQL 16 |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery 5.x + Celery Beat |
| **Email Provider** | SendGrid (free tier: 100 emails/day) |
| **SMS/Voice Providers** | Country-specific (Twilio, Termii, Vonage, etc.) |
| **Prayer Times API** | Aladhan API (https://aladhan.com/prayer-times-api) |
| **Credential Encryption** | django-encrypted-model-fields |
| **Containerization** | Docker + Docker Compose |
| **Reverse Proxy** | Nginx |
| **Web Server** | Gunicorn |
| **VPS** | Ubuntu 24.04 LTS |

---

## 5. Project Structure

```
al_muadhin/
├── manage.py
├── docker-compose.yml
├── Dockerfile
├── nginx/
│   └── nginx.conf
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── config/                      # Django project settings
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   ├── celery.py                # Celery app configuration
│   └── wsgi.py
├── apps/
│   ├── accounts/                # User model, auth, registration
│   │   ├── models.py
│   │   ├── admin.py
│   │   ├── views.py
│   │   ├── serializers.py
│   │   ├── urls.py
│   │   ├── managers.py
│   │   └── tests/
│   ├── prayers/                 # Prayer time engine
│   │   ├── models.py            # PrayerTimeCache model
│   │   ├── services.py          # Aladhan API client + caching logic
│   │   ├── calculation.py       # Calculation method definitions
│   │   ├── admin.py
│   │   ├── urls.py
│   │   └── tests/
│   ├── notifications/           # Core notification system
│   │   ├── models.py            # NotificationLog, NotificationPreference
│   │   ├── tasks.py             # Celery Beat tasks (3 dispatchers)
│   │   ├── dispatcher.py        # Country → provider routing + fallback
│   │   ├── services.py          # High-level send_email, send_sms, make_call
│   │   ├── admin.py
│   │   ├── urls.py
│   │   └── tests/
│   ├── providers/               # Telephony provider registry
│   │   ├── models.py            # TelcoProvider, Country, ProviderCountry
│   │   ├── adapters/            # Provider adapter implementations
│   │   │   ├── __init__.py
│   │   │   ├── base.py          # BaseAdapter ABC
│   │   │   ├── twilio.py
│   │   │   ├── termii.py
│   │   │   ├── vonage.py
│   │   │   └── sendgrid.py      # Email adapter
│   │   ├── registry.py          # Dynamic adapter loader
│   │   ├── admin.py             # Rich Django admin for provider management
│   │   └── tests/
│   └── dashboard/               # User-facing web UI
│       ├── views.py
│       ├── forms.py
│       ├── urls.py
│       └── tests/
├── templates/
│   ├── base.html
│   ├── dashboard/
│   │   ├── home.html
│   │   ├── preferences.html
│   │   ├── notification_history.html
│   │   └── subscription.html
│   ├── emails/
│   │   ├── daily_summary.html
│   │   ├── daily_summary.txt
│   │   ├── welcome.html
│   │   └── welcome.txt
│   ├── registration/
│   │   ├── login.html
│   │   ├── register.html
│   │   └── password_reset.html
│   └── sms/
│       ├── daily_summary.txt
│       ├── pre_adhan.txt
│       └── adhan.txt
├── static/
│   ├── css/
│   ├── js/
│   └── audio/                   # Adhan recordings (or S3 references)
│       ├── mishary_rashid.mp3
│       └── abdul_basit.mp3
└── media/
```

---

## 6. Data Models

### accounts.User (extends AbstractUser)

```python
class User(AbstractUser):
    phone_number        = CharField(max_length=20, blank=True)          # E.164 format: +2348012345678
    country             = ForeignKey('providers.Country')
    city                = CharField(max_length=100)
    latitude            = DecimalField(max_digits=9, decimal_places=6)
    longitude           = DecimalField(max_digits=9, decimal_places=6)
    timezone            = CharField(max_length=50)                      # e.g. "Africa/Lagos"
    calculation_method  = CharField(choices=CALCULATION_METHODS)         # ISNA, MWL, Egyptian, etc.
    tier                = CharField(choices=['free', 'premium'], default='free')
    summary_hour        = IntegerField(default=5)                       # Local hour to send daily summary (0-23)
    pre_adhan_minutes   = IntegerField(default=15)                      # Minutes before adhan for pre-notification
    preferred_muezzin   = CharField(choices=MUEZZIN_CHOICES, default='mishary_rashid')
    is_active_subscriber = BooleanField(default=True)                   # Can pause notifications
```

### accounts.NotificationPreference

Per-prayer, per-channel preferences for premium users.

```python
class NotificationPreference(Model):
    user            = ForeignKey(User)
    prayer          = CharField(choices=['fajr', 'dhuhr', 'asr', 'maghrib', 'isha'])
    summary_email   = BooleanField(default=True)
    summary_sms     = BooleanField(default=False)
    pre_adhan_sms   = BooleanField(default=False)
    adhan_sms       = BooleanField(default=False)
    adhan_call      = BooleanField(default=False)

    class Meta:
        unique_together = ('user', 'prayer')
```

### providers.Country

```python
class Country(Model):
    code        = CharField(max_length=5, unique=True)    # ISO 3166-1: NG, GB, US, CA, AE
    name        = CharField(max_length=100)
    dial_code   = CharField(max_length=10)                 # +234, +44, +1, +971
    is_supported = BooleanField(default=True)
```

### providers.TelcoProvider

The central model that eliminates redeployment for new providers.

```python
class TelcoProvider(Model):
    name            = CharField(max_length=100)                         # "Twilio US", "Termii NG"
    provider_type   = CharField(choices=['sms', 'voice', 'both'])
    adapter_class   = CharField(max_length=255)                         # "apps.providers.adapters.twilio.TwilioAdapter"
    countries       = ManyToManyField(Country, through='ProviderCountry')

    # Encrypted credentials
    api_key         = EncryptedCharField(max_length=500)
    api_secret      = EncryptedCharField(max_length=500, blank=True)
    account_sid     = EncryptedCharField(max_length=500, blank=True)    # Twilio-specific
    sender_id       = CharField(max_length=50, blank=True)              # SMS sender name/number
    base_url        = URLField(blank=True)                              # For providers with custom endpoints
    auth_token      = EncryptedCharField(max_length=500, blank=True)

    # Operational
    is_active       = BooleanField(default=True)
    supports_voice  = BooleanField(default=False)
    voice_webhook_url = URLField(blank=True)                            # For TwiML/NCCO callback

    # Cost tracking
    cost_per_sms    = DecimalField(max_digits=6, decimal_places=4, default=0)
    cost_per_minute = DecimalField(max_digits=6, decimal_places=4, default=0)
    currency        = CharField(max_length=3, default='USD')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.provider_type})"
```

### providers.ProviderCountry

Priority-based mapping of providers to countries (enables fallback).

```python
class ProviderCountry(Model):
    provider    = ForeignKey(TelcoProvider)
    country     = ForeignKey(Country)
    priority    = IntegerField(default=0)       # Lower = higher priority. 0 = primary.
    is_active   = BooleanField(default=True)

    class Meta:
        unique_together = ('provider', 'country')
        ordering = ['country', 'priority']
```

### prayers.PrayerTimeCache

Caches daily prayer times per city to avoid hammering the Aladhan API.

```python
class PrayerTimeCache(Model):
    city            = CharField(max_length=100)
    country         = ForeignKey('providers.Country')
    latitude        = DecimalField(max_digits=9, decimal_places=6)
    longitude       = DecimalField(max_digits=9, decimal_places=6)
    date            = DateField()
    method          = CharField(max_length=50)       # Calculation method used
    fajr            = TimeField()
    sunrise         = TimeField()
    dhuhr           = TimeField()
    asr             = TimeField()
    maghrib         = TimeField()
    isha            = TimeField()
    fetched_at      = DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('latitude', 'longitude', 'date', 'method')
        indexes = [
            Index(fields=['date', 'method', 'latitude', 'longitude']),
        ]
```

### notifications.NotificationLog

Tracks every notification sent for debugging, analytics, and billing.

```python
class NotificationLog(Model):
    user                = ForeignKey(User)
    notification_type   = CharField(choices=['summary', 'pre_adhan', 'adhan'])
    channel             = CharField(choices=['email', 'sms', 'call'])
    prayer              = CharField(choices=PRAYER_CHOICES, blank=True)
    provider            = ForeignKey(TelcoProvider, null=True, blank=True)
    status              = CharField(choices=['pending', 'sent', 'delivered', 'failed', 'retrying'])
    external_id         = CharField(max_length=255, blank=True)        # Provider's message/call ID
    error_message       = TextField(blank=True)
    retry_count         = IntegerField(default=0)
    cost_estimate       = DecimalField(max_digits=8, decimal_places=4, default=0)
    scheduled_for       = DateTimeField()                               # When it was supposed to fire
    sent_at             = DateTimeField(null=True)                      # When it actually fired
    delivered_at        = DateTimeField(null=True)
    created_at          = DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            Index(fields=['user', 'created_at']),
            Index(fields=['status', 'scheduled_for']),
            Index(fields=['notification_type', 'created_at']),
        ]
```

---

## 7. Notification System Design

### Scheduler Architecture

Celery Beat runs 3 periodic tasks at fixed intervals. Each task queries for users who need a notification at that moment, groups them efficiently, and dispatches via the appropriate channel.

```
Celery Beat (periodic scheduler)
│
├── Every 5 minutes ─→ dispatch_daily_summaries
│   Query: users whose local time == their summary_hour and haven't received today's summary
│   Action: Fetch prayer times (cached), send email (all tiers) + SMS (premium)
│
├── Every 1 minute ──→ dispatch_pre_adhan_notifications
│   Query: users with a prayer in exactly {pre_adhan_minutes} minutes
│   Action: Send SMS to premium users who opted in for that prayer
│
└── Every 1 minute ──→ dispatch_adhan_notifications
    Query: users with a prayer happening NOW (within 60-second window)
    Action: Send SMS and/or initiate phone call for opted-in premium users
```

### Timezone Grouping Strategy

Instead of checking every individual user each tick, users are grouped by `timezone` field:

1. On each tick, calculate: "For timezone X, what is the current local time?"
2. For `dispatch_daily_summaries`: filter users where `timezone` matches a group whose local hour == `summary_hour`.
3. For `dispatch_pre_adhan` / `dispatch_adhan`: use the cached PrayerTimeCache for each city, compare against current local time, and batch-dispatch.

This keeps per-tick database queries bounded: ~40 timezone groups worldwide, not N individual users.

### Dispatch Flow

```
Task fires
  → Query eligible users (by timezone group + preferences)
  → For each user:
      → Fetch prayer times from PrayerTimeCache (or fetch + cache from Aladhan API)
      → Determine channel(s) based on tier + preferences
      → For SMS/Voice:
          → dispatcher.resolve_provider(user.country, channel_type)
          → Returns ordered list of (adapter_instance, provider_record)
          → Try primary adapter.send_sms() or adapter.make_call()
          → On failure: log error, try next fallback provider
          → Log result to NotificationLog
      → For Email:
          → Use SendGrid adapter directly (no country routing needed)
          → Log result to NotificationLog
```

### Retry Strategy

- **SMS**: Retry up to 3 times with exponential backoff (30s, 120s, 300s). After 3 failures, try fallback provider if available.
- **Phone Call**: Retry up to 2 times (60s, 180s). No fallback — phone calls are time-sensitive and a delayed adhan call loses value.
- **Email**: Retry up to 3 times with exponential backoff. Email is the most tolerant of delay.

---

## 8. Provider Adapter Architecture

### Base Adapter (Abstract)

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class SendResult:
    success: bool
    external_id: str = ""
    error_message: str = ""
    cost: float = 0.0

class BaseAdapter(ABC):
    def __init__(self, provider: 'TelcoProvider'):
        self.provider = provider
        self.api_key = provider.api_key
        self.api_secret = provider.api_secret

    @abstractmethod
    def send_sms(self, to: str, message: str) -> SendResult:
        """Send an SMS message. `to` is E.164 format."""
        pass

    @abstractmethod
    def make_call(self, to: str, audio_url: str) -> SendResult:
        """Initiate a phone call that plays the given audio URL."""
        pass

    def validate_phone(self, phone: str) -> bool:
        """Basic E.164 validation."""
        import re
        return bool(re.match(r'^\+[1-9]\d{1,14}$', phone))
```

### Provider Registry (Dynamic Loader)

```python
import importlib

def get_adapter(provider: TelcoProvider) -> BaseAdapter:
    """
    Dynamically loads the adapter class from the provider's adapter_class field.
    E.g., "apps.providers.adapters.twilio.TwilioAdapter" → imports and instantiates.
    """
    module_path, class_name = provider.adapter_class.rsplit('.', 1)
    module = importlib.import_module(module_path)
    adapter_cls = getattr(module, class_name)
    return adapter_cls(provider)
```

### Dispatcher (Country → Provider Resolution)

```python
def resolve_providers(country: Country, channel: str) -> list[tuple[BaseAdapter, TelcoProvider]]:
    """
    Returns an ordered list of (adapter, provider) for the given country and channel.
    Ordered by ProviderCountry.priority. Used for fallback.
    """
    provider_countries = ProviderCountry.objects.filter(
        country=country,
        is_active=True,
        provider__is_active=True,
    ).select_related('provider')

    if channel == 'sms':
        provider_countries = provider_countries.filter(
            provider__provider_type__in=['sms', 'both']
        )
    elif channel == 'voice':
        provider_countries = provider_countries.filter(
            provider__supports_voice=True
        )

    results = []
    for pc in provider_countries.order_by('priority'):
        adapter = get_adapter(pc.provider)
        results.append((adapter, pc.provider))
    return results
```

### Adapter Implementation Examples

**Twilio Adapter:**

```python
class TwilioAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        from twilio.rest import Client
        self.client = Client(provider.account_sid, provider.auth_token)
        self.from_number = provider.sender_id

    def send_sms(self, to, message):
        try:
            msg = self.client.messages.create(body=message, from_=self.from_number, to=to)
            return SendResult(success=True, external_id=msg.sid)
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        try:
            call = self.client.calls.create(
                to=to, from_=self.from_number,
                twiml=f'<Response><Play>{audio_url}</Play></Response>'
            )
            return SendResult(success=True, external_id=call.sid)
        except Exception as e:
            return SendResult(success=False, error_message=str(e))
```

**Termii Adapter:**

```python
class TermiiAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        self.base_url = provider.base_url or "https://api.ng.termii.com/api"
        self.sender_id = provider.sender_id

    def send_sms(self, to, message):
        import requests
        payload = {
            "to": to, "from": self.sender_id, "sms": message,
            "type": "plain", "channel": "generic", "api_key": self.api_key,
        }
        try:
            r = requests.post(f"{self.base_url}/sms/send", json=payload, timeout=10)
            data = r.json()
            if r.ok and data.get("message_id"):
                return SendResult(success=True, external_id=data["message_id"])
            return SendResult(success=False, error_message=data.get("message", "Unknown error"))
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        # Termii doesn't support outbound voice; this should not be called.
        return SendResult(success=False, error_message="Voice not supported by Termii")
```

---

## Milestone 1 — Foundation

**Goal:** Scaffolded Django project with Docker, database, custom User model, and basic admin access.

**Estimated Duration:** 3–4 days

### Checklist

- [ ] Initialize Django 5 project with the directory structure from Section 5
- [ ] Configure split settings (base.py, dev.py, prod.py)
- [ ] Set up Docker Compose with services: `web`, `db` (PostgreSQL 16), `redis` (Redis 7), `celery_worker`, `celery_beat`
- [ ] Write Dockerfile (Python 3.12, multi-stage for prod)
- [ ] Create `apps/accounts` app with custom User model (extend AbstractUser with all fields from Section 6)
- [ ] Create `apps/providers` app with Country model, seed initial countries (NG, GB, US, CA, AE)
- [ ] Write initial migration and verify User creation via Django shell
- [ ] Configure Django Admin for User and Country models
- [ ] Set up django-encrypted-model-fields and verify encryption works
- [ ] Add requirements/base.txt with all core dependencies:
  - `Django>=5.0`, `djangorestframework`, `celery[redis]`, `django-celery-beat`
  - `django-encrypted-model-fields`, `psycopg[binary]`, `redis`, `gunicorn`
  - `requests`, `python-dateutil`, `pytz`
- [ ] Add requirements/dev.txt: `django-debug-toolbar`, `pytest-django`, `factory-boy`, `black`, `ruff`
- [ ] Configure Celery app in `config/celery.py`, verify connection to Redis
- [ ] Create `.env.example` with all required environment variables
- [ ] Write a basic `docker-compose up` smoke test (web, db, redis all healthy)
- [ ] Add `.gitignore`, `README.md` with setup instructions

---

## Milestone 2 — Prayer Engine & Scheduling

**Goal:** Fetch, cache, and serve prayer times. Celery Beat running on schedule.

**Estimated Duration:** 4–5 days

### Checklist

- [ ] Create `apps/prayers` app
- [ ] Implement PrayerTimeCache model (see Section 6)
- [ ] Build Aladhan API client in `prayers/services.py`:
  - [ ] `fetch_prayer_times(latitude, longitude, date, method)` → calls Aladhan API
  - [ ] Parse response into PrayerTimeCache fields
  - [ ] Handle API errors gracefully (timeout, rate limit, malformed response)
- [ ] Implement caching layer:
  - [ ] Check PrayerTimeCache first (by lat/lng + date + method)
  - [ ] If cache miss, fetch from API, store in DB, return
  - [ ] Add Redis cache on top for hot lookups (TTL: 24 hours)
- [ ] Define CALCULATION_METHODS constant with all supported methods:
  - [ ] Muslim World League (MWL)
  - [ ] Islamic Society of North America (ISNA)
  - [ ] Egyptian General Authority of Survey
  - [ ] Umm Al-Qura University, Makkah
  - [ ] University of Islamic Sciences, Karachi
  - [ ] Institute of Geophysics, University of Tehran
- [ ] Map each method to its Aladhan API method ID
- [ ] Write management command: `python manage.py fetch_prayers --city Lagos --date 2026-04-15`
- [ ] Create NotificationPreference model (per-prayer, per-channel settings)
- [ ] Configure Celery Beat schedule in `config/celery.py`:
  - [ ] `dispatch_daily_summaries` every 5 minutes
  - [ ] `dispatch_pre_adhan_notifications` every 1 minute
  - [ ] `dispatch_adhan_notifications` every 1 minute
- [ ] Write stub tasks in `notifications/tasks.py` (log "would send to N users" without actually sending)
- [ ] Implement timezone grouping logic:
  - [ ] Given current UTC time, determine which timezone groups have an actionable moment
  - [ ] Query users in those groups efficiently
- [ ] Add Django Admin for PrayerTimeCache (read-only, searchable by city/date)
- [ ] Write tests:
  - [ ] Test Aladhan API client with mocked responses
  - [ ] Test cache hit/miss logic
  - [ ] Test timezone grouping returns correct user sets
  - [ ] Test Celery tasks fire on schedule (using celery test utilities)

---

## Milestone 3 — Notification Channels (Email + SMS)

**Goal:** Working email and SMS delivery with provider routing and logging.

**Estimated Duration:** 5–7 days

### Checklist

- [ ] Create TelcoProvider model with encrypted fields (see Section 6)
- [ ] Create ProviderCountry model with priority-based mapping
- [ ] Build rich Django Admin for TelcoProvider:
  - [ ] Inline ProviderCountry entries (add countries + priorities from the provider page)
  - [ ] Search by name, filter by provider_type, country, is_active
  - [ ] Display cost_per_sms, cost_per_minute in list view
  - [ ] Add "Test Connection" admin action (sends a test SMS to admin's phone)
- [ ] Implement BaseAdapter ABC in `providers/adapters/base.py` (see Section 8)
- [ ] Implement TwilioAdapter in `providers/adapters/twilio.py`
- [ ] Implement TermiiAdapter in `providers/adapters/termii.py`
- [ ] Implement VonageAdapter in `providers/adapters/vonage.py`
- [ ] Implement SendGridAdapter in `providers/adapters/sendgrid.py` (email only)
- [ ] Build provider registry (`providers/registry.py`):
  - [ ] `get_adapter(provider)` — dynamic class loading from adapter_class field
  - [ ] Validate adapter_class points to a real class on save (model clean method)
- [ ] Build dispatcher (`notifications/dispatcher.py`):
  - [ ] `resolve_providers(country, channel)` — returns ordered (adapter, provider) list
  - [ ] `dispatch_sms(user, message)` — resolves provider, sends, handles fallback
  - [ ] `dispatch_email(user, subject, html, text)` — sends via SendGrid
- [ ] Create NotificationLog model (see Section 6)
- [ ] Wire up actual sending in Celery tasks:
  - [ ] `dispatch_daily_summaries`: fetch prayer times → render email template → send email (all users) + SMS (premium)
  - [ ] `dispatch_pre_adhan_notifications`: resolve eligible users → send SMS
  - [ ] `dispatch_adhan_notifications`: resolve eligible users → send SMS (phone calls deferred to Milestone 5)
- [ ] Implement retry logic:
  - [ ] SMS: 3 retries, exponential backoff (30s, 120s, 300s), then try fallback provider
  - [ ] Email: 3 retries, exponential backoff
  - [ ] Log each attempt in NotificationLog
- [ ] Build email templates:
  - [ ] `daily_summary.html` — clean, mobile-friendly HTML email listing all 5 prayer times
  - [ ] `daily_summary.txt` — plain text fallback
  - [ ] `welcome.html` / `welcome.txt` — sent on registration
- [ ] Build SMS templates:
  - [ ] `daily_summary.txt` — concise, fits in 1 SMS (160 chars if possible)
  - [ ] `pre_adhan.txt` — e.g., "Dhuhr is in 15 minutes (12:45 PM). Prepare for salah."
  - [ ] `adhan.txt` — e.g., "It's time for Dhuhr. Allahu Akbar."
- [ ] Seed test providers in fixtures/management command for dev environment
- [ ] Write tests:
  - [ ] Test each adapter with mocked HTTP responses
  - [ ] Test dispatcher fallback (primary fails → secondary succeeds)
  - [ ] Test dispatcher when no provider exists for a country (graceful error)
  - [ ] Test retry logic fires correct number of times
  - [ ] Test NotificationLog records are created correctly
  - [ ] Test email template renders with correct prayer times

---

## Milestone 4 — User Dashboard

**Goal:** Users can register, log in, set preferences, and view notification history.

**Estimated Duration:** 5–7 days

### Checklist

- [ ] Create `apps/dashboard` app
- [ ] Implement user registration:
  - [ ] Registration form: email, password, phone number, country, city
  - [ ] Auto-detect timezone from city (use a timezone lookup or let user select)
  - [ ] Auto-geocode city to lat/lng (use a simple geocoding service or manual entry)
  - [ ] Send welcome email on registration
- [ ] Implement authentication:
  - [ ] Login page (email + password)
  - [ ] Logout
  - [ ] Password reset via email
  - [ ] "Remember me" functionality
- [ ] Build dashboard home page:
  - [ ] Show today's prayer times for user's location
  - [ ] Show next upcoming prayer with countdown
  - [ ] Show notification delivery status (last 5 notifications)
  - [ ] Quick-toggle to pause/resume all notifications
- [ ] Build preferences page:
  - [ ] Location settings: city, country, timezone (auto-update lat/lng on city change)
  - [ ] Calculation method selector with brief descriptions
  - [ ] Daily summary delivery hour selector (dropdown, 0–23)
  - [ ] Pre-adhan lead time selector (5, 10, 15, 20, 30 minutes)
  - [ ] Per-prayer notification grid:
    - [ ] Rows: Fajr, Dhuhr, Asr, Maghrib, Isha
    - [ ] Columns: Summary Email, Summary SMS, Pre-Adhan SMS, Adhan SMS, Adhan Call
    - [ ] Checkboxes, with SMS/Call columns disabled for free tier users (with upgrade prompt)
  - [ ] Preferred muezzin selector (for phone call adhan)
  - [ ] Phone number field with country code prefix
- [ ] Build notification history page:
  - [ ] Paginated list of NotificationLog entries for the user
  - [ ] Show: date, prayer, type, channel, status, provider used
  - [ ] Filter by notification type, channel, status, date range
- [ ] Build subscription page:
  - [ ] Show current tier (Free / Premium)
  - [ ] Feature comparison table
  - [ ] Upgrade button (payment integration deferred — for now, admin manually upgrades users)
- [ ] Style all pages:
  - [ ] Clean, responsive design (works on mobile)
  - [ ] Islamic-inspired color palette and subtle geometric patterns
  - [ ] Consistent navigation bar with user menu
- [ ] Write tests:
  - [ ] Test registration flow end-to-end
  - [ ] Test preference save/load round-trip
  - [ ] Test free tier users cannot enable SMS/Call checkboxes
  - [ ] Test notification history displays correct data
  - [ ] Test timezone updates when city changes

---

## Milestone 5 — Phone Call Channel & Premium Tier

**Goal:** Premium users receive adhan phone calls at prayer time.

**Estimated Duration:** 4–5 days

### Checklist

- [ ] Prepare adhan audio files:
  - [ ] Source 2–3 high-quality adhan recordings (ensure licensing is clear)
  - [ ] Convert to MP3, normalize audio levels
  - [ ] Host on S3 or serve from static files with a public URL
  - [ ] Map each recording to a MUEZZIN_CHOICES entry
- [ ] Extend TwilioAdapter.make_call():
  - [ ] Generate TwiML response that plays the selected adhan audio
  - [ ] Handle call status callbacks (ringing, answered, completed, failed, busy, no-answer)
  - [ ] Set reasonable timeout (30 seconds ring, then give up)
- [ ] Extend VonageAdapter.make_call():
  - [ ] Generate NCCO JSON that streams the adhan audio
  - [ ] Handle event webhooks
- [ ] Build webhook endpoints for call status:
  - [ ] `POST /api/webhooks/twilio/call-status/` — updates NotificationLog with call outcome
  - [ ] `POST /api/webhooks/vonage/call-event/` — same for Vonage
  - [ ] Secure webhooks (validate Twilio signature, Vonage JWT)
- [ ] Wire phone calls into `dispatch_adhan_notifications` task:
  - [ ] For premium users with adhan_call enabled for this prayer:
    - [ ] Resolve voice provider for user's country
    - [ ] Get audio URL for user's preferred muezzin
    - [ ] Call adapter.make_call(phone, audio_url)
    - [ ] Log to NotificationLog with channel='call'
- [ ] Implement call retry logic:
  - [ ] If busy/no-answer: retry once after 60 seconds
  - [ ] If failed (network error): retry once after 180 seconds
  - [ ] Max 2 retries for calls (they're time-sensitive)
- [ ] Add cost tracking:
  - [ ] Estimate cost per call using provider's cost_per_minute × average adhan duration
  - [ ] Store estimate in NotificationLog.cost_estimate
  - [ ] Add admin dashboard widget showing daily/monthly notification costs
- [ ] Handle concurrency:
  - [ ] Rate-limit outbound calls per provider (e.g., Twilio allows N concurrent calls)
  - [ ] Queue calls and stagger by a few seconds if burst is large
- [ ] Write tests:
  - [ ] Test TwiML generation with different muezzin audio URLs
  - [ ] Test NCCO generation for Vonage
  - [ ] Test webhook signature validation
  - [ ] Test call retry logic (busy → retry → succeed)
  - [ ] Test free tier users never receive calls

---

## Milestone 6 — Multi-Country Provider Registry

**Goal:** Admin can add/swap providers for any country without code changes. System gracefully handles provider outages.

**Estimated Duration:** 3–4 days

### Checklist

- [ ] Enhance Django Admin for TelcoProvider:
  - [ ] Add "Test SMS" action: sends a test message to a configured admin number
  - [ ] Add "Test Call" action: initiates a test call to admin number
  - [ ] Add "Provider Health" read-only field showing last 10 notification success rate
  - [ ] Add help text on each field explaining what to enter for each provider type
  - [ ] Add JSON field `extra_config` for provider-specific settings (e.g., Twilio application SID)
- [ ] Build adapter auto-discovery:
  - [ ] On TelcoProvider save, validate that adapter_class exists and is a subclass of BaseAdapter
  - [ ] Show available adapter classes as a dropdown in admin (scan adapters/ directory)
- [ ] Implement provider health monitoring:
  - [ ] Track success/failure rate per provider over rolling 1-hour window (Redis counter)
  - [ ] If failure rate > 50% over 10+ attempts, auto-mark provider as unhealthy
  - [ ] Unhealthy providers are skipped in dispatch (fallback kicks in)
  - [ ] Send admin alert email when a provider goes unhealthy
  - [ ] Auto-recover: re-check every 10 minutes, mark healthy if test succeeds
- [ ] Build admin provider management guide (in-app):
  - [ ] Step-by-step instructions for adding Twilio, Termii, Vonage
  - [ ] Show which fields are required for each adapter type
- [ ] Implement cost reporting:
  - [ ] Management command: `python manage.py cost_report --month 2026-04`
  - [ ] Breaks down cost by country, provider, channel
  - [ ] Outputs to console or exports CSV
- [ ] Seed providers for all 5 launch countries:
  - [ ] NG: Termii (SMS) as primary
  - [ ] GB: Vonage (SMS + Voice) as primary
  - [ ] US: Twilio (SMS + Voice) as primary
  - [ ] CA: Twilio (SMS + Voice) as primary
  - [ ] AE: TBD — research and document best local provider
- [ ] Document how to add a new country:
  - [ ] Add Country record
  - [ ] Create adapter class (if new provider type)
  - [ ] Add TelcoProvider record with credentials
  - [ ] Create ProviderCountry mapping with priority
  - [ ] Test with "Test SMS" action
- [ ] Write tests:
  - [ ] Test adapter auto-discovery lists all available adapters
  - [ ] Test provider health auto-disable and recovery
  - [ ] Test admin can create a provider and it's immediately usable
  - [ ] Test cost report accuracy against NotificationLog data

---

## Milestone 7 — Hardening, Monitoring & Deployment

**Goal:** Production-ready deployment on VPS with Docker, monitoring, and operational tooling.

**Estimated Duration:** 5–7 days

### Checklist

- [ ] Production Docker setup:
  - [ ] Multi-stage Dockerfile (builder + runtime, minimal image size)
  - [ ] docker-compose.prod.yml with:
    - [ ] `web` (Gunicorn, 4 workers)
    - [ ] `db` (PostgreSQL with volume mount)
    - [ ] `redis` (with persistence)
    - [ ] `celery_worker` (concurrency=4, autoscale 2-8)
    - [ ] `celery_beat` (single instance, using database scheduler for consistency)
    - [ ] `nginx` (reverse proxy, SSL termination, static files)
  - [ ] Health check endpoints for each service
- [ ] Nginx configuration:
  - [ ] SSL with Let's Encrypt (certbot auto-renewal)
  - [ ] Proxy pass to Gunicorn
  - [ ] Serve static and media files
  - [ ] Security headers (HSTS, CSP, X-Frame-Options)
  - [ ] Rate limiting on auth endpoints
- [ ] Django production settings:
  - [ ] DEBUG=False, ALLOWED_HOSTS, SECURE_SSL_REDIRECT
  - [ ] Database connection pooling (django-db-connection-pool or pgBouncer)
  - [ ] Static files collected and served by Nginx
  - [ ] Email backend set to SendGrid
  - [ ] Sentry integration for error tracking
- [ ] Logging:
  - [ ] Structured JSON logging (python-json-logger)
  - [ ] Log all notification dispatches with user_id, provider, status, latency
  - [ ] Log all provider API calls with response time and status code
  - [ ] Rotate logs (logrotate or Docker logging driver)
- [ ] Monitoring & alerts:
  - [ ] Add `/health/` endpoint (checks DB, Redis, Celery worker heartbeat)
  - [ ] Set up UptimeRobot or similar for external monitoring
  - [ ] Alert on: worker queue depth > 1000, notification failure rate > 5%, provider health degradation
  - [ ] Daily summary email to admin: notifications sent, costs, errors
- [ ] Database maintenance:
  - [ ] Auto-vacuum configuration for PostgreSQL
  - [ ] Partition or archive NotificationLog older than 90 days
  - [ ] Clean PrayerTimeCache entries older than 7 days (management command on cron)
  - [ ] Regular backups (pg_dump to S3 or local, daily)
- [ ] Security:
  - [ ] Rotate Django SECRET_KEY
  - [ ] Ensure all provider credentials are encrypted at rest
  - [ ] Add rate limiting to login and registration endpoints
  - [ ] Add CSRF protection on all forms
  - [ ] Audit admin access (log admin logins)
- [ ] Deployment automation:
  - [ ] Write deploy script: pull latest code → build images → run migrations → restart services
  - [ ] Zero-downtime deploy: bring up new containers, then take down old ones
  - [ ] Rollback script: revert to previous image tag
- [ ] Load testing:
  - [ ] Simulate 10,000 users across all 5 countries
  - [ ] Verify Celery can dispatch all notifications within the 60-second window
  - [ ] Identify bottlenecks and optimize (batch DB queries, connection pooling)
- [ ] Write operational runbook:
  - [ ] How to restart services
  - [ ] How to view logs
  - [ ] How to manually trigger a notification batch
  - [ ] How to failover a provider
  - [ ] How to restore from backup

---

## API Endpoints

Internal API (used by the dashboard frontend, could also support a future mobile app).

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register/` | Create account |
| POST | `/api/auth/login/` | Obtain auth token |
| POST | `/api/auth/logout/` | Invalidate token |
| POST | `/api/auth/password-reset/` | Request password reset email |
| POST | `/api/auth/password-reset-confirm/` | Confirm password reset |

### User Profile & Preferences

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/profile/` | Get current user profile |
| PATCH | `/api/profile/` | Update profile fields |
| GET | `/api/preferences/` | Get all notification preferences |
| PUT | `/api/preferences/` | Update notification preferences (batch) |
| PATCH | `/api/preferences/{prayer}/` | Update single prayer preference |

### Prayer Times

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/prayers/today/` | Today's prayer times for current user |
| GET | `/api/prayers/{date}/` | Prayer times for a specific date |
| GET | `/api/prayers/next/` | Next upcoming prayer with countdown |

### Notifications

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/notifications/` | Paginated notification history |
| GET | `/api/notifications/stats/` | Notification stats (sent, delivered, failed counts) |
| POST | `/api/notifications/pause/` | Pause all notifications |
| POST | `/api/notifications/resume/` | Resume all notifications |

### Admin / Internal

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health/` | Service health check |
| POST | `/api/webhooks/twilio/call-status/` | Twilio call status callback |
| POST | `/api/webhooks/vonage/call-event/` | Vonage call event webhook |

---

## Environment Variables

```bash
# Django
DJANGO_SECRET_KEY=your-secret-key
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=almuadhin.com,www.almuadhin.com
DJANGO_SETTINGS_MODULE=config.settings.prod

# Database
DATABASE_URL=postgres://user:pass@db:5432/al_muadhin

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# Email (SendGrid)
SENDGRID_API_KEY=SG.xxxx
DEFAULT_FROM_EMAIL=notifications@almuadhin.com

# Encryption key for provider credentials
FIELD_ENCRYPTION_KEY=your-fernet-key

# Adhan audio (S3 or public URL base)
ADHAN_AUDIO_BASE_URL=https://cdn.almuadhin.com/audio

# Sentry
SENTRY_DSN=https://xxxx@sentry.io/yyyy

# Admin notifications
ADMIN_EMAIL=admin@almuadhin.com
ADMIN_PHONE=+2348012345678
```

Note: Individual provider API keys (Twilio, Termii, Vonage) are NOT stored in environment variables. They are stored encrypted in the database via the TelcoProvider model and managed through Django Admin.

---

## Deployment Architecture

```
VPS (Ubuntu 24.04)
├── Docker Compose
│   ├── nginx         (port 80/443 → gunicorn:8000)
│   ├── web           (Django + Gunicorn, 4 workers)
│   ├── celery_worker (Celery, concurrency 4, autoscale 2-8)
│   ├── celery_beat   (single instance, database scheduler)
│   ├── db            (PostgreSQL 16, volume: /data/postgres)
│   └── redis         (Redis 7, volume: /data/redis)
├── Let's Encrypt SSL (certbot, auto-renewal cron)
├── Backups (pg_dump → /backups/, daily cron, optional S3 sync)
└── Logs (/var/log/al_muadhin/, rotated weekly)
```

---

## Future Considerations

These are explicitly out of scope for v1 but worth designing for:

- **Payment integration**: Stripe or Paystack (Nigeria) for premium subscriptions. The tier system is already in place.
- **Mobile app**: React Native app consuming the API endpoints. API is already designed for this.
- **Push notifications**: FCM/APNs as an additional channel (free, no per-message cost).
- **Qibla direction**: Add a compass feature to the dashboard.
- **Islamic calendar**: Show Hijri dates alongside Gregorian.
- **Ramadan mode**: Auto-enable Fajr + Maghrib call alerts during Ramadan, special Iftar/Suhoor notifications.
- **Community features**: Masjid-specific prayer time adjustments (some masajids follow slightly different times).
- **WhatsApp channel**: WhatsApp Business API as an SMS alternative (popular in NG, AE).
- **Additional countries**: Saudi Arabia, Pakistan, Egypt, Malaysia, Indonesia, Turkey.
- **Multi-language**: Arabic, Hausa, Urdu, Malay, Turkish UI translations.
- **Offline-capable PWA**: Service worker for prayer time display without internet.
