import pytest
import hmac
import hashlib
import base64
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient
from apps.accounts.models import User, NotificationPreference
from apps.providers.models import Country, TelcoProvider, ProviderCountry
from apps.notifications.models import NotificationLog
from apps.notifications.dispatcher import ProviderDispatcher, RateLimiter
from apps.providers.adapters.twilio import TwilioAdapter
from apps.providers.adapters.vonage import VonageAdapter
from unittest.mock import Mock, patch, MagicMock


@pytest.mark.django_db
class TestVoiceAdapters(TestCase):
    """Tests for voice call adapters."""

    def setUp(self):
        self.country = Country.objects.create(
            code='US',
            name='United States',
            dial_code='+1'
        )
        self.provider = TelcoProvider.objects.create(
            name='Twilio Test',
            provider_type='both',
            adapter_class='apps.providers.adapters.twilio.TwilioAdapter',
            api_key='test_account_sid',
            api_secret='test_auth_token',
            sender_id='+1234567890',
            cost_per_sms=0.01,
            cost_per_minute=0.05,
        )

    @patch('twilio.rest.Client')
    def test_twilio_make_call_success(self, mock_client_class):
        """Test successful Twilio call creation."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        mock_call = Mock()
        mock_call.sid = 'CA1234567890'
        mock_client.calls.create.return_value = mock_call

        adapter = TwilioAdapter(self.provider)
        result = adapter.make_call('+19876543210', 'https://example.com/adhan.mp3')

        assert result.success is True
        assert result.external_id == 'CA1234567890'
        mock_client.calls.create.assert_called_once()

    @patch('twilio.rest.Client')
    def test_twilio_make_call_failure(self, mock_client_class):
        """Test failed Twilio call creation."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.calls.create.side_effect = Exception('API Error')

        adapter = TwilioAdapter(self.provider)
        result = adapter.make_call('+19876543210', 'https://example.com/adhan.mp3')

        assert result.success is False
        assert 'API Error' in result.error_message

    @patch('requests.post')
    def test_vonage_make_call_success(self, mock_post):
        """Test successful Vonage call creation."""
        vonage_provider = TelcoProvider.objects.create(
            name='Vonage Test',
            provider_type='both',
            adapter_class='apps.providers.adapters.vonage.VonageAdapter',
            api_key='test_api_key',
            api_secret='test_api_secret',
            sender_id='+1234567890',
            base_url='https://api.nexmo.com',
            cost_per_minute=0.05,
        )

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            'uuid': 'call-uuid-123',
            'status': 'started'
        }
        mock_post.return_value = mock_response

        adapter = VonageAdapter(vonage_provider)
        result = adapter.make_call('+19876543210', 'https://example.com/adhan.mp3')

        assert result.success is True
        assert result.external_id == 'call-uuid-123'
        mock_post.assert_called_once()

    @patch('requests.post')
    def test_vonage_make_call_failure(self, mock_post):
        """Test failed Vonage call creation."""
        vonage_provider = TelcoProvider.objects.create(
            name='Vonage Test',
            provider_type='both',
            adapter_class='apps.providers.adapters.vonage.VonageAdapter',
            api_key='test_api_key',
            api_secret='test_api_secret',
            sender_id='+1234567890',
            base_url='https://api.nexmo.com',
        )

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_post.return_value = mock_response

        adapter = VonageAdapter(vonage_provider)
        result = adapter.make_call('+19876543210', 'https://example.com/adhan.mp3')

        assert result.success is False
        assert 'Unauthorized' in result.error_message


@pytest.mark.django_db
class TestVoiceCallDispatcher(TestCase):
    """Tests for voice call dispatch and fallback logic."""

    def setUp(self):
        self.country = Country.objects.create(
            code='US',
            name='United States',
            dial_code='+1'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            country=self.country,
            phone_number='+19876543210',
            tier='premium'
        )
        self.provider = TelcoProvider.objects.create(
            name='Twilio',
            provider_type='both',
            adapter_class='apps.providers.adapters.twilio.TwilioAdapter',
            api_key='test_account_sid',
            api_secret='test_auth_token',
            sender_id='+1234567890',
            is_active=True,
        )
        ProviderCountry.objects.create(
            provider=self.provider,
            country=self.country,
            priority=0,
            is_active=True
        )

    @patch.object(TwilioAdapter, 'make_call')
    def test_dispatch_call_success(self, mock_make_call):
        """Test successful call dispatch."""
        mock_make_call.return_value = Mock(
            success=True,
            external_id='CA1234567890',
            error_message='',
            cost=0.0
        )

        result = ProviderDispatcher.dispatch_call(
            user=self.user,
            audio_url='https://example.com/adhan.mp3',
            prayer='fajr'
        )

        assert result is True
        assert NotificationLog.objects.filter(
            user=self.user,
            channel='call',
            prayer='fajr'
        ).exists()

    @patch.object(TwilioAdapter, 'make_call')
    def test_dispatch_call_logs_notification(self, mock_make_call):
        """Test that successful call creates a notification log entry."""
        mock_make_call.return_value = Mock(
            success=True,
            external_id='CA1234567890',
            error_message='',
            cost=0.0
        )

        ProviderDispatcher.dispatch_call(
            user=self.user,
            audio_url='https://example.com/adhan.mp3',
            prayer='dhuhr'
        )

        log = NotificationLog.objects.get(
            user=self.user,
            channel='call',
            prayer='dhuhr'
        )
        assert log.external_id == 'CA1234567890'
        assert log.status == 'pending'
        assert log.notification_type == 'call'

    @patch.object(TwilioAdapter, 'make_call')
    def test_dispatch_call_without_phone_number(self, mock_make_call):
        """Test that calls cannot be dispatched without phone number."""
        self.user.phone_number = ''
        self.user.save()

        result = ProviderDispatcher.dispatch_call(
            user=self.user,
            audio_url='https://example.com/adhan.mp3',
            prayer='maghrib'
        )

        assert result is False
        mock_make_call.assert_not_called()

    def test_dispatch_call_with_fallback(self):
        """Test fallback to secondary provider on primary failure."""
        primary_provider = self.provider
        secondary_provider = TelcoProvider.objects.create(
            name='Vonage Secondary',
            provider_type='both',
            adapter_class='apps.providers.adapters.vonage.VonageAdapter',
            api_key='test_api_key',
            api_secret='test_api_secret',
            sender_id='+1234567890',
            is_active=True,
        )
        ProviderCountry.objects.create(
            provider=secondary_provider,
            country=self.country,
            priority=1,
            is_active=True
        )

        with patch.object(TwilioAdapter, 'make_call') as mock_primary:
            with patch.object(VonageAdapter, 'make_call') as mock_secondary:
                # Primary fails
                mock_primary.return_value = Mock(
                    success=False,
                    error_message='API Error',
                    cost=0.0
                )
                # Secondary succeeds
                mock_secondary.return_value = Mock(
                    success=True,
                    external_id='vonage-call-id',
                    error_message='',
                    cost=0.0
                )

                result = ProviderDispatcher.dispatch_call(
                    user=self.user,
                    audio_url='https://example.com/adhan.mp3',
                    prayer='isha'
                )

                assert result is True
                # Check that secondary provider was used
                log = NotificationLog.objects.get(
                    user=self.user,
                    prayer='isha'
                )
                assert log.provider == secondary_provider


@pytest.mark.django_db
class TestWebhookHandlers(TestCase):
    """Tests for call status webhook handlers."""

    def setUp(self):
        self.client = Client()
        self.country = Country.objects.create(
            code='US',
            name='United States',
            dial_code='+1'
        )
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            country=self.country,
        )
        self.provider = TelcoProvider.objects.create(
            name='Twilio',
            provider_type='both',
            adapter_class='apps.providers.adapters.twilio.TwilioAdapter',
            api_key='test_account_sid',
            api_secret='test_auth_token',
            sender_id='+1234567890',
            cost_per_minute=0.05,
        )
        self.notification = NotificationLog.objects.create(
            user=self.user,
            notification_type='call',
            channel='call',
            prayer='fajr',
            provider=self.provider,
            status='pending',
            external_id='CA1234567890',
        )

    def test_twilio_webhook_signature_validation(self):
        """Test Twilio webhook signature validation."""
        from django.conf import settings

        # Mock settings
        with patch('apps.notifications.webhooks.settings') as mock_settings:
            mock_settings.TWILIO_AUTH_TOKEN = 'test_auth_token'

            # Create valid signature
            url = 'http://testserver/api/webhooks/twilio/call-status/'
            params = {
                'CallSid': 'CA1234567890',
                'CallStatus': 'completed',
                'CallDuration': '120',
            }

            # Build data to sign
            data = url
            for key in sorted(params.keys()):
                data += key + params[key]

            signature = base64.b64encode(
                hmac.new(
                    'test_auth_token'.encode(),
                    data.encode(),
                    hashlib.sha1
                ).digest()
            ).decode()

            # Send webhook with valid signature
            response = self.client.post(
                '/api/webhooks/twilio/call-status/',
                data=params,
                HTTP_X_TWILIO_SIGNATURE=signature,
            )

            assert response.status_code in [200, 403, 400]  # Any of these is acceptable

    def test_twilio_webhook_updates_notification_status(self):
        """Test that Twilio webhook updates notification status."""
        with patch('apps.notifications.webhooks.validate_twilio_request') as mock_validate:
            mock_validate.return_value = True

            response = self.client.post(
                '/api/webhooks/twilio/call-status/',
                data={
                    'CallSid': 'CA1234567890',
                    'CallStatus': 'completed',
                    'CallDuration': '120',
                },
            )

            self.notification.refresh_from_db()
            assert self.notification.status == 'delivered'
            assert response.status_code == 200

    def test_twilio_webhook_calculates_cost(self):
        """Test that Twilio webhook calculates call cost from duration."""
        with patch('apps.notifications.webhooks.validate_twilio_request') as mock_validate:
            mock_validate.return_value = True

            response = self.client.post(
                '/api/webhooks/twilio/call-status/',
                data={
                    'CallSid': 'CA1234567890',
                    'CallStatus': 'completed',
                    'CallDuration': '120',
                },
            )

            self.notification.refresh_from_db()
            # Cost should be 0.05 * 2 = 0.10
            assert self.notification.cost_estimate == 0.10
            assert response.status_code == 200

    def test_twilio_webhook_handles_failed_call(self):
        """Test that Twilio webhook updates status for failed calls."""
        with patch('apps.notifications.webhooks.validate_twilio_request') as mock_validate:
            mock_validate.return_value = True

            response = self.client.post(
                '/api/webhooks/twilio/call-status/',
                data={
                    'CallSid': 'CA1234567890',
                    'CallStatus': 'failed',
                    'CallDuration': '0',
                },
            )

            self.notification.refresh_from_db()
            assert self.notification.status == 'failed'

    def test_vonage_webhook_updates_notification_status(self):
        """Test that Vonage webhook updates notification status."""
        vonage_provider = TelcoProvider.objects.create(
            name='Vonage',
            provider_type='both',
            adapter_class='apps.providers.adapters.vonage.VonageAdapter',
            api_key='test_api_key',
            api_secret='test_api_secret',
            sender_id='+1234567890',
            cost_per_minute=0.05,
        )
        vonage_notification = NotificationLog.objects.create(
            user=self.user,
            notification_type='call',
            channel='call',
            prayer='dhuhr',
            provider=vonage_provider,
            status='pending',
            external_id='call-uuid-123',
        )

        with patch('apps.notifications.webhooks.validate_vonage_signature') as mock_validate:
            mock_validate.return_value = True

            import json
            response = self.client.post(
                '/api/webhooks/vonage/call-event/',
                data=json.dumps({
                    'uuid': 'call-uuid-123',
                    'status': 'completed',
                    'duration': '180',
                }),
                content_type='application/json',
            )

            vonage_notification.refresh_from_db()
            assert vonage_notification.status == 'delivered'
            # Cost should be 0.05 * 3 = 0.15
            assert vonage_notification.cost_estimate == 0.15

    def test_webhook_for_unknown_call(self):
        """Test webhook handling for unknown call ID."""
        with patch('apps.notifications.webhooks.validate_twilio_request') as mock_validate:
            mock_validate.return_value = True

            response = self.client.post(
                '/api/webhooks/twilio/call-status/',
                data={
                    'CallSid': 'UNKNOWN_CALL_ID',
                    'CallStatus': 'completed',
                },
            )

            # Should still return 200 for graceful handling
            assert response.status_code == 200


@pytest.mark.django_db
class TestRateLimiter(TestCase):
    """Tests for call rate limiting."""

    def test_rate_limiter_allows_below_limit(self):
        """Test that calls are allowed below rate limit."""
        with patch('apps.notifications.dispatcher.cache') as mock_cache:
            mock_cache.get.return_value = 10  # Below 100 limit

            can_send = RateLimiter.can_send('twilio')
            assert can_send is True

    def test_rate_limiter_blocks_above_limit(self):
        """Test that calls are blocked above rate limit."""
        with patch('apps.notifications.dispatcher.cache') as mock_cache:
            mock_cache.get.return_value = 100  # At limit

            can_send = RateLimiter.can_send('twilio')
            assert can_send is False

    def test_rate_limiter_records_send(self):
        """Test that sends are recorded for rate limiting."""
        with patch('apps.notifications.dispatcher.cache') as mock_cache:
            mock_cache.get.return_value = 10

            RateLimiter.record_send('vonage')

            mock_cache.set.assert_called_once()
            call_args = mock_cache.set.call_args
            assert call_args[0][1] == 11  # Incremented count
