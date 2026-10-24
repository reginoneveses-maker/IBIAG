"""Offline ExportHub-v1 reconciliation and synthetic-only preservation rehearsal.
Never connects to a database from the CLI; never changes native business records.
"""
import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

MAX_JSON = 64 * 1024 * 1024
MAX_FILES = 128 * 1024 * 1024
CHUNK = 1024 * 1024
MAX_MANIFEST = 12 * 1024 * 1024
NATIVE = {"leads", "products", "suppliers", "product_offers", "quotations", "orders",
          "commercial_invoices", "packing_lists"}
MAP_TARGETS = {"company": {"leads"}, "opportunity": {"leads"}, "product": {"products"},
               "product-profile": {"product_offers"}, "quote": {"quotations"}, "shipment": {"orders"}}
ARRAYS = {"shipments": "shipment", "documents": "shipment-document", "tasks": "task",
          "sectorRecords": "sector-record", "products": "product-profile"}
FILE_GROUPS = {"specs": "spec", "crmFiles": "crm-file", "sectorFiles": "sector-file"}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def encoded(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()

def unique_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError("Duplicate JSON property")
            result[key] = value
        return result
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda v: (_ for _ in ()).throw(ValueError("Non-finite JSON")))

def identity(value):
    return isinstance(value, str) and 0 < len(value) <= 200 and not any(ord(c) < 32 for c in value)

def name_key(value):
    return " ".join(unicodedata.normalize("NFKC", str(value or "")).casefold().split())

def plan_reconciliation(raw, native=None, links=None, files=None):
    if not isinstance(raw, bytes) or len(raw) > MAX_JSON:
        raise ValueError("Backup must be bounded original JSON bytes")
    source = unique_json(raw)
    if not isinstance(source, dict) or source.get("format") != "exporthub-v1":
        raise ValueError("Expected the existing ExportHub-v1 manual export")
    native, links, files = native or {}, links or [], files or {}
    if not isinstance(native, dict) or set(native) - NATIVE:
        raise ValueError("Use only a business-record inventory; no users or credentials")
    if not isinstance(links, list) or not isinstance(files, dict):
        raise ValueError("Invalid explicit links or attachment map")
    for rows in native.values():
        if not isinstance(rows, list) or len(rows) > 50000 or any(not isinstance(r, dict) for r in rows):
            raise ValueError("Invalid native inventory")
    if any(not isinstance(k, str) or not isinstance(v, bytes) for k, v in files.items()) or sum(map(len, files.values())) > MAX_FILES:
        raise ValueError("Attachment package exceeds the isolated rehearsal limit")
    nodes, refs, blockers = [], [], []
    def problem(code, key):
        blockers.append({"code": code, "source": str(key)[:240]})
    def register(kind, rows):
        if not isinstance(rows, list) or len(rows) > 50000:
            problem("invalid-array", kind)
            return
        for row in rows:
            if not isinstance(row, dict) or not identity(row.get("id")):
                problem("invalid-id", kind)
                continue
            nodes.append({"key": kind + ":" + row["id"], "kind": kind, "id": row["id"], "record": row})
    records = source.get("records", [])
    if not isinstance(records, list) or len(records) > 1000:
        raise ValueError("Invalid collection export")
    names, payloads = [], {}
    for record in records:
        if not isinstance(record, dict) or not identity(record.get("name")) or "payload" not in record:
            problem("invalid-collection", "records")
            continue
        names.append(record["name"])
        if type(record.get("revision")) is not int or record["revision"] < 0:
            problem("invalid-revision", record["name"])
        payloads[record["name"]] = record["payload"]
    for n, count in Counter(names).items():
        if count > 1: problem("duplicate-collection", n)
    register("product", source.get("products", []))
    commercial = payloads.get("commercial", {})
    if not isinstance(commercial, dict):
        problem("invalid-commercial", "commercial")
        commercial = {}
    for key, kind in (("companies", "company"), ("contacts", "contact"), ("ops", "opportunity"),
                      ("quotes", "quote"), ("quoteDrafts", "quote-draft")):
        register(kind, commercial.get(key, []))
    for name, kind in ARRAYS.items():
        register(kind, payloads.get(name, []))
    for name, kind in FILE_GROUPS.items():
        register(kind, source.get(name, []))
    by_key = {}
    for node in nodes:
        by_key.setdefault(node["key"], []).append(node)
    for key, rows in by_key.items():
        if len(rows) > 1: problem("duplicate-source-id", key)
    def ref(node, field, kind):
        value = node["record"].get(field)
        if value:
            target = kind + ":" + value if isinstance(value, str) else ""
            refs.append({"from": node["key"], "field": field, "to": target})
            if len(by_key.get(target, [])) != 1: problem("unresolved-source-link", node["key"] + "/" + field)
    for node in nodes:
        kind, row = node["kind"], node["record"]
        if kind == "contact": ref(node, "companyId", "company")
        if kind == "opportunity":
            ref(node, "companyId", "company")
            ids = row.get("contactIds", [])
            if not isinstance(ids, list): problem("invalid-contact-links", node["key"])
            else:
                for cid in ids:
                    if not isinstance(cid, str) or len(by_key.get("contact:" + cid, [])) != 1:
                        problem("unresolved-source-link", node["key"] + "/contactIds")
        if kind in {"quote", "shipment", "task", "sector-record", "crm-file"}: ref(node, "opportunityId" if kind != "crm-file" else "opportunity_id", "opportunity")
        if kind in {"shipment", "task"}: ref(node, "quoteId", "quote")
        if kind == "task": ref(node, "recordId", "sector-record")
        if kind in {"shipment", "sector-record"}: ref(node, "productId", "product")
        if kind in {"shipment-document", "sector-record"}: ref(node, "shipmentId", "shipment")
        if kind == "spec": ref(node, "product_id", "product")
        if kind == "sector-file": ref(node, "record_id", "sector-record")
    if source.get("crmInterchange") is not None:
        origins = commercial.get("interchangeLinks", [])
        if source["crmInterchange"] != "embedded-origins-v1" or not isinstance(origins, list) or type(source.get("crmOriginCount")) is not int or source.get("crmOriginCount") != len(origins):
            problem("invalid-crm-origin-registry", "commercial")
    expected_files, manifest = {}, []
    for node in nodes:
        if node["kind"] in FILE_GROUPS.values():
            expected_files[node["key"]] = node["record"]
    for key in files:
        if key not in expected_files: problem("unindexed-file", key)
    revision_hashes = {}
    revisions = source.get("specRevisions", [])
    if not isinstance(revisions, list):
        problem("invalid-spec-revisions", "specRevisions")
        revisions = []
    seen_versions = set()
    seen_spec_ids = set()
    for revision in revisions:
        if not isinstance(revision, dict):
            problem("invalid-spec-revision", "specRevisions")
            continue
        sid, root, number = revision.get("spec_id"), revision.get("root_id"), revision.get("revision")
        if isinstance(sid, str):
            if sid in seen_spec_ids: problem("duplicate-spec-revision", sid)
            seen_spec_ids.add(sid)
        if not identity(sid) or len(by_key.get("spec:" + str(sid), [])) != 1 or not identity(root) or len(by_key.get("spec:" + str(root), [])) != 1 or type(number) is not int or number < 1 or (root, number) in seen_versions:
            problem("invalid-spec-revision-link", str(sid))
        if identity(root) and type(number) is int: seen_versions.add((root, number))
        digest = revision.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch("[0-9a-f]{64}", digest):
            problem("invalid-spec-digest", str(sid))
        else: revision_hashes["spec:" + str(sid)] = digest
    for key, meta in expected_files.items():
        value = files.get(key)
        if value is None:
            problem("missing-private-file", key)
            continue
        size = meta.get("size")
        if type(size) is not int or size != len(value):
            problem("file-size-mismatch", key)
        digest = sha(value)
        expected = revision_hashes.get(key)
        if expected and expected != digest: problem("file-version-digest-mismatch", key)
        manifest.append({"source": key, "size": len(value), "sha256": digest,
                         "versionDigestChecked": bool(expected)})
    reviewed, mappings, suggestions = set(), [], []
    native_index = {name: {} for name in NATIVE}
    for collection, rows in native.items():
        for row in rows:
            if identity(row.get("id")): native_index[collection].setdefault(row["id"], []).append(row)
    for link in links:
        if not isinstance(link, dict) or set(link) != {"source", "collection", "target"}:
            problem("invalid-reviewed-link", "links")
            continue
        key, collection, target = link["source"], link["collection"], link["target"]
        if not all(isinstance(value, str) for value in (key, collection, target)):
            problem("invalid-reviewed-link", "links")
            continue
        if not isinstance(key, str) or key in reviewed or len(by_key.get(key, [])) != 1:
            problem("ambiguous-reviewed-source", key)
            continue
        reviewed.add(key)
        kind = by_key[key][0]["kind"]
        if collection not in MAP_TARGETS.get(kind, set()) or not identity(target) or len(native_index.get(collection, {}).get(target, [])) != 1:
            problem("ambiguous-native-target", key)
            continue
        mappings.append(dict(link))
    lead_names = {}
    for row in native.get("leads", []):
        lead_names.setdefault((name_key(row.get("company")), name_key(row.get("country"))), []).append(row)
    for node in nodes:
        if node["kind"] == "company" and node["key"] not in reviewed:
            candidates = lead_names.get((name_key(node["record"].get("name")), name_key(node["record"].get("country"))), [])
            suggestions.append({"source": node["key"], "candidates": [r["id"] for r in candidates if identity(r.get("id"))],
                                "automaticWriteAllowed": False})
    mapping_by_source = {m["source"]: m for m in mappings}
    conversion_constraints = []
    for node in nodes:
        if node["kind"] == "contact":
            conversion_constraints.append({"source": node["key"], "reasons": ["standalone-contact-requires-lossless-native-model"]})
        if node["kind"] != "quote": continue
        row = node["record"]
        reasons = []
        if row.get("currency") != "USD": reasons.append("legacy-downstream-requires-confirmed-usd")
        review = row.get("completionReview")
        state = review.get("inputState") if isinstance(review, dict) else None
        if not isinstance(state, dict):
            reasons.append("review-memory-missing-preserve-approved-values")
            state = {}
        profile_id = state.get("productId")
        if not isinstance(profile_id, str) or "product-profile:" + profile_id not in mapping_by_source:
            reasons.append("reviewed-offer-mapping-required")
        op_id = row.get("opportunityId")
        op_nodes = by_key.get("opportunity:" + op_id, []) if isinstance(op_id, str) else []
        company_id = op_nodes[0]["record"].get("companyId") if len(op_nodes) == 1 else None
        if ("opportunity:" + str(op_id) not in mapping_by_source and
                "company:" + str(company_id) not in mapping_by_source):
            reasons.append("reviewed-customer-mapping-required")
        workbook = row.get("workbookPricing")
        if isinstance(workbook, dict) and (workbook.get("mode") != "products" or workbook.get("unit") != "kg" or not isinstance(workbook.get("lines"), list) or len(workbook["lines"]) != 1):
            reasons.append("legacy-workbook-not-a-single-kg-item")
        target = mapping_by_source.get(node["key"])
        if target:
            existing = native_index[target["collection"]][target["target"]][0]
            if row.get("currency") != "USD" or existing.get("total_usd") != row.get("total"):
                reasons.append("existing-native-snapshot-differs")
        if reasons: conversion_constraints.append({"source": node["key"], "reasons": reasons})
    plan = {"format": "ibiag-workspace-reconciliation-v1", "sourceSha256": sha(raw),
            "mode": "offline-preservation-plan", "canStageSyntheticArchive": not blockers,
            "businessReady": False, "businessWrites": False, "identityWrites": False,
            "sourceCollections": names, "sourceNodes": len(nodes), "sourceLinks": refs,
            "attachments": sorted(manifest, key=lambda x: x["source"]), "reviewedLinks": mappings,
            "suggestions": suggestions, "blockers": blockers, "conversionConstraints": conversion_constraints,
            "unmappedBusinessRecords": [n["key"] for n in nodes if n["kind"] in MAP_TARGETS and n["key"] not in {m["source"] for m in mappings}],
            "limitations": ["An archive is not an operational migration or approval of old prices.",
                           "Source-only export contains attachment indexes, not PDF bytes.",
                           "No user, role, invitation, paid service or backup setting is imported.",
                           "Filename/transport hashes alone do not prove the source document's authenticity."]}
    plan["planSha256"] = sha(encoded(plan))
    return plan

async def require_synthetic_database(db):
    if not re.fullmatch(r"ibiag_rehearsal_[a-z0-9_]{1,80}", db.name):
        raise ValueError("Only explicitly marked isolated rehearsal databases are accepted")
    control = await db.workspace_rehearsal_control.find_one({"_id": "synthetic-only"})
    if not control or control.get("synthetic") is not True:
        raise ValueError("Synthetic rehearsal marker required; no database was modified")

async def insert_immutable(collection, record):
    from pymongo.errors import DuplicateKeyError
    old = await collection.find_one({"_id": record["_id"]})
    if old:
        if old != record: raise ValueError("Previously staged bytes/manifest differ; nothing was overwritten")
        return
    try: await collection.insert_one(dict(record))
    except DuplicateKeyError:
        old = await collection.find_one({"_id": record["_id"]})
        if old != record: raise ValueError("Concurrent archive differs; nothing was overwritten") from None

async def stage_synthetic_archive(db, raw, files, native=None, links=None):
    await require_synthetic_database(db)
    plan = plan_reconciliation(raw, native, links, files)
    if not plan["canStageSyntheticArchive"]:
        raise ValueError("Resolve all source/attachment/mapping blockers before staging")
    aid = plan["planSha256"]
    from bson import BSON
    contents = [("original-export.json", raw), *sorted(files.items())]
    assets = []
    for key, content in contents:
        token = sha(key.encode())
        parts = [aid + ":" + token + ":" + str(index) for index, offset in enumerate(range(0, len(content), CHUNK))]
        assets.append({"source": key, "size": len(content), "sha256": sha(content), "chunks": parts})
    manifest = {"_id": aid, "format": "ibiag-workspace-rehearsal-v1", "plan": plan, "assets": assets}
    if len(BSON.encode(manifest)) > MAX_MANIFEST:
        raise ValueError("Archive manifest exceeds the bounded rehearsal limit; no chunks were written")
    for asset, (_, content) in zip(assets, contents):
        for index, offset in enumerate(range(0, len(content), CHUNK)):
            part = content[offset:offset + CHUNK]
            await insert_immutable(db.workspace_rehearsal_blobs, {"_id": asset["chunks"][index], "archive": aid, "ordinal": index,
                "size": len(part), "sha256": sha(part), "bytes": part})
    # Publish the manifest only after every chunk can be recovered and verified.
    await verify_assets(db, manifest)
    await insert_immutable(db.workspace_rehearsal_archives, manifest)
    return {"archiveId": aid, "sourceSha256": plan["sourceSha256"], "assets": len(assets), "businessReady": False}

async def verify_assets(db, manifest):
    output = {}
    for asset in manifest["assets"]:
        chunks = []
        for ordinal, cid in enumerate(asset["chunks"]):
            chunk = await db.workspace_rehearsal_blobs.find_one({"_id": cid})
            if not chunk or chunk["archive"] != manifest["_id"] or chunk["ordinal"] != ordinal or chunk["size"] != len(chunk["bytes"]) or sha(chunk["bytes"]) != chunk["sha256"]:
                raise ValueError("Incomplete or altered archive; preserve source and investigate")
            chunks.append(bytes(chunk["bytes"]))
        raw = b"".join(chunks)
        if len(raw) != asset["size"] or sha(raw) != asset["sha256"]:
            raise ValueError("Recovered bytes do not match the archive manifest")
        output[asset["source"]] = raw
    return output

async def recover_synthetic_archive(db, archive_id):
    await require_synthetic_database(db)
    manifest = await db.workspace_rehearsal_archives.find_one({"_id": archive_id})
    if not manifest: raise ValueError("No complete, published archive")
    return await verify_assets(db, manifest)

def read_manifest_files(root, manifest):
    root = Path(root).resolve()
    result = {}
    for key, relative in manifest.items():
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise ValueError("Attachment paths must be relative to the named input directory")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError("Attachment path escapes the named input directory or does not exist")
        if path.stat().st_size > MAX_FILES:
            raise ValueError("Attachment exceeds the package limit")
        result[key] = path.read_bytes()
    return result

def main():
    parser = argparse.ArgumentParser(description="Offline-only plan. No MongoDB connection, imports or writes.")
    parser.add_argument("--backup", required=True)
    parser.add_argument("--native-inventory")
    parser.add_argument("--links")
    parser.add_argument("--files-manifest")
    parser.add_argument("--files-root")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source_path = Path(args.backup)
    if source_path.stat().st_size > MAX_JSON: raise ValueError("Backup too large")
    load = lambda path: unique_json(Path(path).read_bytes()) if path else None
    if bool(args.files_manifest) != bool(args.files_root):
        raise ValueError("Provide both the explicit attachment map and input directory")
    files = read_manifest_files(args.files_root, load(args.files_manifest)) if args.files_manifest else {}
    plan = plan_reconciliation(source_path.read_bytes(), load(args.native_inventory), load(args.links), files)
    with Path(args.output).open("x", encoding="utf-8") as handle:
        json.dump(plan, handle, ensure_ascii=False, indent=2)
    return 0 if plan["canStageSyntheticArchive"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
