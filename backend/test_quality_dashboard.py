"""Metadata-only quality panel on disposable mock and real MongoDB."""
import copy
import os
import unittest
from datetime import date
import test_order_crm_link as fixtures
import server
from quality_dashboard import quality_rows, quality_summary

class QualityRuleTests(unittest.TestCase):
    def row(self, **changes):
        cert={"id":"c","supplier_id":"s","name":"Organic","issue_date":"2026-01-01","expiry_date":"2026-10-20","alert_days":0,"file_path":"private.pdf",**changes}
        return quality_rows([cert],[],[{"id":"s","name":"Supplier"}],[],date(2026,10,20))[0]
    def test_expiry_boundary_and_alert_days_are_explicit(self):
        self.assertEqual(self.row()["flags"],["expiring"])
        self.assertEqual(self.row(expiry_date="2026-10-19")["flags"],["expired"])
        self.assertEqual(self.row(expiry_date="2026-10-21",alert_days=0)["flags"],[])
        self.assertEqual(self.row(expiry_date="2026-11-19",alert_days=30)["flags"],["expiring"])
        self.assertEqual(self.row(expiry_date="2026-11-20",alert_days=30)["flags"],[])
    def test_invalid_missing_and_reversed_dates_never_imply_approval(self):
        for changes in ({"expiry_date":"2026-02-30"},{"issue_date":"2026-11-01"},{"issue_date":"2026-10-21","expiry_date":"2026-10-20"}):
            self.assertIn("invalid_dates",self.row(**changes)["flags"])
        self.assertIn("missing_expiry",self.row(expiry_date="")["flags"])
        self.assertIn("data_review",self.row(alert_days=True)["flags"])
        self.assertIn("data_review",self.row(alert_days=-1)["flags"])
        self.assertIn("missing_file",self.row(file_path=" ")["flags"])
    def test_ambiguous_references_and_unclassified_content_are_not_invented(self):
        rows=quality_rows([], [{"id":"d","supplier_id":"s","product_id":"p","title":"COA","document_type":"COA / Laudo","file_path":"file"}],
            [{"id":"s","name":"A"},{"id":"s","name":"B"}],[{"id":"p","name":"Product"}],date(2026,10,20))
        self.assertEqual(rows[0]["flags"],["data_review"])
        self.assertEqual(rows[0]["supplier_name"],"")
        self.assertNotIn("file_path",rows[0])
    def test_duplicate_record_ids_fail_instead_of_collapsing_rows(self):
        with self.assertRaises(ValueError):quality_rows([{"id":"a"},{"id":"a"}],[],[],[],date(2026,10,20))

class QualityTests(unittest.IsolatedAsyncioTestCase):
    real_mongo=False
    headers=fixtures.OrderCrmLinkTests.headers
    asyncTearDown=fixtures.OrderCrmLinkTests.asyncTearDown
    async def asyncSetUp(self):
        await fixtures.OrderCrmLinkTests.asyncSetUp(self)
        await self.db.suppliers.insert_one({"id":"s","name":"Supplier","private_cost":"PRIVATE"})
        await self.db.certifications.insert_many([
            {"id":"c1","supplier_id":"s","name":"Expired","expiry_date":"2020-01-01","issue_date":"2019-01-01","alert_days":30,"file_path":"PRIVATE-CERT-PATH","notes":"PRIVATE-NOTE"},
            {"id":"c2","supplier_id":"missing","name":"Needs review","expiry_date":"","file_path":""}])
        await self.db.documents.insert_many([
            {"id":"d1","supplier_id":"s","product_id":"p","title":"Product COA","document_type":"COA / Laudo","file_path":"PRIVATE-DOC-PATH","notes":"PRIVATE-NOTE"},
            {"id":"d2","title":"Ignored invoice","document_type":"Outros","file_path":"secret"},
            {"id":"d3","title":"Deleted COA","document_type":"COA / Laudo","deleted_at":"2026-01-01"},
            {"id":"d4","title":"Unclassified","file_path":"secret"}])
    async def get(self, query="", user="admin"):
        return await self.client.get("/api/gestao/quality"+query,headers=self.headers(user) if user else {})
    async def snapshot(self):
        return {name:await self.db[name].find({},{"_id":0}).to_list(None) for name in await self.db.list_collection_names()}
    async def test_admin_only_redacted_no_store_and_no_database_writes(self):
        before=await self.snapshot()
        for user,code in ((None,401),("owner",403),("stranger",403)):
            self.assertEqual((await self.get(user=user)).status_code,code)
        response=await self.get()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.headers["cache-control"],"private, no-store")
        self.assertEqual(response.headers["x-content-type-options"],"nosniff")
        self.assertNotIn("PRIVATE",response.text)
        self.assertEqual(response.json()["total"],3)
        self.assertEqual(await self.snapshot(),before)
    async def test_existing_sources_are_combined_without_deleted_or_unclassified_files(self):
        data=(await self.get()).json()
        self.assertEqual({r["id"] for r in data["rows"]},{"c1","c2","d1"})
        self.assertEqual(data["summary"]["by_source"],{"certification":2,"document":1})
        self.assertEqual(data["summary"]["needs_attention"],2)
        self.assertEqual(data["summary"]["without_findings"],1)
        self.assertEqual(data["summary"]["flags"]["expired"],1)
        row=next(r for r in data["rows"] if r["id"]=="d1")
        self.assertEqual((row["supplier_name"],row["product_name"]),("Supplier","Product"))
        self.assertTrue(row["file_declared"])
        self.assertNotIn("approved",row)
    async def test_filters_pagination_and_counts_match_the_applied_query(self):
        for query,ids in (("?source=certification",{"c1","c2"}),("?source=document",{"d1"}),
                ("?supplier_id=s",{"c1","d1"}),("?product_id=p",{"d1"}),
                ("?attention=expired",{"c1"}),("?attention=without_findings",{"d1"})):
            response=await self.get(query);self.assertEqual(response.status_code,200,response.text)
            self.assertEqual({r["id"] for r in response.json()["rows"]},ids)
            self.assertEqual(response.json()["summary"]["total"],len(ids))
        first=(await self.get("?limit=1")).json();second=(await self.get("?limit=1&skip=1")).json()
        self.assertEqual(first["total"],3);self.assertNotEqual(first["rows"][0]["id"],second["rows"][0]["id"])
        self.assertEqual((await self.get("?skip=100")).json()["rows"],[])
    async def test_invalid_filters_and_bounds_are_rejected(self):
        for query in ("?source=unknown","?attention=approved","?limit=101","?skip=-1","?skip=10001","?supplier_id=bad%00id"):
            self.assertEqual((await self.get(query)).status_code,422,query)
    async def test_broken_or_ambiguous_references_are_visible_and_names_not_guessed(self):
        await self.db.suppliers.insert_one({"id":"s","name":"Duplicate"})
        await self.db.products.delete_one({"id":"p"})
        data=(await self.get("?source=document")).json();row=data["rows"][0]
        self.assertEqual(row["supplier_name"],"")
        self.assertIn("data_review",row["flags"]);self.assertIn("missing_product",row["flags"])
        self.assertEqual(row["product_name"],"")
    async def test_duplicate_ids_fail_closed_with_recoverable_error(self):
        await self.db.certifications.insert_one({"id":"c1","name":"Duplicate"})
        response=await self.get()
        self.assertEqual(response.status_code,409,response.text)
        self.assertNotIn("rows",response.json())
    async def test_source_limit_refuses_silent_incomplete_totals(self):
        await self.db.certifications.insert_many([{"id":"extra-"+str(i),"name":"Synthetic"} for i in range(4999)])
        response=await self.get()
        self.assertEqual(response.status_code,413,response.text)
        # Restricting source still allows the unrelated document query.
        self.assertEqual((await self.get("?source=document")).status_code,200)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class RealMongoQualityTests(QualityTests):
    real_mongo=True
