#!/bin/bash

# Al-Muadhin Deployment Script
# This script handles production deployment with zero-downtime updates

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
APP_NAME="al_muadhin"
SLACK_WEBHOOK="${SLACK_WEBHOOK_URL:-}"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

send_slack_notification() {
    if [ -z "$SLACK_WEBHOOK" ]; then
        return
    fi

    local message="$1"
    local status="$2"

    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"$message\", \"status\":\"$status\"}" \
        "$SLACK_WEBHOOK" || true
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    if [ ! -f ".env" ]; then
        log_error ".env file not found"
        exit 1
    fi

    log_info "All prerequisites met"
}

verify_health() {
    log_info "Verifying application health..."

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

    log_error "Application failed health check"
    return 1
}

pull_latest_code() {
    log_info "Pulling latest code from repository..."

    git fetch origin
    git reset --hard origin/main

    if [ $? -ne 0 ]; then
        log_error "Failed to pull latest code"
        return 1
    fi

    log_info "Code updated successfully"
    return 0
}

build_images() {
    log_info "Building Docker images..."

    docker-compose -f $DOCKER_COMPOSE_FILE build

    if [ $? -ne 0 ]; then
        log_error "Failed to build Docker images"
        return 1
    fi

    log_info "Docker images built successfully"
    return 0
}

run_migrations() {
    log_info "Running database migrations..."

    docker-compose -f $DOCKER_COMPOSE_FILE run --rm web python manage.py migrate

    if [ $? -ne 0 ]; then
        log_error "Database migrations failed"
        return 1
    fi

    log_info "Database migrations completed"
    return 0
}

collect_static() {
    log_info "Collecting static files..."

    docker-compose -f $DOCKER_COMPOSE_FILE run --rm web python manage.py collectstatic --noinput

    if [ $? -ne 0 ]; then
        log_error "Failed to collect static files"
        return 1
    fi

    log_info "Static files collected"
    return 0
}

restart_services() {
    log_info "Restarting services..."

    docker-compose -f $DOCKER_COMPOSE_FILE down
    docker-compose -f $DOCKER_COMPOSE_FILE up -d

    if [ $? -ne 0 ]; then
        log_error "Failed to restart services"
        return 1
    fi

    log_info "Services restarted"
    return 0
}

cleanup_old_images() {
    log_info "Cleaning up old Docker images..."

    docker image prune -f > /dev/null 2>&1

    log_info "Old images cleaned up"
}

# Main deployment flow
main() {
    log_info "Starting deployment of $APP_NAME"
    send_slack_notification "Deployment started for $APP_NAME" "in_progress"

    # Run checks and deployment steps
    check_prerequisites || exit 1
    pull_latest_code || exit 1
    build_images || exit 1
    run_migrations || exit 1
    collect_static || exit 1
    restart_services || exit 1
    verify_health || exit 1
    cleanup_old_images

    log_info "Deployment completed successfully!"
    send_slack_notification "✅ Deployment completed for $APP_NAME at $(date)" "success"
}

# Run main function
main
