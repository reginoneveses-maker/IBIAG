"""CRM authorization predicates; no ownership is accepted from browser data."""
from fastapi import HTTPException


def lead_scope(user, query=None):
    query = dict(query or {})
    if user.get("role") != "admin":
        query["owner_id"] = user["id"]
    return query


async def require_lead(db, user, lead_id):
    lead = await db.leads.find_one(lead_scope(user, {"id": lead_id}), {"_id": 0})
    if not lead:
        raise HTTPException(404, "Empresa não encontrada")
    return lead


async def visible_lead_ids(db, user):
    return [lead["id"] async for lead in db.leads.find(lead_scope(user), {"id": 1})]


async def document_scope(db, user, query=None):
    query = dict(query or {})
    if user.get("role") == "admin":
        return query
    ids = await visible_lead_ids(db, user)
    return {"$and": [query, {"$or": [{"lead_id": {"$in": [None, ""]}}, {"lead_id": {"$in": ids}}]},
                     {"file_path": {"$nin": await private_file_paths(db, user)}}]}


async def private_file_paths(db, user):
    if user.get("role") == "admin":
        return []
    ids = await visible_lead_ids(db, user)
    query = {"lead_id": {"$exists": True, "$nin": [None, "", *ids]}}
    return list({doc["file_path"] async for doc in db.documents.find(query, {"file_path": 1}) if doc.get("file_path")})


async def shared_file_scope(db, user, query=None, fields=("file_path",)):
    paths = await private_file_paths(db, user)
    return {"$and": [query or {}, *[{field: {"$nin": paths}} for field in fields]]} if paths else query or {}


async def authorize_crm_file(db, user, path):
    # A former uploader must not retain access after the lead is transferred.
    # Private CRM linkage takes priority over upload prefixes/shared spec links.
    if path in await private_file_paths(db, user):
        raise HTTPException(404, "Arquivo não encontrado")
