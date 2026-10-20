"""Exercise real HTTP packing routes, also against disposable MongoDB in CI."""
import asyncio
import copy
import io
import os
import unittest
from unittest.mock import patch
from pypdf import PdfReader
import test_commercial_invoices as fixtures
import server

class PackingListTests(unittest.IsolatedAsyncioTestCase):
    real_mongo = False
    headers = fixtures.CommercialInvoiceTests.headers
    create_order = fixtures.CommercialInvoiceTests.create_order
    update_order = fixtures.CommercialInvoiceTests.update_order
    asyncTearDown = fixtures.CommercialInvoiceTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.CommercialInvoiceTests.asyncSetUp(self)
        self.body = {"id":"pl1","reference":"PL-TEST-1","order_id":"sale","source_order_version":self.order["version"],
            "issue_date":"2026-10-19","seller_name":"Test Seller","seller_address":"Example address","seller_country":"Brazil",
            "buyer_address":"Test Buyer Address","buyer_country":"Portugal","signatory":"Test Operator","change_note":"Packing review",
            "packages":[{"marks":"BOXES 1-2","packaging":"Carton","package_count":2,"net_kg":"2","gross_kg":"2.5","volume_m3":"0.02",
                "allocations":[{"index":0,"quantity":"2"}]}]}

    async def create(self, **changes):
        return await self.client.post('/api/packing-lists',headers=self.headers(),json={**self.body,**changes})

    async def document(self, **changes):
        response=await self.create(**changes)
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def decide(self, record, status='approved', **changes):
        return await self.client.post(f'/api/packing-lists/{record["id"]}/status',headers=self.headers(),json={
            'version':record['version'],'status':status,'details_confirmed':True,'change_note':'Explicit packing decision',**changes})

    async def approved(self):
        response=await self.decide(await self.document())
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def pdf(self):
        return await self.client.get('/api/packing-lists/pl1/pdf',headers=self.headers())

    def details(self, record=None):
        return {k:(record or self.body)[k] for k in server.PACKING_DETAILS if k in (record or self.body)}

    @staticmethod
    def text(response):
        return '\n'.join(p.extract_text() for p in PdfReader(io.BytesIO(response.content)).pages)

    async def test_preview_create_and_pdf_exclude_all_financial_and_private_fields(self):
        before=await self.db.orders.find_one({'id':'sale'})
        finance=await server.all_finance_entries()
        preview=await self.client.get('/api/orders/sale/packing-list-draft',headers=self.headers())
        self.assertEqual(preview.status_code,200,preview.text)
        self.assertEqual(await self.db.packing_lists.count_documents({}),0)
        record=await self.document()
        for data in (preview.json(),record):
            for private in ('unit_price','line_total','total_usd','supplier_id','supplier_name','PRIVATE-COST-CANARY','PRIVATE-ORDER-CANARY','payment_terms'):
                self.assertNotIn(private,str(data))
        self.assertEqual(record['totals'],{'package_count':2,'net_kg':'2','gross_kg':'2.5','volume_m3':'0.02'})
        self.assertEqual(record['history'][0]['by'],'admin')
        pdf=await self.pdf();self.assertEqual(pdf.status_code,200,pdf.text[:100])
        text=self.text(pdf);self.assertIn('DRAFT',text);self.assertIn('PACKING LIST',text)
        self.assertNotIn('USD',text);self.assertNotIn('Fornecedor',text)
        self.assertEqual(await self.db.orders.find_one({'id':'sale'}),before)
        self.assertEqual(await server.all_finance_entries(),finance)
        self.assertEqual(await self.db.commercial_invoices.count_documents({}),0)
        self.assertEqual(await self.db.invoices.count_documents({}),0)

    async def test_every_route_requires_admin_including_owner_and_spoofed_headers(self):
        await self.document()
        for identity,expected in ((None,401),('owner',403),('stranger',403)):
            headers=self.headers(identity) if identity else {}
            headers={**headers,'X-User-Role':'admin'}
            for path in ('/orders/sale/packing-list-draft','/packing-lists','/packing-lists/pl1','/packing-lists/pl1/pdf'):
                self.assertEqual((await self.client.get('/api'+path,headers=headers)).status_code,expected)
            self.assertEqual((await self.client.post('/api/packing-lists',headers=headers,json=self.body)).status_code,expected)
            self.assertEqual((await self.client.put('/api/packing-lists/pl1',headers=headers,json={**self.details(),'version':1})).status_code,expected)
            self.assertEqual((await self.client.post('/api/packing-lists/pl1/status',headers=headers,json={'version':1,'status':'approved','change_note':'Forged'})).status_code,expected)

    async def test_strict_contract_rejects_forged_snapshots_totals_and_numeric_types(self):
        for key,value in (('totals',{}),('history',[]),('source_order_snapshot',{}),('status','approved'),('source_order_version',True),('id','../../secret'),('reference','Bad\r\nHeader'),('issue_date','2026-02-30')):
            response=await self.create(**{key:value});self.assertIn(response.status_code,(400,422),response.text)
        for key,value in (('package_count',True),('net_kg',2),('gross_kg','NaN'),('volume_m3','1e3')):
            groups=copy.deepcopy(self.body['packages']);groups[0][key]=value
            self.assertEqual((await self.create(packages=groups)).status_code,422)
        self.assertEqual(await self.db.packing_lists.count_documents({}),0)

    async def test_rejects_bad_order_stale_preview_and_ambiguous_source(self):
        for changes in ({'order_id':'missing'},{'source_order_version':self.order['version']+1}):
            self.assertIn((await self.create(**changes)).status_code,(404,409))
        for values in ({'status':'draft'},{'status':'cancelled'},{'workflow_enabled':False},{'deleted_at':'2026-01-01'}):
            await self.db.orders.replace_one({'id':'sale'},{**self.order,**values})
            self.assertEqual((await self.create()).status_code,409)
        await self.db.orders.replace_one({'id':'sale'},copy.deepcopy(self.order))
        await self.db.orders.insert_one(copy.deepcopy(self.order))
        self.assertEqual((await self.create()).status_code,409)

    async def test_decimal_reconciliation_and_group_totals_are_not_multiplied_by_package_count(self):
        groups=copy.deepcopy(self.body['packages']);groups[0]['allocations'][0]['quantity']='0.123456789012'
        groups.append({**copy.deepcopy(groups[0]),'marks':'BOXES 3-4','allocations':[{'index':0,'quantity':'1.876543210988'}]})
        doc=await self.document(packages=groups)
        approved=await self.decide(doc);self.assertEqual(approved.status_code,200,approved.text)
        self.assertEqual(approved.json()['totals'],{'package_count':4,'net_kg':'4','gross_kg':'5.0','volume_m3':'0.04'})
        text=self.text(await self.pdf());self.assertIn('0.123456789012 kg',text);self.assertIn('1.876543210988 kg',text)

    async def test_drafts_allow_incomplete_packing_but_approval_requires_exact_complete_order(self):
        for groups in ([],[{**self.body['packages'][0],'allocations':[{'index':0,'quantity':'1.999999999999'}]}],
                       [{**self.body['packages'][0],'net_kg':'','gross_kg':''}], [{**self.body['packages'][0],'marks':''}],
                       [{**self.body['packages'][0],'packaging':''}]):
            doc=await self.document(packages=groups)
            if not groups or not groups[0].get('net_kg'):
                self.assertIsNone(doc['totals']['net_kg'])
                pdf=await self.client.get(f'/api/packing-lists/{doc["id"]}/pdf',headers=self.headers())
                self.assertEqual(pdf.status_code,200)
                self.assertIn('Not provided for all groups',self.text(pdf))
                self.assertNotIn('Net weight kg: 0',self.text(pdf))
            self.assertEqual((await self.decide(doc)).status_code,400)
            self.assertEqual((await self.decide(doc,'cancelled')).status_code,200)
            # Fresh references remain required, even after cancellation.
            self.body['id']+='x';self.body['reference']+='x'
        self.assertEqual(await self.db.packing_lists.count_documents({'status':'approved'}),0)

    async def test_overallocation_duplicate_marks_items_and_invalid_weights_are_refused(self):
        original=self.body['packages'][0]
        bad=[{**original,'net_kg':'3','gross_kg':'2'}, {**original,'volume_m3':'0'},
             {**original,'allocations':[{'index':0,'quantity':'2.000000000001'}]},
             {**original,'allocations':[{'index':1,'quantity':'1'}]},
             {**original,'allocations':[{'index':0,'quantity':'1'},{'index':0,'quantity':'1'}]},
             {**original,'net_kg':'1000000000001'}]
        for group in bad:
            response=await self.create(packages=[group]);self.assertEqual(response.status_code,400,response.text)
        group={**original,'allocations':[{'index':0,'quantity':'1'}]}
        self.assertEqual((await self.create(packages=[group,{**group,'marks':' boxes 1-2 '}])).status_code,400)
        self.assertEqual(await self.db.packing_lists.count_documents({}),0)

    async def test_multiple_items_must_each_be_fully_allocated_and_optional_volume_stays_unknown(self):
        order=copy.deepcopy(self.order);order['items'].append({**order['items'][0],'quantity':3});order['total_usd']=21.30
        await self.db.orders.replace_one({'id':'sale'},order)
        group={**self.body['packages'][0],'volume_m3':'','allocations':[{'index':0,'quantity':'2'}]}
        doc=await self.document(packages=[group]);self.assertEqual((await self.decide(doc)).status_code,400)
        edit=await self.client.put('/api/packing-lists/pl1',headers=self.headers(),json={**self.details(doc),'version':1,'change_note':'Include second item','packages':[{**group,'allocations':[{'index':0,'quantity':'2'},{'index':1,'quantity':'3'}]}]})
        self.assertEqual(edit.status_code,200,edit.text)
        approved=await self.decide(edit.json());self.assertEqual(approved.status_code,200,approved.text)
        self.assertIsNone(approved.json()['totals']['volume_m3'])
        self.assertIn('Not provided for all groups',self.text(await self.pdf()))

    async def test_approval_requires_explicit_review_complete_parties_and_recipient(self):
        doc=await self.document()
        self.assertEqual((await self.decide(doc,details_confirmed=False)).status_code,400)
        self.assertEqual((await self.decide(doc,change_note='')).status_code,422)
        for changes in ({'seller_address':''},{'delivery_same_as_buyer':False}):
            edit=await self.client.put('/api/packing-lists/pl1',headers=self.headers(),json={**self.details(doc),**changes,'version':doc['version'],'change_note':'Review missing details'})
            self.assertEqual(edit.status_code,200,edit.text);doc=edit.json()
            self.assertEqual((await self.decide(doc)).status_code,400)

    async def test_missing_buyer_country_is_never_inferred_and_must_be_reviewed_before_approval(self):
        await self.db.orders.update_one({'id':'sale'},{'$set':{'customer_country':''}})
        doc=await self.document(buyer_country='')
        self.assertEqual(doc['buyer_country'],'')
        self.assertEqual((await self.decide(doc)).status_code,400)
        edit=await self.client.put('/api/packing-lists/pl1',headers=self.headers(),json={**self.details(doc),'buyer_country':'Portugal','version':1,'change_note':'Review missing buyer country'})
        self.assertEqual(edit.status_code,200,edit.text)
        self.assertEqual((await self.decide(edit.json())).status_code,200)

    async def test_approved_immutable_cancelled_terminal_and_references_retained(self):
        doc=await self.approved()
        self.assertEqual((await self.client.put('/api/packing-lists/pl1',headers=self.headers(),json={**self.details(doc),'version':doc['version'],'change_note':'Rewrite approved'})).status_code,409)
        cancelled=await self.decide(doc,'cancelled');self.assertEqual(cancelled.status_code,200)
        self.assertEqual((await self.decide(cancelled.json())).status_code,409)
        self.assertIn('CANCELLED',self.text(await self.pdf()))
        self.assertEqual((await self.create(id='pl2')).status_code,409)
        new=await self.document(id='pl2',reference='PL-2')
        preview=await self.client.get('/api/orders/sale/packing-list-draft',headers=self.headers())
        self.assertEqual(preview.json()['active_packing_id'],new['id'])

    async def test_active_packing_blocks_order_items_customer_and_cancel_but_allows_payment_logistics(self):
        doc=await self.approved();pdf_before=(await self.pdf()).content
        for changes in ({'number':'CHANGED'},{'status':'cancelled'}):
            response=await self.update_order({**self.order,**changes});self.assertEqual(response.status_code,409,response.text)
        response=await self.update_order({**self.order,'finance_paid':True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual((await self.pdf()).content,pdf_before)
        self.assertEqual(len(await server.all_finance_entries()),1)
        self.assertEqual((await self.decide(doc,'cancelled')).status_code,200)
        response=await self.update_order({**response.json(),'status':'cancelled'});self.assertEqual(response.status_code,200,response.text)

    async def test_concurrent_creation_and_decisions_have_single_winner(self):
        responses=await asyncio.gather(self.create(),self.create(id='pl2',reference='PL-2'))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409])
        doc=next(r.json() for r in responses if r.status_code==200)
        decisions=await asyncio.gather(self.decide(doc),self.decide(doc,'cancelled'))
        self.assertEqual(sorted(r.status_code for r in decisions),[200,409])
        self.assertEqual(await self.db.packing_lists.count_documents({}),1)
        saved=await self.db.packing_lists.find_one({'id':doc['id']});self.assertEqual(len(saved['history']),2)

    async def test_order_edit_race_does_not_create_stale_document(self):
        document,order=await asyncio.gather(self.create(),self.update_order({**self.order,'number':'CHANGED'}))
        self.assertEqual(sorted((document.status_code,order.status_code)),[200,409])
        self.assertEqual(await self.db.packing_lists.count_documents({}),int(document.status_code==200))

    async def test_external_source_drift_blocks_approval_and_approved_download(self):
        doc=await self.document()
        await self.db.orders.update_one({'id':'sale'},{'$set':{'number':'EXTERNAL'}})
        self.assertEqual((await self.decide(doc)).status_code,409)
        detail=await self.client.get('/api/packing-lists/pl1',headers=self.headers());self.assertTrue(detail.json()['source_changed'])
        await self.db.orders.update_one({'id':'sale'},{'$set':{'number':self.order['number']}})
        approved=await self.decide(doc);self.assertEqual(approved.status_code,200)
        await self.db.orders.update_one({'id':'sale'},{'$set':{'number':'EXTERNAL'}})
        self.assertEqual((await self.pdf()).status_code,409)

    async def test_pdf_is_private_deterministic_escaped_and_cancellation_during_render_is_refused(self):
        doc=await self.document(notes='<img src="https://private.invalid"> & <script>text</script>')
        response=await self.decide(doc);self.assertEqual(response.status_code,200,response.text);doc=response.json()
        response=await self.pdf();self.assertEqual(response.headers['cache-control'],'private, no-store')
        self.assertEqual(response.headers['x-content-type-options'],'nosniff')
        self.assertIn('-approved-v2.pdf',response.headers['content-disposition'])
        self.assertEqual((await self.pdf()).content,response.content)
        reader=PdfReader(io.BytesIO(response.content));self.assertFalse(reader.pages[0].get('/Annots'))
        self.assertNotIn('/OpenAction',reader.trailer['/Root']);self.assertIn('<script>text</script>',self.text(response))
        started=asyncio.Event();finish=asyncio.Event();original=server.packing_pdf_bytes
        async def delayed(record):
            result=await original(record);started.set();await finish.wait();return result
        with patch.object(server,'packing_pdf_bytes',side_effect=delayed):
            task=asyncio.create_task(self.pdf());await asyncio.wait_for(started.wait(),10)
            self.assertEqual((await self.decide(doc,'cancelled')).status_code,200);finish.set()
            self.assertEqual((await task).status_code,409)

    async def test_list_projection_pagination_filters_and_duplicate_document_refusal(self):
        await self.document()
        response=await self.client.get('/api/packing-lists?status=draft&order_id=sale&limit=1',headers=self.headers())
        self.assertEqual(response.status_code,200,response.text);self.assertEqual(len(response.json()),1)
        self.assertNotIn('packages',response.json()[0]);self.assertNotIn('history',response.json()[0])
        self.assertEqual((await self.client.get('/api/packing-lists?skip=1',headers=self.headers())).json(),[])
        self.assertEqual((await self.client.get('/api/packing-lists?limit=251',headers=self.headers())).status_code,422)
        self.assertEqual((await self.client.get('/api/packing-lists?status=forged',headers=self.headers())).status_code,422)
        await self.db.packing_lists.insert_one({**(await self.db.packing_lists.find_one({'id':'pl1'})),'_id':'duplicate'})
        self.assertEqual((await self.client.get('/api/packing-lists/pl1',headers=self.headers())).status_code,409)

    async def test_renderer_failure_glyph_and_bounded_history_leave_approval_uncommitted(self):
        doc=await self.document(notes='漢字')
        self.assertEqual((await self.decide(doc)).status_code,400)
        saved=await self.db.packing_lists.find_one({'id':'pl1'});self.assertEqual(saved['version'],1)
        edit=await self.client.put('/api/packing-lists/pl1',headers=self.headers(),json={**self.details(doc),'notes':'Safe text','version':1,'change_note':'Use supported glyphs'})
        self.assertEqual(edit.status_code,200,edit.text);doc=edit.json()
        with patch.object(server,'render_packing_list',side_effect=ValueError('PRIVATE-RENDER-CANARY')):
            response=await self.decide(doc);self.assertEqual(response.status_code,400);self.assertNotIn('PRIVATE-RENDER-CANARY',response.text)
        for extra,expected in (({'history':[{}]*50},400),({'notes':'x'*300000},413)):
            await self.db.packing_lists.update_one({'id':'pl1'},{'$set':extra})
            before=await self.db.packing_lists.find_one({'id':'pl1'})
            self.assertEqual((await self.decide(doc,'cancelled')).status_code,expected)
            self.assertEqual(await self.db.packing_lists.find_one({'id':'pl1'}),before)
            await self.db.packing_lists.replace_one({'id':'pl1'},{k:v for k,v in doc.items() if k!='source_changed'})

    async def test_multipage_pdf_retains_all_groups_and_headers(self):
        groups=[{**self.body['packages'][0],'marks':f'GROUP {i:02d}', 'packaging':('Long carton description '*3),'allocations':[{'index':0,'quantity':'0.08'}]} for i in range(25)]
        await self.document(packages=groups)
        response=await self.pdf();self.assertEqual(response.status_code,200,response.text[:100])
        reader=PdfReader(io.BytesIO(response.content));self.assertGreater(len(reader.pages),1)
        for page in reader.pages:
            text=page.extract_text();self.assertIn('PACKING LIST',text);self.assertIn('DRAFT',text)
        text=self.text(response)
        for i in range(25):self.assertIn(f'GROUP {i:02d}',text)

@unittest.skipUnless(os.environ.get('TEST_MONGO_URL'),'Requires disposable MongoDB')
class RealMongoPackingListTests(PackingListTests):
    real_mongo = True
