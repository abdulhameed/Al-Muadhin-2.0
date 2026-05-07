from .base import BaseAdapter, SendResult


class TermiiAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        self.base_url = provider.base_url or "https://api.ng.termii.com/api"
        self.sender_id = provider.sender_id

    def send_sms(self, to, message):
        try:
            import requests
            payload = {
                "to": to,
                "from": self.sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }
            r = requests.post(f"{self.base_url}/sms/send", json=payload, timeout=10)
            data = r.json()
            if r.ok and data.get("message_id"):
                return SendResult(success=True, external_id=data["message_id"])
            return SendResult(success=False, error_message=data.get("message", "Unknown error"))
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        return SendResult(success=False, error_message="Voice not supported by Termii")
