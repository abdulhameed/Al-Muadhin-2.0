from dataclasses import dataclass
from abc import ABC, abstractmethod
import re


@dataclass
class SendResult:
    success: bool
    external_id: str = ""
    error_message: str = ""
    cost: float = 0.0


class BaseAdapter(ABC):
    def __init__(self, provider):
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

    def send_email(self, to: str, subject: str, html: str, text: str = None) -> SendResult:
        """Send an email. Override in adapter if supported."""
        return SendResult(success=False, error_message="This provider does not support email")

    def validate_phone(self, phone: str) -> bool:
        """Basic E.164 validation."""
        return bool(re.match(r'^\+[1-9]\d{1,14}$', phone))
