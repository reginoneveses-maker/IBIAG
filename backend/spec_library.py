"""Read-only supplier spec view over existing specs, documents and offer links."""
import re
import unicodedata


def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in unicodedata.normalize("NFKD", str(value or "")).casefold() if not unicodedata.combining(c))).strip()


def is_spec_document(doc):
    kind = normalized(doc.get("document_type"))
    if kind:
        return kind in {"ficha tecnica", "ficha tecnica original", "ficha tecnica spec", "especificacao tecnica", "spec original", "spec fornecedor", "spec ibiag", "spec", "specs", "specification", "technical data sheet", "technical specification"}
    text = normalized(" ".join(str(doc.get(k) or "") for k in ("title", "file_name")))
    return bool(re.search(r"\b(?:specs?|specification|specifications|ficha tecnica|technical data sheet|technical specification)\b", text))


async def supplier_spec_library(db):
    suppliers = {s["id"]: s async for s in db.suppliers.find({}, {"_id": 0})}
    names = {}
    for supplier in suppliers.values():
        names.setdefault(normalized(supplier["name"]), []).append(supplier["id"])
    offer_links = {}
    async for offer in db.product_offers.find({"deleted_at": {"$in": [None, ""]}}, {"_id": 0}):
        if offer.get("supplier_id") in suppliers:
            for doc_id in offer.get("spec_document_ids") or []:
                offer_links.setdefault(doc_id, []).append(offer)

    def resolve(record, links=()):
        sid = record.get("supplier_id")
        if sid in suppliers:
            return sid, "supplier_id"
        matching = names.get(normalized(record.get("supplier_name")), [])
        if len(matching) == 1:
            return matching[0], "supplier_name"
        if len(matching) > 1:
            return "", "Nome de fornecedor ambíguo."
        linked = {x["supplier_id"] for x in links}
        if len(linked) == 1:
            return next(iter(linked)), "product_offer"
        return "", "Ofertas vinculadas a fornecedores diferentes." if linked else "Fornecedor não identificado."

    items, unassigned, seen_paths = [], [], set()
    async for spec in db.specs.find({"deleted_at": {"$in": [None, ""]}}, {"_id": 0}):
        sid, reason = resolve(spec)
        row = {**spec, "source_type": "spec", "supplier_id": sid, "supplier_name": suppliers[sid]["name"] if sid else spec.get("supplier_name", "")}
        if sid:
            items.append(row)
            for slot in ("original", "ibiag"):
                if spec.get(slot + "_file_path"):
                    seen_paths.add((sid, spec[slot + "_file_path"]))
        else:
            unassigned.append({**row, "assignment_reason": reason})
    async for doc in db.documents.find({"deleted_at": {"$in": [None, ""]}}, {"_id": 0}):
        links = offer_links.get(doc["id"], [])
        if not is_spec_document(doc) and not links:
            continue
        sid, reason = resolve(doc, links)
        if sid and doc.get("file_path") and (sid, doc["file_path"]) in seen_paths:
            continue
        product = doc.get("product_name") or next((x.get("product_name") for x in links if x.get("supplier_id") == sid and x.get("product_name")), "")
        row = {"id": "document:" + doc["id"], "document_id": doc["id"], "source_type": "document", "supplier_id": sid,
               "supplier_name": suppliers[sid]["name"] if sid else doc.get("supplier_name", ""),
               "product_name": product or doc.get("title") or doc.get("file_name"), "title": doc.get("title", ""),
               "code": "", "version": "", "description": doc.get("notes", ""),
               "original_file_path": doc.get("file_path", ""), "original_file_name": doc.get("file_name", ""),
               "ibiag_file_path": "", "ibiag_file_name": "", "assignment_reason": "" if sid else reason,
               "assignment_source": reason if sid else "", "created_at": doc.get("created_at", "")}
        (items if sid else unassigned).append(row)
        if sid and doc.get("file_path"):
            seen_paths.add((sid, doc["file_path"]))
    counts = {sid: 0 for sid in suppliers}
    for row in items:
        counts[row["supplier_id"]] += 1
    key = lambda row: (normalized(row.get("supplier_name")), normalized(row.get("product_name")), row["id"])
    return {"items": sorted(items, key=key), "unassigned": sorted(unassigned, key=key), "counts": counts,
            "total": len(items), "unassigned_total": len(unassigned)}
