"""Administrative dossier HTTP checks on mock and disposable real MongoDB."""
import copy
import os
import unittest
import test_commercial_invoices as fixtures
import server

class DossierTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=fixtures.CommercialInvoiceTests.headers
    create_order=fixtures.CommercialInvoiceTests.create_order
    update_order=fixtures.CommercialInvoiceTests.update_order
    asyncTearDown=fixtures.CommercialInvoiceTests.asyncTearDown
    async def asyncSetUp(self):
        await fixtures.CommercialInvoiceTests.asyncSetUp(self)
    async def get(self, oid="sale",user="admin"):
        return await self.client.get("/api/orders/"+oid+"/dossier",headers=self.headers(user) if user else {})
    async def snapshot(self):
        return {name:await self.db[name].find({},{"_id":0}).to_list(None) for name in await self.db.list_collection_names()}
    async def documents(self,status="approved"):
        invoice={"id":"ci","order_id":"sale","reference":"CI-DOSSIER","status":status,"issue_date":"2026-10-19","version":1,
                 "source_order_revision":server.invoice_revision(server.commercial_snapshot(self.order)),"notes":"PRIVATE-INVOICE"}
        packing={"id":"pl","order_id":"sale","reference":"PL-DOSSIER","status":status,"issue_date":"2026-10-19","version":1,
                 "source_order_revision":server.packing_revision(server.packing_snapshot(self.order)),"notes":"PRIVATE-PACKING"}
        await self.db.commercial_invoices.insert_one(invoice)
        await self.db.packing_lists.insert_one(packing)
    async def test_admin_only_private_projection_and_completely_readonly(self):
        await self.documents()
        await self.db.orders.update_one({"id":"sale"},{"$set":{"shipment":{"status":"planned","reference":"SHIP","origin":"Santos","destination":"Lisbon","carrier":"Carrier","notes":"PRIVATE-SHIP","history":[{"secret":"PRIVATE-HISTORY"}]}}})
        before=await self.snapshot()
        for user,code in ((None,401),("owner",403),("stranger",403)):
            self.assertEqual((await self.get(user=user)).status_code,code)
        response=await self.get()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.headers["cache-control"],"private, no-store")
        self.assertEqual(response.headers["x-content-type-options"],"nosniff")
        for marker in ("PRIVATE","unit_price","total_usd","supplier","source_order_snapshot","payment_terms","history"):
            self.assertNotIn(marker,response.text)
        self.assertEqual(response.json()["shipment"]["origin"],"Santos")
        self.assertEqual(await self.snapshot(),before)
    async def test_missing_documents_and_no_quote_are_not_global_release(self):
        response=await self.get();self.assertEqual(response.status_code,200,response.text)
        data=response.json()
        self.assertEqual((data["invoice_state"],data["packing_state"]),("missing","missing"))
        self.assertEqual(data["quote"]["state"],"not_linked")
        self.assertEqual(data["counts"],{"invoices":0,"packing_lists":0,"active_invoices":0,"active_packing_lists":0})
        self.assertIn("documents_pending",data["flags"])
        self.assertNotIn("quote_review",data["flags"])
        self.assertNotIn("ready",data)
    async def test_current_approved_docs_and_changed_order_are_distinct(self):
        await self.documents()
        data=(await self.get()).json()
        self.assertEqual((data["invoice_state"],data["packing_state"]),("approved","approved"))
        self.assertTrue(data["invoices"][0]["source_current"])
        self.assertTrue(data["commercial_source_checked"])
        await self.db.orders.update_one({"id":"sale"},{"$set":{"number":"Changed"}})
        data=(await self.get()).json()
        self.assertEqual((data["invoice_state"],data["packing_state"]),("outdated","outdated"))
        self.assertFalse(data["invoices"][0]["source_current"])
        self.assertIn("data_review",data["flags"])
    async def test_cancelled_docs_remain_visible_and_multiple_active_docs_are_ambiguous(self):
        await self.documents("cancelled")
        data=(await self.get()).json()
        self.assertEqual(data["invoice_state"],"missing")
        self.assertEqual(data["invoices"][0]["status"],"cancelled")
        self.assertEqual(data["counts"]["active_invoices"],0)
        original=await self.db.commercial_invoices.find_one({"id":"ci"},{"_id":0})
        await self.db.commercial_invoices.insert_many([{**original,"id":"ci2","status":"approved"},{**original,"id":"ci3","status":"draft"}])
        data=(await self.get()).json()
        self.assertEqual(data["invoice_state"],"ambiguous")
        self.assertEqual(data["counts"]["invoices"],3)
        self.assertEqual(data["counts"]["active_invoices"],2)
    async def test_quote_snapshot_is_preserved_and_current_revision_and_link_are_checked(self):
        snapshot={"reference":"Q-ORIGINAL","payment_terms":"Prepaid","delivery_terms":"30 days"}
        await self.db.orders.update_one({"id":"sale"},{"$set":{"source_quote_id":"q","source_quote_revision":4,"source_quote_snapshot":snapshot}})
        await self.db.quotations.insert_one({"id":"q","status":"approved","version":4,"reference":"Changed title","notes":"PRIVATE-QUOTE"})
        data=(await self.get()).json()
        self.assertEqual(data["quote"]["state"],"linked")
        self.assertEqual(data["quote"]["reference"],"Q-ORIGINAL")
        await self.db.quotations.update_one({"id":"q"},{"$set":{"version":5}})
        self.assertEqual((await self.get()).json()["quote"]["state"],"review")
        await self.db.quotations.update_one({"id":"q"},{"$set":{"version":4}})
        await self.db.orders.insert_one({**self.order,"id":"other","source_quote_id":"q"})
        self.assertEqual((await self.get()).json()["quote"]["state"],"review")
        await self.db.quotations.delete_many({})
        self.assertEqual((await self.get()).json()["quote"]["state"],"missing")
        await self.db.quotations.insert_many([{"id":"q"},{"id":"q"}])
        self.assertEqual((await self.get()).json()["quote"]["state"],"ambiguous")
    async def test_missing_archived_ambiguous_and_invalid_order_ids_are_rejected(self):
        self.assertEqual((await self.get("missing")).status_code,404)
        self.assertEqual((await self.get("bad%00id")).status_code,422)
        await self.db.orders.update_one({"id":"sale"},{"$set":{"deleted_at":"2026-10-19"}})
        self.assertEqual((await self.get()).status_code,404)
        await self.db.orders.insert_one(copy.deepcopy(self.order))
        self.assertEqual((await self.get()).status_code,409)
    async def test_bad_source_and_unknown_doc_state_never_look_approved(self):
        await self.documents("invented")
        await self.db.orders.update_one({"id":"sale"},{"$set":{"items":[]}})
        data=(await self.get()).json()
        self.assertFalse(data["commercial_source_checked"])
        self.assertEqual(data["invoices"][0]["status"],"unknown")
        self.assertEqual(data["invoice_state"],"review")
        self.assertIsNone(data["invoices"][0]["source_current"])
        self.assertIn("data_review",data["flags"])
        await self.db.orders.update_one({"id":"sale"},{"$set":{"source_quote_id":{"$ne":None}}})
        self.assertEqual((await self.get()).status_code,409)
    async def test_duplicate_doc_ids_and_caps_refuse_partial_or_arbitrary_results(self):
        await self.documents()
        duplicate=await self.db.commercial_invoices.find_one({"id":"ci"},{"_id":0})
        await self.db.commercial_invoices.insert_one(duplicate)
        self.assertEqual((await self.get()).status_code,409)
        await self.db.commercial_invoices.delete_many({})
        await self.db.commercial_invoices.insert_many([{"id":str(i),"order_id":"sale","status":"cancelled"} for i in range(201)])
        self.assertEqual((await self.get()).status_code,413)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class RealMongoDossierTests(DossierTests):
    real_mongo=True
