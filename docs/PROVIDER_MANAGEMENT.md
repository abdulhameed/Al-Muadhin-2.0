# Provider Management Guide

This guide explains how to manage telecommunications providers in Al-Muadhin and optimize notification delivery across countries.

## Overview

Al-Muadhin supports multiple SMS and voice call providers per country with automatic fallback. This allows you to:

- Use the best provider for each region
- Automatically switch to backup providers if primary fails
- Monitor provider performance and health
- Track costs by provider and country
- Test providers before production use

## Provider Setup

### Initial Setup

To seed initial providers for the five launch countries:

```bash
python manage.py seed_providers
```

This creates:
- **Twilio** (SMS + Voice) for US, CA
- **Vonage** (SMS + Voice) for GB, US (fallback)
- **Termii** (SMS) for NG
- **SendGrid** (Email) for all countries

### Adding Environment Variables

Set these environment variables for each provider:

```bash
# Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token

# Vonage (formerly Nexmo)
VONAGE_API_KEY=your_api_key
VONAGE_API_SECRET=your_api_secret

# Termii
TERMII_API_KEY=your_api_key

# SendGrid
SENDGRID_API_KEY=your_api_key
```

## Managing Providers via Admin Panel

### Access the Admin Panel

1. Go to `http://localhost:8000/admin/`
2. Log in with your admin credentials
3. Click "Telco Providers" in the left sidebar

### Provider List View

The provider list shows key metrics for each provider:

| Column | Description |
|--------|-------------|
| Name | Provider name (Twilio, Vonage, etc.) |
| Type | SMS, Voice, or Both |
| Health Status | 🟢 Healthy, 🟡 Degraded, 🔴 Unhealthy |
| Total Sent | Total notifications dispatched |
| Success Rate | % of delivered/sent notifications |
| Countries | Number of countries supported |

### Health Status Indicators

- **🟢 Healthy** (≥95%): Provider is performing well
- **🟡 Degraded** (80-95%): Provider has issues, fallback in use
- **🔴 Unhealthy** (<80%): Provider is disabled, fallback required

### Adding a New Provider

1. Click "Add Telco Provider" button
2. Fill in the provider details:
   - **Name**: e.g., "Twilio-US"
   - **Type**: SMS, Voice, or Both
   - **Adapter Class**: Full Python path to adapter (e.g., `apps.providers.adapters.twilio.TwilioAdapter`)
3. Enter API credentials (stored encrypted)
4. Set pricing (cost per SMS, cost per minute)
5. In the "Provider Countries" section:
   - Click "Add another Provider Country"
   - Select the country
   - Set priority (0 = primary, 1+ = fallback)
6. Click "Save"

### Adapter Classes

Choose the correct adapter based on provider:

- `apps.providers.adapters.twilio.TwilioAdapter` — Twilio
- `apps.providers.adapters.vonage.VonageAdapter` — Vonage
- `apps.providers.adapters.termii.TermiiAdapter` — Termii
- `apps.providers.adapters.sendgrid.SendGridAdapter` — SendGrid

### Testing a Provider

#### Test SMS

1. Select a provider in the list
2. Click the checkbox next to it
3. From "Action" dropdown, select "Test SMS delivery"
4. Click "Go"

The admin will receive a test SMS. Check the logs for detailed results.

#### Test Phone Call

1. Select a provider
2. From "Action" dropdown, select "Test call delivery"
3. Click "Go"

A test call will be initiated. Check logs for status.

## Provider Health Monitoring

### Automatic Health Checking

The system automatically monitors provider health every 10 minutes:

```
Task: monitor-provider-health
Schedule: Every 10 minutes
```

Health calculation is based on recent notifications:
- Recent notifications: Last 100 or last 1 hour
- Minimum threshold: 10 notifications required
- Success: Status is 'sent' or 'delivered'
- Failure: Status is 'failed' or 'retrying'

### Health Status Rules

| Condition | Action |
|-----------|--------|
| Success rate drops below 50% | Provider marked unhealthy, disabled |
| Unhealthy for 30+ minutes | Can attempt recovery if success rate ≥80% |
| Success rate recovers to 80%+ | Provider marked healthy, re-enabled |

### Manual Health Management

In the provider detail view:

- **Mark as healthy**: Sets health to 95% for 24 hours, re-enables provider
- **Mark as unhealthy**: Sets health to 20% for 24 hours, disables provider

Use these to override automatic decisions for maintenance or testing.

## Configuring Provider Priority

Providers are selected in priority order for each country:

```
Nigeria (NG):
  1. Termii (priority 0) — Primary
  2. Twilio (priority 1) — Fallback

UK (GB):
  1. Vonage (priority 0) — Primary
  2. SendGrid (priority 1) — Email fallback

US:
  1. Twilio (priority 0) — Primary
  2. Vonage (priority 1) — SMS fallback
  3. SendGrid (priority 2) — Email fallback
```

### Changing Priority

1. Go to Admin → Provider Countries
2. Find the entry you want to change
3. Click to edit
4. Modify the "Priority" field
5. Save

Lower priority = tried first.

## Cost Tracking

### View Cost Summary

API endpoint (admin only):

```
GET /api/notifications/cost_summary/?days=30
```

Response includes:
- Total cost for the period
- Breakdown by provider
- Breakdown by country
- Breakdown by channel (SMS, voice, email)
- Breakdown by notification type

### View Provider-Specific Costs

API endpoint (admin only):

```
GET /api/notifications/cost_by_provider/
```

Returns cost data for all active providers.

### Cost Details in Admin

In the provider detail view, the "Health & Activity" section shows:
- Recent activity (last 5 notifications)
- Success rate
- Cost breakdown

## Troubleshooting

### Provider Not Working

**Symptom**: All notifications failing for a provider

**Steps**:
1. Check if provider is marked as active: Admin → Telco Providers → check `is_active`
2. Verify API credentials are correct
3. Test the provider: Select it, run "Test SMS" or "Test call" action
4. Check application logs for error messages
5. Verify adapter class path is correct

### Provider Auto-Disabled

**Symptom**: Provider automatically marked unhealthy

**Steps**:
1. Check the "Health Status" indicator (🔴 red = disabled)
2. Click the provider to see detailed health metrics
3. Review recent notifications to identify the issue:
   - Authentication error? Check credentials
   - Rate limiting? Check provider logs/dashboard
   - Network issue? Check provider status page
4. Once fixed, click "Mark as healthy" to re-enable

### High Costs

**Symptom**: Unexpected high costs

**Steps**:
1. Use cost reporting: `/api/notifications/cost_summary/?days=7`
2. Identify which provider or country is expensive
3. Check if fallback is being used excessively (primary provider failing)
4. Consider switching primary provider if a cheaper alternative exists
5. Review notification preferences to ensure premium features aren't over-enabled

## Advanced Topics

### Adding a New Provider Type

To add a new SMS/voice provider:

1. Create adapter in `apps/providers/adapters/`:

```python
# apps/providers/adapters/myprovider.py
from .base import BaseAdapter, SendResult

class MyProviderAdapter(BaseAdapter):
    def send_sms(self, to, message):
        # Implementation
        pass
    
    def make_call(self, to, audio_url):
        # Implementation
        pass
```

2. In Admin, click "Add Provider" and set:
   - Adapter class: `apps.providers.adapters.myProvider.MyProviderAdapter`
   - Provider type: SMS/Voice/Both
   - API credentials

3. Test before assigning to countries

### Adding a New Country

1. Admin → Countries → "Add Country"
2. Fill in:
   - Code: 2-letter ISO code (e.g., "FR")
   - Name: Full country name
   - Dial code: International dialing code (e.g., "+33")
   - Is supported: Check if this country is active
3. Save

4. Add provider mappings:
   - Admin → Provider Countries → "Add"
   - Select the new country
   - Select primary and fallback providers

### Bulk Actions

In the provider list, you can select multiple providers and:
- Mark as healthy
- Mark as unhealthy

Use for maintenance or emergency actions.

## Monitoring & Alerts

### Built-In Metrics

The admin dashboard shows:
- Provider health status
- Success rates
- Cost summaries
- Recent activity

### Integration with External Monitoring

For external monitoring (e.g., Datadog, New Relic), use:

```bash
GET /api/notifications/cost_summary/
GET /api/notifications/cost_by_provider/
```

Parse the JSON response to feed into your monitoring system.

### Custom Alerts

To receive alerts when a provider fails:

1. Set up a monitoring endpoint that calls the health check API
2. Create a scheduled task that queries provider health
3. Send alerts if any provider is unhealthy

Example alert trigger:

```python
from apps.providers.services import ProviderHealthMonitor

for provider in TelcoProvider.objects.all():
    health = ProviderHealthMonitor.get_provider_health(provider)
    if health < 50:
        send_alert(f"{provider.name} is unhealthy: {health}%")
```

## Frequently Asked Questions

**Q: How often is provider health checked?**
A: Every 10 minutes. The monitoring task runs automatically via Celery Beat.

**Q: What happens if the primary provider fails?**
A: The system automatically tries the next provider (by priority) until one succeeds.

**Q: Can I test a provider in production?**
A: Yes, the "Test SMS" and "Test call" actions send real messages. Use a test phone number or ensure you control the recipient.

**Q: How are costs calculated?**
A: SMS cost = `cost_per_sms` × count. Voice cost = `cost_per_minute` × duration_in_minutes.

**Q: Can I disable a provider permanently?**
A: Yes, uncheck the `is_active` checkbox. The provider won't be selected even if others fail.

**Q: What's the difference between provider type SMS and Voice?**
A: SMS providers send text messages. Voice providers make phone calls. Some support both.

## Support

For issues with specific providers, consult their documentation:

- **Twilio**: https://www.twilio.com/docs
- **Vonage**: https://developer.vonage.com/api
- **Termii**: https://termii.com/docs
- **SendGrid**: https://docs.sendgrid.com
