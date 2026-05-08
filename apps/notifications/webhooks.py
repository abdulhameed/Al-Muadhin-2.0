import logging
import hmac
import hashlib
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from .models import NotificationLog
from django.utils import timezone

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def twilio_call_status(request):
    """Handle Twilio call status callbacks."""
    try:
        # Validate the request came from Twilio
        if not validate_twilio_request(request):
            logger.warning("Invalid Twilio signature")
            return JsonResponse({'error': 'Invalid signature'}, status=403)

        # Get call metadata from POST data
        call_sid = request.POST.get('CallSid')
        call_status = request.POST.get('CallStatus')

        if not call_sid:
            return JsonResponse({'error': 'Missing CallSid'}, status=400)

        # Find the notification log entry
        try:
            notification = NotificationLog.objects.get(external_id=call_sid)
        except NotificationLog.DoesNotExist:
            logger.warning(f"Twilio callback for unknown call: {call_sid}")
            return JsonResponse({'status': 'ok'})

        # Map Twilio status to our status
        status_map = {
            'queued': 'pending',
            'ringing': 'pending',
            'in-progress': 'sent',
            'completed': 'delivered',
            'busy': 'failed',
            'failed': 'failed',
            'no-answer': 'failed',
            'canceled': 'failed',
        }

        new_status = status_map.get(call_status, 'pending')
        notification.status = new_status

        # Record call duration if available
        duration = request.POST.get('CallDuration')
        if duration:
            try:
                duration_secs = int(duration)
                provider = notification.provider
                if provider and duration_secs > 0:
                    cost_per_min = float(provider.cost_per_minute)
                    duration_mins = duration_secs / 60.0
                    notification.cost_estimate = cost_per_min * duration_mins
            except (ValueError, TypeError):
                pass

        if new_status == 'delivered':
            notification.delivered_at = timezone.now()

        notification.save()

        logger.info(f"Call {call_sid} status updated to {call_status}")
        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error processing Twilio callback: {e}")
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def vonage_call_event(request):
    """Handle Vonage call status callbacks."""
    try:
        import json

        # Parse JSON body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Validate the request came from Vonage
        if not validate_vonage_signature(request):
            logger.warning("Invalid Vonage signature")
            return JsonResponse({'error': 'Invalid signature'}, status=403)

        uuid = data.get('uuid')
        status = data.get('status')

        if not uuid or not status:
            return JsonResponse({'error': 'Missing uuid or status'}, status=400)

        # Find the notification log entry
        try:
            notification = NotificationLog.objects.get(external_id=uuid)
        except NotificationLog.DoesNotExist:
            logger.warning(f"Vonage callback for unknown call: {uuid}")
            return JsonResponse({'status': 'ok'})

        # Map Vonage status to our status
        status_map = {
            'started': 'pending',
            'ringing': 'pending',
            'answered': 'sent',
            'machine': 'sent',
            'human': 'sent',
            'completed': 'delivered',
        }

        new_status = status_map.get(status, 'pending')
        notification.status = new_status

        # Get duration from duration field if available
        duration = data.get('duration')
        if duration:
            try:
                duration_secs = int(duration)
                provider = notification.provider
                if provider and duration_secs > 0:
                    cost_per_min = float(provider.cost_per_minute)
                    duration_mins = duration_secs / 60.0
                    notification.cost_estimate = cost_per_min * duration_mins
            except (ValueError, TypeError):
                pass

        if new_status == 'delivered':
            notification.delivered_at = timezone.now()

        notification.save()

        logger.info(f"Call {uuid} status updated to {status}")
        return JsonResponse({'status': 'ok'})

    except Exception as e:
        logger.error(f"Error processing Vonage callback: {e}")
        return JsonResponse({'error': str(e)}, status=500)


def validate_twilio_request(request):
    """Validate that a request came from Twilio."""
    auth_token = settings.TWILIO_AUTH_TOKEN
    url = request.build_absolute_uri()

    # Get signature from X-Twilio-Signature header
    twilio_signature = request.META.get('HTTP_X_TWILIO_SIGNATURE', '')

    # Get the request data
    params = request.POST.dict()

    # Build the data to sign (URL + all params)
    data = url
    for key in sorted(params.keys()):
        data += key + params[key]

    # Compute the signature
    computed_signature = hmac.new(
        auth_token.encode(),
        data.encode(),
        hashlib.sha1
    ).digest()

    computed_signature = __import__('base64').b64encode(computed_signature).decode()

    return hmac.compare_digest(computed_signature, twilio_signature)


def validate_vonage_signature(request):
    """Validate that a request came from Vonage."""
    api_secret = settings.VONAGE_API_SECRET

    # Get signature from header
    vonage_signature = request.META.get('HTTP_X_VONAGE_SIGNATURE', '')

    # Get request body
    body = request.body

    # Compute signature
    computed_signature = hmac.new(
        api_secret.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(computed_signature, vonage_signature)
