"""Read-only order dossier. No file content, regulatory completeness or mutations."""
from commercial_invoices import commercial_snapshot, revision
from packing_lists import packing_snapshot
from operations_dashboard import operation_rows

DOC_FIELDS=("id","order_id","reference","status","issue_date","version","source_order_revision","source_order_version")
SHIPMENT_FIELDS=("reference","status","mode","origin","destination","carrier","transport_reference","planned_departure","planned_arrival","actual_departure","actual_arrival","actual_delivery")
def text(value,limit=500):
    return value[:limit] if isinstance(value,str) else ""

def valid_id(value):
    return isinstance(value,str) and 0<len(value)<=200 and not any(ord(c)<32 or ord(c)==127 for c in value)

def checked_docs(records):
    seen=set()
    for record in records:
        rid=record.get("id")
        if not valid_id(rid) or rid in seen: raise ValueError("Identificadores de documentos inconsistentes. Revise os cadastros.")
        seen.add(rid)

def dossier(order,invoices,packing_lists,quotes,today):
    checked_docs(invoices);checked_docs(packing_lists)
    active_invoices=[r for r in invoices if r.get("status") in {"draft","approved"}]
    active_packing=[r for r in packing_lists if r.get("status") in {"draft","approved"}]
    operation=operation_rows([order],active_invoices,active_packing,today)[0]
    expected_invoice=expected_packing=None
    try: expected_invoice=revision(commercial_snapshot(order));expected_packing=revision(packing_snapshot(order))
    except (TypeError,ValueError,KeyError,ArithmeticError): pass
    def documents(records,expected):
        rows=[]
        for r in records:
            status=r.get("status")
            rows.append({"id":r["id"],"reference":text(r.get("reference"),200),"status":status if status in {"draft","approved","cancelled"} else "unknown",
                         "issue_date":text(r.get("issue_date"),10),
                         "version":r.get("version") if type(r.get("version")) is int and r["version"]>=1 else None,
                         "source_current":r.get("source_order_revision")==expected if expected else None})
        return sorted(rows,key=lambda r:(r["status"]=="cancelled",r["reference"],r["id"]))
    invoice_rows=documents(invoices,expected_invoice);packing_rows=documents(packing_lists,expected_packing)
    invoice_state="review" if any(r["status"]=="unknown" or r["version"] is None for r in invoice_rows) else operation["invoice_status"]
    packing_state="review" if any(r["status"]=="unknown" or r["version"] is None for r in packing_rows) else operation["packing_status"]
    flags=[flag for flag in operation["flags"] if flag in {"documents_pending","shipment_missing","shipment_overdue","data_review"}]
    if any(r["status"]=="unknown" or r["version"] is None for r in invoice_rows+packing_rows):
        if "data_review" not in flags: flags.append("data_review")
    qid=order.get("source_quote_id") or ""
    quote={"state":"not_linked","id":"","reference":"","recorded_version":None,"current_status":""}
    if qid:
        if not valid_id(qid): raise ValueError("Vínculo de cotação inconsistente. Revise o pedido.")
        snapshot=order.get("source_quote_snapshot") or {}
        if not isinstance(snapshot,dict): snapshot={}
        quote.update(id=qid,reference=text(snapshot.get("reference"),200),
                     recorded_version=order.get("source_quote_revision") if type(order.get("source_quote_revision")) is int else None)
        if not quotes: quote["state"]="missing"
        elif len(quotes)>1: quote["state"]="ambiguous"
        else:
            record=quotes[0];state=record.get("status")
            quote["current_status"]=state if state in {"draft","approved","cancelled"} else "unknown"
            quote["state"]="linked" if state=="approved" and record.get("linked_order_id")==order["id"] and type(record.get("version")) is int and record["version"]==quote["recorded_version"] else "review"
        if quote["state"]!="linked": flags.append("quote_review")
    shipment=order.get("shipment") or {}
    if not isinstance(shipment,dict): shipment={}
    return {"order":{**{key:text(order.get(key),500 if key=="customer" else 200) for key in ("id","number","customer","customer_country","order_date","incoterm","lead_id")},
                     "status":operation["status"],"version":order.get("version") if type(order.get("version")) is int else None},
            "quote":quote,"invoice_state":invoice_state,"packing_state":packing_state,
            "commercial_source_checked":bool(expected_invoice and expected_packing),
            "invoices":invoice_rows,"packing_lists":packing_rows,
            "shipment":{key:text(shipment.get(key),500) for key in SHIPMENT_FIELDS},
            "flags":sorted(set(flags)),
            "counts":{"invoices":len(invoice_rows),"packing_lists":len(packing_rows),
                      "active_invoices":len(active_invoices),"active_packing_lists":len(active_packing)}}
