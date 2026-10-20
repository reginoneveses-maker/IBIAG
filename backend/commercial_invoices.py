"""Internal commercial invoices: bounded records and public-field-only snapshots."""
import hashlib
import json
import re
import uuid
from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from business_workflow import number, money

TEXT = r"^[^\x00-\x08\x0b-\x1f\x7f]*$"
class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)

class CustomsLine(StrictInput):
    index: int = Field(ge=0, le=99)
    origin_country: str = Field(default="", max_length=100, pattern=TEXT)
    hs_code: str = Field(default="", pattern=r"^(?:[0-9]{6}(?:[0-9]{2}){0,2})?$")

class InvoiceDetails(StrictInput):
    issue_date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    seller_name: str = Field(default="", max_length=200, pattern=TEXT)
    seller_tax_id: str = Field(default="", max_length=80, pattern=TEXT)
    seller_address: str = Field(default="", max_length=1000, pattern=TEXT)
    seller_country: str = Field(default="", max_length=100, pattern=TEXT)
    buyer_address: str = Field(default="", max_length=1000, pattern=TEXT)
    buyer_country: str = Field(default="", max_length=100, pattern=TEXT)
    buyer_tax_id: str = Field(default="", max_length=80, pattern=TEXT)
    delivery_same_as_buyer: bool = True
    ship_to_name: str = Field(default="", max_length=200, pattern=TEXT)
    ship_to_address: str = Field(default="", max_length=1000, pattern=TEXT)
    ship_to_country: str = Field(default="", max_length=100, pattern=TEXT)
    incoterm_place: str = Field(default="", max_length=200, pattern=TEXT)
    payment_terms: str = Field(default="", max_length=1000, pattern=TEXT)
    delivery_terms: str = Field(default="", max_length=1000, pattern=TEXT)
    buyer_reference: str = Field(default="", max_length=120, pattern=TEXT)
    notes: str = Field(default="", max_length=2000, pattern=TEXT)
    declaration: str = Field(default="", max_length=2000, pattern=TEXT)
    signatory: str = Field(default="", max_length=160, pattern=TEXT)
    customs: list[CustomsLine] = Field(min_length=1, max_length=100)
    change_note: str = Field(min_length=3, max_length=300, pattern=TEXT)

class InvoiceCreate(InvoiceDetails):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    reference: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9 /_.-]*$")
    order_id: str = Field(min_length=1, max_length=200, pattern=TEXT)
    source_order_version: int = Field(ge=1)

class InvoiceEdit(InvoiceDetails):
    version: int = Field(ge=1)

class InvoiceDecision(StrictInput):
    version: int = Field(ge=1)
    status: Literal["approved", "cancelled"]
    details_confirmed: bool = False
    change_note: str = Field(min_length=3, max_length=300, pattern=TEXT)

DETAILS = tuple(k for k in InvoiceDetails.model_fields if k != "change_note")
SUMMARY = ("id", "reference", "order_id", "version", "status", "issue_date", "customer", "total_usd", "updated_at")
INCOTERMS = {"EXW", "FOB", "FCA", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"}

def commercial_snapshot(order):
    """An allowlist, never the order/quote/cost/supplier dictionaries themselves."""
    items = []
    for raw in order.get("items", []):
        qty = number(raw.get("quantity"), "Quantidade", True)
        price = number(raw.get("unit_price"), "Preço", True)
        if qty > Decimal("1e12") or price > Decimal("1e12") or qty.as_tuple().exponent < -12 or price.as_tuple().exponent < -12:
            raise ValueError("Revise limites e precisão dos itens antes de emitir a invoice.")
        name, unit = raw.get("product_name"), raw.get("unit")
        if not isinstance(name, str) or not name.strip() or len(name) > 500 or not isinstance(unit, str) or not unit.strip() or len(unit) > 40:
            raise ValueError("Revise descrição e unidade dos itens no pedido.")
        items.append({"product_name": name, "unit": unit, "quantity": float(qty),
                      "unit_price": float(price), "line_total": money(qty*price)})
    if not 1 <= len(items) <= 100:
        raise ValueError("Pedido deve conter de1 a100 itens.")
    total = money(sum((Decimal(str(i["line_total"])) for i in items), Decimal(0)))
    if total > 1e12 or total != money(number(order.get("total_usd"), "Total", True)):
        raise ValueError("Total do pedido não corresponde aos itens. Revise o pedido.")
    if order.get("incoterm") not in INCOTERMS or not isinstance(order.get("customer"), str) or not order["customer"].strip():
        raise ValueError("Revise cliente e Incoterm do pedido.")
    for key, limit in (("id",200),("number",200),("customer",500),("customer_country",100),("order_date",10),("receivable_due_date",10)):
        value = order.get(key, "")
        if not isinstance(value, str) or len(value) > limit or not re.fullmatch(TEXT, value):
            raise ValueError("Revise os dados comerciais do pedido.")
    result = {key: order.get(key, "") for key in ("id", "number", "customer", "customer_country", "order_date", "incoterm", "receivable_due_date")}
    quote = order.get("source_quote_snapshot") or {}
    if not isinstance(quote, dict) or any(not isinstance(quote.get(k,""), str) or len(quote.get(k,""))>1000 or not re.fullmatch(TEXT,quote.get(k,"")) for k in ("payment_terms","delivery_terms")):
        raise ValueError("Revise as condições comerciais da cotação vinculada.")
    result.update(items=items, total_usd=total, currency="USD",
                  payment_terms=quote.get("payment_terms", ""), delivery_terms=quote.get("delivery_terms", ""))
    return result

def revision(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":")).encode()).hexdigest()

def validate_details(record, today, approval=False):
    try: issued = date.fromisoformat(record["issue_date"])
    except (ValueError, TypeError): raise ValueError("Informe data de emissão válida.") from None
    if issued > today: raise ValueError("Data de emissão não pode estar no futuro.")
    snapshot = record["source_order_snapshot"]
    if snapshot.get("order_date") and record["issue_date"] < snapshot["order_date"]:
        raise ValueError("Emissão não pode anteceder a data do pedido.")
    lines = record["customs"]
    if len(lines) != len(snapshot["items"]) or [line["index"] for line in lines] != list(range(len(lines))):
        raise ValueError("Informe os dados aduaneiros de cada item, na ordem do pedido.")
    country = snapshot.get("customer_country")
    if country and record["buyer_country"] != country:
        raise ValueError("País do comprador deve coincidir com o pedido.")
    if approval:
        required = ("seller_name", "seller_tax_id", "seller_address", "seller_country", "buyer_address", "buyer_country",
                    "incoterm_place", "payment_terms", "delivery_terms", "signatory")
        if any(not record[k].strip() for k in required):
            raise ValueError("Complete emitente, comprador, local do Incoterm, condições e responsável antes de aprovar.")
        if not record["delivery_same_as_buyer"] and any(not record[k].strip() for k in ("ship_to_name", "ship_to_address", "ship_to_country")):
            raise ValueError("Complete nome, endereço e país do destinatário.")
        if any(not line["origin_country"] or not line["hs_code"] for line in lines):
            raise ValueError("Confira país de origem e classificação HS/NCM de todos os itens.")

def invoice_event(record, previous, actor, reason, now):
    history = (previous or {}).get("history", [])
    if not isinstance(history, list) or len(history) >= 50:
        raise ValueError("Histórico da invoice exige revisão administrativa.")
    result = dict(record)
    result.update(version=int((previous or {}).get("version") or 0)+1, updated_at=now,
                  created_at=(previous or {}).get("created_at") or now)
    changes = {k: result.get(k) for k in (*DETAILS, "status") if result.get(k) != (previous or {}).get(k)}
    result["history"] = history + [{"id": str(uuid.uuid4()), "at": now, "by": actor["id"],
                                  "by_name": str(actor.get("name") or "")[:160], "version": result["version"],
                                  "note": reason, "changes": changes}]
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()) > 256*1024:
        raise OverflowError("Invoice atingiu o limite de tamanho. Solicite revisão administrativa.")
    return result
