"""Shipment HTTP checks, repeated against disposable MongoDB in CI."""
import asyncio
import copy
import os
import unittest
from unittest.mock import patch, AsyncMock
import httpx

import test_order_crm_link as fixtures
import server


class ShipmentTests(unittest.IsolatedAsyncioTestCase):
    real_mongo = False
    headers = fixtures.OrderCrmLinkTests.headers
    create = fixtures.OrderCrmLinkTests.create
    update = fixtures.OrderCrmLinkTests.update
    asyncTearDown = fixtures.OrderCrmLinkTests.asyncTearDown

    async def asyncSetUp(self):
        await fixtures.OrderCrmLinkTests.asyncSetUp(self)
        response = await self.create({**self.body, "status": "confirmed", "order_date": "2020-10-01",
            "receivable_due_date": "2020-11-01", "track_stock": True,
            "items": [{"product_id": "p", "offer_id": "offer", "quantity": 2, "unit_price": 3}]})
        self.assertEqual(response.status_code, 200, response.text)
        self.order = response.json()
        self.payload = {"version": self.order["version"], "status": "planned", "reference": "SHIP-1",
                        "origin": "Santos", "destination": "Lisboa", "mode": "sea", "responsible_id": "owner",
                        "planned_departure": "2020-10-02", "planned_arrival": "2020-10-10",
                        "change_note": "Planejamento inicial"}

    async def save(self, **changes):
        response = await self.client.put("/api/orders/sale/shipment", headers=self.headers(),
                                         json={**self.payload, **changes})
        if response.status_code == 200:
            self.payload.update(changes)
            self.payload["version"] = response.json()["version"]
        return response

    async def record(self):
        return await self.db.orders.find_one({"id": "sale"}, {"_id": 0})

    async def test_complete_workflow_moves_stock_once_and_keeps_single_receivable(self):
        for state, dates in [("planned", {}), ("booked", {}),
            ("in_transit", {"actual_departure": "2020-10-02"}),
            ("arrived", {"actual_arrival": "2020-10-10"}),
            ("delivered", {"actual_delivery": "2020-10-11"})]:
            response = await self.save(status=state, **dates)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(await server.all_finance_entries()), 1)
        order = await self.record()
        self.assertEqual(order["status"], "delivered")
        self.assertEqual(len(order["shipment"]["history"]), 5)
        self.assertEqual(order["shipment"]["history"][-1]["by"], "admin")
        products, orders, purchases = await server.business_snapshot()
        self.assertEqual(server.inventory_balances(products, orders, purchases)["p"]["stock"], 8)
        self.assertEqual((await self.db.products.find_one({"id": "p"}))["stock"], 10)

    async def test_access_control_on_all_endpoints(self):
        for headers, expected in [({}, 401), (self.headers("owner"), 403), (self.headers("stranger"), 403)]:
            headers = {**headers, "X-User-Role": "admin"}
            for path in ("/api/shipments", "/api/orders/sale/shipment"):
                self.assertEqual((await self.client.get(path, headers=headers)).status_code, expected)
            self.assertEqual((await self.client.put("/api/orders/sale/shipment", headers=headers, json=self.payload)).status_code, expected)
        self.assertFalse((await self.record())["shipment"])

    async def test_invalid_values_never_write(self):
        before = await self.record()
        for changes, expected in [({"planned_arrival": "2020-09-30"}, 400),
            ({"planned_departure": "2020-02-30"}, 400), ({"status": "in_transit"}, 400),
            ({"responsible_id": "missing"}, 400), ({"history": []}, 422),
            ({"reference": "bad\x00"}, 422), ({"version": True}, 422),
            ({"reference": " "}, 422), ({"mode": "unknown"}, 422)]:
            response = await self.save(**changes)
            self.assertEqual(response.status_code, expected, response.text)
            self.assertEqual(await self.record(), before)
        await self.db.users.update_one({"id": "owner"}, {"$set": {"active": False}})
        self.assertEqual((await self.save()).status_code, 400)

    async def test_old_version_and_concurrent_writes_cannot_duplicate_history(self):
        payload = copy.deepcopy(self.payload)
        first, second = await asyncio.gather(*[
            self.client.put("/api/orders/sale/shipment", headers=self.headers(), json=payload)
            for _ in range(2)])
        self.assertEqual(sorted([first.status_code, second.status_code]), [200, 409])
        self.assertEqual(len((await self.record())["shipment"]["history"]), 1)
        stale = await self.save(version=self.order["version"])
        self.assertEqual(stale.status_code, 409)

    async def test_generic_order_update_cannot_replace_history_or_skip_states(self):
        self.assertEqual((await self.save()).status_code, 200)
        current = await self.record()
        response = await self.update({**current, "shipment": {"status": "delivered", "history": []}, "notes": "Commercial note"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["shipment"], current["shipment"])
        response = await self.update({**response.json(), "status": "delivered"})
        self.assertEqual(response.status_code, 409)

    async def test_cancel_transport_preserves_sale_and_reopen_history(self):
        for state in ("planned", "cancelled", "planned"):
            response = await self.save(status=state)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()["status"], "confirmed")
            self.assertEqual(len(await server.all_finance_entries()), 1)
        self.assertEqual(len((await self.record())["shipment"]["history"]), 3)

    async def test_real_dates_and_route_are_immutable_after_departure(self):
        for state in ("planned", "booked"):
            self.assertEqual((await self.save(status=state)).status_code, 200)
        self.assertEqual((await self.save(status="in_transit", actual_departure="2020-10-02")).status_code, 200)
        before = await self.record()
        for changes in ({"origin": "Other"}, {"actual_departure": "2020-10-03"},
                        {"status": "booked"}, {"status": "arrived", "actual_arrival": "2999-01-01"},
                        {"status": "arrived", "actual_arrival": "2020-10-01"}):
            response = await self.save(**changes)
            self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual(await self.record(), before)

    async def test_listing_is_paginated_and_excludes_history_and_commercial_snapshot(self):
        self.assertEqual((await self.save()).status_code, 200)
        response = await self.client.get("/api/shipments?limit=1&status=planned", headers=self.headers())
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()), 1)
        summary = response.json()[0]
        self.assertNotIn("history", summary["shipment"])
        self.assertNotIn("source_price_snapshot", summary)
        self.assertNotIn("items", summary)
        self.assertEqual((await self.client.get("/api/shipments?skip=1", headers=self.headers())).json(), [])
        self.assertEqual((await self.client.get("/api/shipments?status=delivered", headers=self.headers())).json(), [])
        self.assertEqual((await self.client.get("/api/shipments?limit=251", headers=self.headers())).status_code, 422)

    async def test_failure_before_commit_leaves_order_and_history_unchanged(self):
        before = await self.record()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app, raise_app_exceptions=False), base_url="http://test") as client:
            with patch.object(server, "business_snapshot", AsyncMock(side_effect=RuntimeError("synthetic-private-marker"))):
                response = await client.put("/api/orders/sale/shipment", headers=self.headers(), json=self.payload)
        self.assertEqual(response.status_code, 500)
        self.assertNotIn("synthetic-private-marker", response.text)
        self.assertEqual(await self.record(), before)
        self.assertEqual((await self.save()).status_code, 200)  # lease released after failure

    async def test_byte_limit_rejects_new_event_without_dropping_old_history(self):
        self.assertEqual((await self.save()).status_code, 200)
        record = await self.record()
        record["shipment"]["history"][0]["note"] = "文" * 90000
        await self.db.orders.replace_one({"id": "sale"}, record)
        before = await self.record()
        self.assertEqual((await self.save(change_note="New event")).status_code, 413)
        self.assertEqual(await self.record(), before)

    async def test_backfill_existing_shipment_and_forged_creation_do_not_double_ledger(self):
        order = (await self.update({**self.order, "status": "shipped"})).json()
        self.payload["version"] = order["version"]
        response = await self.save(status="in_transit", actual_departure="2020-10-02")
        self.assertEqual(response.status_code, 200, response.text)
        products, orders, purchases = await server.business_snapshot()
        self.assertEqual(server.inventory_balances(products, orders, purchases)["p"]["stock"], 8)
        self.assertEqual(len(await server.all_finance_entries()), 1)
        forged = await self.create({"id": "forged", "customer": "Other", "shipment": {"status": "delivered", "history": [{"by": "forged"}]}})
        self.assertEqual(forged.status_code, 200, forged.text)
        self.assertEqual(forged.json()["shipment"], {})

    async def test_draft_legacy_and_duplicate_responsible_rejected(self):
        for changes in ({"status": "draft"}, {"workflow_enabled": False}):
            original = await self.record()
            await self.db.orders.update_one({"id": "sale"}, {"$set": changes})
            self.assertEqual((await self.save()).status_code, 400)
            await self.db.orders.replace_one({"id": "sale"}, original)
        await self.db.users.insert_one({"id": "owner", "name": "Duplicate", "role": "admin"})
        self.assertEqual((await self.save()).status_code, 400)

    async def test_archived_history_read_only_and_history_bound(self):
        self.assertEqual((await self.save()).status_code, 200)
        record = await self.record()
        history = record["shipment"]["history"]
        await self.db.orders.update_one({"id": "sale"}, {"$set": {"shipment.history": history * 100}})
        before = await self.record()
        self.assertEqual((await self.save()).status_code, 400)
        self.assertEqual(await self.record(), before)
        await self.db.orders.update_one({"id": "sale"}, {"$set": {"deleted_at": "2020-12-01"}})
        detail = await self.client.get("/api/orders/sale/shipment", headers=self.headers())
        self.assertEqual(detail.json()["allowed_statuses"], [])
        self.assertEqual((await self.save()).status_code, 409)
        self.assertEqual((await self.client.get("/api/shipments", headers=self.headers())).json(), [])
        self.assertEqual(len((await self.client.get("/api/shipments?archived=true", headers=self.headers())).json()), 1)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class RealMongoShipmentTests(ShipmentTests):
    real_mongo = True
