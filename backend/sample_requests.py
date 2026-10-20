"""Sample requests: one product per request, no automatic stock or finance writes."""
import copy
import json
import re
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

STATES = ("requested", "preparing", "sent", "delivered", "evaluated", "cancelled")
TRANSITIONS = {
    "requested": ("preparing", "cancelled"), "preparing": ("sent", "cancelled"),
    "sent": ("delivered",), "delivered": ("evaluated",),
    "evaluated": (), "cancelled": (),
}
TERMS = ("quantity", "unit", "lot", "packaging", "recipient", "address", "destination_country",
         "delivery_method", "carrier", "tracking_code", "expected_delivery", "follow_up_on",
         "cost_amount", "cost_currency", "notes")
IDENTITY = ("id", "reference", "lead_id", "customer", "customer_country", "product_id", "product_name",
            "catalog_unit", "offer_id", "supplier_id", "supplier_name", "requested_on")
RESULT = ("status", "sent_on", "delivered_on", "evaluated_on", "feedback_result", "feedback")
SUMMARY = ("id", "reference", "lead_id", "customer", "product_name", "quantity", "unit",
           "status", "requested_on", "expected_delivery", "follow_up_on", "version")
FROZEN_AFTER_SEND = ("quantity", "unit", "lot", "packaging", "recipient", "address",
                     "destination_country", "delivery_method")
NUMBER = re.compile(r"^[0-9]{1,13}(?:\.[0-9]{1,12})?$")


class SampleData(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    quantity: str = Field(min_length=1, max_length=26)
    unit: Literal["g", "kg", "mL", "L", "unit"] = "g"
    lot: str = Field(default="", max_length=120)
    packaging: str = Field(default="", max_length=300)
    recipient: str = Field(default="", max_length=200)
    address: str = Field(default="", max_length=1500)
    destination_country: str = Field(default="", max_length=100)
    delivery_method: Literal["courier", "postal", "hand", "air", "sea", "road"] = "courier"
    carrier: str = Field(default="", max_length=200)
    tracking_code: str = Field(default="", max_length=200)
    expected_delivery: str = Field(default="", max_length=10)
    follow_up_on: str = Field(default="", max_length=10)
    cost_amount: str = Field(default="", max_length=26)
    cost_currency: Literal["USD", "BRL", "EUR"] = "USD"
    notes: str = Field(default="", max_length=3000)

    @field_validator("*")
    @classmethod
    def clean_text(cls, value):
        if isinstance(value, str):
            if any(ord(c)<32 and c not in "\n\r\t" for c in value) or "\x7f" in value:
                raise ValueError("Texto com caractere de controle.")
            return value.strip()
        return value

    @field_validator("quantity", "cost_amount")
    @classmethod
    def decimal_text(cls, value, info):
        if value=="" and info.field_name=="cost_amount": return value
        if not NUMBER.fullmatch(value): raise ValueError("Informe decimal positivo com ponto, sem expoente.")
        amount=Decimal(value)
        if amount>Decimal("1000000000000") or (amount<=0 if info.field_name=="quantity" else amount<0):
            raise ValueError("Quantidade ou custo fora do limite.")
        return format(amount, "f")


class SampleCreate(SampleData):
    id: str = Field(min_length=36, max_length=36, pattern=r"^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$")
    reference: str = Field(min_length=1, max_length=100, pattern=r"^[^\x00-\x1f\x7f]+$")
    lead_id: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$")
    product_id: str = Field(min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$")
    offer_id: str = Field(default="", max_length=200, pattern=r"^[^\x00-\x1f\x7f]*$")
    requested_on: str = Field(min_length=10, max_length=10)
    change_note: str = Field(min_length=3, max_length=300)

    @field_validator("reference", "lead_id", "product_id", "change_note")
    @classmethod
    def not_blank(cls, value, info):
        if len(value.strip()) < (3 if info.field_name=="change_note" else 1):
            raise ValueError("Campo obrigatório.")
        return value.strip()


class SampleEdit(SampleData):
    version: int = Field(ge=1)
    change_note: str = Field(min_length=3, max_length=300)

    @field_validator("change_note")
    @classmethod
    def reason(cls, value):
        if len(value.strip())<3: raise ValueError("Informe o motivo.")
        return value.strip()


class SampleDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    version: int = Field(ge=1)
    status: Literal["preparing", "sent", "delivered", "evaluated", "cancelled"]
    occurred_on: str = Field(default="", max_length=10)
    feedback_result: Literal["", "approved", "rejected", "retest"] = ""
    feedback: str = Field(default="", max_length=3000)
    change_note: str = Field(min_length=3, max_length=300)

    @field_validator("feedback", "change_note")
    @classmethod
    def text(cls, value, info):
        if any(ord(c)<32 and c not in "\n\r\t" for c in value) or "\x7f" in value:
            raise ValueError("Texto com caractere de controle.")
        if info.field_name=="change_note" and len(value.strip())<3: raise ValueError("Informe o motivo.")
        return value.strip()


def calendar(value):
    if not isinstance(value,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",value):
        raise ValueError("Informe data no formato AAAA-MM-DD.")
    return date.fromisoformat(value)


def validate_sample(record, today):
    requested=calendar(record["requested_on"])
    if requested>today: raise ValueError("A solicitação não pode estar no futuro.")
    for key in ("expected_delivery", "follow_up_on"):
        if record.get(key) and calendar(record[key])<requested:
            raise ValueError("A previsão não pode anteceder a solicitação.")
    previous=requested
    for key in ("sent_on", "delivered_on", "evaluated_on"):
        if record.get(key):
            current=calendar(record[key])
            if current<previous or current>today: raise ValueError("Datas reais devem ser cronológicas e não futuras.")
            previous=current
    if record["status"] in {"sent","delivered","evaluated"}:
        if not record.get("sent_on") or any(not record.get(k) for k in ("recipient","address","destination_country","packaging")):
            raise ValueError("Antes do envio, confira destinatário, endereço, país, embalagem e data real.")
        if record["delivery_method"]!="hand" and not record.get("carrier"):
            raise ValueError("Informe a transportadora ou selecione entrega em mãos.")
    if record["status"] in {"delivered","evaluated"} and not record.get("delivered_on"):
        raise ValueError("Informe a data real da entrega.")
    if record["status"]=="evaluated" and (not record.get("evaluated_on") or not record.get("feedback_result") or not record.get("feedback")):
        raise ValueError("Informe data, resultado e retorno do comprador.")
    if record.get("expected_delivery") and record.get("sent_on") and calendar(record["expected_delivery"])<calendar(record["sent_on"]):
        raise ValueError("A chegada prevista não pode anteceder o envio real.")


def transition(previous, body):
    if body.status not in TRANSITIONS.get(previous["status"], ()):
        raise ValueError("Transição de amostra não permitida.")
    result=dict(previous)
    if body.status in {"sent","delivered","evaluated"}:
        key={"sent":"sent_on","delivered":"delivered_on","evaluated":"evaluated_on"}[body.status]
        if not body.occurred_on: raise ValueError("Informe a data real desta etapa.")
        result[key]=body.occurred_on
    elif body.occurred_on:
        raise ValueError("Esta etapa não recebe data real.")
    if body.status=="evaluated":
        result.update(feedback_result=body.feedback_result,feedback=body.feedback)
    elif body.feedback_result or body.feedback:
        raise ValueError("Retorno do comprador pertence à etapa de avaliação.")
    result["status"]=body.status
    return result


def sample_event(record, previous, actor, note, stamp):
    result=copy.deepcopy(record)
    version=(previous["version"] if previous else 0)+1
    fields=TERMS+IDENTITY+RESULT
    changes={key:record.get(key,"") for key in fields if not previous or record.get(key,"")!=previous.get(key,"")}
    result.update(version=version,updated_at=stamp)
    result.setdefault("created_at",stamp)
    events=copy.deepcopy((previous or {}).get("history",[]))
    events.append({"id":str(uuid.uuid4()),"at":stamp,"by":actor["id"],
                   "by_name":str(actor.get("name") or actor.get("email") or actor["id"])[:160],
                   "note":note,"version":version,"changes":changes})
    result["history"]=events
    if len(events)>100 or len(json.dumps(result,ensure_ascii=False).encode())>256*1024:
        raise OverflowError("Amostra excede o limite de tamanho; nenhuma revisão foi descartada.")
    return result
