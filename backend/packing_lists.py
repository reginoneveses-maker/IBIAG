"""Bounded manual packing groups; exact quantity reconciliation, no prices."""
import json
import uuid
from datetime import date
from decimal import Decimal
from pydantic import Field
from commercial_invoices import StrictInput, TEXT, commercial_snapshot, revision, InvoiceDecision

DECIMAL = r"^(?:|[0-9]{1,13}(?:\.[0-9]{1,12})?)$"
class Allocation(StrictInput):
    index: int = Field(ge=0, le=99)
    quantity: str = Field(default="", max_length=26, pattern=DECIMAL)
class PackageGroup(StrictInput):
    marks: str = Field(default="", max_length=160, pattern=TEXT)
    packaging: str = Field(default="", max_length=100, pattern=TEXT)
    package_count: int = Field(ge=1, le=100000)
    net_kg: str = Field(default="", max_length=26, pattern=DECIMAL)
    gross_kg: str = Field(default="", max_length=26, pattern=DECIMAL)
    volume_m3: str = Field(default="", max_length=26, pattern=DECIMAL)
    allocations: list[Allocation] = Field(min_length=1, max_length=100)
class PackingDetails(StrictInput):
    issue_date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
    seller_name: str = Field(default="", max_length=200, pattern=TEXT)
    seller_address: str = Field(default="", max_length=1000, pattern=TEXT)
    seller_country: str = Field(default="", max_length=100, pattern=TEXT)
    buyer_address: str = Field(default="", max_length=1000, pattern=TEXT)
    buyer_country: str = Field(default="", max_length=100, pattern=TEXT)
    delivery_same_as_buyer: bool = True
    ship_to_name: str = Field(default="", max_length=200, pattern=TEXT)
    ship_to_address: str = Field(default="", max_length=1000, pattern=TEXT)
    ship_to_country: str = Field(default="", max_length=100, pattern=TEXT)
    notes: str = Field(default="", max_length=2000, pattern=TEXT)
    signatory: str = Field(default="", max_length=160, pattern=TEXT)
    packages: list[PackageGroup] = Field(default_factory=list, max_length=100)
    change_note: str = Field(min_length=3, max_length=300, pattern=TEXT)
class PackingCreate(PackingDetails):
    id: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$")
    reference: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9 /_.-]*$")
    order_id: str = Field(min_length=1, max_length=200, pattern=TEXT)
    source_order_version: int = Field(ge=1)
class PackingEdit(PackingDetails):
    version: int = Field(ge=1)
PackingDecision = InvoiceDecision
DETAILS = tuple(k for k in PackingDetails.model_fields if k != "change_note")
SUMMARY = ("id", "reference", "order_id", "version", "status", "issue_date", "customer", "totals", "updated_at")

def packing_snapshot(order):
    # Reuse commercial integrity checks; retain only non-financial public fields.
    sale = commercial_snapshot(order)
    result = {k: sale[k] for k in ("id", "number", "customer", "customer_country", "order_date", "incoterm")}
    result["items"] = [{k: i[k] for k in ("product_name", "unit", "quantity")} for i in sale["items"]]
    return result

def amount(value):
    result = Decimal(value or "0")
    if not result.is_finite() or result < 0 or result > Decimal("1e12"):
        raise ValueError("Quantidade, peso ou cubagem fora dos limites.")
    return result

def validate_details(record, today, approval=False):
    try: issued = date.fromisoformat(record["issue_date"])
    except (TypeError, ValueError): raise ValueError("Informe data de emissão válida.") from None
    snapshot = record["source_order_snapshot"]
    if issued > today or (snapshot.get("order_date") and record["issue_date"] < snapshot["order_date"]):
        raise ValueError("Emissão deve estar entre a data do pedido e hoje.")
    if snapshot.get("customer_country") and record["buyer_country"] != snapshot["customer_country"]:
        raise ValueError("País do comprador deve coincidir com o pedido.")
    quantities = [Decimal(0) for _ in snapshot["items"]]
    marks = set(); net = gross = volume = Decimal(0); count = 0; all_volumes = all_net = all_gross = True
    for group in record["packages"]:
        mark = group["marks"].strip().casefold()
        if mark and mark in marks: raise ValueError("Marcas dos grupos devem ser distintas.")
        if mark: marks.add(mark)
        seen = set()
        for allocation in group["allocations"]:
            index = allocation["index"]
            if index >= len(quantities) or index in seen: raise ValueError("Item inválido ou repetido no grupo.")
            seen.add(index); quantity = amount(allocation["quantity"]); quantities[index] += quantity
            if approval and quantity <= 0: raise ValueError("Informe quantidade positiva em cada alocação.")
        n, g, v = (amount(group[k]) for k in ("net_kg", "gross_kg", "volume_m3"))
        if g < n: raise ValueError("Peso bruto não pode ser menor que o líquido.")
        if group["volume_m3"] and v <= 0: raise ValueError("Cubagem informada deve ser positiva.")
        if approval and (not mark or not group["packaging"].strip() or n <= 0 or g <= 0):
            raise ValueError("Confira marcas, embalagem e pesos positivos de cada grupo.")
        net += n; gross += g; volume += v; count += group["package_count"]
        all_volumes = all_volumes and bool(group["volume_m3"])
        all_net = all_net and bool(group["net_kg"])
        all_gross = all_gross and bool(group["gross_kg"])
    for i, item in enumerate(snapshot["items"]):
        target = Decimal(str(item["quantity"]))
        if quantities[i] > target: raise ValueError("Quantidade embalada excede o pedido.")
        if approval and quantities[i] != target: raise ValueError("A soma embalada de cada item deve corresponder exatamente ao pedido completo.")
    if approval:
        if not record["packages"]: raise ValueError("Informe os volumes antes de aprovar.")
        if any(not record[k].strip() for k in ("seller_name", "seller_address", "seller_country", "buyer_address", "buyer_country", "signatory")):
            raise ValueError("Complete emitente, comprador e responsável antes de aprovar.")
        if not record["delivery_same_as_buyer"] and any(not record[k].strip() for k in ("ship_to_name", "ship_to_address", "ship_to_country")):
            raise ValueError("Complete os dados do destinatário.")
    # Group weights/volume/allocations are group TOTALS, never per-package multipliers.
    record["totals"] = {"package_count": count, "net_kg": format(net,"f") if record["packages"] and all_net else None,
                        "gross_kg": format(gross,"f") if record["packages"] and all_gross else None,
                        "volume_m3": format(volume,"f") if record["packages"] and all_volumes else None}

def packing_event(record, previous, actor, reason, now):
    history = (previous or {}).get("history", [])
    if not isinstance(history, list) or len(history) >= 50: raise ValueError("Histórico exige revisão administrativa.")
    result = dict(record)
    result.update(version=int((previous or {}).get("version") or 0)+1, updated_at=now, created_at=(previous or {}).get("created_at") or now)
    result["history"] = history + [{"id":str(uuid.uuid4()),"at":now,"by":actor["id"],"by_name":str(actor.get("name") or "")[:160],
        "version":result["version"],"note":reason,"changes":{k:result.get(k) for k in (*DETAILS,"status") if result.get(k)!=(previous or {}).get(k)}}]
    if len(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(",", ":")).encode())>256*1024:
        raise OverflowError("Packing List atingiu o limite de tamanho.")
    return result
