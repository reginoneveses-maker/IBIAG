"""Read-only administrative operations over actual HTTP and disposable MongoDB."""
import copy
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch
import test_commercial_invoices as fixtures
import server
from operations_dashboard import operation_rows

class OperationsTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=fixtures.CommercialInvoiceTests.headers
    create_order=fixtures.CommercialInvoiceTests.create_order
    update_order=fixtures.CommercialInvoiceTests.update_order
    asyncTearDown=fixtures.CommercialInvoiceTests.asyncTearDown
    async def asyncSetUp(self):
        await fixtures.CommercialInvoiceTests.asyncSetUp(self)
        self.order.update(order_date='2026-10-01',receivable_due_date='2026-10-10')
        await self.db.orders.replace_one({'id':'sale'},copy.deepcopy(self.order))
    async def get(self,query=''):
        return await self.client.get('/api/gestao/operations'+query,headers=self.headers())
    async def test_requires_admin_and_never_writes_or_exposes_private_fields(self):
        for user,status in ((None,401),('owner',403),('stranger',403)):
            response=await self.client.get('/api/gestao/operations',headers=self.headers(user) if user else {'X-User-Role':'admin'})
            self.assertEqual(response.status_code,status)
        before=await self.db.orders.find_one({'id':'sale'});finance=await server.all_finance_entries();locks=await self.db.workflow_locks.find({}).to_list(None)
        response=await self.get();self.assertEqual(response.status_code,200,response.text)
        data=response.json();self.assertEqual(data['total'],1);row=data['rows'][0]
        for name in ('supplier','unit_price','total_usd','PRIVATE-ORDER-CANARY','PRIVATE-COST-CANARY','history','payment_terms'):
            self.assertNotIn(name,str(data))
        self.assertEqual(set(row['flags']),{'receivable_overdue','documents_pending','shipment_missing'})
        self.assertEqual(await self.db.orders.find_one({'id':'sale'}),before)
        self.assertEqual(await server.all_finance_entries(),finance)
        self.assertEqual(await self.db.workflow_locks.find({}).to_list(None),locks)
    async def test_filters_literal_country_calendar_status_and_archives(self):
        await self.db.orders.insert_many([{**self.order,'id':'second','customer_country':'Brazil','status':'draft'},
            {**self.order,'id':'archived','deleted_at':'2026-10-01'}])
        data=(await self.get('?country=Portugal&status=confirmed&date_from=2026-10-01&date_to=2026-10-01')).json()
        self.assertEqual([r['id'] for r in data['rows']],['sale']);self.assertEqual(data['summary']['total'],1)
        self.assertEqual((await self.get('?country=%7B%22%24ne%22%3Anull%7D')).json()['total'],0)
        for query in ('?date_from=2026-02-30','?date_from=2026-11-01&date_to=2026-10-01','?date_to=20261001'):
            self.assertEqual((await self.get(query)).status_code,400)
        for query in ('?status=forged','?attention=secret','?limit=101','?skip=-1','?country=%00'):
            self.assertEqual((await self.get(query)).status_code,422)
    async def test_attention_filters_list_but_summary_stays_for_whole_base_filter_and_pages_stable(self):
        await self.db.orders.insert_one({**self.order,'id':'draft','status':'draft'})
        data=(await self.get('?attention=documents_pending&limit=1')).json()
        self.assertEqual(data['summary']['total'],2);self.assertEqual(data['total'],1)
        self.assertEqual(data['summary']['attention']['documents_pending'],1)
        self.assertEqual(data['rows'][0]['id'],'sale')
        self.assertEqual((await self.get('?skip=1&limit=1')).json()['rows'][0]['id'],'draft')
        self.assertEqual((await self.get('?skip=2')).json()['rows'],[])
    async def test_document_status_is_revision_checked_and_ambiguous_or_cancelled_never_ready(self):
        snapshot=server.commercial_snapshot(self.order);packing=server.packing_snapshot(self.order)
        inv={'id':'ci','order_id':'sale','status':'approved','source_order_revision':server.invoice_revision(snapshot)}
        pl={'id':'pl','order_id':'sale','status':'approved','source_order_revision':server.packing_revision(packing)}
        await self.db.commercial_invoices.insert_one(copy.deepcopy(inv));await self.db.packing_lists.insert_one(copy.deepcopy(pl))
        data=(await self.get()).json();row=data['rows'][0];self.assertEqual(row['invoice_status'],'approved');self.assertEqual(row['packing_status'],'approved');self.assertNotIn('documents_pending',row['flags'])
        await self.db.orders.update_one({'id':'sale'},{'$set':{'number':'External change'}})
        row=(await self.get()).json()['rows'][0];self.assertEqual(row['invoice_status'],'outdated');self.assertEqual(row['packing_status'],'outdated');self.assertIn('data_review',row['flags'])
        await self.db.commercial_invoices.insert_one({**inv,'id':'ci2'})
        await self.db.packing_lists.update_one({'id':'pl'},{'$set':{'status':'cancelled'}})
        row=(await self.get()).json()['rows'][0];self.assertEqual(row['invoice_status'],'ambiguous');self.assertEqual(row['packing_status'],'missing')
    async def test_payment_is_real_linked_ledger_and_today_is_not_overdue_in_fortaleza(self):
        class FixedClock(datetime):
            @classmethod
            def now(cls,tz=None): return datetime(2026,10,20,1,0,tzinfo=timezone.utc).astimezone(tz or timezone.utc)
        await self.db.orders.update_one({'id':'sale'},{'$set':{'receivable_due_date':'2026-10-19'}})
        with patch.object(server,'datetime',FixedClock):
            data=(await self.get()).json();self.assertEqual(data['today'],'2026-10-19');self.assertEqual(data['timezone'],'America/Fortaleza');self.assertNotIn('receivable_overdue',data['rows'][0]['flags'])
        await self.db.orders.update_one({'id':'sale'},{'$set':{'receivable_due_date':'2026-10-01'}})
        self.assertIn('receivable_overdue',(await self.get()).json()['rows'][0]['flags'])
        paid=await self.client.patch('/api/finance/order:sale/toggle-paid',headers=self.headers(),json={'paid':True})
        self.assertEqual(paid.status_code,200,paid.text);self.assertTrue(paid.json()['paid'])
        row=(await self.get()).json()['rows'][0];self.assertTrue(row['finance_paid']);self.assertNotIn('receivable_overdue',row['flags'])
        self.assertEqual(len(await server.all_finance_entries()),1)
    async def test_legacy_bad_dates_and_invalid_source_never_present_as_completed(self):
        for changes in ({'workflow_enabled':False},{'order_date':'invalid'},{'receivable_due_date':'2026-02-30'},
                        {'items':[]},{'finance_paid':'yes'},{'status':'invented'}):
            await self.db.orders.replace_one({'id':'sale'},{**self.order,**changes})
            response=await self.get();self.assertEqual(response.status_code,200,response.text)
            row=response.json()['rows'][0];self.assertIn('data_review',row['flags'])
            self.assertNotEqual((row['invoice_status'],row['packing_status']),('approved','approved'))
    async def test_shipment_overdue_and_recorded_arrival_stop_the_expected_arrival_alert(self):
        shipment={'status':'in_transit','planned_departure':'2026-10-02','planned_arrival':'2026-10-03','actual_departure':'2026-10-02'}
        await self.db.orders.update_one({'id':'sale'},{'$set':{'status':'shipped','shipment':shipment}})
        row=(await self.get()).json()['rows'][0];self.assertIn('shipment_overdue',row['flags']);self.assertNotIn('shipment_missing',row['flags'])
        await self.db.orders.update_one({'id':'sale'},{'$set':{'shipment':{**shipment,'status':'arrived','actual_arrival':'2026-10-04'}}})
        self.assertNotIn('shipment_overdue',(await self.get()).json()['rows'][0]['flags'])
    async def test_safety_caps_and_duplicate_ids_refuse_incomplete_or_ambiguous_totals(self):
        await self.db.orders.insert_one(copy.deepcopy(self.order))
        self.assertEqual((await self.get()).status_code,409)
        await self.db.orders.delete_many({})
        await self.db.orders.insert_many([{**self.order,'id':f'o{i}'} for i in range(1001)])
        self.assertEqual((await self.get()).status_code,413)
        self.assertEqual((await self.get('?country=missing')).json()['total'],0)

@unittest.skipUnless(os.environ.get('TEST_MONGO_URL'),'Requires disposable MongoDB')
class RealMongoOperationsTests(OperationsTests):
    real_mongo=True
