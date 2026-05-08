from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_home, name='home'),
    path('preferences/', views.dashboard_preferences, name='preferences'),
    path('history/', views.dashboard_notification_history, name='history'),
    path('subscription/', views.dashboard_subscription, name='subscription'),
    path('pause-notifications/', views.pause_notifications, name='pause_notifications'),
    path('resume-notifications/', views.resume_notifications, name='resume_notifications'),
]
