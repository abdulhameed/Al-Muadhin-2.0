#!/bin/bash

# Al-Muadhin Backup Script
# Creates PostgreSQL database backups and optionally uploads to S3

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
BACKUP_DIR="${BACKUP_DIR:-./backups}"
DB_NAME="${DB_NAME:-al_muadhin}"
DB_USER="${DB_USER:-postgres}"
DB_HOST="${DB_HOST:-db}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${DB_NAME}_${TIMESTAMP}.sql.gz"

log_info "Starting database backup..."
log_info "Database: $DB_NAME"
log_info "Backup file: $BACKUP_FILE"

# Create the backup
docker-compose -f docker-compose.prod.yml exec -T db pg_dump \
    -U "$DB_USER" \
    -d "$DB_NAME" | gzip > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    log_info "Backup created successfully"
    log_info "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
else
    log_error "Backup failed"
    exit 1
fi

# Upload to S3 if configured
if [ -n "$S3_BUCKET" ]; then
    log_info "Uploading backup to S3: $S3_BUCKET"

    aws s3 cp "$BACKUP_FILE" "s3://$S3_BUCKET/backups/" \
        --sse AES256 \
        --storage-class STANDARD_IA

    if [ $? -eq 0 ]; then
        log_info "Backup uploaded to S3 successfully"
    else
        log_error "Failed to upload backup to S3"
        exit 1
    fi
fi

# Clean up old backups (local only, keep S3 versioning)
log_info "Cleaning up old backups (older than $RETENTION_DAYS days)..."

find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

log_info "Backup script completed successfully"
