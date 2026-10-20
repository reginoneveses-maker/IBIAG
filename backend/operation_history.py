"""Immutable history blocks, atomically referenced by the owning record.

Only ALREADY COMMITTED events are copied before a business CAS. Orphan blocks
from failed CAS/leases are unreachable and never treated as committed events.
No transactions, TTL, external storage or background task is required.
"""
import base64
import copy
import hashlib
import hmac
import json
import re
import time
from datetime import datetime
from pymongo.errors import DuplicateKeyError

KINDS = {'quotation','commercial_invoice','packing_list','shipment','sample'}
ROTATE_EVENTS = 32
ROTATE_BYTES = 96*1024
MAX_RECORD_BYTES = 256*1024
MAX_BLOCK_BYTES = 512*1024
MAX_PAGE_BYTES = 512*1024
BLOCK_ID = re.compile(r'^h1-[0-9a-f]{64}$')
EMPTY = {'head':'','count':0,'last_version':0}

class HistoryError(ValueError): pass
class HistoryConflict(HistoryError): pass
class InvalidCursor(HistoryError): pass


def encoded(value):
    return json.dumps(value,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(',',':')).encode('utf-8')


def metadata(value):
    if value is None: return dict(EMPTY)
    if not isinstance(value,dict) or set(value)!={'head','count','last_version'}:
        raise HistoryError('Metadados do histórico exigem revisão administrativa.')
    if not isinstance(value['count'],int) or isinstance(value['count'],bool) or not isinstance(value['last_version'],int) or isinstance(value['last_version'],bool) or not 0<=value['count']<=value['last_version']<=10**12:
        raise HistoryError('Contagem do histórico exige revisão administrativa.')
    if value['count']==0:
        if value!=EMPTY: raise HistoryError('Referência de histórico inválida.')
    elif not isinstance(value['head'],str) or not BLOCK_ID.fullmatch(value['head']):
        raise HistoryError('Referência de histórico inválida.')
    return dict(value)


def check_events(kind,events,prior,max_version):
    if kind not in KINDS or not isinstance(events,list) or len(events)>100:
        raise HistoryError('Histórico exige revisão administrativa.')
    key='order_version' if kind=='shipment' else 'version'
    fields={'id','at','by','by_name','note','changes',key}
    if kind=='shipment': fields|={'from_status','to_status'}
    seen=set();last=prior['last_version']
    for event in events:
        if not isinstance(event,dict) or set(event)!=fields:
            raise HistoryError('Evento do histórico exige revisão administrativa.')
        for name,limit in (('id',80),('by',200),('by_name',160),('note',300),('at',80)):
            value=event[name]
            if not isinstance(value,str) or len(value)>limit or '\x00' in value or (name in {'id','by','at'} and not value):
                raise HistoryError('Evento do histórico exige revisão administrativa.')
        try: stamp=datetime.fromisoformat(event['at'])
        except (TypeError,ValueError): raise HistoryError('Data do histórico exige revisão administrativa.') from None
        if stamp.tzinfo is None or event['id'] in seen or not isinstance(event[key],int) or isinstance(event[key],bool) or not last<event[key]<=max_version or not isinstance(event['changes'],dict):
            raise HistoryError('Sequência do histórico exige revisão administrativa.')
        if kind!='shipment' and event[key]!=last+1:
            raise HistoryError('Há lacuna na sequência do histórico.')
        if kind=='shipment' and any(not isinstance(event[k],str) for k in ('from_status','to_status')):
            raise HistoryError('Estado do histórico exige revisão administrativa.')
        seen.add(event['id']);last=event[key]
    if kind!='shipment' and (prior['count']!=prior['last_version'] or last!=max_version):
        raise HistoryError('Contagem do histórico não corresponde à versão do documento.')
    return last


def block_document(kind,rid,events,prior):
    payload={'kind':kind,'resource_id':rid,'previous':prior,'events':events}
    raw=encoded(payload)
    if len(raw)>MAX_BLOCK_BYTES: raise OverflowError('Bloco de histórico excede o limite de tamanho.')
    return {'_id':'h1-'+hashlib.sha256(raw).hexdigest(),**payload}


async def read_block(collection,kind,rid,meta):
    record=await collection.find_one({'_id':meta['head']})
    if record is None: raise HistoryConflict('Bloco do histórico não encontrado. Solicite revisão administrativa.')
    try:
        if set(record)!={'_id','kind','resource_id','previous','events'} or record['kind']!=kind or record['resource_id']!=rid:
            raise HistoryError('Vínculo de histórico incompatível.')
        previous=metadata(record['previous'])
        last=check_events(kind,record['events'],previous,meta['last_version'])
        if not record['events'] or previous['count']+len(record['events'])!=meta['count'] or last!=meta['last_version'] or block_document(kind,rid,record['events'],previous)!=record:
            raise HistoryError('Integridade do bloco de histórico não confirmada.')
    except (TypeError,ValueError,OverflowError):
        raise HistoryConflict('Integridade do histórico não confirmada. Solicite revisão administrativa.') from None
    return record['events'],previous


async def prepare_history(collection,kind,rid,container,version,ensure_owned):
    """Called under the existing business lease; copies only committed past events.

    Does not alter the source. Returned history fields MUST be committed with
    that same source's version CAS; callers never update an archive pointer alone.
    """
    if len(encoded(container))>MAX_RECORD_BYTES: raise OverflowError('Registro excede o limite de tamanho do histórico.')
    prior=metadata(container.get('history_archive'))
    events=container.get('history',[])
    check_events(kind,events,prior,version)
    if prior['count']: await read_block(collection,kind,rid,prior)
    if len(events)<ROTATE_EVENTS and len(encoded(events))<ROTATE_BYTES: return container
    if not events: return container
    block=block_document(kind,rid,events,prior)
    await ensure_owned()
    existing=await collection.find_one({'_id':block['_id']})
    if existing is None:
        try: await collection.insert_one(copy.deepcopy(block))
        except DuplicateKeyError: pass  # Idempotent retry after uncertain archive insertion.
        existing=await collection.find_one({'_id':block['_id']})
    if existing!=block: raise HistoryConflict('Bloco de histórico incompatível. Nenhuma revisão foi descartada.')
    await ensure_owned()
    key='order_version' if kind=='shipment' else 'version'
    result=dict(container)
    result.update(history=[],history_archive={'head':block['_id'],'count':prior['count']+len(events),'last_version':events[-1][key]})
    return result


def history_fields(record):
    result={'history':record.get('history',[])}
    if 'history_archive' in record: result['history_archive']=record['history_archive']
    return result


def cursor_key(secret):
    return hmac.new(secret.encode(),b'IBIAG/operation-history/cursor/v1',hashlib.sha256).digest()


def seal(payload,secret):
    raw=base64.urlsafe_b64encode(encoded(payload)).rstrip(b'=')
    signature=hmac.new(cursor_key(secret),raw,hashlib.sha256).hexdigest().encode()
    return (raw+b'.'+signature).decode('ascii')


def unseal(token,secret,kind,rid,version):
    try:
        if not isinstance(token,str) or not 1<=len(token)<=2048: raise ValueError()
        raw,signature=token.encode('ascii').split(b'.')
        if not hmac.compare_digest(hmac.new(cursor_key(secret),raw,hashlib.sha256).hexdigest().encode(),signature): raise ValueError()
        payload=json.loads(base64.b64decode(raw+b'='*(-len(raw)%4),altchars=b'-_',validate=True))
        if set(payload)!={'kind','id','version','expires','position'} or payload['kind']!=kind or payload['id']!=rid or type(payload['version']) is not int or type(payload['expires']) is not int or payload['expires']<time.time(): raise ValueError()
        if payload['version']!=version: raise HistoryConflict('Histórico alterado. Atualize a consulta antes de continuar.')
        position=payload['position']
        if not isinstance(position,dict) or set(position)!={'block','offset'} or type(position['offset']) is not int or not 0<=position['offset']<=100: raise ValueError()
        if position['block']!='recent': metadata(position['block'])
        return position
    except HistoryConflict: raise
    except (ValueError,TypeError,KeyError,UnicodeError):
        raise InvalidCursor('Página de histórico inválida ou expirada. Atualize a consulta.') from None


async def history_page(collection,kind,rid,container,version,secret,limit=20,cursor=''):
    prior=metadata(container.get('history_archive'))
    events=container.get('history',[])
    check_events(kind,events,prior,version)
    if prior['count']: await read_block(collection,kind,rid,prior)
    position=unseal(cursor,secret,kind,rid,version) if cursor else {'block':'recent','offset':0}
    items=[];size=0
    while position is not None and len(items)<limit:
        if position['block']=='recent': batch,parent=events,prior
        else: batch,parent=await read_block(collection,kind,rid,metadata(position['block']))
        batch=list(reversed(batch));offset=position['offset']
        if offset>len(batch): raise InvalidCursor('Página de histórico inválida. Atualize a consulta.')
        full=False
        while offset<len(batch) and len(items)<limit:
            item=batch[offset];length=len(encoded(item))
            if length>MAX_PAGE_BYTES: raise OverflowError('Evento excede o limite de consulta.')
            if size+length>MAX_PAGE_BYTES: full=True;break
            items.append(item);size+=length;offset+=1
        if offset<len(batch): position={**position,'offset':offset}
        else: position={'block':parent,'offset':0} if parent['count'] else None
        if full: break
    token=seal({'kind':kind,'id':rid,'version':version,'expires':int(time.time())+900,'position':position},secret) if position is not None else ''
    return {'items':items,'next_cursor':token,'total':prior['count']+len(events),'snapshot_version':version}
