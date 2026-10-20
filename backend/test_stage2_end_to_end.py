"""One isolated CRM→quote→order→documents→shipment→receipt HTTP journey."""
import os
import unittest
import test_commercial_invoices as fixtures
import server

class Stage2JourneyTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=fixtures.CommercialInvoiceTests.headers
    create_order=fixtures.CommercialInvoiceTests.create_order
    update_order=fixtures.CommercialInvoiceTests.update_order
    asyncSetUp=fixtures.CommercialInvoiceTests.asyncSetUp
    asyncTearDown=fixtures.CommercialInvoiceTests.asyncTearDown
    def ok(self,response):
        self.assertEqual(response.status_code,200,response.text[:500]);return response.json()
    async def test_quote_order_documents_shipment_receipt_remain_single_linked_operation(self):
        price=self.ok(await self.client.get('/api/prices/price/order-draft',headers=self.headers()))
        quote=self.ok(await self.client.post('/api/quotations',headers=self.headers(),json={'id':'full-quote','reference':'Q-FULL','lead_id':'lead1',
            'source_price_id':'price','source_price_revision':price['source_price_revision'],'valid_until':'2099-12-31','incoterm':'FOB',
            'payment_terms':'Prepaid','delivery_terms':'30 days','change_note':'Review whole operation'}))
        quote=self.ok(await self.client.post('/api/quotations/full-quote/status',headers=self.headers(),json={'version':quote['version'],'status':'approved','change_note':'Internal terms approved'}))
        source=self.ok(await self.client.get('/api/quotations/full-quote/order-draft',headers=self.headers()))
        order=self.ok(await self.client.post('/api/orders',headers=self.headers(),json={**source,'id':'full-sale','number':'SO-FULL',
            'status':'draft','order_date':'2026-10-01','receivable_due_date':'2026-10-10','track_stock':True}))
        self.assertEqual(order['lead_id'],'lead1');self.assertEqual(order['source_quote_id'],'full-quote')
        self.assertFalse([f for f in await server.all_finance_entries() if f['source_order_id']=='full-sale'])
        order=self.ok(await self.client.put('/api/orders/full-sale',headers=self.headers(),json={**order,'status':'confirmed'}))
        invoice=self.ok(await self.client.post('/api/commercial-invoices',headers=self.headers(),json={**self.invoice_body,'id':'full-ci','reference':'CI-FULL',
            'order_id':'full-sale','source_order_version':order['version'],'payment_terms':'Prepaid','delivery_terms':'30 days'}))
        invoice=self.ok(await self.client.post('/api/commercial-invoices/full-ci/status',headers=self.headers(),json={
            'version':invoice['version'],'status':'approved','details_confirmed':True,'change_note':'Complete invoice reviewed'}))
        packing=self.ok(await self.client.post('/api/packing-lists',headers=self.headers(),json={'id':'full-pl','reference':'PL-FULL','order_id':'full-sale',
            'source_order_version':order['version'],'issue_date':'2026-10-19','seller_name':'Synthetic Seller','seller_address':'Test address',
            'seller_country':'Brazil','buyer_address':'Test buyer address','buyer_country':'Portugal','signatory':'Synthetic Operator',
            'change_note':'Complete packing reviewed','packages':[{'marks':'BOXES 1-2','packaging':'Carton','package_count':2,
                'net_kg':'2','gross_kg':'2.5','allocations':[{'index':0,'quantity':'2'}]}]}))
        packing=self.ok(await self.client.post('/api/packing-lists/full-pl/status',headers=self.headers(),json={
            'version':packing['version'],'status':'approved','details_confirmed':True,'change_note':'Physical data reviewed'}))
        pdfs={}
        for path in ('commercial-invoices/full-ci','packing-lists/full-pl'):
            response=await self.client.get('/api/'+path+'/pdf',headers=self.headers());self.assertEqual(response.status_code,200);pdfs[path]=response.content
        shipment={'mode':'sea','reference':'SHIP-FULL','origin':'Santos','destination':'Lisbon','responsible_id':'admin',
            'planned_departure':'2026-10-02','planned_arrival':'2026-10-03','change_note':'Review complete shipment'}
        version=order['version']
        for state,dates in (('planned',{}),('booked',{}),('in_transit',{'actual_departure':'2026-10-02'}),
                            ('arrived',{'actual_departure':'2026-10-02','actual_arrival':'2026-10-03'}),
                            ('delivered',{'actual_departure':'2026-10-02','actual_arrival':'2026-10-03','actual_delivery':'2026-10-04'})):
            result=self.ok(await self.client.put('/api/orders/full-sale/shipment',headers=self.headers(),json={**shipment,**dates,'status':state,'version':version}))
            version=result['version']
            ledger=[f for f in await server.all_finance_entries() if f.get('source_order_id')=='full-sale']
            self.assertEqual(len(ledger),1);self.assertEqual(ledger[0]['amount'],8.52)
        receipt=self.ok(await self.client.patch('/api/finance/order:full-sale/toggle-paid',headers=self.headers(),json={'paid':True}))
        repeated=self.ok(await self.client.patch('/api/finance/order:full-sale/toggle-paid',headers=self.headers(),json={'paid':True}))
        self.assertTrue(receipt['paid']);self.assertEqual(receipt['paid_date'],repeated['paid_date'])
        for path,data in pdfs.items():
            response=await self.client.get('/api/'+path+'/pdf',headers=self.headers());self.assertEqual(response.status_code,200);self.assertEqual(response.content,data)
        report=self.ok(await self.client.get('/api/gestao/operations?status=delivered',headers=self.headers()))
        self.assertEqual(report['total'],1);row=report['rows'][0]
        self.assertEqual(row['id'],'full-sale');self.assertEqual(row['flags'],[]);self.assertTrue(row['finance_paid'])
        self.assertEqual(row['invoice_status'],'approved');self.assertEqual(row['packing_status'],'approved')
        stored=await self.db.orders.find_one({'id':'full-sale'});self.assertEqual(len(stored['shipment']['history']),5)
        inventory=await server.business_snapshot()
        balances=server.inventory_balances(*inventory)
        self.assertEqual(balances['p']['stock'],8)
        self.assertEqual(balances['p']['stock_reserved'],0)
        self.assertEqual(await self.db.orders.count_documents({'source_quote_id':'full-quote'}),1)
        self.assertEqual((await self.client.get('/api/quotations/full-quote/order-draft',headers=self.headers())).status_code,409)

@unittest.skipUnless(os.environ.get('TEST_MONGO_URL'),'Requires disposable MongoDB')
class RealMongoStage2JourneyTests(Stage2JourneyTests):
    real_mongo=True
