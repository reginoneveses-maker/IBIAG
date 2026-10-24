"""Unified UI/API uses synthetic Mongo only; repeated with disposable Mongo in CI."""
import asyncio
import copy
import os
import unittest
import uuid
import test_order_price_source as support
import server

def state(currency="USD"):
    return {"productId":"offer","fields":{"product":"Product","supplier":"Supplier","customer":"Original Buyer",
      "opportunityId":"lead1","quantity":"1000","cost":"17.5","rate":"5","margin":"20","fees":"0",
      "indirect":"0","currency":currency,"incoterm":"EXW","namedPlace":"Synthetic factory","mode":"Marítimo"},
      "sources":{},"sourceValues":{},"packages":[],"taxes":[],"confirmed":True,"freightConfirmed":False,
      "packagingCharge":"included","packagingExtra":"","updatedAt":""}

class IntegratedWorkspaceTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=support.PriceOrderTests.headers
    asyncTearDown=support.PriceOrderTests.asyncTearDown
    async def asyncSetUp(self):
        await support.PriceOrderTests.asyncSetUp(self)
    def ok(self, r):
        self.assertEqual(r.status_code,200,r.text[:500])
        return r.json()
    async def req(self,method,path,**kwargs):
        return await self.client.request(method,"/api/integrated"+path,headers=self.headers(),**kwargs)
    async def test_native_identity_read_through_and_no_catalog_mutation(self):
        before=await self.db.product_offers.find_one({"id":"offer"})
        data=self.ok(await self.req("GET","/catalog"))
        self.assertEqual(data["offers"][0]["id"],"offer")
        self.assertEqual(data["offers"][0]["profile"]["supplier"],"Supplier")
        self.assertNotIn("cost",data["offers"][0]["profile"]) # unknown is not zero
        customers=self.ok(await self.req("GET","/customers"))["customers"]
        self.assertIn("lead1",[r["id"] for r in customers])
        self.assertEqual(await self.db.product_offers.find_one({"id":"offer"}),before)
        self.assertEqual(await self.db.integrated_quotes.count_documents({}),0)
        for path in ("/catalog","/customers","/workspace"):
            self.assertEqual((await self.client.get("/api/integrated"+path,headers=self.headers("owner"))).status_code,403)
            self.assertIn((await self.client.get("/api/integrated"+path)).status_code,(401,403))
        await self.db.products.update_one({"id":"p"},{"$set":{"name":"Updated ingredient"}})
        self.assertEqual(self.ok(await self.req("GET","/catalog"))["offers"][0]["name"],"Updated ingredient")
    async def test_incomplete_draft_recovery_cas_replay_and_isolation(self):
        data=state()
        data["fields"]["cost"]=""
        data["confirmed"]=False
        body={"draft":{"id":"DRAFT-test","title":"Synthetic draft","kind":"completion","data":data,"updatedAt":"2026-10-24T00:00:00.000Z"},"expectedUpdatedAt":None,"requestId":str(uuid.uuid4())}
        saved=self.ok(await self.req("PUT","/drafts/DRAFT-test",json=body))["draft"]
        self.assertEqual(saved["data"]["fields"]["cost"],"")
        self.assertEqual(self.ok(await self.req("PUT","/drafts/DRAFT-test",json=body))["draft"],saved)
        changed=copy.deepcopy(body);changed["draft"]["data"]["fields"]["cost"]="20"
        self.assertEqual((await self.req("PUT","/drafts/DRAFT-test",json=changed)).status_code,409)
        changed["requestId"]=str(uuid.uuid4())
        self.assertEqual((await self.req("PUT","/drafts/DRAFT-test",json=changed)).status_code,409)
        changed["expectedUpdatedAt"]=saved["updatedAt"]
        changed["draft"]["updatedAt"]=saved["updatedAt"]
        self.ok(await self.req("PUT","/drafts/DRAFT-test",json=changed))
        # New HTTP client after closing and reopening the authenticated session.
        import httpx
        await self.client.aclose()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test")
        recovered=self.ok(await self.req("GET","/workspace"))["drafts"][0]
        self.assertEqual(recovered["data"]["fields"]["cost"],"20")
        await self.db.users.insert_one({"id":"otheradmin","email":"otheradmin@example.com","role":"admin"})
        response=await self.client.get("/api/integrated/workspace",headers=self.headers("otheradmin"))
        self.assertEqual(response.json(),{"drafts":[],"quotes":[]})
    async def test_server_calculation_snapshot_and_missing_optional_fields(self):
        payload={"id":"COT-integrated","state":state()}
        quote=self.ok(await self.req("POST","/quotes",json=payload))["quote"]
        self.assertEqual((quote["unitPrice"],quote["total"]),(4.375,4375))
        self.assertIn("MOQ a confirmar",quote["completionReview"]["pending"])
        self.assertEqual(self.ok(await self.req("POST","/quotes",json=payload))["quote"],quote)
        payload["state"]["fields"]["cost"]="20"
        self.assertEqual((await self.req("POST","/quotes",json=payload)).status_code,409)
        payload["id"]="COT-missing";payload["state"]["fields"]["cost"]=""
        self.assertEqual((await self.req("POST","/quotes",json=payload)).status_code,400)
        self.assertEqual(await self.db.prices.count_documents({}),1)
        self.assertEqual(await self.db.integrated_quotes.count_documents({}),1)
    async def test_profile_confirmation_conflict_and_preserved_document_links(self):
        await self.db.product_offers.update_one({"id":"offer"},{"$set":{"spec_document_ids":["private-spec"],"notes":"KEEP"}})
        source=self.ok(await self.req("GET","/catalog"))["offers"][0]["profile"]
        body={"patch":{"cost":"19","priceCurrency":"BRL","priceRate":"1"},"source":source,"confirmed":False}
        self.assertEqual((await self.req("PUT","/offers/offer/profile",json=body)).status_code,400)
        body["confirmed"]=True
        self.ok(await self.req("PUT","/offers/offer/profile",json=body))
        current=await self.db.product_offers.find_one({"id":"offer"})
        self.assertEqual(current["spec_document_ids"],["private-spec"])
        self.assertEqual(current["notes"],"KEEP")
        self.assertEqual(float(self.ok(await self.req("GET","/catalog"))["offers"][0]["profile"]["cost"]),19)
        self.assertEqual(current["supplier_price"],19)
        self.assertEqual((await self.req("PUT","/offers/offer/profile",json=body)).status_code,409)
    async def test_quote_to_native_approval_order_and_no_duplicate_handoff(self):
        self.ok(await self.req("POST","/quotes",json={"id":"COT-flow","state":state()}))
        terms={"valid_until":"2099-12-31","payment_terms":"Prepaid","delivery_terms":"Synthetic factory pickup","change_note":"Review synthetic transaction"}
        native=self.ok(await self.req("POST","/quotes/COT-flow/handoff",json=terms))
        self.assertEqual(native["status"],"draft")
        self.assertEqual(self.ok(await self.req("POST","/quotes/COT-flow/handoff",json=terms))["id"],native["id"])
        self.assertEqual(await self.db.quotations.count_documents({}),1)
        self.assertEqual((await self.req("POST","/quotes/COT-flow/handoff",json={**terms,"payment_terms":"Different terms"})).status_code,409)
        approved=self.ok(await self.client.post("/api/quotations/"+native["id"]+"/status",headers=self.headers(),
            json={"version":native["version"],"status":"approved","change_note":"Approve synthetic terms"}))
        self.assertTrue(approved["can_order"])
        source=self.ok(await self.client.get("/api/quotations/"+native["id"]+"/order-draft",headers=self.headers()))
        order=self.ok(await self.client.post("/api/orders",headers=self.headers(),json={**source,"id":"integrated-order","status":"draft"}))
        self.assertEqual(order["items"][0]["quantity"],1000)
        self.assertEqual(order["total_usd"],4375)
        self.assertEqual(order["source_quote_snapshot"]["source_integrated_snapshot"]["total"],4375)
        self.assertEqual((await self.client.get("/api/quotations/"+native["id"]+"/order-draft",headers=self.headers())).status_code,409)
        self.assertEqual(await server.all_finance_entries(),[])
    async def test_quote_history_cursor_keeps_owner_scope_and_does_not_skip_when_new_quotes_arrive(self):
        from datetime import datetime, timezone, timedelta
        saved=self.ok(await self.req("POST","/quotes",json={"id":"COT-history-source","state":state()}))["quote"]
        actor=(await self.db.integrated_quotes.find_one({"id":"COT-history-source"}))["owner_id"]
        await self.db.integrated_quotes.delete_many({"owner_id":actor})  # synthetic fixture only
        start=datetime(2026,1,1,tzinfo=timezone.utc)
        rows=[{"_id":actor+":Q"+str(i),"id":"Q"+str(i),"owner_id":actor,"created_at":(start+timedelta(seconds=i)).isoformat(),"quote":{**saved,"id":"Q"+str(i)}} for i in range(205)]
        await self.db.integrated_quotes.insert_many(rows)
        first=self.ok(await self.req("GET","/workspace"))
        self.assertEqual(len(first["quotes"]),100)
        cursor=first["quoteNextCursor"]
        await self.db.integrated_quotes.insert_one({"_id":actor+":new","id":"new","owner_id":actor,"created_at":"2099-01-01T00:00:00+00:00","quote":{**saved,"id":"new"}})
        all_ids=[q["id"] for q in first["quotes"]]
        while cursor:
            page=self.ok(await self.req("GET","/workspace",params={"quoteBefore":cursor}))
            all_ids.extend(q["id"] for q in page["quotes"])
            cursor=page.get("quoteNextCursor")
        self.assertEqual(len(all_ids),205)
        self.assertEqual(len(set(all_ids)),205)
        self.assertNotIn("new",all_ids)
        self.assertEqual(self.ok(await self.req("GET","/workspace"))["quotes"][0]["id"],"new")
        await self.db.users.insert_one({"id":"otheradmin","email":"otheradmin@example.com","role":"admin"})
        foreign=await self.client.get("/api/integrated/workspace",headers=self.headers("otheradmin"),params={"quoteBefore":first["quoteNextCursor"]})
        self.assertEqual(foreign.status_code,400)
        self.assertEqual((await self.req("GET","/workspace",params={"quoteBefore":"not-a-valid-cursor"})).status_code,400)

    async def test_saved_quote_retry_and_handoff_preserve_customer_identity(self):
        payload={"id":"COT-identity","state":state()}
        original=self.ok(await self.req("POST","/quotes",json=payload))["quote"]
        before=await self.db.integrated_quotes.find_one({"id":payload["id"]})
        terms={"valid_until":"2099-12-31","payment_terms":"Prepaid","delivery_terms":"Factory","change_note":"Reviewed"}
        for changes in ({"company":"Different buyer"},{"company":"Original Buyer","country":"Different country"}):
            await self.db.leads.update_one({"id":"lead1"},{"$set":changes})
            replay=self.ok(await self.req("POST","/quotes",json=payload))
            self.assertTrue(replay["alreadySaved"])
            self.assertEqual(replay["quote"],original)
            denied=await self.req("POST","/quotes/COT-identity/handoff",json=terms)
            self.assertEqual(denied.status_code,409,denied.text)
            self.assertEqual(await self.db.quotations.count_documents({}),0)
            self.assertEqual(await self.db.integrated_quotes.find_one({"id":payload["id"]}),before)
        await self.db.leads.update_one({"id":"lead1"},{"$set":before["customer_identity"]})
        # Identity country is restored explicitly; unrelated contact edits are safe.
        await self.db.leads.update_one({"id":"lead1"},{"$set":{"contact_name":"New contact"}})
        self.ok(await self.req("POST","/quotes/COT-identity/handoff",json=terms))

    async def test_other_currencies_quote_without_invented_usd_conversion(self):
        import io
        from pypdf import PdfReader
        from sale_currency import sale_amount
        for currency in ("BRL","EUR"):
            payload={"id":"COT-"+currency,"state":state(currency)}
            quote=self.ok(await self.req("POST","/quotes",json=payload))["quote"]
            terms={"valid_until":"2099-12-31","payment_terms":"Prepaid","delivery_terms":"Factory","change_note":"Reviewed"}
            native=self.ok(await self.req("POST","/quotes/"+payload["id"]+"/handoff",json=terms))
            self.assertEqual(native["currency"],currency)
            self.assertEqual(native["total_usd"],0)
            self.assertEqual(native["total_amount"],quote["total"])
            approved=self.ok(await self.client.post("/api/quotations/"+native["id"]+"/status",headers=self.headers(),json={"version":native["version"],"status":"approved","change_note":"Confirmed terms"}))
            source=self.ok(await self.client.get("/api/quotations/"+native["id"]+"/order-draft",headers=self.headers()))
            oid="order-"+currency
            order=self.ok(await self.client.post("/api/orders",headers=self.headers(),json={**source,"id":oid,"status":"draft"}))
            self.assertEqual(order["currency"],currency)
            self.assertEqual(float(sale_amount(order)),quote["total"])
            bad=await self.client.put("/api/orders/"+oid,headers=self.headers(),json={**order,"currency":"USD"})
            self.assertEqual(bad.status_code,400,bad.text)
            order=self.ok(await self.client.put("/api/orders/"+oid,headers=self.headers(),json={**order,"status":"confirmed","number":oid,"order_date":"2026-10-19","receivable_due_date":"2099-12-31"}))
            finance=[f for f in await server.all_finance_entries() if f.get("source_order_id")==oid]
            self.assertEqual([(f["currency"],f["amount"]) for f in finance],[(currency,quote["total"])])
            invoice_source=self.ok(await self.client.get("/api/orders/"+oid+"/commercial-invoice-draft",headers=self.headers()))
            public=invoice_source["source_order_snapshot"]
            self.assertEqual(public["currency"],currency)
            self.assertEqual(float(sale_amount(public)),quote["total"])
            body={"id":"inv-"+currency,"reference":"CI-"+currency,"order_id":oid,"source_order_version":order["version"],"issue_date":"2026-10-19","seller_name":"Synthetic IBIAG","seller_tax_id":"TEST","seller_address":"Example street","seller_country":"Brazil","buyer_address":"Example buyer","buyer_country":order["customer_country"],"incoterm_place":"Factory","payment_terms":"Prepaid","delivery_terms":"Factory","signatory":"Synthetic operator","customs":[{"index":0,"origin_country":"Brazil","hs_code":"11063010"}],"change_note":"Reviewed document"}
            invoice=self.ok(await self.client.post("/api/commercial-invoices",headers=self.headers(),json=body))
            self.ok(await self.client.post("/api/commercial-invoices/"+invoice["id"]+"/status",headers=self.headers(),json={"version":invoice["version"],"status":"approved","details_confirmed":True,"change_note":"Confirmed document"}))
            pdf=await self.client.get("/api/commercial-invoices/"+invoice["id"]+"/pdf",headers=self.headers())
            self.assertEqual(pdf.status_code,200,pdf.text[:80] if pdf.status_code!=200 else "")
            text="\n".join(p.extract_text() for p in PdfReader(io.BytesIO(pdf.content)).pages)
            self.assertIn("Currency: "+currency,text)
            self.assertIn("TOTAL "+currency,text)
            self.assertNotIn("TOTAL USD",text)
            packing_source=self.ok(await self.client.get("/api/orders/"+oid+"/packing-list-draft",headers=self.headers()))
            self.assertNotIn("total_amount",str(packing_source))
            packing={k:v for k,v in body.items() if k in server.PACKING_DETAILS}
            packing.update(id="pl-"+currency,reference="PL-"+currency,order_id=oid,source_order_version=order["version"],change_note="Packing review",packages=[{"marks":"TEST","packaging":"Bags","package_count":40,"net_kg":"1000","gross_kg":"1040","volume_m3":"2","allocations":[{"index":0,"quantity":"1000"}]}])
            document=self.ok(await self.client.post("/api/packing-lists",headers=self.headers(),json=packing))
            self.ok(await self.client.post("/api/packing-lists/"+document["id"]+"/status",headers=self.headers(),json={"version":document["version"],"status":"approved","details_confirmed":True,"change_note":"Confirmed packing"}))
            shipment={"version":order["version"],"status":"planned","reference":"SHIP-"+currency,"origin":"Factory","destination":"Buyer","mode":"sea","responsible_id":"admin","planned_departure":"2026-10-24","planned_arrival":"2026-11-10","change_note":"Synthetic planning"}
            shipped=self.ok(await self.client.put("/api/orders/"+oid+"/shipment",headers=self.headers(),json=shipment))
            stored=await self.db.orders.find_one({"id":oid})
            self.assertEqual(stored["currency"],currency)
            self.assertEqual(float(sale_amount(stored)),quote["total"])
            preserved=await self.db.integrated_quotes.find_one({"id":payload["id"]})
            self.assertEqual(preserved["quote"],quote)
        self.assertEqual(await self.db.quotations.count_documents({}),2)
    async def test_manual_unregistered_quote_can_finish_and_duplicate_references_are_not_deleted(self):
        data=state();data["productId"]="";data["fields"]["opportunityId"]=""
        self.ok(await self.req("POST","/quotes",json={"id":"COT-manual","state":data}))
        await self.db.products.insert_one({"id":"p","name":"Ambiguous"})
        result=self.ok(await self.req("GET","/catalog"))
        self.assertEqual(result["offers"],[])
        self.assertTrue(result["issues"])
        self.assertEqual(await self.db.products.count_documents({"id":"p"}),2)
        self.assertEqual(await self.db.integrated_quotes.count_documents({}),1)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Requires disposable MongoDB")
class RealMongoIntegratedWorkspaceTests(IntegratedWorkspaceTests):
    real_mongo=True
