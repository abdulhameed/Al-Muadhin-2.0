from .base import BaseAdapter, SendResult


class TwilioAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        self.account_sid = provider.account_sid
        self.auth_token = provider.auth_token
        self.from_number = provider.sender_id

    def send_sms(self, to, message):
        """Send SMS via Twilio."""
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=to
            )
            return SendResult(success=True, external_id=msg.sid)
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        """Make a phone call with audio playback."""
        try:
            from twilio.rest import Client
            from twilio.twiml.voice_response import VoiceResponse
            
            client = Client(self.account_sid, self.auth_token)
            
            # Build TwiML response
            response = VoiceResponse()
            response.play(audio_url, loop=1)
            response.hangup()
            
            # Create call with TwiML
            call = client.calls.create(
                to=to,
                from_=self.from_number,
                twiml=str(response),
                timeout=30,  # Ring timeout in seconds
            )
            return SendResult(
                success=True,
                external_id=call.sid,
                cost=0.0  # Cost will be calculated based on call duration
            )
        except Exception as e:
            return SendResult(success=False, error_message=str(e))
