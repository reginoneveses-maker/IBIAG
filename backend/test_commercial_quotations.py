"""Commercial quotation lifecycle, isolated HTTP and optional disposable MongoDB."""
import asyncio
import copy
import os
import unittest
from unittest.mock import patch
import httpx
import test_order_price_source as fixtures
import server

class QuotationTests(unittest.IsolatedAsyncioTestCase):
    real_mongo = False
    headers = fixtures.PriceOrderTests.headers
    create = fixtures.PriceOrderTests.create
    update = fixtures.PriceOrderTests.update
    asyncTearDown = fixtures.PriceOrderTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.PriceOrderTests.asyncSetUp(self)
        await self.db.prices.update_one({"id": "price"}, {"$set": {"quantity": 2}})
        preview = (await self.client.get("/api/prices/price/order-draft", headers=self.headers())).json()
        self.quote_body = {"id": "q1", "reference": "COT-1", "lead_id": "lead1", "source_price_id": "price",
            "source_price_revision": preview["source_price_revision"], "valid_until": "2099-12-31", "incoterm": "FOB",
            "payment_terms": "50% before shipment", "delivery_terms": "Santos port, 30 days after confirmation",
            "change_note": "Initial commercial review"}

    async def quote(self, **changes):
        r = await self.client.post("/api/quotations", headers=self.headers(), json={**self.quote_body, **changes})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    async def state(self, q, status="approved"):
        return await self.client.post(f"/api/quotations/{q['id']}/status", headers=self.headers(),
            json={"version": q["version"], "status": status, "change_note": "Explicit internal decision"})

    async def approved(self):
        q = await self.quote()
        r = await self.state(q)
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()

    async def order_preview(self):
        return await self.client.get("/api/quotations/q1/order-draft", headers=self.headers())

    async def test_canonical_quote_and_internal_approval_never_create_business_movements(self):
        q = await self.quote()
        self.assertEqual(q["status"], "draft")
        self.assertEqual(q["customer"], "Original Buyer")
        self.assertEqual(q["items"][0]["quantity"], 2)
        self.assertEqual(q["items"][0]["unit_price"], 4.26)
        self.assertEqual(q["total_usd"], 8.52)
        self.assertEqual(q["history"][0]["by"], "admin")
        self.assertNotIn("_id", q)
        self.assertEqual((await self.order_preview()).status_code, 409)
        approved = await self.state(q)
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertTrue(approved.json()["can_order"])
        self.assertEqual(approved.json()["approved_by"], "admin")
        self.assertEqual(await self.db.orders.count_documents({}), 0)
        self.assertEqual(await server.all_finance_entries(), [])

    async def test_stale_price_unknown_buyer_and_strict_input_never_write(self):
        for changes, status in [({"lead_id": "missing"}, 400), ({"version": 1}, 422),
            ({"total_usd": 1}, 422), ({"history": []}, 422), ({"status": "approved"}, 422),
            ({"payment_terms": "bad\x00"}, 422), ({"valid_until": "2026-02-30"}, 400),
            ({"valid_until": "2000-01-01"}, 400), ({"source_price_revision": "a"*64}, 409)]:
            r = await self.client.post("/api/quotations", headers=self.headers(), json={**self.quote_body, **changes})
            self.assertEqual(r.status_code, status, r.text)
        await self.db.prices.update_one({"id": "price"}, {"$set": {"quantity": 3}})
        r = await self.client.post("/api/quotations", headers=self.headers(), json=self.quote_body)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(await self.db.quotations.count_documents({}), 0)

    async def test_versioned_terms_frozen_after_approval_and_price_changes_do_not_reprice(self):
        q = await self.quote()
        terms = {key: self.quote_body[key] for key in server.QUOTE_TERMS if key in self.quote_body}
        response = await self.client.put("/api/quotations/q1", headers=self.headers(),
            json={**terms, "version": q["version"], "payment_terms": "100% before shipment", "change_note": "Terms reviewed"})
        self.assertEqual(response.status_code, 200, response.text)
        q = response.json()
        self.assertEqual(q["version"], 2)
        self.assertEqual(len(q["history"]), 2)
        self.assertEqual((await self.state(q)).status_code, 200)
        response = await self.client.put("/api/quotations/q1", headers=self.headers(),
            json={**terms, "version": 3, "change_note": "Rewrite approved quote"})
        self.assertEqual(response.status_code, 409)
        await self.db.prices.update_one({"id": "price"}, {"$set": {"supplier_price": 999}})
        preview = await self.order_preview()
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertEqual(preview.json()["total_usd"], 8.52)
        self.assertEqual(preview.json()["source_quote_snapshot"]["payment_terms"], "100% before shipment")

    async def test_order_uses_approved_snapshot_ignores_forgery_and_keeps_one_ledger(self):
        q = await self.approved()
        preview = (await self.order_preview()).json()
        await self.db.leads.update_one({"id": "lead1"}, {"$set": {"company": "Changed later"}})
        r = await self.create({**self.body, **preview, "items": [], "incoterm": "CIF", "lead_id": "missing",
                               "source_quote_snapshot": {"total_usd": 1}, "total_usd": 1})
        self.assertEqual(r.status_code, 200, r.text)
        order = r.json()
        self.assertEqual(order["incoterm"], "FOB")
        self.assertEqual(order["customer"], "Original Buyer")
        self.assertEqual(order["total_usd"], 8.52)
        self.assertEqual(order["source_quote_snapshot"]["reference"], q["reference"])
        self.assertEqual(await server.all_finance_entries(), [])
        order = (await self.update({**order, "status": "confirmed", "order_date": "2020-10-01", "receivable_due_date": "2020-11-01", "track_stock": True})).json()
        r = await self.update({**order, "status": "shipped"})
        self.assertEqual(r.status_code, 200, r.text)
        products, orders, purchases = await server.business_snapshot()
        self.assertEqual(server.inventory_balances(products, orders, purchases)["p"]["stock"], 8)
        self.assertEqual(len(await server.all_finance_entries()), 1)
        self.assertEqual((await self.state(q, "cancelled")).status_code, 409)
        self.assertEqual((await self.order_preview()).status_code, 409)

    async def test_old_clients_preserve_snapshot_and_no_generic_order_bypass(self):
        await self.approved()
        order = (await self.create({**self.body, **(await self.order_preview()).json()})).json()
        for changes in ({"source_quote_id": "other"}, {"lead_id": "lead2"}, {"incoterm": "CIF"}, {"items": []}):
            self.assertEqual((await self.update({**order, **changes})).status_code, 409)
        old = {k: v for k, v in order.items() if not k.startswith("source_quote")}
        r = await self.update({**old, "source_quote_snapshot": {"forged": True}, "notes": "Unrelated note"})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["source_quote_snapshot"], order["source_quote_snapshot"])
        manual = await self.create({"id": "manual", "customer": "Manual", "source_quote_snapshot": {"forged": True}, "source_quote_revision": 999})
        self.assertEqual(manual.json()["source_quote_snapshot"], {})
        self.assertEqual(manual.json()["source_quote_revision"], 0)

    async def test_expiration_cancellation_and_closed_quote_cannot_convert(self):
        q = await self.approved()
        await self.db.quotations.update_one({"id": "q1"}, {"$set": {"valid_until": "2000-01-01"}})
        self.assertEqual((await self.order_preview()).status_code, 409)
        detail = (await self.client.get("/api/quotations/q1", headers=self.headers())).json()
        self.assertTrue(detail["expired"])
        self.assertFalse(detail["can_order"])
        cancel = await self.state(q, "cancelled")
        self.assertEqual(cancel.status_code, 200, cancel.text)
        self.assertEqual((await self.state(cancel.json())).status_code, 409)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_all_quotation_endpoints_are_administrative(self):
        await self.quote()
        for headers, expected in [({}, 401), (self.headers("owner"), 403), (self.headers("stranger"), 403)]:
            headers = {**headers, "X-User-Role": "admin"}
            for path in ("/api/quotations", "/api/quotations/q1", "/api/quotations/q1/order-draft"):
                self.assertEqual((await self.client.get(path, headers=headers)).status_code, expected)
            self.assertEqual((await self.client.post("/api/quotations", headers=headers, json=self.quote_body)).status_code, expected)
            self.assertEqual((await self.client.put("/api/quotations/q1", headers=headers, json={**{k: self.quote_body[k] for k in server.QUOTE_TERMS if k in self.quote_body}, "version": 1, "change_note": "Forged admin"})).status_code, expected)
            self.assertEqual((await self.client.post("/api/quotations/q1/status", headers=headers,
                json={"version": 1, "status": "approved", "change_note": "Forged admin"})).status_code, expected)

    async def test_deletion_guards_keep_quote_references_even_when_cancelled(self):
        q = await self.quote()
        self.assertEqual((await self.state(q, "cancelled")).status_code, 200)
        for path in ("/api/leads/lead1", "/api/prices/price", "/api/product-offers/offer", "/api/products/p", "/api/suppliers/s"):
            r = await self.client.delete(path, headers=self.headers())
            self.assertIn(r.status_code, (400, 409), r.text)
        self.assertEqual(await self.db.quotations.count_documents({}), 1)

    async def test_concurrent_decisions_are_versioned_and_conversion_cannot_duplicate(self):
        q = await self.quote()
        decisions = await asyncio.gather(self.state(q), self.state(q, "cancelled"))
        self.assertEqual(sorted(r.status_code for r in decisions), [200, 409])
        winner = next(r.json() for r in decisions if r.status_code == 200)
        self.assertEqual(len(winner["history"]), 2)
        q2 = await self.quote(id="q2", reference="COT-2")
        self.assertEqual((await self.state(q2)).status_code, 200)
        preview = (await self.client.get("/api/quotations/q2/order-draft", headers=self.headers())).json()
        results = await asyncio.gather(*[self.create({**self.body, **preview, "id": f"sale-{i}"}) for i in range(2)])
        self.assertEqual(sorted(r.status_code for r in results), [200, 409])
        self.assertEqual(await self.db.orders.count_documents({}), 1)

    async def test_cancel_racing_conversion_never_leaves_cancelled_quote_with_order(self):
        q = await self.approved()
        preview = (await self.order_preview()).json()
        order, cancel = await asyncio.gather(self.create({**self.body, **preview}), self.state(q, "cancelled"))
        self.assertEqual(sorted((order.status_code, cancel.status_code)), [200, 409])
        stored = await self.db.quotations.find_one({"id": "q1"})
        self.assertEqual(await self.db.orders.count_documents({}), int(stored["status"] == "approved"))
        self.assertEqual(await server.all_finance_entries(), [])

    async def test_bad_revision_other_source_and_direct_confirmation_rejected(self):
        q = await self.approved()
        source = (await self.order_preview()).json()
        for changes, expected in [({"source_quote_revision": 1}, 409), ({"source_quote_revision": True}, 422),
            ({"source_price_id": "price"}, 400), ({"status": "confirmed"}, 400)]:
            response = await self.create({**self.body, **source, **changes})
            self.assertEqual(response.status_code, expected, response.text)
        await self.db.product_offers.update_one({"id": "offer"}, {"$set": {"active": False}})
        self.assertEqual((await self.order_preview()).status_code, 409)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_list_projection_pagination_and_reference_collision(self):
        await self.quote()
        r = await self.client.get("/api/quotations?limit=1&status=draft&lead_id=lead1", headers=self.headers())
        self.assertEqual(r.status_code, 200, r.text)
        summary = r.json()[0]
        for key in ("history", "source_price_snapshot", "items", "payment_terms"):
            self.assertNotIn(key, summary)
        self.assertEqual((await self.client.get("/api/quotations?skip=1", headers=self.headers())).json(), [])
        self.assertEqual((await self.client.get("/api/quotations?lead_id=lead2", headers=self.headers())).json(), [])
        self.assertEqual((await self.client.get("/api/quotations?limit=251", headers=self.headers())).status_code, 422)
        self.assertEqual((await self.client.post("/api/quotations", headers=self.headers(), json={**self.quote_body, "id": "q2"})).status_code, 409)

    async def test_failure_before_commit_and_bounds_preserve_records(self):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="http://test") as client:
            with patch.object(server, "quotation_event", side_effect=RuntimeError("synthetic-private-marker")):
                r = await client.post("/api/quotations", headers=self.headers(), json=self.quote_body)
        self.assertEqual(r.status_code, 500)
        self.assertNotIn("synthetic-private-marker", r.text)
        self.assertEqual(await self.db.quotations.count_documents({}), 0)
        q = await self.quote()
        await self.db.quotations.update_one({"id": "q1"}, {"$set": {"history": q["history"]*50}})
        before = await self.db.quotations.find_one({"id": "q1"})
        self.assertEqual((await self.state(q)).status_code, 400)
        self.assertEqual(await self.db.quotations.find_one({"id": "q1"}), before)

    async def test_snapshot_names_survive_catalog_rename(self):
        await self.approved()
        await self.db.products.update_one({"id": "p"}, {"$set": {"name": "Renamed product"}})
        await self.db.product_offers.update_one({"id": "offer"}, {"$set": {"supplier_name": "Renamed label"}})
        r = await self.create({**self.body, **(await self.order_preview()).json()})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["items"][0]["product_name"], "Product")
        self.assertEqual(r.json()["items"][0]["supplier_name"], "Supplier")
        self.assertEqual((await self.update({**r.json(), "notes": "Reviewed"})).status_code, 200)

    async def test_catalog_change_after_preview_cannot_change_approved_unit(self):
        await self.approved()
        source = (await self.order_preview()).json()
        await self.db.product_offers.update_one({"id": "offer"}, {"$set": {"unit": "box"}})
        response = await self.create({**self.body, **source})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_archived_cancelled_order_still_prevents_second_conversion(self):
        await self.approved()
        source = (await self.order_preview()).json()
        response = await self.create({**self.body, **source})
        self.assertEqual(response.status_code, 200, response.text)
        cancelled = await self.update({**response.json(), "status": "cancelled", "order_date": "2026-10-19"})
        self.assertEqual(cancelled.status_code, 200, cancelled.text)
        archived = await self.client.delete(f"/api/orders/{self.body['id']}", headers=self.headers())
        self.assertEqual(archived.status_code, 200, archived.text)
        self.assertEqual((await self.order_preview()).status_code, 409)
        duplicate = await self.create({**self.body, **source, "id": "second-order"})
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        detail = (await self.client.get("/api/quotations/q1", headers=self.headers())).json()
        self.assertEqual(detail["linked_order_id"], self.body["id"])
        self.assertFalse(detail["can_order"])

    async def test_size_limit_and_optimistic_edit_preserve_previous_document(self):
        q = await self.quote()
        terms = {k: q[k] for k in server.QUOTE_TERMS}
        self.assertEqual((await self.state(q)).status_code, 200)
        r = await self.client.put("/api/quotations/q1", headers=self.headers(),
            json={**terms, "version": 1, "change_note": "Stale edit"})
        self.assertEqual(r.status_code, 409)
        await self.db.quotations.update_one({"id": "q1"}, {"$set": {"source_price_snapshot": {"legacy": "x" * (256 * 1024)}}})
        before = await self.db.quotations.find_one({"id": "q1"})
        response = await self.state({**q, "version": 2}, "cancelled")
        self.assertEqual(response.status_code, 413)
        self.assertEqual(await self.db.quotations.find_one({"id": "q1"}), before)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class RealMongoQuotationTests(QuotationTests):
    real_mongo = True
