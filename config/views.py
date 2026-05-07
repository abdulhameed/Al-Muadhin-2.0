from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """Health check endpoint for monitoring."""
    status = 'healthy'
    db_status = 'healthy'
    redis_status = 'healthy'
    celery_status = 'healthy'
    status_code = 200

    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception as e:
        logger.error(f'Database health check failed: {e}')
        db_status = 'unhealthy'
        status = 'unhealthy'
        status_code = 503

    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
    except Exception as e:
        logger.error(f'Redis health check failed: {e}')
        redis_status = 'unhealthy'
        status = 'unhealthy'
        status_code = 503

    return JsonResponse({
        'status': status,
        'db_status': db_status,
        'redis_status': redis_status,
        'celery_status': celery_status,
    }, status=status_code)
