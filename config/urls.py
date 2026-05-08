from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from .views import health_check

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-auth/', include('rest_framework.urls')),
    path('health/', health_check, name='health_check'),
    path('api/', include([
        path('auth/', include('apps.accounts.urls', namespace='auth')),
        path('profile/', include('apps.accounts.urls')),
        path('prayers/', include('apps.prayers.urls', namespace='prayers')),
        path('notifications/', include('apps.notifications.urls', namespace='notifications')),
        path('webhooks/', include('apps.notifications.webhook_urls', namespace='webhooks')),
    ])),
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    if 'debug_toolbar' in settings.INSTALLED_APPS:
        urlpatterns += [path('__debug__/', include('debug_toolbar.urls'))]
