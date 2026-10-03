"""Unit pricing and order totals. No database or external service access."""
import re, math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def decimal_number(value, quantity=False):
    text = re.sub(r"\s", "", str(value if value is not None else 0))
    if not text:
        text = "0"
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".") if text.rfind(",") > text.rfind(".") else text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif quantity and re.fullmatch(r"[1-9]\d{0,2}(?:\.\d{3})+", text):
        text = text.replace(".", "")
    try:
        number = Decimal(text)
    except InvalidOperation:
        raise ValueError("Informe apenas valores numéricos válidos.")
    if not number.is_finite():
        raise ValueError("Informe apenas valores numéricos finitos.")
    return number


def calculate_price(p):
    supplier, quantity, margin, rate = map(decimal_number, [p.supplier_price, p.quantity, p.margin_pct, p.exchange_rate])
    extras = sum((decimal_number(x.get("value", 0)) for x in p.extras), Decimal(0)) if p.extras else decimal_number(p.extra_costs)
    taxes = sum((decimal_number(x.get("pct", 0)) for x in p.taxes), Decimal(0)) if p.taxes else decimal_number(p.taxes_pct)
    values = [supplier, margin, rate, extras, taxes] + [decimal_number(x.get("value", 0)) for x in p.extras] + [decimal_number(x.get("pct", 0)) for x in p.taxes]
    if quantity <= 0 or any(v < 0 for v in values):
        raise ValueError("Quantidade deve ser positiva; preços, custos e percentuais não podem ser negativos.")
    if taxes >= 100 or (p.margin_mode == "margin" and taxes + margin >= 100):
        raise ValueError("Impostos e margem precisam permitir um preço de venda válido (soma menor que 100%).")
    if p.currency == "USD" and rate <= 0:
        raise ValueError("Informe o câmbio para calcular em USD.")
    def rounded(value, places=2):
        return value.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
    cost = supplier + extras
    raw = cost * (1 + margin / 100) / (1 - taxes / 100) if p.margin_mode == "markup" else cost / (1 - (margin + taxes) / 100)
    price = rounded(raw, 4)
    usd = rounded(price / rate, 4) if rate > 0 else Decimal(0)
    sale_total, cost_total = rounded(price * quantity), rounded(cost * quantity)
    tax_total = rounded(sale_total * taxes / 100)
    result = {"extra_costs":float(rounded(extras,4)), "taxes_pct":float(rounded(taxes,4)),
        "sell_price_brl":float(price), "sell_price_usd":float(usd),
        "supplier_total":float(rounded(supplier*quantity)), "extras_total":float(rounded(extras*quantity)),
        "cost_total":float(cost_total), "sale_total_brl":float(sale_total), "sale_total_usd":float(rounded(usd*quantity)),
        "tax_total":float(tax_total), "profit_total":float(rounded(sale_total-tax_total-cost_total))}

    if not all(math.isfinite(value) for value in result.values()):
        raise ValueError("Os valores informados são grandes demais para calcular.")
    return result
