# IBIAG Backup / Disaster Recovery

The production setup keeps a backup copy of the application database outside the primary MongoDB instance.

## Automated database backup

backend/backup.py exports every MongoDB collection to a compressed JSONL archive and uploads it to an S3-compatible bucket.

The GitHub Actions workflow .github/workflows/backup.yml runs daily at 03:17 UTC and can also be started manually.

Configure GitHub Secrets:
- IBIAG_MONGO_URL
- IBIAG_DB_NAME
- IBIAG_BACKUP_S3_BUCKET
- IBIAG_BACKUP_S3_ACCESS_KEY
- IBIAG_BACKUP_S3_SECRET_KEY
- IBIAG_BACKUP_S3_ENDPOINT (optional for AWS S3)
- IBIAG_BACKUP_S3_REGION (optional)

Repository variables:
- IBIAG_BACKUP_S3_PREFIX (default: ibiag/database)
- IBIAG_BACKUP_RETENTION_DAYS (default: 30)

Before production launch, document/object storage for specs, certificates, COAs and photos must also be included in the backup policy, followed by a real restore test.

Never commit MongoDB or S3 credentials to the repository.
