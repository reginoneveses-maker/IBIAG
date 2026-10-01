# IBIAG production deployment

## Target architecture

- Web frontend served over HTTPS at the IBIAG domain.
- FastAPI backend behind HTTPS.
- One central MongoDB database.
- One central S3-compatible object-storage bucket for documents (AWS S3, Cloudflare R2, MinIO or equivalent).
- Secrets configured only in the hosting provider / CI, never in Git.
- Daily database backup to separate storage.
- Restore test before production launch.

## Required production secrets

Backend:
- MONGO_URL
- DB_NAME
- JWT_SECRET
- CORS_ORIGINS
- APP_NAME
- STORAGE_PROVIDER=s3
- S3_BUCKET
- S3_ACCESS_KEY
- S3_SECRET_KEY
- S3_REGION (optional)
- S3_ENDPOINT (optional for S3-compatible providers)
- EMERGENT_LLM_KEY (only if using the legacy Emergent storage provider)
- FIRECRAWL_API_KEY (for live buyer discovery)

Seed/admin:
- ADMIN_EMAIL
- ADMIN_PASSWORD

Backup:
- IBIAG_MONGO_URL
- IBIAG_DB_NAME
- IBIAG_BACKUP_S3_BUCKET
- IBIAG_BACKUP_S3_ACCESS_KEY
- IBIAG_BACKUP_S3_SECRET_KEY
- IBIAG_BACKUP_S3_ENDPOINT (if not AWS)
- IBIAG_BACKUP_S3_REGION

Frontend build:
- REACT_APP_BACKEND_URL

## Deployment order

1. Create managed MongoDB.
2. Create S3-compatible object storage and set `STORAGE_PROVIDER=s3`.
3. Deploy backend container and configure secrets.
4. Verify `/api/health`.
5. Deploy frontend with `REACT_APP_BACKEND_URL` pointing to the backend HTTPS URL.
6. Configure DNS and TLS.
7. Run login, product, supplier, document, CRM and buyer-discovery smoke tests.
8. Run a real database backup.
9. Restore the backup into an isolated database and verify record counts.
10. Only then switch the production domain to the new deployment.

## Important

The repository is deployment-ready, but external infrastructure and credentials are intentionally not stored in GitHub. Production is not considered live until the steps above are executed and the restore test succeeds.
