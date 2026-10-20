"""HTTP history rotation/failure/pagination tests, repeated on disposable MongoDB."""
import asyncio
import copy
import os
import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from bson.int64 import Int64
import operation_history as history
import test_commercial_invoices as fixtures
import server

class CollectionProxy:
    def __init__(self,collection,**overrides): self.collection=collection;self.overrides=overrides
    def __getattr__(self,key): return self.overrides.get(key) or getattr(self.collection,key)
class DatabaseProxy:
    def __init__(self,database,**overrides): self.database=database;self.overrides=overrides
    def __getattr__(self,key): return self.overrides.get(key) or getattr(self.database,key)

class OperationHistoryTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=fixtures.CommercialInvoiceTests.headers
    create_order=fixtures.CommercialInvoiceTests.create_order
    update_order=fixtures.CommercialInvoiceTests.update_order
    asyncTearDown=fixtures.CommercialInvoiceTests.asyncTearDown
    async def asyncSetUp(self):
        await fixtures.CommercialInvoiceTests.asyncSetUp(self)
        self.ok(await self.client.post('/api/commercial-invoices',headers=self.headers(),json=self.invoice_body))
        self.ok(await self.client.post('/api/packing-lists',headers=self.headers(),json={'id':'pl1','reference':'PL-HISTORY','order_id':'sale',
            'source_order_version':self.order['version'],'issue_date':'2026-10-19','buyer_country':'Portugal','change_note':'Initial packing review'}))
        source=self.ok(await self.client.get('/api/prices/price/order-draft',headers=self.headers()))
        self.ok(await self.client.post('/api/quotations',headers=self.headers(),json={'id':'q1','reference':'Q-HISTORY','lead_id':'lead1','source_price_id':'price',
            'source_price_revision':source['source_price_revision'],'valid_until':'2099-12-31','incoterm':'FOB','payment_terms':'Prepaid','delivery_terms':'30 days','change_note':'Initial quote review'}))
        self.shipment={'status':'planned','reference':'SHIP-HISTORY','origin':'Santos','destination':'Lisbon','mode':'sea','responsible_id':'admin',
            'planned_departure':'2026-10-19','planned_arrival':'2026-10-20','change_note':'Initial shipment review'}
        self.ok(await self.client.put('/api/orders/sale/shipment',headers=self.headers(),json={**self.shipment,'version':self.order['version']}))
    def ok(self,response):
        self.assertEqual(response.status_code,200,response.text[:500]);return response.json()
    def identity(self,kind):
        return {'quotation':('quotations','q1'),'commercial_invoice':('commercial-invoices','inv1'),'packing_list':('packing-lists','pl1'),'shipment':('orders','sale'),'sample':('samples','sample-test')}[kind]
    async def current(self,kind):
        collection={'quotation':'quotations','commercial_invoice':'commercial_invoices','packing_list':'packing_lists','shipment':'orders'}[kind]
        return await self.db[collection].find_one({'id':self.identity(kind)[1]},{'_id':0})
    async def edit(self,kind,i):
        previous=await self.current(kind);path,rid=self.identity(kind)
        if kind=='shipment': body={**self.shipment,'version':previous['version'],'carrier':f'Carrier {i}','change_note':f'Revision {i}'};path=f'{path}/{rid}/shipment'
        else:
            fields={'quotation':server.QUOTE_TERMS,'commercial_invoice':server.COMMERCIAL_INVOICE_DETAILS,'packing_list':server.PACKING_DETAILS}[kind]
            body={**{k:previous[k] for k in fields},'version':previous['version'],'notes':f'Business revision {i}','change_note':f'Revision {i}'};path=f'{path}/{rid}'
        return await self.client.put('/api/'+path,headers=self.headers(),json=body)
    async def page(self,kind='commercial_invoice',cursor='',limit=2,user='admin',rid=None):
        return await self.client.get(f'/api/operations-history/{kind}/{rid or self.identity(kind)[1]}',headers=self.headers(user) if user else {},params={'limit':limit,'cursor':cursor})
    async def rotate(self,kind='commercial_invoice',edits=7):
        with patch.object(history,'ROTATE_EVENTS',3):
            for i in range(edits): self.ok(await self.edit(kind,i))
        return await self.current(kind)
    async def all_events(self,kind='commercial_invoice',limit=2):
        cursor='';events=[]
        for _ in range(100):
            data=self.ok(await self.page(kind,cursor,limit));events.extend(data['items']);cursor=data['next_cursor']
            if not cursor: self.assertEqual(len(events),data['total']);return events
        self.fail('Pagination did not end')

    async def test_all_four_histories_rotate_and_return_every_committed_event_once(self):
        for kind in ('quotation','commercial_invoice','packing_list','shipment'):
            record=await self.rotate(kind)
            container=record['shipment'] if kind=='shipment' else record
            self.assertEqual(len(container['history']),2);self.assertEqual(container['history_archive']['count'],6)
            events=await self.all_events(kind)
            self.assertEqual(len(events),8);self.assertEqual(len({e['id'] for e in events}),8)
            self.assertEqual(events[0]['note'],'Revision 6')
            versions=[e['order_version' if kind=='shipment' else 'version'] for e in events]
            self.assertEqual(versions,sorted(versions,reverse=True))
        # MongoDB may return stored counters as Int64, even at small values.
        record=await self.current('commercial_invoice');meta=record['history_archive']
        await self.db.commercial_invoices.update_one({'id':'inv1'},{'$set':{'history_archive':{**meta,'count':Int64(meta['count']),'last_version':Int64(meta['last_version'])}}})
        self.assertEqual(len(await self.all_events('commercial_invoice')),8)
        self.assertEqual(await self.db.operation_history.count_documents({}),8)
        self.assertEqual(len(await server.all_finance_entries()),1)
        self.assertEqual((await self.current('shipment'))['status'],'confirmed')

    async def test_default_threshold_passes_old_fifty_and_hundred_event_limits_without_losing_events(self):
        for kind,edits in (('commercial_invoice',60),('shipment',105)):
            for i in range(edits): self.ok(await self.edit(kind,i))
            record=await self.current(kind);container=record['shipment'] if kind=='shipment' else record
            self.assertLessEqual(len(container['history']),32)
            events=await self.all_events(kind,limit=50)
            self.assertEqual(len(events),edits+1);self.assertEqual(len({e['id'] for e in events}),edits+1)
        self.assertEqual(len(await server.all_finance_entries()),1)

    async def test_every_history_requires_admin_and_is_private_readonly(self):
        for kind in history.KINDS:
            for user,code in ((None,401),('owner',403),('stranger',403)):
                self.assertEqual((await self.page(kind,user=user)).status_code,code)
        before=await self.current('commercial_invoice');locks=await self.db.workflow_locks.find({}).to_list(None)
        response=await self.page();self.ok(response)
        self.assertEqual(response.headers['cache-control'],'private, no-store');self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertEqual(await self.current('commercial_invoice'),before);self.assertEqual(await self.db.workflow_locks.find({}).to_list(None),locks)
        self.assertEqual(await self.db.operation_history.count_documents({}),0)
        self.assertNotIn('PRIVATE-COST-CANARY',response.text);self.assertNotIn('PRIVATE-ORDER-CANARY',response.text)
        for path in ('/api/operations-history/unknown/inv1','/api/operations-history/commercial_invoice/missing'):
            self.assertIn((await self.client.get(path,headers=self.headers())).status_code,(404,422))
        self.assertEqual((await self.page(limit=51)).status_code,422)
        self.assertEqual((await self.client.delete('/api/operations-history/commercial_invoice/inv1',headers=self.headers())).status_code,405)

    async def test_archive_write_failure_keeps_business_record_and_history_unchanged(self):
        for i in range(2): self.ok(await self.edit('commercial_invoice',i))
        before=await self.current('commercial_invoice')
        async def fail(*args,**kwargs): raise RuntimeError('PRIVATE-ARCHIVE-CANARY')
        proxy=DatabaseProxy(self.db,operation_history=CollectionProxy(self.db.operation_history,insert_one=fail))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app,raise_app_exceptions=False),base_url='http://test') as other:
            with patch.object(server,'db',proxy),patch.object(history,'ROTATE_EVENTS',3):
                response=await other.put('/api/commercial-invoices/inv1',headers=self.headers(),json={**{k:before[k] for k in server.COMMERCIAL_INVOICE_DETAILS},'version':before['version'],'change_note':'Attempted revision'})
        self.assertEqual(response.status_code,500);self.assertNotIn('PRIVATE-ARCHIVE-CANARY',response.text)
        self.assertEqual(await self.current('commercial_invoice'),before);self.assertEqual(await self.db.operation_history.count_documents({}),0)
        with patch.object(history,'ROTATE_EVENTS',3): self.ok(await self.edit('commercial_invoice',9))
        self.assertEqual(len(await self.all_events()),4)

    async def test_business_failure_leaves_unreachable_block_and_retry_reuses_it_without_phantom_event(self):
        for i in range(2): self.ok(await self.edit('commercial_invoice',i))
        before=await self.current('commercial_invoice')
        async def fail(*args,**kwargs): raise RuntimeError('PRIVATE-CAS-CANARY')
        proxy=DatabaseProxy(self.db,commercial_invoices=CollectionProxy(self.db.commercial_invoices,replace_one=fail))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app,raise_app_exceptions=False),base_url='http://test') as other:
            with patch.object(server,'db',proxy),patch.object(history,'ROTATE_EVENTS',3):
                response=await other.put('/api/commercial-invoices/inv1',headers=self.headers(),json={**{k:before[k] for k in server.COMMERCIAL_INVOICE_DETAILS},'version':before['version'],'change_note':'Never committed'})
        self.assertEqual(response.status_code,500);self.assertNotIn('PRIVATE-CAS-CANARY',response.text)
        self.assertEqual(await self.current('commercial_invoice'),before);self.assertEqual(await self.db.operation_history.count_documents({}),1)
        events=await self.all_events();self.assertEqual(len(events),3);self.assertNotIn('Never committed',[e['note'] for e in events])
        with patch.object(history,'ROTATE_EVENTS',3): self.ok(await self.edit('commercial_invoice',9))
        self.assertEqual(await self.db.operation_history.count_documents({}),1);self.assertEqual(len(await self.all_events()),4)

    async def test_expired_lease_after_archive_insert_never_commits_a_new_business_revision(self):
        for i in range(2): self.ok(await self.edit('commercial_invoice',i))
        before=await self.current('commercial_invoice')
        @asynccontextmanager
        async def lease():
            calls=0
            async def ensure():
                nonlocal calls
                calls+=1
                if calls==2: raise server.HTTPException(409,'Lease expired')
            yield ensure
        with patch.object(server,'business_write_lock',lease),patch.object(history,'ROTATE_EVENTS',3):
            self.assertEqual((await self.edit('commercial_invoice',9)).status_code,409)
        self.assertEqual(await self.current('commercial_invoice'),before);self.assertEqual(len(await self.all_events()),3)
        self.assertEqual(await self.db.operation_history.count_documents({}),1)

    async def test_concurrent_edits_produce_one_revision_and_one_archive_block(self):
        for i in range(2): self.ok(await self.edit('commercial_invoice',i))
        before=await self.current('commercial_invoice');body={**{k:before[k] for k in server.COMMERCIAL_INVOICE_DETAILS},'version':before['version'],'change_note':'Concurrent review'}
        with patch.object(history,'ROTATE_EVENTS',3):
            responses=await asyncio.gather(*(self.client.put('/api/commercial-invoices/inv1',headers=self.headers(),json=body) for _ in range(2)))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409]);self.assertEqual(await self.db.operation_history.count_documents({}),1)
        events=await self.all_events();self.assertEqual(len(events),4);self.assertEqual(sum(e['note']=='Concurrent review' for e in events),1)

    async def test_cursor_is_signed_scoped_expiring_and_refuses_changed_snapshot(self):
        await self.rotate();first=self.ok(await self.page());token=first['next_cursor'];self.assertTrue(token)
        bad=token[:-1]+('0' if token[-1]!='0' else '1')
        self.assertEqual((await self.page(cursor=bad)).status_code,400)
        self.assertEqual((await self.client.get('/api/auth/me',headers={'Authorization':'Bearer '+token})).status_code,401)
        self.assertEqual((await self.page('packing_list',cursor=token)).status_code,400)
        expired=history.seal({'kind':'commercial_invoice','id':'inv1','version':first['snapshot_version'],'expires':0,'position':{'block':'recent','offset':0}},server.JWT_SECRET)
        self.assertEqual((await self.page(cursor=expired)).status_code,400)
        self.ok(await self.edit('commercial_invoice',90))
        self.assertEqual((await self.page(cursor=token)).status_code,409)
        self.assertEqual(len(await self.all_events()),9)

    async def test_corrupted_or_missing_committed_block_fails_without_fake_empty_history(self):
        record=await self.rotate();head=record['history_archive']['head'];block=await self.db.operation_history.find_one({'_id':head})
        await self.db.operation_history.update_one({'_id':head},{'$set':{'events.0.note':'Changed outside the application'}})
        self.assertEqual((await self.page(limit=50)).status_code,409)
        self.assertEqual((await self.page(limit=1)).status_code,409)
        await self.db.operation_history.replace_one({'_id':head},block)
        await self.db.operation_history.delete_one({'_id':head})
        self.assertEqual((await self.page(limit=50)).status_code,409)
        self.assertEqual((await self.edit('commercial_invoice',90)).status_code,409)
        self.assertEqual(await self.current('commercial_invoice'),record)

    async def test_byte_bounded_pages_continue_and_invalid_legacy_history_is_preserved(self):
        await self.rotate()
        with patch.object(history,'MAX_PAGE_BYTES',1000):
            events=await self.all_events(limit=50);self.assertEqual(len(events),8)
        before=await self.current('commercial_invoice')
        await self.db.commercial_invoices.update_one({'id':'inv1'},{'$set':{'history':before['history']*10}})
        invalid=await self.current('commercial_invoice')
        self.assertEqual((await self.edit('commercial_invoice',90)).status_code,400)
        self.assertEqual(await self.current('commercial_invoice'),invalid)

    async def test_quote_audit_references_are_not_copied_into_commercial_order_snapshot(self):
        record=await self.rotate('quotation')
        approved=self.ok(await self.client.post('/api/quotations/q1/status',headers=self.headers(),json={'version':record['version'],'status':'approved','change_note':'Approved reviewed conditions'}))
        draft=self.ok(await self.client.get('/api/quotations/q1/order-draft',headers=self.headers()))
        self.assertNotIn('history_archive',draft['source_quote_snapshot']);self.assertNotIn('history',draft['source_quote_snapshot'])
        self.assertEqual(len(await self.all_events('quotation')),9)
        self.assertEqual(approved['status'],'approved')

@unittest.skipUnless(os.environ.get('TEST_MONGO_URL'),'Requires disposable MongoDB')
class RealMongoOperationHistoryTests(OperationHistoryTests):
    real_mongo=True
