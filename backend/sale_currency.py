"""Explicit sale denomination; legacy USD shapes stay compatible. No FX inference."""
from decimal import Decimal, InvalidOperation

SALE_CURRENCIES = {"USD", "BRL", "EUR"}

def sale_currency(record):
    currency = record.get("currency", "USD")
    if currency not in SALE_CURRENCIES:
        raise ValueError("Moeda comercial não suportada.")
    return currency

def sale_amount(record):
    currency = sale_currency(record)
    value = record.get("total_usd") if currency == "USD" else record.get("total_amount")
    if value is None:
        raise ValueError("Informe o total na moeda da operação.")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            raise ValueError()
        if currency != "USD" and Decimal(str(record.get("total_usd", 0))) != 0:
            raise ValueError()
        if currency == "USD" and record.get("total_amount") is not None and Decimal(str(record["total_amount"])) != amount:
            raise ValueError()
    except (ValueError, TypeError, InvalidOperation):
        raise ValueError("Total incompatível com a moeda da operação.") from None
    return amount

def sale_fields(currency, amount):
    if currency not in SALE_CURRENCIES:
        raise ValueError("Moeda comercial não suportada.")
    if currency == "USD":
        return {"total_usd": amount}
    return {"currency": currency, "total_amount": amount, "total_usd": 0}
