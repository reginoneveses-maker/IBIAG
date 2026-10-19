"""Bounded, read-only operational checks. Never imports app/startup or prints secrets."""
import asyncio
import json
import os
import sys

from motor.motor_asyncio import AsyncIOMotorClient
from api_security import cors_origins_from, validate_jwt_secret
from serve import server_options

QUERY_MS = 5000


def configuration_checks(environ):
    checks = {
        "public_registration_disabled": environ.get("ALLOW_PUBLIC_REGISTRATION", "false").strip().lower() == "false",
        "paid_discovery_disabled": environ.get("ALLOW_PAID_DISCOVERY", "false").strip().lower() == "false",
        "api_docs_disabled": environ.get("ENABLE_API_DOCS", "false").strip().lower() == "false",
    }
    try:
        validate_jwt_secret(environ.get("JWT_SECRET", ""))
        checks["jwt_format_valid"] = True
    except (TypeError, ValueError): checks["jwt_format_valid"] = False
    try:
        origins = cors_origins_from(environ)
        checks["https_origins_configured"] = bool(origins) and all(origin.startswith("https://") for origin in origins)
    except (TypeError, ValueError): checks["https_origins_configured"] = False
    try:
        options = server_options(environ)
        checks["proxy_configuration_valid"] = True
        checks["proxy_trust_configured"] = bool(options["forwarded_allow_ips"])
    except (TypeError, ValueError):
        checks["proxy_configuration_valid"] = checks["proxy_trust_configured"] = False
    return checks


async def aggregate_count(collection, stages):
    rows = await collection.aggregate([*stages, {"$count":"count"}], maxTimeMS=QUERY_MS,
                                      allowDiskUse=False).to_list(1)
    return rows[0]["count"] if rows else 0


def missing(field): return {"$or":[{field:{"$exists":False}}, {field:{"$in":[None, ""]}}]}


def linked(field): return {field:{"$exists":True, "$nin":[None, ""]}}


async def orphan_count(db, name, field, foreign_collection, foreign_field="id"):
    return await aggregate_count(db[name], [
        {"$match":linked(field)},
        {"$lookup":{"from":foreign_collection,"localField":field,"foreignField":foreign_field,"as":"_audit_reference"}},
        {"$match":{"_audit_reference.0":{"$exists":False}}},
    ])


async def collect(db, environ):
    # Only fixed commands/queries; no user-selected collections, query operators
    # or free text. Each query has a server time budget and cannot spill to disk.
    findings = {}
    try:
        status = await db.command({"connectionStatus":1, "showPrivileges":True})
        info = status.get("authInfo", {})
        authenticated = bool(info.get("authenticatedUsers"))
        privileges = info.get("authenticatedUserPrivileges")
        forbidden = {"anyAction", "dropDatabase", "createUser", "dropUser", "grantRole", "revokeRole",
                     "grantPrivilege", "revokePrivilege", "changePassword", "changeCustomData"}
        review = None if not privileges else bool(any(
            set(item.get("actions", [])) & forbidden
            or item.get("resource", {}).get("anyResource")
            or item.get("resource", {}).get("cluster")
            or item.get("resource", {}).get("db", db.name) != db.name
            for item in privileges))
        authentication = {"query_completed":True,"authenticated":authenticated,
                          "privilege_details_available":isinstance(privileges, list) and bool(privileges),
                          "privileges_require_review":review}
    except Exception:
        authentication = {"query_completed":False,"authenticated":None,
                          "privilege_details_available":False,"privileges_require_review":None}

    failures=[]
    for name in ("users", "leads", "tasks", "documents"):
        try:
            findings[name+"_missing_id"] = await db[name].count_documents(missing("id"), maxTimeMS=QUERY_MS)
            findings[name+"_duplicate_id_groups"] = await aggregate_count(db[name], [
                {"$match":linked("id")}, {"$group":{"_id":"$id","count":{"$sum":1}}}, {"$match":{"count":{"$gt":1}}}])
        except Exception: failures.append(name+"_identity")
    try:
        findings["users_missing_email"] = await db.users.count_documents(missing("email"), maxTimeMS=QUERY_MS)
        findings["users_duplicate_email_groups"] = await aggregate_count(db.users, [
            {"$match":{"email":{"$type":"string"}}},
            {"$group":{"_id":{"$toLower":"$email"},"count":{"$sum":1}}}, {"$match":{"count":{"$gt":1}}}])
        findings["users_unknown_role"] = await db.users.count_documents({"role":{"$nin":["admin","user"]}}, maxTimeMS=QUERY_MS)
    except Exception: failures.append("users_access")
    for name in ("leads", "tasks"):
        try:
            findings[name+"_missing_owner"] = await db[name].count_documents(missing("owner_id"), maxTimeMS=QUERY_MS)
            findings[name+"_orphan_owner"] = await orphan_count(db,name,"owner_id","users")
        except Exception: failures.append(name+"_ownership")
    for name in ("documents", "tasks", "interactions"):
        try: findings[name+"_orphan_lead"] = await orphan_count(db,name,"lead_id","leads")
        except Exception: failures.append(name+"_lead_reference")
    storage = environ.get("STORAGE_PROVIDER", "gridfs").strip().lower()
    if storage == "gridfs":
        try: findings["documents_missing_gridfs_object"] = await orphan_count(db,"documents","file_path","ibiag_files.files","filename")
        except Exception: failures.append("gridfs_document_references")
    elif storage != "s3": failures.append("storage_configuration")
    config = configuration_checks(environ)
    return {
        "scope":"configured-database-only", "read_only":True,
        "authentication":authentication,"configuration_checks":config,
        "finding_counts":findings,"incomplete_checks":failures,
        "automated_checks_passed":bool(authentication["authenticated"]
            and authentication["privilege_details_available"]
            and authentication["privileges_require_review"] is False
            and all(config.values()) and not any(findings.values()) and not failures),
        "manual_evidence_required":["actual_proxy_peer_and_header_sanitization","database_persistence_and_recovery_policy",
            "effective_storage_privacy_and_object_reference_coverage","authorized_published_account_flows",
            "content_malware_and_capacity_policy","administrative_access_and_MFA_policy"],
        "production_certified":False,
    }


async def execute():
    uri, name = os.environ.get("MONGO_URL"), os.environ.get("DB_NAME")
    if not uri or not name: raise ValueError("Configuration unavailable")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, socketTimeoutMS=10000,
                               connectTimeoutMS=5000, maxPoolSize=2)
    try: return await collect(client[name], os.environ)
    finally: client.close()


def main():
    try:
        result = asyncio.run(execute())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["automated_checks_passed"] else 1
    except (Exception, KeyboardInterrupt):
        print(json.dumps({"read_only":True,"audit_completed":False,"production_certified":False,
                          "error":"Auditoria não concluída; detalhes de conexão não são exibidos."},ensure_ascii=False),file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
