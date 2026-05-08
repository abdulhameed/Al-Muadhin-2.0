from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PrayerTimesViewSet

app_name = 'prayers'

router = DefaultRouter()
router.register(r'', PrayerTimesViewSet, basename='prayers')

urlpatterns = router.urls
