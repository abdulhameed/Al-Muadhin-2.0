from .base import BaseAdapter, SendResult


class TwilioAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        self.account_sid = provider.account_sid
        self.auth_token = provider.auth_token
        self.from_number = provider.sender_id

    def send_sms(self, to, message):
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(body=message, from_=self.from_number, to=to)
            return SendResult(success=True, external_id=msg.sid)
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            twiml = f'<Response><Play>{audio_url}</Play></Response>'
            call = client.calls.create(to=to, from_=self.from_number, twiml=twiml)
            return SendResult(success=True, external_id=call.sid)
        except Exception as e:
            return SendResult(success=False, error_message=str(e))
