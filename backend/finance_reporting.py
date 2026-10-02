"""Currency-separated financial reporting without assumed exchange rates."""
from datetime import datetime

def currency_code(value):
    return str(value or "BRL").upper().strip()

def cashflow_rows(entries, invoices, keys, currency="BRL"):
    currency = currency_code(currency)
    fields = ("receivable", "payable", "received", "paid", "nf_saida", "nf_entrada")
    data = {key: {"month": key, "currency": currency, **{f: 0.0 for f in fields}} for key in keys}
    for entry in entries:
        if entry.get("cancelled") or currency_code(entry.get("currency")) != currency:
            continue
        amount = float(entry.get("amount") or 0)
        due_key = (entry.get("due_date") or "")[:7]
        kind = entry.get("kind")
        if kind not in ("receivable", "payable"):
            continue
        if due_key in data:
            data[due_key][kind] += amount
        if entry.get("paid"):
            paid_key = (entry.get("paid_date") or entry.get("due_date") or "")[:7]
            if paid_key in data:
                data[paid_key]["received" if kind == "receivable" else "paid"] += amount
    for invoice in invoices:
        # NF-e totals are BRL unless an explicit source currency was stored.
        if currency_code(invoice.get("currency")) != currency:
            continue
        key = (invoice.get("issue_date") or "")[:7]
        if key in data:
            data[key]["nf_saida" if invoice.get("kind") == "saida" else "nf_entrada"] += float(invoice.get("total") or 0)
    running = 0.0
    for key in keys:
        row = data[key]
        for field in fields:
            row[field] = round(row[field], 2)
        row["balance"] = round(row["receivable"] - row["payable"], 2)
        row["cash_balance"] = round(row["received"] - row["paid"], 2)
        running += row["balance"]
        row["cumulative"] = round(running, 2)
    return list(data.values())

def pending_totals(entries):
    totals = {}
    for entry in entries:
        if entry.get("paid") or entry.get("cancelled") or entry.get("kind") not in ("receivable", "payable"):
            continue
        currency = currency_code(entry.get("currency"))
        row = totals.setdefault(currency, {"currency": currency, "receivable": 0.0, "payable": 0.0})
        row[entry["kind"]] += float(entry.get("amount") or 0)
    return [{**row, "receivable": round(row["receivable"], 2), "payable": round(row["payable"], 2)}
            for currency, row in sorted(totals.items())]
