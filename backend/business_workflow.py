"""Order/purchase ledgers are the source for stock movements and linked accounts.

Changing a status recomputes the view instead of incrementing a second balance.
Retries and confirmed -> shipped -> delivered therefore cannot duplicate stock
movements or financial entries. Database writes are serialized by the API.
"""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from datetime import date

ORDER_STATUSES = {"draft", "confirmed", "shipped", "delivered", "cancelled"}
PURCHASE_STATUSES = {"ordered", "received", "paid", "cancelled"}
CURRENCIES = {"BRL", "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CNY"}

def number(value, label, positive=False):
    try:
        amount=Decimal(str(value or 0))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{label} inválido")
    if not amount.is_finite() or amount < 0 or (positive and amount <= 0):
        raise ValueError(f"{label} deve ser maior que zero" if positive else f"{label} inválido")
    return amount

def money(value):
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))

def valid_date(value, label, required=False):
    if not value and not required:
        return ""
    try:
        date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ValueError(f"{label} obrigatória e no formato AAAA-MM-DD")
    return value

def normalize_order(body, previous, products, offers):
    result=dict(body)
    status=result.get("status", "draft")
    if status not in ORDER_STATUSES:
        raise ValueError("Situação do pedido inválida")
    if not str(result.get("customer", "")).strip():
        raise ValueError("Cliente obrigatório")
    if previous and previous.get("status") in {"shipped", "delivered"}:
        if status not in {"shipped", "delivered"} or (previous["status"]=="delivered" and status!="delivered"):
            raise ValueError("Pedido embarcado não pode ser revertido. Registre a devolução separadamente.")
        for field in ("items", "track_stock", "total_usd"):
            if result.get(field) != previous.get(field):
                raise ValueError("Itens e valores de pedido embarcado não podem ser alterados")
    if previous and previous.get("finance_paid") and status=="cancelled":
        raise ValueError("Pedido com recebimento registrado não pode ser cancelado")
    if previous and previous.get("finance_paid") and status=="draft":
        raise ValueError("Pedido com recebimento registrado não pode voltar a rascunho")
    if previous and previous.get("status")=="cancelled" and status!="cancelled":
        raise ValueError("Crie um novo pedido para uma operação cancelada")
    items=[]
    total=Decimal(0)
    for raw in result.get("items", []):
        product=products.get(raw.get("product_id"))
        if not product:
            raise ValueError("Selecione um produto cadastrado para cada item")
        offer=offers.get(raw.get("offer_id"))
        existing_item = next((i for i in (previous or {}).get("items", []) if i == raw), None)
        grandfathered = existing_item and (previous or {}).get("status") in {"confirmed", "shipped", "delivered"}
        if not offer or offer.get("product_id") != product["id"] or (not offer.get("active", True) and not grandfathered):
            raise ValueError("Selecione uma oferta ativa do produto e fornecedor")
        qty=number(raw.get("quantity"), "Quantidade", positive=True)
        price=number(raw.get("unit_price"), "Preço unitário USD", positive=True)
        unit=str(raw.get("unit") or offer.get("unit") or product.get("unit") or "kg")
        if result.get("track_stock") and unit != (product.get("unit") or "kg"):
            raise ValueError("A unidade do pedido deve coincidir com a unidade do estoque")
        item={"product_id":product["id"],"product_name":product["name"],
              "offer_id":offer["id"],"supplier_id":offer.get("supplier_id", ""),
              "supplier_name":offer.get("supplier_name", ""), "quantity":float(qty),
              "unit":unit,"unit_price":float(price)}
        if grandfathered:
            item.update({key: existing_item.get(key, item[key]) for key in ("product_name", "supplier_id", "supplier_name")})
        total+=Decimal(str(money(qty*price)))
        items.append(item)
    if status in {"confirmed", "shipped", "delivered"} and not items:
        raise ValueError("Adicione os itens antes de confirmar o pedido")
    if len(items)>100:
        raise ValueError("Limite de 100 itens por pedido")
    if items:
        result["total_usd"]=money(total)
        result["products"]="; ".join(f'{x["product_name"]} ({x["supplier_name"]}): {x["quantity"]:g} {x["unit"]}' for x in items)
    else:
        result["total_usd"]=money(number(result.get("total_usd"), "Total USD"))
    if previous and previous.get("finance_paid"):
        if result["total_usd"]!=previous.get("total_usd") or any(result.get(f)!=previous.get(f) for f in ("receivable_due_date", "customer")):
            raise ValueError("Valor e vencimento de pedido pago não podem ser alterados")
    result["items"]=items
    result["order_date"]=valid_date(result.get("order_date"), "Data do pedido",status!="draft")
    result["delivery_date"]=valid_date(result.get("delivery_date"), "Data de entrega")
    result["receivable_due_date"]=valid_date(result.get("receivable_due_date"), "Vencimento",status in {"confirmed","shipped","delivered"})
    result["workflow_enabled"]=True
    # Payment state and creation time are owned by the stored ledger, not the client.
    result["finance_paid"]=bool((previous or {}).get("finance_paid"))
    result["finance_paid_date"]=(previous or {}).get("finance_paid_date", "")
    result["deleted_at"]=(previous or {}).get("deleted_at", "")
    if previous:
        result["created_at"]=previous.get("created_at",result.get("created_at"))
    return result

def normalize_purchase(body, previous, products, suppliers):
    result=dict(body)
    status=result.get("status", "ordered")
    if status not in PURCHASE_STATUSES:
        raise ValueError("Situação de compra inválida")
    if not str(result.get("product", "")).strip() and not result.get("product_id"):
        raise ValueError("Produto obrigatório")
    supplier=suppliers.get(result.get("supplier_id"))
    if not supplier:
        raise ValueError("Selecione um fornecedor cadastrado")
    result["supplier_name"]=supplier["name"]
    qty=number(result.get("quantity"),"Quantidade",True)
    price=number(result.get("unit_price"),"Preço unitário",True)
    result.update(quantity=float(qty),unit_price=float(price),total=money(qty*price))
    currency=str(result.get("currency") or "BRL").strip().upper()
    if currency not in CURRENCIES:
        raise ValueError("Moeda não suportada")
    result["currency"]=currency
    result["date"]=valid_date(result.get("date"),"Data da compra",True)
    result["due_date"]=valid_date(result.get("due_date"),"Vencimento",status!="cancelled")
    if result.get("product_id"):
        product=products.get(result["product_id"])
        if not product:
            raise ValueError("Produto não encontrado")
        result["product"]=product["name"]
        if result.get("track_stock") and (result.get("unit") or "kg") != (product.get("unit") or "kg"):
            raise ValueError("A unidade da compra deve coincidir com a do estoque")
    elif result.get("track_stock"):
        raise ValueError("Selecione um produto cadastrado para receber em estoque")
    was_received=bool((previous or {}).get("stock_received") or (previous or {}).get("status")=="received")
    received=bool(result.get("stock_received") or status=="received")
    if was_received and not received:
        raise ValueError("Recebimento não pode ser desfeito. Registre a devolução separadamente.")
    if was_received:
        for field in ("product_id","quantity","unit","track_stock"):
            if result.get(field)!=previous.get(field):
                raise ValueError("Itens de compra recebida não podem ser alterados")
        if status=="cancelled":
            raise ValueError("Compra recebida não pode ser cancelada sem registrar devolução")
    if previous and previous.get("status")=="cancelled" and status!="cancelled":
        raise ValueError("Crie uma nova compra para uma operação cancelada")
    result["stock_received"]=received
    result["workflow_enabled"]=True
    paid=bool(status=="paid")
    if previous and previous.get("finance_paid") and not paid:
        raise ValueError("Altere o registro do pagamento no financeiro antes de editar a compra")
    if previous and previous.get("finance_paid") and any(result.get(f)!=previous.get(f) for f in ("total","currency","due_date","supplier_id")):
        raise ValueError("Valor, moeda e vencimento de compra paga não podem ser alterados")
    result["finance_paid"]=paid
    result["finance_paid_date"]=(previous or {}).get("finance_paid_date", "")
    result["deleted_at"]=(previous or {}).get("deleted_at", "")
    if paid and not result["finance_paid_date"]:
        result["finance_paid_date"]=result.get("updated_at", "")
    if previous:
        result["created_at"]=previous.get("created_at",result.get("created_at"))
    return result

def inventory_balances(products, orders, purchases):
    result={p["id"]:{**p,"stock":float(p.get("stock") or 0),"stock_reserved":0.0,"stock_movement":0.0} for p in products}
    for purchase in purchases:
        if purchase.get("deleted_at") or not purchase.get("workflow_enabled") or not purchase.get("track_stock") or not purchase.get("stock_received") or purchase.get("status")=="cancelled":
            continue
        product=result.get(purchase.get("product_id"))
        if product:
            product["stock_movement"]+=float(purchase.get("quantity") or 0)
    for order in orders:
        if order.get("deleted_at") or not order.get("workflow_enabled") or not order.get("track_stock"):
            continue
        for item in order.get("items", []):
            product=result.get(item.get("product_id"))
            if not product:
                continue
            qty=float(item.get("quantity") or 0)
            if order.get("status")=="confirmed":
                product["stock_reserved"]+=qty
            elif order.get("status") in {"shipped", "delivered"}:
                product["stock_movement"]-=qty
    for product in result.values():
        product["stock"]+=product["stock_movement"]
        product["stock_available"]=product["stock"]-product["stock_reserved"]
        for f in ("stock", "stock_reserved", "stock_available", "stock_movement"):
            product[f]=round(product[f],6)
    return result

def validate_balances(balances):
    for product in balances.values():
        if product["stock_available"] < -0.000001:
            raise ValueError(f'Estoque insuficiente para {product["name"]}. Disponível após a operação: {product["stock_available"]:g} {product.get("unit", "kg")}')

def linked_finance(orders, purchases):
    result=[]
    for record in orders:
        if not record.get("workflow_enabled") or record.get("status") not in {"confirmed", "shipped", "delivered"} or record.get("deleted_at"):
            continue
        result.append({"id":"order:"+record["id"],"source_order_id":record["id"],"kind":"receivable",
                       "description":"Pedido "+(record.get("number") or record["id"]),"party":record["customer"],
                       "amount":record["total_usd"],"currency":"USD","due_date":record.get("receivable_due_date", ""),
                       "paid":record.get("finance_paid",False),"paid_date":record.get("finance_paid_date", ""),
                       "category":"Venda","created_at":record.get("created_at", "")})
    for record in purchases:
        if not record.get("workflow_enabled") or record.get("status")=="cancelled" or record.get("deleted_at"):
            continue
        result.append({"id":"purchase:"+record["id"],"source_purchase_id":record["id"],"kind":"payable",
                       "description":"Compra de "+record["product"],"party":record.get("supplier_name", ""),
                       "amount":record["total"],"currency":record.get("currency", "BRL"),"due_date":record.get("due_date", ""),
                       "paid":record.get("finance_paid",False),"paid_date":record.get("finance_paid_date", ""),
                       "category":"Compra","created_at":record.get("created_at", "")})
    return result
