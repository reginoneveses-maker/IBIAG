"""Bounded internal quotation records. No document sending or external acceptance."""
import json
import uuid
from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class QuotationTerms(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    valid_until: str = Field(min_length=10, max_length=10, pattern=r"^\d{4}-\d{2}-\d{2}$")
    incoterm: Literal["EXW", "FOB", "FCA", "CFR", "CIF", "CPT", "CIP", "DAP", "DPU", "DDP"]
    payment_terms: str = Field(min_length=3, max_length=1000, pattern=r"^[^\x00]*$")
    delivery_terms: str = Field(min_length=3, max_length=1000, pattern=r"^[^\x00]*$")
    notes: str = Field(default="", max_length=2000, pattern=r"^[^\x00]*$")
    change_note: str = Field(min_length=3, max_length=300, pattern=r"^[^\x00]*$")

class QuotationCreate(QuotationTerms):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    reference: str = Field(min_length=1, max_length=80, pattern=r"^[^\x00]*$")
    lead_id: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00]*$")
    source_price_id: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00]*$")
    source_price_revision: str = Field(pattern=r"^[0-9a-f]{64}$")

class QuotationEdit(QuotationTerms):
    version: int = Field(ge=1)

class QuotationState(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)
    version: int = Field(ge=1)
    status: Literal["approved", "cancelled"]
    change_note: str = Field(min_length=3, max_length=300, pattern=r"^[^\x00]*$")

TERMS = ("valid_until", "incoterm", "payment_terms", "delivery_terms", "notes")
SUMMARY = ("id", "reference", "version", "status", "customer", "customer_country", "lead_id",
           "valid_until", "incoterm", "total_usd", "total_amount", "currency", "updated_at")

def validate_terms(record, today):
    try:
        until = date.fromisoformat(record["valid_until"])
    except (TypeError, ValueError):
        raise ValueError("Informe uma data de validade válida.") from None
    if until < today:
        raise ValueError("A validade da cotação não pode estar no passado.")

def quotation_event(record, previous, actor, note, now):
    history = (previous or {}).get("history", [])
    if not isinstance(history, list) or len(history) >= 50:
        raise ValueError("Histórico da cotação exige revisão administrativa.")
    result = dict(record)
    version = int((previous or {}).get("version") or 0) + 1
    result.update(version=version, updated_at=now, created_at=(previous or {}).get("created_at") or now)
    changed = {key: result.get(key) for key in (*TERMS, "status") if result.get(key) != (previous or {}).get(key)}
    result["history"] = history + [{"id": str(uuid.uuid4()), "at": now, "by": actor["id"],
        "by_name": str(actor.get("name") or "")[:160], "version": version,
        "note": note, "changes": changed}]
    if len(json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode()) > 256*1024:
        raise OverflowError("Cotação atingiu o limite de tamanho. Solicite revisão administrativa.")
    return result
