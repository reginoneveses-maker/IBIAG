"""Native IBIAG session and MongoDB records; reusable Claude quotation engine.
No migration, scheduled backup or external provider is invoked.
"""
import asyncio
import hashlib
import json
import math
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError

ENGINE = Path(__file__).parent / "generated" / "quote-engine.cjs"
slots = asyncio.Semaphore(4)

class DraftSave(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    draft: dict
    expectedUpdatedAt: str | None
    requestId: str = Field(pattern=r"^[0-9a-f-]{36}$")

class QuoteSave(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    state: dict

class Handoff(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    valid_until: str
    payment_terms: str
    delivery_terms: str
    change_note: str

class ProfileSave(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    patch: dict[str, str]
    source: dict[str, str]
    confirmed: bool

def bounded(value):
    try:
        raw = json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError):
        raise HTTPException(400, "Estrutura inválida.") from None
    if len(raw.encode()) > 200000:
        raise HTTPException(413, "Cotação muito grande.")
    return raw

async def engine(kind, data):
    raw = bounded({"kind": kind, "data": data})
    async with slots:
        try:
            proc = await asyncio.create_subprocess_exec(
                os.environ.get("IBIAG_NODE_EXECUTABLE", "node"), str(ENGINE),
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        except OSError:
            raise HTTPException(503, "Motor comercial indisponível. Seu preenchimento foi preservado.") from None
        try:
            output, _ = await asyncio.wait_for(proc.communicate(raw.encode()), timeout=10)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            proc.kill()
            await proc.wait()
            raise HTTPException(503, "Motor comercial indisponível. Salve o rascunho antes de tentar novamente.") from None
    try:
        result = json.loads(output) if len(output) < 1000000 else {}
    except (ValueError, TypeError):
        result = {}
    if not result.get("ok") or proc.returncode:
        raise HTTPException(400, "Revise os campos essenciais e confirme os valores da cotação.")
    return result["data"]

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()

def profile_for(offer, product, supplier):
    # Descriptive text is never parsed into invented numeric package dimensions.
    saved = offer.get("ibiag_quote_profile") or {}
    identity = offer.get("ibiag_quote_profile_identity")
    if identity and identity != {"productId": product["id"], "supplierId": supplier["id"], "unit": "kg"}:
        saved = {}
    result = {k: v for k, v in saved.items() if isinstance(v, str)}
    result.update(id=offer["id"], supplier=supplier["name"], origin=product.get("origin", ""))
    price = offer.get("supplier_price")
    if isinstance(price, (int, float)) and price > 0:
        result.update(cost=str(price), priceCurrency="BRL", priceRate="1")
    elif result.get("cost") != "0":
        result.pop("cost", None)
    if product.get("payment_terms") and not result.get("paymentTerms"):
        result["paymentTerms"] = product["payment_terms"]
    result["nativeRevision"] = digest({"offer": offer, "product": product, "supplier": supplier})
    return result

def install(api, rt):
    admin = rt.get_commercial_user
    async def unique(collection, rid):
        matches = await collection.find({"id": rid}, {"_id": 0}).limit(2).to_list(2)
        if len(matches) != 1:
            raise HTTPException(409, "Referência ausente ou duplicada. Revise o cadastro sem excluir registros.")
        return matches[0]

    async def references(offer_id):
        offer = await unique(rt.db.product_offers, offer_id)
        product = await unique(rt.db.products, offer.get("product_id"))
        supplier = await unique(rt.db.suppliers, offer.get("supplier_id"))
        if offer.get("active", True) is not True:
            raise HTTPException(409, "Oferta inativa. Selecione outra oferta.")
        if (offer.get("unit") or product.get("unit") or "kg") != "kg":
            raise HTTPException(400, "Este precificador usa kg. Utilize o módulo de preços para outra unidade.")
        return offer, product, supplier

    @api.get("/integrated/operators")
    async def operators(user=Depends(admin)):
        rows = await rt.db.users.find({"active": {"$ne": False}}, {"_id": 0, "id": 1, "name": 1, "role": 1}).limit(250).to_list(250)
        return rows

    @api.get("/integrated/catalog")
    async def catalog(response: Response, q: str = Query("", max_length=160), user=Depends(admin)):
        response.headers["Cache-Control"] = "private, no-store"
        query = {"active": {"$ne": False}}
        if q.strip():
            query["$or"] = [{"product_name": {"$regex": re.escape(q.strip()), "$options": "i"}},
                            {"supplier_name": {"$regex": re.escape(q.strip()), "$options": "i"}}]
        offers = await rt.db.product_offers.find(query, {"_id": 0}).sort("id", 1).limit(101).to_list(101)
        suppliers = await rt.db.suppliers.find({"id": {"$in": [o.get("supplier_id") for o in offers]}}, {"_id": 0}).to_list(1000)
        products = await rt.db.products.find({"id": {"$in": [o.get("product_id") for o in offers]}}, {"_id": 0}).to_list(1000)
        output, issues = [], []
        for o in offers[:100]:
            ps = [p for p in products if p.get("id") == o.get("product_id")]
            ss = [s for s in suppliers if s.get("id") == o.get("supplier_id")]
            if len(ps) != 1 or len(ss) != 1 or sum(x.get("id") == o.get("id") for x in offers) != 1:
                issues.append("Referência ausente ou duplicada: " + str(o.get("id", "")))
                continue
            if (o.get("unit") or ps[0].get("unit") or "kg") != "kg":
                issues.append("Oferta em outra unidade: " + o["id"])
                continue
            output.append({"id": o["id"], "name": ps[0]["name"], "productId": ps[0]["id"],
                           "supplierId": ss[0]["id"], "supplier": ss[0]["name"],
                           "profile": profile_for(o, ps[0], ss[0]),
                           "documentIds": list(dict.fromkeys(o.get("spec_document_ids", []) + o.get("certificate_document_ids", []) + o.get("other_document_ids", [])))})
        return {"offers": output, "hasMore": len(offers) > 100, "issues": issues}

    @api.get("/integrated/customers")
    async def customers(response: Response, q: str = Query("", max_length=160), user=Depends(admin)):
        response.headers["Cache-Control"] = "private, no-store"
        query = {"company": {"$regex": re.escape(q.strip()), "$options": "i"}} if q.strip() else {}
        rows = await rt.db.leads.find(query, {"_id": 0, "id": 1, "company": 1, "country": 1,
             "contact_name": 1, "email": 1, "phone": 1}).sort("company", 1).limit(101).to_list(101)
        return {"customers": rows[:100], "hasMore": len(rows) > 100}

    @api.get("/integrated/workspace")
    async def workspace(response: Response, user=Depends(admin)):
        response.headers["Cache-Control"] = "private, no-store"
        drafts = await rt.db.integrated_quote_drafts.find({"owner_id": user["id"]}, {"_id": 0, "draft": 1}).sort("updated_at", -1).limit(100).to_list(100)
        quotes = await rt.db.integrated_quotes.find({"owner_id": user["id"]}, {"_id": 0, "quote": 1}).sort("created_at", -1).limit(100).to_list(100)
        return {"drafts": [r["draft"] for r in drafts], "quotes": [r["quote"] for r in quotes]}

    @api.put("/integrated/drafts/{did}")
    async def save_draft(did: str, body: DraftSave, user=Depends(admin)):
        if body.draft.get("id") != did:
            raise HTTPException(400, "Identificador divergente.")
        draft = await engine("draft", body.draft)
        key = user["id"] + ":" + did
        fingerprint = digest({"title": draft["title"], "kind": draft["kind"], "data": draft["data"]})
        async with rt.business_write_lock() as ensure_owned:
            old = await rt.db.integrated_quote_drafts.find_one({"_id": key})
            if old and old.get("token") == body.requestId:
                if old.get("fingerprint") != fingerprint:
                    raise HTTPException(409, "Pedido repetido com conteúdo diferente.")
                return {"draft": old["draft"], "alreadySaved": True}
            if (old["draft"]["updatedAt"] if old else None) != body.expectedUpdatedAt:
                raise HTTPException(409, "Rascunho alterado em outra janela. Salve uma cópia ou retome a versão atual.")
            now = rt.now_iso().replace("+00:00", "Z")
            if old and now <= old["draft"]["updatedAt"]:
                now = (datetime.fromisoformat(old["draft"]["updatedAt"]) + timedelta(microseconds=1)).isoformat().replace("+00:00", "Z")
            draft.update(updatedAt=now, writeToken=body.requestId)
            record = {"_id": key, "owner_id": user["id"], "draft": draft, "token": body.requestId,
                      "fingerprint": fingerprint, "updated_at": now}
            await ensure_owned()
            if old:
                result = await rt.db.integrated_quote_drafts.replace_one({"_id": key, "updated_at": old["updated_at"]}, record)
                if not result.matched_count:
                    raise HTTPException(409, "Rascunho alterado.")
            else:
                if await rt.db.integrated_quote_drafts.count_documents({"owner_id": user["id"]}) >= 100:
                    raise HTTPException(409, "Limite de rascunhos atingido. Solicite revisão, sem apagar registros.")
                try: await rt.db.integrated_quote_drafts.insert_one(record)
                except DuplicateKeyError: raise HTTPException(409, "Rascunho alterado.") from None
            return {"draft": draft, "alreadySaved": False}

    @api.post("/integrated/quotes")
    async def save_quote(body: QuoteSave, user=Depends(admin)):
        quote = await engine("quote", body.state)
        quote["id"] = body.id
        offer_id = body.state.get("productId", "")
        lead_id = quote.get("opportunityId", "")
        refs = {}
        if offer_id:
            offer, product, supplier = await references(offer_id)
            refs.update(offer_id=offer_id, product_id=product["id"], supplier_id=supplier["id"])
        if lead_id:
            lead = await unique(rt.db.leads, lead_id)
            if quote["customer"] != lead["company"]:
                raise HTTPException(409, "Nome do cliente diverge do vínculo CRM. Revise ou selecione sem vínculo.")
        key = user["id"] + ":" + body.id
        fingerprint = digest(body.state)
        record = {"_id": key, "id": body.id, "owner_id": user["id"], "quote": quote,
                  "fingerprint": fingerprint, "lead_id": lead_id, **refs, "created_at": rt.now_iso()}
        old = await rt.db.integrated_quotes.find_one({"_id": key})
        if old:
            if old["fingerprint"] != fingerprint: raise HTTPException(409, "Cotação revisada é imutável. Crie outra versão.")
            return {"quote": old["quote"], "alreadySaved": True}
        try: await rt.db.integrated_quotes.insert_one(record)
        except DuplicateKeyError:
            old = await rt.db.integrated_quotes.find_one({"_id": key})
            if not old or old["fingerprint"] != fingerprint: raise HTTPException(409, "Cotação revisada é imutável.") from None
            return {"quote": old["quote"], "alreadySaved": True}
        return {"quote": quote, "alreadySaved": False}

    @api.put("/integrated/offers/{oid}/profile")
    async def update_profile(oid: str, body: ProfileSave, user=Depends(admin)):
        bounded(body.model_dump())
        if not body.confirmed:
            raise HTTPException(400, "Confirmação explícita obrigatória.")
        allowed = {"supplier", "cost", "priceCurrency", "priceRate", "priceValidUntil", "moqKg", "leadDays", "logistics"}
        if set(body.patch) - allowed or any(len(v) > 40000 for v in body.patch.values()):
            raise HTTPException(400, "Campos não permitidos.")
        async with rt.business_write_lock() as ensure_owned:
            offer, product, supplier = await references(oid)
            current = profile_for(offer, product, supplier)
            if body.source.get("nativeRevision") != current["nativeRevision"]:
                raise HTTPException(409, "Cadastro alterado. Recarregue antes de confirmar; a cotação foi preservada.")
            if body.patch.get("supplier", supplier["name"]) != supplier["name"]:
                raise HTTPException(400, "Selecione outra oferta para trocar o fornecedor vinculado.")
            for k in ("cost", "priceRate", "moqKg", "leadDays"):
                if k in body.patch:
                    try:
                        n = rt.decimal_number(body.patch[k])
                        if not math.isfinite(float(n)) or n < 0 or k == "priceRate" and n <= 0: raise ValueError()
                    except (ValueError, ArithmeticError):
                        raise HTTPException(400, "Valor cadastral inválido.") from None
            if body.patch.get("priceCurrency", "BRL") != "BRL" or body.patch.get("priceRate", "1") != "1":
                raise HTTPException(400, "Preço confirmado nesta ficha é BRL/kg.")
            saved = {**(offer.get("ibiag_quote_profile") or {}), **body.patch}
            now = rt.now_iso()
            await ensure_owned()
            query = {"id": oid, "updated_at": offer["updated_at"]} if "updated_at" in offer else {"id": oid, "updated_at": {"$exists": False}}
            updates = {"ibiag_quote_profile": saved, "ibiag_quote_profile_identity": {"productId": product["id"], "supplierId": supplier["id"], "unit": "kg"}, "ibiag_quote_profile_review": {"by": user["id"], "at": now, "fields": sorted(body.patch), "previousPrice": offer.get("supplier_price"), "previousProfile": offer.get("ibiag_quote_profile", {})}, "updated_at": now}
            if "cost" in body.patch:
                updates["supplier_price"] = float(rt.decimal_number(body.patch["cost"]))
            result = await rt.db.product_offers.update_one(query, {"$set": updates})
            if not result.matched_count: raise HTTPException(409, "Oferta alterada.")
            return {"saved": True}

    @api.post("/integrated/quotes/{qid}/handoff")
    async def handoff(qid: str, body: Handoff, user=Depends(admin)):
        async with rt.business_write_lock() as ensure_owned:
            record = await rt.db.integrated_quotes.find_one({"_id": user["id"] + ":" + qid})
            if not record: raise HTTPException(404, "Cotação não encontrada.")
            q = record["quote"]
            if q["currency"] != "USD":
                raise HTTPException(400, "O pedido legado exige USD. Gere outra cotação em USD com câmbio confirmado; valores salvos não serão convertidos automaticamente.")
            if not record.get("offer_id") or not record.get("lead_id"):
                raise HTTPException(400, "Vincule cliente e oferta em uma nova cotação antes de preparar o pedido.")
            offer, product, supplier = await references(record["offer_id"])
            lead = await unique(rt.db.leads, record["lead_id"])
            if q["supplier"] != supplier["name"]:
                raise HTTPException(409, "Fornecedor da proposta diverge da oferta. Revise o vínculo antes de criar o pedido.")
            if offer.get("product_id") != record["product_id"] or offer.get("supplier_id") != record["supplier_id"]:
                raise HTTPException(409, "Oferta mudou de vínculo. Revise antes de continuar.")
            values = body.model_dump()
            try:
                terms = rt.QuotationEdit(version=1, incoterm=q["incoterm"], notes="", **values).model_dump(exclude={"version", "change_note"})
            except Exception:
                raise HTTPException(400, "Revise validade, pagamento e condições de entrega.") from None
            rt.check_quotation_terms(terms)
            native_id = "IQ-" + hashlib.sha256((user["id"] + ":" + qid).encode()).hexdigest()[:40]
            old = await rt.db.quotations.find_one({"id": native_id}, {"_id": 0})
            if old:
                if old.get("source_integrated_quote_id") != qid or old.get("source_integrated_owner") != user["id"]:
                    raise HTTPException(409, "Identificador comercial ambíguo.")
                if any(old.get(key) != value for key, value in terms.items()):
                    raise HTTPException(409, "A cotação já foi preparada com condições diferentes. Abra a cotação existente para revisar.")
                return await rt.quotation_view(old)
            item = {"product_id": product["id"], "offer_id": offer["id"], "supplier_id": supplier["id"],
                    "product_name": q["product"], "supplier_name": q["supplier"], "quantity": q["quantity"],
                    "unit": "kg", "unit_price": q["unitPrice"]}
            native = {**terms, "id": native_id, "reference": native_id, "lead_id": lead["id"],
                      "customer": q["customer"], "customer_country": lead.get("country", ""), "items": [item],
                      "total_usd": q["total"], "status": "draft", "source_integrated_quote_id": qid,
                      "source_integrated_owner": user["id"], "source_integrated_snapshot": q}
            result = rt.checked_quote_event(native, None, user, body.change_note)
            await ensure_owned()
            await rt.db.quotations.insert_one(dict(result))
            return await rt.quotation_view(result)
