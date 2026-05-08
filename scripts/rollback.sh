#!/bin/bash

# Al-Muadhin Rollback Script
# Reverts to the previous stable deployment

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

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

verify_health() {
    log_info "Verifying application health after rollback..."

    local max_retries=30
    local retry_count=0

    while [ $retry_count -lt $max_retries ]; do
        if curl -sf http://localhost:8000/health/ > /dev/null 2>&1; then
            log_info "Application is healthy"
            return 0
        fi

        retry_count=$((retry_count + 1))
        echo "Waiting for application to be ready... ($retry_count/$max_retries)"
        sleep 2
    done

    log_error "Application failed health check after rollback"
    return 1
}

main() {
    log_warn "Starting rollback procedure"

    if [ ! -f "docker-compose.prod.yml" ]; then
        log_error "docker-compose.prod.yml not found"
        exit 1
    fi

    # Get the previous commit
    local prev_commit=$(git log --oneline -2 | tail -1 | awk '{print $1}')

    if [ -z "$prev_commit" ]; then
        log_error "Could not find previous commit"
        exit 1
    fi

    log_info "Rolling back to commit: $prev_commit"

    # Reset to previous commit
    git reset --hard $prev_commit

    if [ $? -ne 0 ]; then
        log_error "Failed to reset to previous commit"
        exit 1
    fi

    log_info "Rebuilding and restarting services..."

    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml build
    docker-compose -f docker-compose.prod.yml up -d

    if [ $? -ne 0 ]; then
        log_error "Failed to restart services"
        exit 1
    fi

    # Verify health
    verify_health || exit 1

    log_info "Rollback completed successfully!"
}

main
