"""Isolated HTTP invoice tests, repeated against disposable MongoDB in CI."""
import asyncio
import copy
import io
import os
import unittest
from unittest.mock import patch
import httpx
from pypdf import PdfReader
import test_order_price_source as fixtures
import server

class CommercialInvoiceTests(unittest.IsolatedAsyncioTestCase):
    real_mongo = False
    headers = fixtures.PriceOrderTests.headers
    create_order = fixtures.PriceOrderTests.create
    update_order = fixtures.PriceOrderTests.update
    asyncTearDown = fixtures.PriceOrderTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.PriceOrderTests.asyncSetUp(self)
        await self.db.prices.update_one({"id": "price"}, {"$set": {"quantity": 2, "notes": "PRIVATE-COST-CANARY"}})
        price = (await self.client.get("/api/prices/price/order-draft", headers=self.headers())).json()
        r = await self.create_order({**self.body, **price, "notes": "PRIVATE-ORDER-CANARY"})
        self.assertEqual(r.status_code, 200, r.text)
        r = await self.update_order({**r.json(), "status": "confirmed", "number": "SO-TEST", "order_date": "2026-10-19", "receivable_due_date": "2026-11-19"})
        self.assertEqual(r.status_code, 200, r.text)
        self.order = r.json()
        self.invoice_body = {"id": "inv1", "reference": "CI-TEST-1", "order_id": "sale", "source_order_version": self.order["version"],
            "issue_date": "2026-10-19", "seller_name": "IBIAG Test Exporter", "seller_tax_id": "TEST-ONLY-REG",
            "seller_address": "100 Example Street", "seller_country": "Brazil", "buyer_address": "200 Example Avenue",
            "buyer_country": "Portugal", "incoterm_place": "Santos", "payment_terms": "Prepaid", "delivery_terms": "Santos port, 30 days",
            "signatory": "Test Operator", "customs": [{"index": 0, "origin_country": "Brazil", "hs_code": "11063010"}],
            "change_note": "Commercial document review"}

    async def create(self, **changes):
        return await self.client.post("/api/commercial-invoices", headers=self.headers(), json={**self.invoice_body, **changes})

    async def invoice(self, **changes):
        r = await self.create(**changes)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    async def decide(self, record, status="approved", **changes):
        return await self.client.post(f"/api/commercial-invoices/{record['id']}/status", headers=self.headers(),
            json={"version": record["version"], "status": status, "details_confirmed": True, "change_note": "Explicit internal decision", **changes})

    async def approved(self):
        r = await self.decide(await self.invoice())
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    async def pdf(self, iid="inv1"):
        return await self.client.get(f"/api/commercial-invoices/{iid}/pdf", headers=self.headers())

    @staticmethod
    def text(response):
        return "\n".join(page.extract_text() for page in PdfReader(io.BytesIO(response.content)).pages)

    async def test_readonly_preview_and_creation_do_not_duplicate_business_ledgers(self):
        before = await self.db.orders.find_one({"id": "sale"})
        finance = await server.all_finance_entries()
        r = await self.client.get("/api/orders/sale/commercial-invoice-draft", headers=self.headers())
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["source_order_snapshot"]["items"][0]["unit_price"], 4.26)
        self.assertEqual(await self.db.commercial_invoices.count_documents({}), 0)
        invoice = await self.invoice()
        self.assertEqual(invoice["status"], "draft")
        self.assertEqual(invoice["customer"], "Original Buyer")
        self.assertEqual(invoice["total_usd"], 8.52)
        self.assertEqual(invoice["history"][0]["by"], "admin")
        self.assertNotIn("_id", invoice)
        self.assertEqual(await self.db.orders.find_one({"id": "sale"}), before)
        self.assertEqual(await server.all_finance_entries(), finance)
        self.assertEqual(await self.db.invoices.count_documents({}), 0)  # Existing NF-e is untouched.
        payload = str(invoice)
        for private in ("PRIVATE-COST-CANARY", "PRIVATE-ORDER-CANARY", "supplier_name", "supplier_price", "supplier_id"):
            self.assertNotIn(private, payload)

    async def test_all_routes_require_admin_and_ignore_role_spoofing(self):
        await self.invoice()
        for auth, expected in [({}, 401), (self.headers("owner"), 403), (self.headers("stranger"), 403)]:
            headers = {**auth, "X-User-Role": "admin"}
            for path in ("/api/orders/sale/commercial-invoice-draft", "/api/commercial-invoices", "/api/commercial-invoices/inv1", "/api/commercial-invoices/inv1/pdf"):
                self.assertEqual((await self.client.get(path, headers=headers)).status_code, expected)
            self.assertEqual((await self.client.post("/api/commercial-invoices", headers=headers, json=self.invoice_body)).status_code, expected)
            details = {k: v for k,v in self.invoice_body.items() if k not in {"id", "reference", "order_id", "source_order_version"}}
            self.assertEqual((await self.client.put("/api/commercial-invoices/inv1", headers=headers, json={**details, "version": 1})).status_code, expected)
            self.assertEqual((await self.client.post("/api/commercial-invoices/inv1/status", headers=headers, json={"version": 1, "status": "approved", "change_note": "Forged approval"})).status_code, expected)

    async def test_unknown_unconfirmed_archived_and_ambiguous_orders_cannot_generate_documents(self):
        self.assertEqual((await self.create(order_id="missing")).status_code, 404)
        for values in ({"status": "draft"}, {"status": "cancelled"}, {"deleted_at": "2026-10-19"}, {"workflow_enabled": False}):
            await self.db.orders.update_one({"id": "sale"}, {"$set": values})
            self.assertEqual((await self.create()).status_code, 409)
            await self.db.orders.replace_one({"id": "sale"}, copy.deepcopy(self.order))
        await self.db.orders.insert_one({**self.order, "_id": "duplicate-order"})
        self.assertEqual((await self.create()).status_code, 409)
        self.assertEqual(await self.db.commercial_invoices.count_documents({}), 0)

    async def test_strict_input_stale_order_bad_dates_and_customs_never_write(self):
        cases = [({"source_order_snapshot": {}},422),({"total_usd": 1},422),({"status":"approved"},422),
            ({"source_order_version":True},422),({"source_order_version":1},409),({"seller_name":"bad\x00"},422),
            ({"issue_date":"2099-12-31"},400),({"issue_date":"2026-02-30"},400),({"issue_date":"2026-10-18"},400),
            ({"buyer_country":"Germany"},400),({"customs":[{"index":1}]},400),({"customs":[{"index":0,"hs_code":"ABC"}]},422)]
        for changes, expected in cases:
            r = await self.create(**changes)
            self.assertEqual(r.status_code, expected, r.text)
        self.assertEqual(await self.db.commercial_invoices.count_documents({}), 0)

    async def test_draft_pdf_is_watermarked_and_pdf_text_has_no_private_data_or_active_content(self):
        await self.invoice(notes='<img src="https://private.invalid/probe"> & <script>bad()</script>')
        r = await self.pdf()
        self.assertEqual(r.status_code, 200, r.text[:100])
        text = self.text(r)
        self.assertIn("DRAFT", text)
        self.assertIn("COMMERCIAL INVOICE", text)
        self.assertIn("<img", text)
        for secret in ("PRIVATE-COST-CANARY", "PRIVATE-ORDER-CANARY", "Supplier", "supplier_price"):
            self.assertNotIn(secret, text)
        reader = PdfReader(io.BytesIO(r.content))
        self.assertNotIn("/OpenAction", reader.trailer["/Root"])
        self.assertNotIn("/Names", reader.trailer["/Root"])
        self.assertTrue(all(not p.get("/Annots") for p in reader.pages))
        self.assertEqual(r.headers["content-type"], "application/pdf")
        self.assertIn("no-store", r.headers["cache-control"])
        self.assertEqual(r.headers["x-content-type-options"], "nosniff")
        self.assertIn("-draft-v1.pdf", r.headers["content-disposition"])

    async def test_approval_requires_complete_details_and_explicit_review(self):
        record = await self.invoice(seller_address="", customs=[{"index":0}])
        self.assertEqual((await self.decide(record, details_confirmed=False)).status_code, 400)
        self.assertEqual((await self.decide(record)).status_code, 400)
        current = (await self.client.get("/api/commercial-invoices/inv1", headers=self.headers())).json()
        self.assertEqual(current["version"], 1)
        self.assertEqual(current["status"], "draft")

    async def test_approved_pdf_is_deterministic_precise_and_does_not_claim_a_signature(self):
        record = await self.approved()
        first, second = await self.pdf(), await self.pdf()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.content, second.content)
        text = self.text(first)
        self.assertGreaterEqual(PdfReader(io.BytesIO(first.content)).metadata.creation_date.year, 2026)
        for value in ("IBIAG Test Exporter", "Original Buyer", "11063010", "4.26", "8.52", "Prepaid", "APPROVED", "No electronic or handwritten signature"):
            self.assertIn(value, text)
        self.assertNotIn("DRAFT", text)
        self.assertNotIn("CANCELLED", text)
        self.assertEqual(record["approved_by"], "admin")
        self.assertIn("-approved-v2.pdf", first.headers["content-disposition"])

    async def test_pdf_preserves_quantity_and_unit_precision_beyond_four_decimals(self):
        items = [{**self.order["items"][0], "quantity":2.001234, "unit_price":4.261512}]
        await self.db.orders.update_one({"id":"sale"},{"$set":{"items":items,"total_usd":8.53}})
        await self.approved()
        text = self.text(await self.pdf())
        for value in ("2.001234", "4.261512", "8.53"):
            self.assertIn(value,text)

    async def test_edit_versions_approved_immutability_and_reference_collision(self):
        record = await self.invoice()
        details = {k:record[k] for k in server.COMMERCIAL_INVOICE_DETAILS}
        r = await self.client.put("/api/commercial-invoices/inv1", headers=self.headers(), json={**details,"payment_terms":"100% prepaid","version":1,"change_note":"Updated terms"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["version"],2)
        stale = await self.decide(record)
        self.assertEqual(stale.status_code,409)
        self.assertEqual((await self.decide(r.json())).status_code,200)
        r = await self.client.put("/api/commercial-invoices/inv1", headers=self.headers(), json={**details,"version":3,"change_note":"Rewrite approval"})
        self.assertEqual(r.status_code,409)
        self.assertEqual((await self.create(id="inv2",reference="CI-OTHER")).status_code,409)

    async def test_order_commercial_edit_and_cancellation_are_blocked_until_invoice_cancelled(self):
        invoice = await self.approved()
        for changes in ({"incoterm":"CIF"},{"number":"Other reference"},{"receivable_due_date":"2026-12-19"},{"status":"cancelled"}):
            r = await self.update_order({**self.order,**changes})
            self.assertEqual(r.status_code,409,r.text)
        cancelled = await self.decide(invoice,"cancelled")
        self.assertEqual(cancelled.status_code,200,cancelled.text)
        r = await self.update_order({**self.order,"incoterm":"CIF"})
        self.assertEqual(r.status_code,200,r.text)
        pdf = await self.pdf()
        self.assertEqual(pdf.status_code,200)
        self.assertIn("CANCELLED",self.text(pdf))
        self.assertNotIn("DRAFT",self.text(pdf))
        self.assertEqual((await self.decide(cancelled.json())).status_code,409)

    async def test_logistics_and_payment_do_not_change_commercial_pdf_or_duplicate_finance(self):
        await self.approved()
        before = (await self.pdf()).content
        r = await self.update_order({**self.order,"status":"shipped"})
        self.assertEqual(r.status_code,200,r.text)
        payment = await self.client.patch("/api/finance/order:sale/toggle-paid",headers=self.headers(),json={"paid":True})
        self.assertEqual(payment.status_code,200,payment.text)
        self.assertEqual((await self.pdf()).content,before)
        self.assertEqual(len(await server.all_finance_entries()),1)

    async def test_concurrent_creations_and_decisions_have_only_one_winner(self):
        creations = await asyncio.gather(self.create(),self.create(id="inv2",reference="CI-2"))
        self.assertEqual(sorted(r.status_code for r in creations),[200,409])
        invoice = next(r.json() for r in creations if r.status_code==200)
        decisions = await asyncio.gather(self.decide(invoice),self.decide(invoice,"cancelled"))
        self.assertEqual(sorted(r.status_code for r in decisions),[200,409])
        self.assertEqual(await self.db.commercial_invoices.count_documents({}),1)
        stored = await self.db.commercial_invoices.find_one({"id":invoice["id"]})
        self.assertEqual(len(stored["history"]),2)

    async def test_concurrent_order_edit_and_document_creation_cannot_capture_stale_values(self):
        doc, order = await asyncio.gather(self.create(),self.update_order({**self.order,"incoterm":"CIF"}))
        self.assertEqual(sorted((doc.status_code,order.status_code)),[200,409])
        self.assertEqual(await self.db.commercial_invoices.count_documents({}),int(doc.status_code==200))

    async def test_cancelled_document_keeps_reference_and_allows_a_new_number(self):
        record = await self.invoice()
        self.assertEqual((await self.decide(record,"cancelled")).status_code,200)
        self.assertEqual((await self.create(id="inv2")).status_code,409)
        self.assertEqual((await self.create(id="inv2",reference="CI-2")).status_code,200)
        source = (await self.client.get("/api/orders/sale/commercial-invoice-draft",headers=self.headers())).json()
        self.assertEqual(source["active_invoice_id"],"inv2")

    async def test_external_commercial_drift_blocks_approval_and_approved_download(self):
        record = await self.approved()
        await self.db.orders.update_one({"id":"sale"},{"$set":{"customer":"Externally changed"}})
        detail = (await self.client.get("/api/commercial-invoices/inv1",headers=self.headers())).json()
        self.assertTrue(detail["source_changed"])
        self.assertEqual((await self.pdf()).status_code,409)

    async def test_cancel_during_pdf_generation_never_returns_stale_approval(self):
        record = await self.approved()
        entered, release = asyncio.Event(), asyncio.Event()
        original = server.invoice_pdf_bytes
        async def delayed(value):
            entered.set()
            await release.wait()
            return await original(value)
        with patch.object(server,"invoice_pdf_bytes",side_effect=delayed):
            task = asyncio.create_task(self.pdf())
            await asyncio.wait_for(entered.wait(),2)
            try:
                self.assertEqual((await self.decide(record,"cancelled")).status_code,200)
            finally:
                release.set()
            response = await task
        self.assertEqual(response.status_code,409,response.text)
        self.assertNotEqual(response.headers["content-type"],"application/pdf")

    async def test_summary_pagination_and_filters_do_not_expose_addresses_or_history(self):
        await self.invoice()
        r = await self.client.get("/api/commercial-invoices?status=draft&order_id=sale&limit=1",headers=self.headers())
        self.assertEqual(r.status_code,200)
        self.assertEqual(len(r.json()),1)
        for field in ("history","seller_address","source_order_snapshot","customs"):
            self.assertNotIn(field,r.json()[0])
        self.assertEqual((await self.client.get("/api/commercial-invoices?skip=1",headers=self.headers())).json(),[])
        self.assertEqual((await self.client.get("/api/commercial-invoices?limit=251",headers=self.headers())).status_code,422)

    async def test_multiple_pdf_pages_repeat_headers_without_dropping_items(self):
        items=[{**self.order["items"][0],"product_name":f"LINE-{i:02d} "+"AÇAÍ EXTRACT POWDER - ORGANIC INGREDIENT "*4} for i in range(25)]
        await self.db.orders.update_one({"id":"sale"},{"$set":{"items":items,"total_usd":213}})
        await self.invoice(customs=[{"index":i,"origin_country":"Brazil","hs_code":"11063010"} for i in range(25)])
        r=await self.pdf()
        self.assertEqual(r.status_code,200)
        reader=PdfReader(io.BytesIO(r.content))
        self.assertGreaterEqual(len(reader.pages),3)
        text=self.text(r)
        for i in range(25):self.assertIn(f"LINE-{i:02d}",text)
        for page in reader.pages:
            self.assertIn("COMMERCIAL INVOICE",page.extract_text())
            self.assertIn("DRAFT",page.extract_text())
        self.assertIn("213.00",text)

    async def test_renderer_errors_do_not_leak_input_or_commit_approval(self):
        record=await self.invoice()
        with patch.object(server,"render_commercial_invoice",side_effect=ValueError("PRIVATE-RENDER-CANARY")):
            r=await self.decide(record)
        self.assertEqual(r.status_code,400)
        self.assertNotIn("PRIVATE-RENDER-CANARY",r.text)
        stored=await self.db.commercial_invoices.find_one({"id":"inv1"})
        self.assertEqual((stored["status"],stored["version"]),("draft",1))

    async def test_bad_glyph_preflight_does_not_approve_or_silently_omit_text(self):
        record = await self.invoice(declaration="漢字")
        r = await self.decide(record)
        self.assertEqual(r.status_code,400,r.text)
        stored = await self.db.commercial_invoices.find_one({"id":"inv1"})
        self.assertEqual((stored["status"],stored["version"]),("draft",1))

    async def test_failure_and_history_or_size_limits_preserve_documents(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app,raise_app_exceptions=False),base_url="http://test") as client:
            with patch.object(server,"invoice_event",side_effect=RuntimeError("PRIVATE-ERROR-CANARY")):
                r = await client.post("/api/commercial-invoices",headers=self.headers(),json=self.invoice_body)
        self.assertEqual(r.status_code,500)
        self.assertNotIn("PRIVATE-ERROR-CANARY",r.text)
        self.assertEqual(await self.db.commercial_invoices.count_documents({}),0)
        record = await self.invoice()
        for values, expected in [({"history":record["history"]*50},400),({"history":record["history"],"legacy":"x"*(256*1024)},413)]:
            await self.db.commercial_invoices.update_one({"id":"inv1"},{"$set":values})
            before = await self.db.commercial_invoices.find_one({"id":"inv1"})
            self.assertEqual((await self.decide(record,"cancelled")).status_code,expected)
            self.assertEqual(await self.db.commercial_invoices.find_one({"id":"inv1"}),before)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class RealMongoCommercialInvoiceTests(CommercialInvoiceTests):
    real_mongo = True
