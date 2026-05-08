from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import NotificationsViewSet

app_name = 'notifications'

router = DefaultRouter()
router.register(r'', NotificationsViewSet, basename='notifications')

urlpatterns = router.urls
