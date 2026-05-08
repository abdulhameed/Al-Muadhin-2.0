# Al-Muadhin Operational Runbook

This runbook provides procedures for operating and maintaining the Al-Muadhin prayer notification service in production.

## Table of Contents

1. [Deployment](#deployment)
2. [Monitoring](#monitoring)
3. [Troubleshooting](#troubleshooting)
4. [Maintenance](#maintenance)
5. [Backup & Recovery](#backup--recovery)
6. [Emergency Procedures](#emergency-procedures)
7. [Common Tasks](#common-tasks)

## Deployment

### Prerequisites

- SSH access to production server
- Docker and Docker Compose installed
- Git access to the repository
- Environment variables configured in `.env` file

### Initial Deployment

```bash
# 1. Clone the repository
git clone <repository-url> /opt/al-muadhin
cd /opt/al-muadhin

# 2. Create environment file
cp .env.example .env
# Edit .env with production values

# 3. Create SSL certificates (if not using external provider)
mkdir -p certificates
# Add cert.pem and key.pem (e.g., from Let's Encrypt)

# 4. Run initial deployment
bash scripts/deploy.sh
```

### Regular Deployments

```bash
cd /opt/al-muadhin

# Pull latest code and restart
bash scripts/deploy.sh
```

The script will:
1. Pull latest code from main branch
2. Build Docker images
3. Run database migrations
4. Collect static files
5. Restart services
6. Verify application health
7. Send Slack notification

### Rollback Procedure

If deployment causes issues:

```bash
cd /opt/al-muadhin

# Rollback to previous commit
bash scripts/rollback.sh
```

The rollback script will:
1. Revert to the previous git commit
2. Rebuild Docker images
3. Restart services
4. Verify health

## Monitoring

### Health Check

Check application health:

```bash
curl http://localhost:8000/health/
```

Response format:

```json
{
  "db_status": "healthy",
  "redis_status": "healthy",
  "celery_worker_heartbeat": "healthy"
}
```

### View Logs

#### Django/Application Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f web
```

#### Celery Worker Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f celery_worker
```

#### Celery Beat Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f celery_beat
```

#### Nginx Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f nginx
```

#### All Logs

```bash
docker-compose -f docker-compose.prod.yml logs -f
```

### Monitor Services

```bash
# Show running containers
docker-compose -f docker-compose.prod.yml ps

# Monitor resource usage
docker stats

# Check service health
docker-compose -f docker-compose.prod.yml ps --format "table {{.Service}}\t{{.Status}}"
```

### Metrics to Monitor

#### Key Performance Indicators

- **Notification Delivery Rate**: % of notifications delivered successfully
- **Average Response Time**: API response time (target: <200ms)
- **Error Rate**: % of requests returning 5xx errors (target: <0.1%)
- **Celery Queue Depth**: Number of pending tasks (target: <100)
- **Provider Health**: Success rate by provider (target: >95%)
- **Database Connection Pool**: Active connections (target: <20)

#### Common Alerts

- Provider health drops below 50%
- Database connection errors
- Redis connection failure
- Celery worker down
- Disk space low (<10% remaining)
- High error rate (>1%)

## Troubleshooting

### Application Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs web

# Common issues:
# 1. Database connection error - check DB_HOST, DB_PASSWORD in .env
# 2. Redis connection error - check REDIS_URL in .env
# 3. Secret key not set - ensure DJANGO_SECRET_KEY is in .env
```

### Database Connection Errors

```bash
# Test database connection
docker-compose -f docker-compose.prod.yml exec db psql -U postgres -d al_muadhin

# If connection fails:
# 1. Check DB container is running: docker ps | grep postgres
# 2. Check network connectivity: docker-compose -f docker-compose.prod.yml logs db
# 3. Verify credentials in .env
```

### Redis Connection Errors

```bash
# Test Redis connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Should respond with: PONG

# If no response:
# 1. Check Redis container running: docker ps | grep redis
# 2. Check logs: docker-compose -f docker-compose.prod.yml logs redis
```

### High Memory Usage

```bash
# Check container memory usage
docker stats

# If web service uses too much memory:
# 1. Check for memory leaks in logs
# 2. Restart service: docker-compose -f docker-compose.prod.yml restart web
# 3. Scale workers down if using multiple workers

# If database uses too much memory:
# 1. Check for missing indexes
# 2. Vacuum database (safe):
docker-compose -f docker-compose.prod.yml exec -T db vacuum analyze
```

### Slow API Responses

```bash
# Check database query performance
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -d al_muadhin

# Enable query logging in postgres:
# ALTER SYSTEM SET log_min_duration_statement = 1000;
# SELECT pg_reload_conf();

# Check for slow queries
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -d al_muadhin -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

### Celery Tasks Not Running

```bash
# Check Celery worker status
docker-compose -f docker-compose.prod.yml exec celery_worker celery -A config inspect active

# Check scheduled tasks
docker-compose -f docker-compose.prod.yml exec celery_beat celery -A config inspect scheduled

# Restart Celery worker if stuck
docker-compose -f docker-compose.prod.yml restart celery_worker

# Check task queue depth
docker-compose -f docker-compose.prod.yml exec redis redis-cli llen celery

# Flush stuck tasks (use with caution)
docker-compose -f docker-compose.prod.yml exec redis redis-cli FLUSHDB
```

## Maintenance

### Database Maintenance

#### Vacuum (Clean up disk space)

```bash
# Safe vacuum (recommended)
docker-compose -f docker-compose.prod.yml exec -T db vacuum analyze

# Full vacuum (may lock tables, run during low traffic)
docker-compose -f docker-compose.prod.yml exec -T db vacuum full analyze
```

#### Reindex (Rebuild indexes)

```bash
# Rebuild indexes (safe)
docker-compose -f docker-compose.prod.yml exec -T db reindex database al_muadhin
```

#### Check Database Size

```bash
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -d al_muadhin -c \
  "SELECT pg_size_pretty(pg_database_size('al_muadhin'));"
```

### Clear Cache

```bash
# Clear Redis cache (loses all cached data, be careful)
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli FLUSHDB

# Specific cache keys
docker-compose -f docker-compose.prod.yml exec -T redis redis-cli DEL key_name
```

### Database Cleanup

```bash
# Archive old notifications (older than 90 days)
docker-compose -f docker-compose.prod.yml exec web python manage.py \
  manage_old_notifications --archive --days 90

# Clean old prayer time cache (older than 7 days)
docker-compose -f docker-compose.prod.yml exec web python manage.py \
  clean_prayer_cache --days 7
```

## Backup & Recovery

### Create Manual Backup

```bash
bash scripts/backup.sh

# Backup will be saved to ./backups/backup_al_muadhin_YYYYMMDD_HHMMSS.sql.gz
```

### Restore from Backup

```bash
# List available backups
ls -lh ./backups/backup_*.sql.gz

# Restore from backup (will overwrite current database)
BACKUP_FILE="./backups/backup_al_muadhin_20260101_120000.sql.gz"

# Stop the application
docker-compose -f docker-compose.prod.yml down

# Restore database
gunzip -c "$BACKUP_FILE" | docker exec -i al_muadhin_db psql -U postgres al_muadhin

# Restart application
docker-compose -f docker-compose.prod.yml up -d
```

### Schedule Automated Backups

Add to crontab (runs daily at 2 AM):

```bash
0 2 * * * cd /opt/al-muadhin && bash scripts/backup.sh >> logs/backup.log 2>&1
```

### Backup Retention

- Local backups: 30 days (auto-deleted by backup script)
- S3 backups: 90 days (configure S3 lifecycle policy)

## Emergency Procedures

### Site Maintenance Mode

Enable maintenance mode (show message to all users):

```bash
# Create maintenance flag
docker-compose -f docker-compose.prod.yml exec web python manage.py \
  shell -c "from django.conf import settings; \
  print('Maintenance mode enabled')"

# Update Nginx to show maintenance page
# Edit nginx.conf and uncomment maintenance block, then reload:

docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### Disable a Provider Immediately

If a provider is causing issues:

```bash
# Access Django admin and disable provider via UI, OR:

docker-compose -f docker-compose.prod.yml exec web python manage.py shell

# Then:
from apps.providers.models import TelcoProvider
provider = TelcoProvider.objects.get(name='Twilio')
provider.is_active = False
provider.save()
exit()
```

### Stop All Notifications

Emergency only (prevents all notifications):

```bash
# Pause all users' notifications
docker-compose -f docker-compose.prod.yml exec web python manage.py shell

from apps.accounts.models import User
User.objects.all().update(is_active_subscriber=False)
exit()

# Resume when issue is fixed
from apps.accounts.models import User
User.objects.all().update(is_active_subscriber=True)
exit()
```

### Scale Services

```bash
# Scale web service to 2 instances
docker-compose -f docker-compose.prod.yml up -d --scale web=2

# Scale celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery_worker=3
```

## Common Tasks

### Add New Administrator

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py \
  createsuperuser
```

### Reset User Password

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py \
  changepassword username
```

### View Application Stats

```bash
# Total notifications sent
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
from apps.notifications.models import NotificationLog
print(f"Total notifications: {NotificationLog.objects.count()}")
print(f"Delivered: {NotificationLog.objects.filter(status='delivered').count()}")
print(f"Failed: {NotificationLog.objects.filter(status='failed').count()}")
exit()
```

### Test Email Delivery

```bash
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
from django.core.mail import send_mail
send_mail(
    'Test Email',
    'This is a test email from Al-Muadhin',
    'notifications@almuadhin.com',
    ['test@example.com'],
)
exit()
```

### Test SMS Provider

```bash
# Via admin interface:
# 1. Go to http://localhost/admin/providers/telcoprovider/
# 2. Select a provider
# 3. Choose "Test SMS delivery" from Actions dropdown
# 4. Click Go
```

### View Cost Summary

```bash
# Via API (admin only)
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost/api/notifications/cost_summary/?days=30

# Via Django shell
docker-compose -f docker-compose.prod.yml exec web python manage.py shell
from apps.providers.services import CostAnalytics
from datetime import timedelta
from django.utils import timezone

end = timezone.now()
start = end - timedelta(days=30)
summary = CostAnalytics.get_cost_summary(start, end)
print(f"Total cost: {summary['total_cost']}")
exit()
```

## Monitoring Checklist

Daily checks:

- [ ] Application health: `curl http://localhost:8000/health/`
- [ ] All services running: `docker-compose -f docker-compose.prod.yml ps`
- [ ] No critical errors in logs
- [ ] Database size normal
- [ ] Disk space available (>20%)
- [ ] Provider health status

Weekly checks:

- [ ] Review error logs for patterns
- [ ] Check backup success
- [ ] Review cost trends
- [ ] Monitor notification delivery rate
- [ ] Verify provider performance

Monthly checks:

- [ ] Database maintenance (vacuum, reindex)
- [ ] SSL certificate expiration
- [ ] Security updates needed
- [ ] Performance review
- [ ] Capacity planning

## Contacts & Escalation

In case of critical issues:

1. **Application errors**: Check logs first, then contact development team
2. **Database issues**: Stop application, backup database, contact DBA
3. **Complete outage**: Switch to maintenance mode, investigate root cause
4. **Security incident**: Isolate affected systems, notify security team

## Additional Resources

- [Provider Management Guide](./PROVIDER_MANAGEMENT.md)
- [Development Setup](./SETUP.md)
- Django documentation: https://docs.djangoproject.com
- PostgreSQL documentation: https://www.postgresql.org/docs
- Docker documentation: https://docs.docker.com
