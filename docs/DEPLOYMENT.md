# IBIAG production deployment

## Target architecture

- Web frontend served over HTTPS at the IBIAG domain.
- FastAPI backend behind HTTPS.
- One central MongoDB database.
- One central S3-compatible object-storage bucket for documents (AWS S3, Cloudflare R2, MinIO or equivalent).
- Secrets configured only in the hosting provider / CI, never in Git.
- Backup/restore and additional services require explicit operator authorization; the backup schedule remains paused. Do not provision infrastructure or incur provider credits automatically.

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
- ALLOW_PUBLIC_REGISTRATION=false (recommended; admins create additional users)

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

## Security candidate status

The stage-1 security composition is a draft review candidate, not a release approval. Follow docs/SECURITY_RELEASE_VALIDATION.md in the audit branch and complete proxy, storage/database privileges, legacy-data and controlled-production checks before deployment. Main currently auto-deploys without waiting for CI; merging is a release action.

Startup creates only the configured administrator when absent; it does not reset an existing password, promote an existing account, seed business tables or run the old catalog/prospecting purges. An empty installation remains empty until the operator supplies approved business data through the existing screens/imports. Existing data and migration markers are preserved. See docs/STARTUP_DATA_SAFETY.md for remaining startup effects.

## Deployment order (only after validation and authorization)

1. Validate the existing MongoDB deployment and least-privilege access. Provision a new paid service only with explicit authorization.
2. Validate the existing storage backend and permissions. Configure S3 only if separately approved; do not change storage provider implicitly.
3. Deploy backend container and configure secrets. Set `ADMIN_EMAIL` and `ADMIN_PASSWORD` for the first administrator.
4. Verify `/api/health`.
5. Deploy frontend with `REACT_APP_BACKEND_URL` pointing to the backend HTTPS URL.
6. Configure DNS and TLS.
7. Run login, product, supplier, document, CRM and buyer-discovery smoke tests.
8. If separately authorized, run a database backup without exposing credentials or writing to unapproved storage.
9. If separately authorized, restore into an isolated test database and verify records; do not overwrite production.
10. Only then switch the production domain to the new deployment.

## Important

The repository contains a candidate requiring validation. Infrastructure, credentials, proxy behavior and real workflows need operational evidence; passing CI alone does not prove production readiness. No backup, paid integration, migration or deployment is authorized merely by this document.
