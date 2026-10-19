"""Saved price calculation to draft order, without external services or live data."""
import asyncio
import copy
import os
import unittest

import test_order_crm_link as fixtures
import server


class PriceOrderTests(unittest.IsolatedAsyncioTestCase):
    real_mongo = False
    headers = fixtures.OrderCrmLinkTests.headers
    create = fixtures.OrderCrmLinkTests.create
    update = fixtures.OrderCrmLinkTests.update
    asyncTearDown = fixtures.OrderCrmLinkTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.OrderCrmLinkTests.asyncSetUp(self)
        await self.db.suppliers.insert_one({"id": "s", "name": "Supplier"})
        self.price = {"id": "price", "product_name": "Fake title", "product_id": "p", "offer_id": "offer",
                      "supplier_id": "s", "supplier_name": "Fake supplier", "unit": "kg", "quantity": 1000,
                      "supplier_price": 17.5, "margin_pct": 15, "taxes": [{"name": "Tax", "pct": 6}],
                      "exchange_rate": 5.2, "sell_price_usd": 999999, "sale_total_usd": 999999}
        await self.db.prices.insert_one(copy.deepcopy(self.price))

    async def preview(self, pid="price", user="admin"):
        return await self.client.get(f"/api/prices/{pid}/order-draft", headers=self.headers(user))

    async def linked_order(self, **changes):
        preview = await self.preview()
        self.assertEqual(preview.status_code, 200, preview.text)
        body = {**self.body, **preview.json(), **changes}
        response = await self.create(body)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    async def test_preview_recalculates_canonical_values_and_never_writes(self):
        before = await self.db.prices.find_one({"id": "price"})
        response = await self.preview()
        self.assertEqual(response.status_code, 200, response.text)
        source = response.json()
        self.assertEqual(source["items"][0]["quantity"], 1000)
        self.assertEqual(source["items"][0]["unit_price"], 4.26)
        self.assertEqual(source["total_usd"], 4260)
        self.assertEqual(source["source_price_snapshot"]["product_name"], "Product")
        self.assertEqual(source["source_price_snapshot"]["supplier_name"], "Supplier")
        self.assertEqual(len(source["source_price_revision"]), 64)
        self.assertEqual((await self.preview()).json(), source)  # legacy timestamps absent: stable
        self.assertEqual(await self.db.prices.find_one({"id": "price"}), before)
        self.assertEqual(await self.db.orders.count_documents({}), 0)
        self.assertEqual(await self.db.finance.count_documents({}), 0)

    async def test_create_ignores_forged_items_totals_and_snapshot_and_preserves_crm(self):
        order = await self.linked_order(items=[{"product_id": "wrong", "offer_id": "wrong", "quantity": 1, "unit_price": 1}],
                                        total_usd=1, source_price_snapshot={"supplier_price": 0})
        self.assertEqual(order["items"][0]["unit_price"], 4.26)
        self.assertEqual(order["items"][0]["quantity"], 1000)
        self.assertEqual(order["total_usd"], 4260)
        self.assertEqual(order["source_price_snapshot"]["supplier_price"], 17.5)
        self.assertEqual(order["source_price_snapshot"]["taxes"], [{"name": "Tax", "pct": 6}])
        self.assertEqual(order["customer"], "Original Buyer")
        self.assertEqual(order["status"], "draft")
        self.assertEqual(await server.all_finance_entries(), [])
        self.assertEqual((await self.db.products.find_one({"id": "p"}))["stock"], 10)
        self.assertEqual((await self.client.get("/api/orders", headers=self.headers())).json()[0], order)

    async def test_stale_revision_cannot_silently_create_new_price_or_confirm_sale(self):
        source = (await self.preview()).json()
        await self.db.prices.update_one({"id": "price"}, {"$set": {"supplier_price": 20}})
        response = await self.create({**self.body, **source})
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(await self.db.orders.count_documents({}), 0)
        fresh = (await self.preview()).json()
        self.assertNotEqual(source["source_price_revision"], fresh["source_price_revision"])
        self.assertEqual((await self.create({**self.body, **fresh, "status": "confirmed"})).status_code, 400)
        self.assertEqual((await self.create({**self.body, **fresh, "source_price_revision": ""})).status_code, 409)
        self.assertEqual((await self.create({**self.body, **fresh})).status_code, 200)

    async def test_saved_origin_is_immutable_after_calculation_edits_and_old_client_updates(self):
        order = await self.linked_order()
        await self.db.prices.update_one({"id": "price"}, {"$set": {"quantity": 50, "supplier_price": 20}})
        old_client = {key: value for key, value in order.items() if not key.startswith("source_price_")}
        response = await self.update({**old_client, "notes": "Reviewed", "source_price_snapshot": {"injected": True}})
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        for key in ("source_price_id", "source_price_revision", "source_price_snapshot", "items", "total_usd"):
            self.assertEqual(updated[key], order[key])
        self.assertEqual(updated["notes"], "Reviewed")
        for changes in ({"source_price_id": ""}, {"source_price_id": "another"},
                        {"items": [{**updated["items"][0], "quantity": 5}]}):
            self.assertEqual((await self.update({**updated, **changes})).status_code, 409)
        self.assertEqual(await self.db.orders.count_documents({}), 1)

    async def test_manual_order_does_not_accept_fake_origin_snapshot_or_later_injection(self):
        response = await self.create({**self.body, "source_price_snapshot": {"secret": "untrusted"}, "source_price_revision": "a" * 64})
        self.assertEqual(response.status_code, 200, response.text)
        manual = response.json()
        self.assertEqual(manual["source_price_snapshot"], {})
        self.assertEqual(manual["source_price_revision"], "")
        self.assertEqual((await self.update({**manual, **(await self.preview()).json()})).status_code, 409)

    async def test_unknown_duplicate_invalid_and_unlinked_calculations_require_review(self):
        self.assertEqual((await self.preview("missing")).status_code, 404)
        variants = [{"offer_id": ""}, {"supplier_id": "missing"}, {"product_id": "wrong"},
                    {"exchange_rate": 0}, {"supplier_price": -1}, {"margin_pct": 100},
                    {"quantity": 0}, {"extras": [{"name": float("nan"), "value": 0}]}]
        for index, change in enumerate(variants):
            with self.subTest(index=index):
                pid = f"invalid-{index}"
                await self.db.prices.insert_one({**self.price, "id": pid, **change})
                self.assertEqual((await self.preview(pid)).status_code, 400)
        await self.db.prices.insert_one(copy.deepcopy(self.price))
        self.assertEqual((await self.preview()).status_code, 409)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_inactive_and_ambiguous_references_fail_without_linking_arbitrary_record(self):
        await self.db.product_offers.update_one({"id": "offer"}, {"$set": {"active": False}})
        self.assertEqual((await self.preview()).status_code, 400)
        await self.db.product_offers.update_one({"id": "offer"}, {"$set": {"active": True}})
        for name, rid in (("product_offers", "offer"), ("products", "p"), ("suppliers", "s")):
            collection = self.db[name]
            duplicate = await collection.find_one({"id": rid}, {"_id": 0})
            result = await collection.insert_one(duplicate)
            self.assertEqual((await self.preview()).status_code, 409)
            await collection.delete_one({"_id": result.inserted_id})

    async def test_preview_permissions_and_origin_validation_cannot_be_forged(self):
        self.assertEqual((await self.client.get("/api/prices/price/order-draft")).status_code, 401)
        for user in ("owner", "stranger"):
            response = await self.client.get("/api/prices/price/order-draft", headers={**self.headers(user), "X-User-Role": "admin"})
            self.assertEqual(response.status_code, 403)
        for change in ({"source_price_id": {"$ne": None}}, {"source_price_id": "bad\x00id"},
                       {"source_price_id": "x" * 201}, {"source_price_revision": "fake"}):
            self.assertEqual((await self.create({**self.body, **change})).status_code, 422)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_protected_origin_deletion_and_racing_creation_never_orphan_orders(self):
        source = (await self.preview()).json()
        results = await asyncio.gather(self.create({**self.body, **source}),
                                       self.client.delete("/api/prices/price", headers=self.headers()))
        self.assertTrue(all(r.status_code in {200, 404, 409} for r in results))
        order = await self.db.orders.find_one({"id": "sale"})
        if order:
            self.assertIsNotNone(await self.db.prices.find_one({"id": order["source_price_id"]}))
        else:
            await self.db.prices.delete_many({"id": "price"})
            await self.db.prices.insert_one(copy.deepcopy(self.price))
            await self.linked_order()
        self.assertEqual((await self.client.delete("/api/orders/sale", headers=self.headers())).status_code, 200)
        self.assertEqual((await self.client.delete("/api/prices/price", headers=self.headers())).status_code, 409)

    async def test_explicit_confirmation_shipping_and_retries_keep_one_account_and_movement(self):
        await self.db.prices.update_one({"id": "price"}, {"$set": {"quantity": 2}})
        order = await self.linked_order(track_stock=True)
        self.assertEqual((await self.create({**self.body, **(await self.preview()).json()})).status_code, 409)
        response = await self.update({**order, "status": "confirmed", "order_date": "2026-10-19", "receivable_due_date": "2026-11-19"})
        self.assertEqual(response.status_code, 200, response.text)
        response = await self.update({**response.json(), "status": "shipped"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(await server.all_finance_entries()), 1)
        products, orders, purchases = await server.business_snapshot()
        self.assertEqual(server.inventory_balances(products, orders, purchases)["p"]["stock"], 8)
        self.assertEqual(await self.db.orders.count_documents({}), 1)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class RealMongoPriceOrderTests(PriceOrderTests):
    real_mongo = True
