"""One complete shipment per order. No database, provider or second ledger."""
import json
import re
import uuid
from datetime import date

STATUSES = ("planned", "booked", "in_transit", "arrived", "delivered", "cancelled")
TRANSITIONS = {"planned": ("planned", "booked", "cancelled"),
               "booked": ("booked", "planned", "in_transit", "cancelled"),
               "in_transit": ("in_transit", "arrived", "delivered"),
               "arrived": ("arrived", "delivered"), "delivered": ("delivered",),
               "cancelled": ("cancelled", "planned")}
SUMMARY_FIELDS = ("reference", "status", "origin", "destination", "mode", "responsible_name",
                  "planned_departure", "planned_arrival", "actual_departure", "actual_arrival",
                  "actual_delivery", "updated_at")
MAX_EVENTS = 100
MAX_BYTES = 256 * 1024


def allowed_statuses(order):
    if order.get("deleted_at") or order.get("workflow_enabled") is not True:
        return []
    previous = order.get("shipment") or {}
    state = order.get("status")
    if not previous:
        return list({"confirmed": ("planned",), "shipped": ("in_transit", "arrived", "delivered"),
                     "delivered": ("delivered",)}.get(state, ()))
    if state not in {"confirmed", "shipped", "delivered"}:
        return []
    return list(TRANSITIONS.get(previous.get("status"), ()))


def build_shipment(order, values, actor, responsible, note, now, today):
    previous = order.get("shipment") or {}
    if values["status"] not in allowed_statuses(order):
        raise ValueError("Transição logística não permitida para este pedido.")
    if not responsible or responsible.get("active", True) is not True or responsible.get("role", "user") not in {"admin", "user"}:
        raise ValueError("Selecione um responsável ativo.")
    result = dict(values)
    dates = {}
    for key in ("planned_departure", "planned_arrival", "actual_departure", "actual_arrival", "actual_delivery"):
        text = result.get(key, "")
        if not text:
            dates[key] = None
            continue
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
                raise ValueError()
            dates[key] = date.fromisoformat(text)
        except (TypeError, ValueError):
            raise ValueError("Informe datas válidas no formato AAAA-MM-DD.") from None
        if key.startswith("actual_") and dates[key] > today:
            raise ValueError("Datas reais não podem estar no futuro.")
    if not dates["planned_departure"] or not dates["planned_arrival"]:
        raise ValueError("Informe saída e chegada previstas.")
    if dates["planned_arrival"] < dates["planned_departure"]:
        raise ValueError("Chegada prevista não pode anteceder a saída prevista.")
    state = result["status"]
    if state in {"in_transit", "arrived", "delivered"} and not dates["actual_departure"]:
        raise ValueError("Informe a saída real para registrar trânsito.")
    if state in {"arrived", "delivered"} and not dates["actual_arrival"]:
        raise ValueError("Informe a chegada real.")
    if state == "delivered" and not dates["actual_delivery"]:
        raise ValueError("Informe a entrega real.")
    if state in {"planned", "booked", "cancelled"} and any(dates[k] for k in dates if k.startswith("actual_")):
        raise ValueError("Datas reais exigem uma situação logística compatível.")
    if state == "in_transit" and (dates["actual_arrival"] or dates["actual_delivery"]):
        raise ValueError("Registre chegada ou entrega para informar suas datas reais.")
    if state == "arrived" and dates["actual_delivery"]:
        raise ValueError("Registre entrega para informar sua data real.")
    for earlier, later in (("actual_departure", "actual_arrival"), ("actual_arrival", "actual_delivery")):
        if dates[earlier] and dates[later] and dates[later] < dates[earlier]:
            raise ValueError("Datas reais devem respeitar saída, chegada e entrega.")
    if dates["actual_departure"] and order.get("order_date") and dates["actual_departure"] < date.fromisoformat(order["order_date"]):
        raise ValueError("Saída real não pode anteceder a data do pedido.")
    if previous.get("actual_departure"):
        for key in ("origin", "destination", "mode"):
            if result.get(key) != previous.get(key):
                raise ValueError("Rota e modal não podem mudar depois da saída real.")
    for key in ("actual_departure", "actual_arrival", "actual_delivery"):
        if previous.get(key) and result.get(key) != previous[key]:
            raise ValueError("Datas reais já registradas não podem ser apagadas ou reescritas.")
    history = previous.get("history", [])
    if not isinstance(history, list) or len(history) >= MAX_EVENTS:
        raise ValueError("Limite ou inconsistência no histórico logístico. Solicite revisão administrativa.")
    result["responsible_name"] = str(responsible.get("name") or responsible.get("email") or responsible["id"])[:160]
    changes = {key: value for key, value in result.items() if value != previous.get(key)}
    result["created_at"] = previous.get("created_at") or now
    result["updated_at"] = now
    result["history"] = history + [{"id": str(uuid.uuid4()), "at": now, "by": actor["id"],
                                   "by_name": str(actor.get("name") or "")[:160],
                                   "order_version": int(order.get("version") or 0) + 1,
                                   "from_status": previous.get("status", ""), "to_status": state,
                                   "note": note, "changes": changes}]
    if len(json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()) > MAX_BYTES:
        raise OverflowError("Histórico logístico atingiu o limite de tamanho. Solicite revisão administrativa.")
    target = {"planned": "confirmed", "booked": "confirmed", "cancelled": "confirmed",
              "in_transit": "shipped", "arrived": "shipped", "delivered": "delivered"}[state]
    return result, target
