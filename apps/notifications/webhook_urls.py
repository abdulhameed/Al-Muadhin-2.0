from django.urls import path
from .webhooks import twilio_call_status, vonage_call_event

app_name = 'webhooks'

urlpatterns = [
    path('twilio/call-status/', twilio_call_status, name='twilio_call_status'),
    path('vonage/call-event/', vonage_call_event, name='vonage_call_event'),
]
