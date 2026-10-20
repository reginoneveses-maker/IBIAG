"""Administrative sample HTTP flows, repeated with a disposable real MongoDB."""
import asyncio
import copy
import io
import os
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import patch, AsyncMock
import httpx
import pandas as pd
import test_order_crm_link as fixtures
import server

class CollectionProxy:
    def __init__(self, collection, **overrides): self.collection=collection; self.overrides=overrides
    def __getattr__(self, key): return self.overrides.get(key) or getattr(self.collection,key)

class DatabaseProxy:
    def __init__(self, database, **overrides): self.database=database; self.overrides=overrides
    def __getattr__(self, key): return self.overrides.get(key) or getattr(self.database,key)

class SampleTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=fixtures.OrderCrmLinkTests.headers
    asyncTearDown=fixtures.OrderCrmLinkTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.OrderCrmLinkTests.asyncSetUp(self)
        await self.db.suppliers.insert_one({"id":"s","name":"Original Supplier"})
        self.payload={"id":str(uuid.uuid4()),"reference":"AM-1","lead_id":"lead1","product_id":"p",
            "offer_id":"offer","requested_on":"2020-10-01","quantity":"25.5","unit":"g",
            "packaging":"One pouch","recipient":"Sample Buyer","address":"Example address",
            "destination_country":"Portugal","carrier":"Synthetic carrier","lot":"LOT-1",
            "expected_delivery":"2020-10-10","follow_up_on":"2020-10-15",
            "cost_amount":"5.25","cost_currency":"EUR","change_note":"Sample requested"}
        self.current=None

    async def create(self, **changes):
        response=await self.client.post("/api/samples",headers=self.headers(),json={**self.payload,**changes})
        if response.status_code==200: self.current=response.json()
        return response

    async def edit(self, **changes):
        body={k:self.current[k] for k in server.SAMPLE_TERMS}
        body.update({"version":self.current["version"],"change_note":"Updated sample",**changes})
        response=await self.client.put("/api/samples/"+self.current["id"],headers=self.headers(),json=body)
        if response.status_code==200: self.current=response.json()
        return response

    async def decide(self, status, **changes):
        body={"version":self.current["version"],"status":status,"change_note":"Recorded "+status,**changes}
        response=await self.client.post("/api/samples/"+self.current["id"]+"/status",headers=self.headers(),json=body)
        if response.status_code==200:self.current=response.json()
        return response

    async def record(self):
        return await self.db.samples.find_one({"id":self.payload["id"]},{"_id":0})

    async def dispatched(self):
        self.assertEqual((await self.create()).status_code,200)
        self.assertEqual((await self.decide("preparing")).status_code,200)
        response=await self.decide("sent",occurred_on="2020-10-02")
        self.assertEqual(response.status_code,200,response.text)

    async def test_complete_cycle_preserves_crm_stock_finance_and_terminal_history(self):
        buyer=await self.db.leads.find_one({"id":"lead1"})
        await self.dispatched()
        self.assertTrue(self.current["delivery_overdue"])
        self.assertEqual((await self.decide("delivered",occurred_on="2020-10-04")).status_code,200)
        self.assertTrue(self.current["feedback_overdue"])
        response=await self.decide("evaluated",occurred_on="2020-10-06",feedback_result="approved",feedback="Application test approved")
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual((self.current["version"],len(self.current["history"])),(5,5))
        self.assertEqual(self.current["history"][-1]["by"],"admin")
        self.assertFalse(self.current["can_edit"])
        self.assertEqual(self.current["allowed_statuses"],[])
        self.assertFalse(self.current["feedback_overdue"])
        self.assertEqual((await self.edit(notes="Cannot rewrite outcome")).status_code,409)
        self.assertEqual(await self.db.leads.find_one({"id":"lead1"}),buyer)
        self.assertEqual((await self.db.products.find_one({"id":"p"}))["stock"],10)
        self.assertEqual(await self.db.orders.count_documents({}),0)
        self.assertEqual(await server.all_finance_entries(),[])

    async def test_all_sample_routes_and_history_require_current_admin(self):
        await self.create()
        for headers,expected in [({},401),(self.headers("owner"),403),(self.headers("stranger"),403)]:
            headers={**headers,"X-User-Role":"admin"}
            for path in ("/api/samples","/api/samples/"+self.current["id"],
                         "/api/operations-history/sample/"+self.current["id"]):
                self.assertEqual((await self.client.get(path,headers=headers)).status_code,expected)
            self.assertEqual((await self.client.post("/api/samples",headers=headers,json=self.payload)).status_code,expected)
            edit={k:self.current[k] for k in server.SAMPLE_TERMS}
            edit.update(version=1,change_note="Forged edit")
            self.assertEqual((await self.client.put("/api/samples/"+self.current["id"],headers=headers,json=edit)).status_code,expected)
            self.assertEqual((await self.client.post("/api/samples/"+self.current["id"]+"/status",headers=headers,
                             json={"version":1,"status":"cancelled","change_note":"Forged decision"})).status_code,expected)
        self.assertEqual((await self.record())["version"],1)

    async def test_strict_create_rejects_forged_history_roles_values_and_invalid_decimals(self):
        for changes in ({"lead_id":{"$ne":None}},{"product_id":"bad\x00id"},{"quantity":True},
                        {"quantity":25},{"quantity":"NaN"},{"quantity":"1e3"},{"quantity":"0"},
                        {"quantity":"1000000000001"},{"quantity":"1.1234567890123"},
                        {"cost_amount":"-1"},{"history":[]},{"status":"sent"},{"customer":"Forged"},
                        {"owner_id":"stranger"},{"change_note":"   "},{"reference":" "}):
            response=await self.create(**changes)
            self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(await self.db.samples.count_documents({}),0)

    async def test_canonical_identity_and_units_survive_source_changes(self):
        self.assertEqual((await self.create()).status_code,200)
        self.assertEqual((self.current["customer"],self.current["product_name"],self.current["supplier_name"]),
                         ("Original Buyer","Product","Original Supplier"))
        self.assertEqual((self.current["catalog_unit"],self.current["unit"],self.current["quantity"]),("kg","g","25.5"))
        for collection,identifier,field in ((self.db.leads,"lead1","company"),(self.db.products,"p","name"),(self.db.suppliers,"s","name")):
            await collection.update_one({"id":identifier},{"$set":{field:"Changed label"}})
        response=await self.edit(notes="Preserve approved identity")
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(self.current["customer"],"Original Buyer")
        self.assertEqual(self.current["supplier_name"],"Original Supplier")
        self.assertEqual(self.current["product_name"],"Product")

    async def test_duplicate_id_reference_and_uncertain_retry_cannot_duplicate_request(self):
        await self.create()
        self.assertEqual((await self.create()).status_code,409)
        self.assertEqual((await self.create(id=str(uuid.uuid4()))).status_code,409)
        self.assertEqual((await self.decide("cancelled")).status_code,200)
        self.assertEqual((await self.create(id=str(uuid.uuid4()))).status_code,409)
        self.assertEqual(await self.db.samples.count_documents({}),1)

    async def test_missing_ambiguous_inactive_and_mismatched_references_are_refused(self):
        for changes in ({"lead_id":"missing"},{"product_id":"missing"},{"offer_id":"missing"}):
            self.assertEqual((await self.create(**changes)).status_code,404)
        await self.db.leads.insert_one({"id":"lead1","company":"Duplicate"})
        self.assertEqual((await self.create()).status_code,409)
        await self.db.leads.delete_one({"company":"Duplicate"})
        for changes in ({"active":False},{"product_id":"other"},{"supplier_id":"missing"}):
            offer=await self.db.product_offers.find_one({"id":"offer"})
            await self.db.product_offers.update_one({"id":"offer"},{"$set":changes})
            response=await self.create()
            self.assertIn(response.status_code,(400,404))
            await self.db.product_offers.replace_one({"id":"offer"},offer)
        self.assertEqual(await self.db.samples.count_documents({}),0)

    async def test_dispatch_rechecks_offer_and_does_not_invent_supplier(self):
        response=await self.create(offer_id="",cost_amount="")
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual((self.current["supplier_id"],self.current["supplier_name"],self.current["cost_amount"]),("","",""))
        self.assertEqual((await self.decide("preparing")).status_code,200)
        self.assertEqual((await self.decide("sent",occurred_on="2020-10-02")).status_code,200)
        # Independent record with an actual offer must fail if that offer becomes inactive.
        self.payload.update(id=str(uuid.uuid4()),reference="AM-2")
        await self.create()
        await self.decide("preparing")
        await self.db.product_offers.update_one({"id":"offer"},{"$set":{"active":False}})
        self.assertEqual((await self.decide("sent",occurred_on="2020-10-02")).status_code,400)
        self.assertEqual(self.current["status"],"preparing")

    async def test_dispatch_validation_dates_and_state_order(self):
        self.assertEqual((await self.create(requested_on="2999-01-01")).status_code,400)
        self.assertEqual((await self.create(expected_delivery="2020-02-30")).status_code,400)
        self.assertEqual((await self.create(packaging="")).status_code,200)
        self.assertEqual((await self.decide("sent",occurred_on="2020-10-02")).status_code,400)
        self.assertEqual((await self.decide("preparing",feedback="Unexpected")).status_code,400)
        await self.decide("preparing")
        before=await self.record()
        self.assertEqual((await self.decide("sent",occurred_on="2020-10-02")).status_code,400)
        self.assertEqual(await self.record(),before)
        await self.edit(packaging="One pouch")
        self.assertEqual((await self.decide("sent",occurred_on="2999-01-01")).status_code,400)
        self.assertEqual((await self.decide("sent",occurred_on="2020-09-30")).status_code,400)
        await self.decide("sent",occurred_on="2020-10-02")
        self.assertEqual((await self.decide("cancelled")).status_code,400)
        self.assertEqual((await self.decide("delivered",occurred_on="2020-10-01")).status_code,400)
        await self.decide("delivered",occurred_on="2020-10-04")
        self.assertEqual((await self.decide("evaluated",occurred_on="2020-10-06")).status_code,400)

    async def test_sent_quantity_lot_destination_and_real_dates_are_preserved(self):
        await self.dispatched()
        for changes in ({"quantity":"50"},{"unit":"kg"},{"lot":"Changed"},{"recipient":"Other"},{"address":"Other"},
                        {"packaging":"Changed"},{"delivery_method":"hand"}):
            self.assertEqual((await self.edit(**changes)).status_code,409)
        self.assertEqual((await self.edit(carrier="Updated reference",tracking_code="<script>unsafe text</script>",cost_amount="0")).status_code,200)
        self.assertEqual(self.current["sent_on"],"2020-10-02")
        body={k:self.current[k] for k in server.SAMPLE_TERMS}
        body.update(version=self.current["version"],change_note="Try forged date",sent_on="2020-10-03")
        self.assertEqual((await self.client.put("/api/samples/"+self.current["id"],headers=self.headers(),json=body)).status_code,422)

    async def test_version_concurrency_keeps_one_committed_event(self):
        await self.create()
        body={"version":1,"status":"preparing","change_note":"Concurrent transition"}
        replies=await asyncio.gather(*[self.client.post("/api/samples/"+self.current["id"]+"/status",
                    headers=self.headers(),json=body) for _ in range(2)])
        self.assertEqual(sorted(r.status_code for r in replies),[200,409])
        self.assertEqual((await self.record())["version"],2)
        self.assertEqual(len((await self.record())["history"]),2)

    async def test_reference_deletions_are_blocked_including_cancelled_history(self):
        await self.create()
        await self.decide("cancelled")
        self.assertEqual((await self.client.delete("/api/leads/lead1",headers=self.headers("owner"))).status_code,409)
        self.assertEqual((await self.client.delete("/api/product-offers/offer",headers=self.headers())).status_code,400)
        # Remove only the disposable fixture offer to prove the sample itself guards product/supplier.
        await self.db.product_offers.delete_one({"id":"offer"})
        self.assertEqual((await self.client.delete("/api/products/p",headers=self.headers())).status_code,400)
        self.assertEqual((await self.client.delete("/api/suppliers/s",headers=self.headers())).status_code,409)
        self.assertIsNotNone(await self.db.products.find_one({"id":"p"}))
        self.assertIsNotNone(await self.db.suppliers.find_one({"id":"s"}))

    async def test_destructive_portfolio_import_is_blocked_before_changes(self):
        await self.create()
        buffer=io.BytesIO()
        with pd.ExcelWriter(buffer,engine="openpyxl") as writer:
            pd.DataFrame([{"Produto":"Replacement","Fornecedor":"New Supplier"}]).to_excel(writer,sheet_name="IBIAG",startrow=2,index=False)
        response=await self.client.post("/api/portfolio/import-xlsx?replace=true",headers=self.headers(),
                 files={"file":("portfolio.xlsx",buffer.getvalue(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        self.assertEqual(response.status_code,400,response.text)
        self.assertIsNotNone(await self.db.products.find_one({"id":"p"}))
        self.assertEqual(await self.db.samples.count_documents({}),1)

    async def test_listing_filters_bounds_and_private_detail(self):
        await self.create(notes="private note",cost_amount="99",tracking_code="private-reference")
        response=await self.client.get("/api/samples?status=requested&lead_id=lead1&product_id=p&limit=1",headers=self.headers())
        self.assertEqual(response.status_code,200)
        row=response.json()[0]
        for key in ("notes","cost_amount","tracking_code","history","supplier_name"):
            self.assertNotIn(key,row)
        self.assertEqual((await self.client.get("/api/samples?skip=1",headers=self.headers())).json(),[])
        self.assertEqual((await self.client.get("/api/samples?status=delivered",headers=self.headers())).json(),[])
        for query in ("limit=251","skip=-1","status=bogus"):
            self.assertEqual((await self.client.get("/api/samples?"+query,headers=self.headers())).status_code,422)
        detail=await self.client.get("/api/samples/"+self.current["id"],headers=self.headers())
        self.assertIn("no-store",detail.headers["cache-control"])
        self.assertNotIn("_id",detail.json())

    async def test_history_rotation_pages_and_stale_cursor(self):
        await self.create()
        for i in range(40):
            response=await self.edit(notes="Revision "+str(i))
            self.assertEqual(response.status_code,200,response.text)
        path="/api/operations-history/sample/"+self.current["id"]
        first=await self.client.get(path,headers=self.headers())
        data=first.json()
        self.assertEqual((first.status_code,data["total"],len(data["items"])),(200,41,20))
        self.assertIn("no-store",first.headers["cache-control"])
        versions=[e["version"] for e in data["items"]]
        cursor=data["next_cursor"]
        while cursor:
            page=(await self.client.get(path,headers=self.headers(),params={"cursor":cursor})).json()
            versions.extend(e["version"] for e in page["items"])
            cursor=page["next_cursor"]
        self.assertEqual(versions,list(range(41,0,-1)))
        self.assertEqual(await self.db.operation_history.count_documents({"kind":"sample"}),1)
        await self.edit(notes="New revision")
        self.assertEqual((await self.client.get(path,headers=self.headers(),params={"cursor":data["next_cursor"]})).status_code,409)

    async def test_failed_cas_cannot_expose_an_uncommitted_history_revision(self):
        await self.create()
        for i in range(31):
            self.assertEqual((await self.edit(notes=str(i))).status_code,200)
        before=await self.record()
        proxy=DatabaseProxy(self.db,samples=CollectionProxy(self.db.samples,replace_one=AsyncMock(return_value=SimpleNamespace(matched_count=0))))
        with patch.object(server,"db",proxy):
            self.assertEqual((await self.edit(notes="Uncommitted proposal")).status_code,409)
        self.assertEqual(await self.record(),before)
        self.assertEqual(await self.db.operation_history.count_documents({"kind":"sample"}),1)
        self.assertEqual((await self.edit(notes="Successful retry")).status_code,200)
        page=(await self.client.get("/api/operations-history/sample/"+self.current["id"],headers=self.headers())).json()
        self.assertEqual(page["total"],33)
        self.assertNotIn("Uncommitted proposal",str(page))
        self.assertEqual(await self.db.operation_history.count_documents({"kind":"sample"}),1)

    async def test_failure_response_is_redacted_and_releases_write_lease(self):
        await self.create()
        before=await self.record()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app,raise_app_exceptions=False),base_url="http://test") as client:
            with patch.object(server,"compact_operation_history",AsyncMock(side_effect=RuntimeError("synthetic-private-marker"))):
                body={k:self.current[k] for k in server.SAMPLE_TERMS}
                body.update(version=1,change_note="Save sample")
                response=await client.put("/api/samples/"+self.current["id"],headers=self.headers(),json=body)
        self.assertEqual(response.status_code,500)
        self.assertNotIn("synthetic-private-marker",response.text)
        self.assertEqual(await self.record(),before)
        self.assertEqual((await self.edit(notes="Recovered")).status_code,200)

    async def test_ambiguous_or_corrupt_record_is_not_arbitrarily_selected(self):
        await self.create()
        other=copy.deepcopy(await self.record())
        await self.db.samples.insert_one(other)
        self.assertEqual((await self.client.get("/api/samples/"+self.current["id"],headers=self.headers())).status_code,409)
        await self.db.samples.delete_one({"_id":other["_id"]})
        await self.db.samples.update_one({"id":self.current["id"]},{"$set":{"version":True}})
        self.assertEqual((await self.client.get("/api/samples/"+self.current["id"],headers=self.headers())).status_code,409)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class RealMongoSampleTests(SampleTests):
    real_mongo=True
