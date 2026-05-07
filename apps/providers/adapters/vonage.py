from .base import BaseAdapter, SendResult


class VonageAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        self.from_number = provider.sender_id

    def send_sms(self, to, message):
        try:
            from vonage import Client
            client = Client(key=self.api_key, secret=self.api_secret)
            response = client.sms.send_message(
                {
                    "to": to,
                    "from": self.from_number,
                    "text": message,
                }
            )
            if response["messages"][0]["status"] == "0":
                return SendResult(success=True, external_id=response["messages"][0]["message-id"])
            return SendResult(success=False, error_message=response["messages"][0]["error-text"])
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        try:
            from vonage import Client
            client = Client(key=self.api_key, secret=self.api_secret)
            response = client.voice.create_call(
                {
                    "to": [{"type": "phone", "number": to}],
                    "from": {"type": "phone", "number": self.from_number},
                    "ncco": [{"action": "stream", "streamUrl": [audio_url]}],
                }
            )
            if "uuid" in response:
                return SendResult(success=True, external_id=response["uuid"])
            return SendResult(success=False, error_message="Failed to create call")
        except Exception as e:
            return SendResult(success=False, error_message=str(e))
