"""Read-only in-quote supplier context reuses native private-file policy."""
import copy
import unittest
from unittest.mock import patch, AsyncMock
import os
import test_commercial_profile as fixtures
import server

class QuoteContextTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    async def asyncSetUp(self):
        await fixtures.native.IntegratedWorkspaceTests.asyncSetUp(self)
        await self.db.users.insert_one({"id":"operator","email":"operator@example.com","role":"user","commercial_profile":"commercial-operator-v1"})
    asyncTearDown=fixtures.CommercialProfileTests.asyncTearDown
    headers=fixtures.CommercialProfileTests.headers
    req=fixtures.CommercialProfileTests.req
    ok=fixtures.CommercialProfileTests.ok
    async def seed_context(self):
        await self.db.suppliers.update_one({"id":"s"},{"$set":{"contact":"Synthetic contact","email":"supplier@example.test","phone":"+55 0000","notes":"SUPPLIER-PRIVATE-NOTES"}})
        await self.db.products.update_one({"id":"p"},{"$set":{"packaging":"25 kg bags (descriptive)","lead_time":"20 days","payment_terms":"Prepaid"}})
        await self.db.documents.insert_many([
          {"id":"visible","title":"Visible synthetic sheet","document_type":"Ficha Técnica","product_id":"p","supplier_id":"s","file_path":"fixture/visible.pdf","file_name":"visible.pdf","notes":"DOC-PRIVATE-NOTES"},
          {"id":"foreign","title":"FOREIGN-CRM-SECRET","lead_id":"lead2","owner_id":"owner","file_path":"fixture/foreign.pdf","file_name":"foreign.pdf"}])
        await self.db.specs.insert_one({"id":"spec","product_id":"p","supplier_id":"s","product_name":"Product","ibiag_file_path":"fixture/ibiag.pdf","ibiag_file_name":"ibiag.pdf","notes":"SPEC-PRIVATE-NOTES"})
        await self.db.certifications.insert_one({"id":"cert","name":"Synthetic expired certification","supplier_id":"s","expiry_date":"2000-01-01","alert_days":30,"file_path":"fixture/cert.pdf","file_name":"cert.pdf"})
        await self.db.product_offers.update_one({"id":"offer"},{"$set":{"spec_document_ids":["visible","foreign"],"spec_ids":["spec"],"certification_ids":["cert"]}})
    async def test_context_keeps_private_crm_files_private_and_reports_expiry_without_writes(self):
        await self.seed_context()
        before={name:await self.db[name].find({},{"_id":0}).to_list(100) for name in ("product_offers","documents","specs","certifications","products","suppliers")}
        response=await self.req("GET","/offers/offer/context")
        data=self.ok(response)
        self.assertEqual(response.headers["cache-control"],"private, no-store")
        self.assertEqual(data["supplier"]["email"],"supplier@example.test")
        self.assertEqual(data["conditions"]["Embalagem registrada"],"25 kg bags (descriptive)")
        self.assertEqual(data["linksRequiringReview"],1)
        self.assertNotIn("FOREIGN-CRM-SECRET",response.text)
        self.assertNotIn("foreign.pdf",response.text)
        self.assertNotIn("PRIVATE-NOTES",response.text)
        self.assertEqual({d["id"] for d in data["documents"]},{"visible","spec","cert"})
        self.assertIn("expired",next(d for d in data["documents"] if d["id"]=="cert")["flags"])
        private=await self.client.get("/api/files/fixture/foreign.pdf",headers=self.headers())
        self.assertIn(private.status_code,(403,404))
        with patch.object(server,"get_object",new=AsyncMock(return_value=(b"%PDF-synthetic-certificate","application/pdf"))):
            certificate=await self.client.get("/api/files/fixture/cert.pdf",headers=self.headers())
        self.assertEqual(certificate.status_code,200)
        self.assertEqual(certificate.content,b"%PDF-synthetic-certificate")
        regular=await self.client.get("/api/files/fixture/cert.pdf",headers=self.headers("owner"))
        self.assertEqual(regular.status_code,403)
        after={name:await self.db[name].find({},{"_id":0}).to_list(100) for name in before}
        self.assertEqual(before,after)
        self.assertEqual(await self.db.integrated_quotes.count_documents({}),0)
        from test_integrated_workspace import state
        self.ok(await self.req("POST","/quotes",json={"id":"COT-expiry-warning","state":state()}))
    async def test_duplicate_document_reference_is_flagged_and_never_silently_chosen(self):
        await self.seed_context()
        doc=await self.db.documents.find_one({"id":"visible"},{"_id":0})
        await self.db.documents.insert_one({**doc,"title":"Ambiguous second sheet"})
        data=self.ok(await self.req("GET","/offers/offer/context"))
        self.assertNotIn("visible",[d["id"] for d in data["documents"]])
        self.assertGreaterEqual(data["linksRequiringReview"],2)
        self.assertEqual(await self.db.documents.count_documents({"id":"visible"}),2)
    async def test_context_requires_commercial_permission_and_valid_unique_references(self):
        self.assertEqual((await self.client.get("/api/integrated/offers/offer/context",headers=self.headers("owner"))).status_code,403)
        self.assertIn((await self.client.get("/api/integrated/offers/offer/context")).status_code,(401,403))
        await self.db.product_offers.update_one({"id":"offer"},{"$set":{"product_id":{"$ne":""}}})
        self.assertEqual((await self.req("GET","/offers/offer/context")).status_code,409)
        self.assertEqual(await self.db.products.count_documents({}),1)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Requires disposable MongoDB")
class RealMongoQuoteContextTests(QuoteContextTests):
    real_mongo=True
