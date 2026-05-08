import json
from .base import BaseAdapter, SendResult


class VonageAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)
        self.from_number = provider.sender_id
        self.base_url = provider.base_url or "https://api.nexmo.com"

    def send_sms(self, to, message):
        """Send SMS via Vonage (Nexmo)."""
        try:
            import requests
            
            payload = {
                "from": self.from_number,
                "to": to,
                "text": message,
                "api_key": self.api_key,
                "api_secret": self.api_secret,
            }
            
            response = requests.post(
                f"{self.base_url}/sms/json",
                data=payload,
                timeout=10
            )
            data = response.json()
            
            if data.get("messages", [{}])[0].get("status") == "0":
                message_id = data["messages"][0].get("message-id")
                return SendResult(success=True, external_id=message_id)
            else:
                error = data["messages"][0].get("error-text", "Unknown error")
                return SendResult(success=False, error_message=error)
        except Exception as e:
            return SendResult(success=False, error_message=str(e))

    def make_call(self, to, audio_url):
        """Make a phone call via Vonage Voice API."""
        try:
            import requests
            import jwt
            from datetime import datetime, timedelta
            
            # Generate JWT token for auth
            payload = {
                "iss": self.api_key,
                "iat": int(datetime.utcnow().timestamp()),
                "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
            }
            token = jwt.encode(payload, self.api_secret, algorithm="HS256")
            
            # Build NCCO (Nexmo Call Control Objects)
            ncco = [
                {
                    "action": "talk",
                    "text": "Please wait while we connect you to the adhan."
                },
                {
                    "action": "stream",
                    "streamUrl": [audio_url]
                }
            ]
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "to": [{"type": "phone", "number": to}],
                "from": {"type": "phone", "number": self.from_number},
                "ncco": ncco,
            }
            
            response = requests.post(
                f"{self.base_url}/v1/calls",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 201:
                data = response.json()
                call_uuid = data.get("uuid")
                return SendResult(
                    success=True,
                    external_id=call_uuid,
                    cost=0.0
                )
            else:
                return SendResult(
                    success=False,
                    error_message=f"HTTP {response.status_code}: {response.text}"
                )
        except Exception as e:
            return SendResult(success=False, error_message=str(e))
