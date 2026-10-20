"""Read-only order operations indicators. No provider, mutation or monetary inference."""
from collections import Counter, defaultdict
from datetime import date
from commercial_invoices import commercial_snapshot, revision
from packing_lists import packing_snapshot

STATUSES = ('draft','confirmed','shipped','delivered','cancelled')
ATTENTION = ('receivable_overdue','shipment_overdue','documents_pending','shipment_missing','data_review')
ELIGIBLE = {'confirmed','shipped','delivered'}
ORDER_FIELDS = ('id','number','customer','customer_country','order_date','receivable_due_date','status','workflow_enabled',
    'finance_paid','lead_id','incoterm','items','total_usd','source_quote_snapshot.payment_terms','source_quote_snapshot.delivery_terms',
    'shipment.status','shipment.reference','shipment.planned_departure','shipment.planned_arrival',
    'shipment.actual_departure','shipment.actual_arrival','shipment.actual_delivery')
DOC_FIELDS = ('id','order_id','status','source_order_revision')

def calendar(value):
    if not isinstance(value,str) or len(value)!=10:
        raise ValueError('Informe datas no formato AAAA-MM-DD.')
    result=date.fromisoformat(value)
    if result.isoformat()!=value: raise ValueError('Informe datas no formato AAAA-MM-DD.')
    return result

def document_states(documents):
    by_order=defaultdict(list)
    for doc in documents: by_order[doc['order_id']].append(doc)
    return by_order

def document_state(documents, expected):
    if not documents: return 'missing'
    if len(documents)!=1: return 'ambiguous'
    doc=documents[0]
    if not expected or doc.get('source_order_revision')!=expected: return 'outdated'
    return doc['status']

def operation_rows(orders, invoices, packing_lists, today):
    invoice_by_order=document_states(invoices);packing_by_order=document_states(packing_lists)
    rows=[]
    for order in orders:
        flags=set();state=order.get('status','');operational=order.get('workflow_enabled') is True
        eligible=operational and state in ELIGIBLE
        def read_date(value, required=False):
            if not value:
                if required: flags.add('data_review')
                return None
            try: return calendar(value)
            except (TypeError,ValueError): flags.add('data_review');return None
        ordered=read_date(order.get('order_date'),True)
        due=read_date(order.get('receivable_due_date'),eligible)
        if state not in STATUSES or not operational: flags.add('data_review')
        if not isinstance(order.get('customer'),str) or not order['customer'].strip(): flags.add('data_review')
        paid=order.get('finance_paid',False)
        if not isinstance(paid,bool): flags.add('data_review')
        if eligible and due and paid is False and due<today: flags.add('receivable_overdue')
        shipment=order.get('shipment') or {}
        if not isinstance(shipment,dict): flags.add('data_review');shipment={}
        shipping_state=shipment.get('status','')
        arrival=read_date(shipment.get('planned_arrival'))
        departure=read_date(shipment.get('planned_departure'))
        real_departure=read_date(shipment.get('actual_departure'))
        real_arrival=read_date(shipment.get('actual_arrival'))
        delivery=read_date(shipment.get('actual_delivery'))
        if eligible:
            if shipping_state in {'','cancelled'}: flags.add('shipment_missing')
            elif shipping_state not in {'planned','booked','in_transit','arrived','delivered'}: flags.add('data_review')
            if shipping_state in {'planned','booked','in_transit'} and arrival and arrival<today and not real_arrival:
                flags.add('shipment_overdue')
            if shipping_state in {'planned','booked'} and departure and departure<today and not real_departure:
                flags.add('shipment_overdue')
            if shipping_state and shipping_state!='cancelled' and (not departure or not arrival): flags.add('data_review')
            if shipping_state=='delivered' and (not delivery or not real_arrival or not real_departure): flags.add('data_review')
            expected_state={'planned':'confirmed','booked':'confirmed','cancelled':'confirmed','in_transit':'shipped','arrived':'shipped','delivered':'delivered'}.get(shipping_state)
            if expected_state and state!=expected_state: flags.add('data_review')
            if shipping_state in {'in_transit','arrived','delivered'} and not real_departure: flags.add('data_review')
            if shipping_state in {'arrived','delivered'} and not real_arrival: flags.add('data_review')
            if departure and arrival and arrival<departure: flags.add('data_review')
            if real_departure and real_arrival and real_arrival<real_departure: flags.add('data_review')
            if real_arrival and delivery and delivery<real_arrival: flags.add('data_review')
        invoice_revision=packing_revision=None
        if eligible:
            try:
                invoice_revision=revision(commercial_snapshot(order));packing_revision=revision(packing_snapshot(order))
            except (TypeError,ValueError,KeyError,ArithmeticError): flags.add('data_review')
        invoice=document_state(invoice_by_order[order['id']],invoice_revision)
        packing=document_state(packing_by_order[order['id']],packing_revision)
        if eligible and (invoice!='approved' or packing!='approved'): flags.add('documents_pending')
        if invoice in {'ambiguous','outdated'} or packing in {'ambiguous','outdated'}: flags.add('data_review')
        rows.append({'id':order['id'],'number':str(order.get('number') or '')[:200], 'customer':str(order.get('customer') or '')[:500],
            'customer_country':str(order.get('customer_country') or '')[:100], 'status':state if state in STATUSES else 'unknown',
            'order_date':ordered.isoformat() if ordered else '', 'receivable_due_date':due.isoformat() if due else '',
            'finance_paid':paid if isinstance(paid,bool) else None,'workflow_enabled':operational,
            'shipment_status':shipping_state if shipping_state in {'planned','booked','in_transit','arrived','delivered','cancelled'} else '',
            'planned_arrival':arrival.isoformat() if arrival else '', 'invoice_status':invoice,'packing_status':packing,
            'flags':sorted(flags),'days_overdue':(today-due).days if 'receivable_overdue' in flags else None})
    rows.sort(key=lambda r:(-len(r['flags']),r['order_date'],r['id']))
    return rows

def summarize(rows):
    states=Counter(r['status'] for r in rows)
    return {'total':len(rows),'by_status':{s:states[s] for s in (*STATUSES,'unknown')},
        'needs_attention':sum(bool(r['flags']) for r in rows),
        'attention':{key:sum(key in r['flags'] for r in rows) for key in ATTENTION}}
