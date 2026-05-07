from .base import BaseAdapter, SendResult


class SendGridAdapter(BaseAdapter):
    def __init__(self, provider):
        super().__init__(provider)

    def send_sms(self, to, message):
        return SendResult(success=False, error_message="SendGrid does not support SMS")

    def make_call(self, to, audio_url):
        return SendResult(success=False, error_message="SendGrid does not support voice calls")

    def send_email(self, to, subject, html, text):
        try:
            from sendgrid import SendGridAPIClient
            from sendgrid.helpers.mail import Mail, Email, To, Content
            
            message = Mail(
                from_email=Email(self.api_key),
                to_emails=To(to),
                subject=subject,
                plain_text_content=Content("text/plain", text),
                html_content=Content("text/html", html),
            )
            sg = SendGridAPIClient(self.api_key)
            response = sg.send(message)
            return SendResult(success=True, external_id=response.headers.get('X-Message-Id', ''))
        except Exception as e:
            return SendResult(success=False, error_message=str(e))
