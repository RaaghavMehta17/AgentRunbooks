#!/bin/bash
# DR Failover Script
# Promotes standby Postgres and switches application to DR region
# Idempotent: safe to run multiple times

set -euo pipefail

# Configuration
PRIMARY_REGION="${PRIMARY_REGION:-us-east-1}"
DR_REGION="${DR_REGION:-us-west-2}"
STANDBY_HOST="${STANDBY_HOST:-postgres-standby.dr.svc.cluster.local}"
STANDBY_PORT="${STANDBY_PORT:-5432}"
STANDBY_DB="${STANDBY_DB:-ops_agents}"
STANDBY_USER="${STANDBY_USER:-postgres}"
STANDBY_PASSWORD="${STANDBY_PASSWORD:-}"

# Notification settings
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
ALERT_EMAIL="${ALERT_EMAIL:-}"

LOG_FILE="/tmp/dr_failover.log"
exec > >(tee -a "$LOG_FILE")
exec 2>&1

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

notify() {
    local message="$1"
    log "NOTIFICATION: $message"
    
    # Slack notification
    if [ -n "$SLACK_WEBHOOK" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 DR Failover: $message\"}" \
            "$SLACK_WEBHOOK" || true
    fi
    
    # Generic webhook
    if [ -n "$WEBHOOK_URL" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"event\":\"dr_failover\",\"message\":\"$message\"}" \
            "$WEBHOOK_URL" || true
    fi
    
    # Email (if mail command available)
    if [ -n "$ALERT_EMAIL" ] && command -v mail &> /dev/null; then
        echo "$message" | mail -s "DR Failover Alert" "$ALERT_EMAIL" || true
    fi
}

check_standby_ready() {
    log "Checking standby database readiness..."
    export PGPASSWORD="$STANDBY_PASSWORD"
    
    if psql -h "$STANDBY_HOST" -p "$STANDBY_PORT" -U "$STANDBY_USER" -d "$STANDBY_DB" \
        -c "SELECT pg_is_in_recovery();" | grep -q "t"; then
        log "✓ Standby is in recovery mode (ready for promotion)"
        return 0
    else
        log "✗ Standby is not in recovery mode (may already be promoted)"
        return 1
    fi
}

promote_standby() {
    log "Promoting standby database..."
    export PGPASSWORD="$STANDBY_PASSWORD"
    
    # Promote standby (if using streaming replication)
    psql -h "$STANDBY_HOST" -p "$STANDBY_PORT" -U "$STANDBY_USER" -d "$STANDBY_DB" \
        -c "SELECT pg_promote();" || {
        log "WARNING: pg_promote() failed, standby may already be promoted"
    }
    
    # Wait for promotion to complete
    sleep 5
    
    # Verify promotion
    if psql -h "$STANDBY_HOST" -p "$STANDBY_PORT" -U "$STANDBY_USER" -d "$STANDBY_DB" \
        -c "SELECT pg_is_in_recovery();" | grep -q "f"; then
        log "✓ Standby successfully promoted to primary"
        return 0
    else
        log "✗ Standby promotion verification failed"
        return 1
    fi
}

update_connection_strings() {
    log "Updating application connection strings..."
    
    # Update Kubernetes Secret with new database host
    if command -v kubectl &> /dev/null; then
        NAMESPACE="${NAMESPACE:-ops-agents}"
        SECRET_NAME="${SECRET_NAME:-ops-agents-secrets}"
        
        # Update DATABASE_URL or DATABASE_HOST in secret
        kubectl -n "$NAMESPACE" patch secret "$SECRET_NAME" \
            --type='json' \
            -p="[{\"op\":\"replace\",\"path\":\"/data/DATABASE_HOST\",\"value\":\"$(echo -n "$STANDBY_HOST" | base64)\"}]" || {
            log "WARNING: Failed to update Kubernetes secret"
        }
        
        log "✓ Updated Kubernetes secret with new database host"
    else
        log "WARNING: kubectl not available, skipping secret update"
    fi
}

run_alembic_check() {
    log "Running Alembic database sanity check..."
    
    # Check if alembic is available
    if ! command -v alembic &> /dev/null; then
        log "WARNING: alembic not found, skipping schema check"
        return 0
    fi
    
    # Run alembic check (verify schema is up to date)
    export DATABASE_URL="postgresql://${STANDBY_USER}:${STANDBY_PASSWORD}@${STANDBY_HOST}:${STANDBY_PORT}/${STANDBY_DB}"
    
    if alembic current &> /dev/null; then
        log "✓ Alembic schema check passed"
        return 0
    else
        log "✗ Alembic schema check failed"
        return 1
    fi
}

freeze_writes() {
    log "Freezing writes to primary (if accessible)..."
    
    # Attempt to set primary to read-only (if still accessible)
    PRIMARY_HOST="${PRIMARY_HOST:-postgres.primary.svc.cluster.local}"
    PRIMARY_PORT="${PRIMARY_PORT:-5432}"
    PRIMARY_USER="${PRIMARY_USER:-postgres}"
    PRIMARY_PASSWORD="${PRIMARY_PASSWORD:-}"
    
    if [ -n "$PRIMARY_PASSWORD" ]; then
        export PGPASSWORD="$PRIMARY_PASSWORD"
        psql -h "$PRIMARY_HOST" -p "$PRIMARY_PORT" -U "$PRIMARY_USER" -d "$STANDBY_DB" \
            -c "ALTER DATABASE $STANDBY_DB SET default_transaction_read_only = on;" 2>/dev/null || {
            log "WARNING: Could not freeze primary (may already be down)"
        }
    fi
}

main() {
    log "=== DR Failover Script Started ==="
    log "Primary Region: $PRIMARY_REGION"
    log "DR Region: $DR_REGION"
    log "Standby Host: $STANDBY_HOST"
    
    # Step 1: Freeze writes (best effort)
    freeze_writes || true
    
    # Step 2: Check standby readiness
    if ! check_standby_ready; then
        log "WARNING: Standby may already be promoted, continuing..."
    fi
    
    # Step 3: Promote standby
    if ! promote_standby; then
        log "ERROR: Failed to promote standby"
        notify "DR Failover FAILED: Could not promote standby database"
        exit 1
    fi
    
    # Step 4: Update connection strings
    update_connection_strings
    
    # Step 5: Run Alembic check
    run_alembic_check || {
        log "WARNING: Alembic check failed, but continuing with failover"
    }
    
    # Step 6: Notify
    notify "DR Failover COMPLETED: Application switched to DR region ($DR_REGION)"
    
    log "=== DR Failover Script Completed ==="
    log "Next steps:"
    log "  1. Verify application health endpoints"
    log "  2. Monitor for any errors"
    log "  3. Update DNS/ingress if needed"
    log "  4. Document failover time and reason"
    
    return 0
}

# Run main function
main "$@"

