#!/bin/sh
# Backup script — runs inside the postgres:14-alpine container.
# Invoked manually or via cron:
#   docker compose --profile backup run --rm backup
#
# Requires these env vars (from .env):
#   POSTGRES_HOST, POSTGRES_USER, POSTGRES_DB, PGPASSWORD
# Output goes to /backups (mounted from BACKUP_STAGING_DIR on the host).
#
# After this script runs, sync /backups to offsite storage (S3, etc.) using
# rclone/s3cmd from a host cron:
#   rclone sync /path/to/backups remote:bucket/aurnom-backups

set -eu

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTFILE="/backups/aurnom_${TIMESTAMP}.sql.gz"

echo "[backup] Starting dump at ${TIMESTAMP}"
pg_dump \
  -h "${POSTGRES_HOST}" \
  -U "${POSTGRES_USER}" \
  "${POSTGRES_DB}" \
  | gzip > "${OUTFILE}"

echo "[backup] Done: ${OUTFILE}"

# Prune local staging older than 7 days to avoid filling KVM 1 disk.
find /backups -name "aurnom_*.sql.gz" -mtime +7 -delete
echo "[backup] Pruned staging older than 7 days."
