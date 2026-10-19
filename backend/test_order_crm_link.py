"""CRM-to-order relationship through HTTP, with isolated mock/real MongoDB."""
import asyncio
import os
import unittest
import uuid
from urllib.parse import urlparse
from unittest.mock import patch

import httpx
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient

with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost:27017", "DB_NAME": "order_crm_test",
                             "JWT_SECRET": "test-secret-only-32-characters-long"}):
    import server


class OrderCrmLinkTests(unittest.IsolatedAsyncioTestCase):
    real_mongo = False

    async def asyncSetUp(self):
        if self.real_mongo:
            url = os.environ["TEST_MONGO_URL"]
            if urlparse(url).hostname not in {"localhost", "127.0.0.1", "mongo"}:
                raise RuntimeError("Only disposable local MongoDB is allowed")
            self.mongo = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        else:
            self.mongo = AsyncMongoMockClient()
        self.db_name = "ibiag_test_order_link_" + uuid.uuid4().hex
        self.db = self.mongo[self.db_name]
        self.db_patch = patch.object(server, "db", self.db)
        self.db_patch.start()
        await self.db.users.insert_many([
            {"id": "admin", "email": "admin@example.com", "role": "admin"},
            {"id": "owner", "email": "owner@example.com", "role": "user"},
            {"id": "stranger", "email": "stranger@example.com", "role": "user"},
        ])
        await self.db.leads.insert_many([
            {"id": "lead1", "company": "Original Buyer", "country": "Portugal", "owner_id": "owner"},
            {"id": "lead2", "company": "Second Buyer", "country": "Germany", "owner_id": "owner"},
        ])
        await self.db.products.insert_one({"id": "p", "name": "Product", "unit": "kg", "stock": 10})
        await self.db.product_offers.insert_one({"id": "offer", "product_id": "p", "supplier_id": "s", "active": True})
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")
        self.body = {"id": "sale", "customer": "Forged name", "customer_country": "Forged country", "lead_id": "lead1"}

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db_patch.stop()
        await self.mongo.drop_database(self.db_name)
        if self.real_mongo:
            self.mongo.close()

    def headers(self, user="admin"):
        return {"Authorization": "Bearer " + server.create_token(user, user + "@example.com")}

    async def create(self, body=None, user="admin"):
        return await self.client.post("/api/orders", headers=self.headers(user), json=body or self.body)

    async def update(self, body):
        return await self.client.put("/api/orders/sale", headers=self.headers(), json=body)

    async def test_link_copies_server_identity_without_business_movements(self):
        response = await self.create()
        self.assertEqual(response.status_code, 200, response.text)
        order = response.json()
        self.assertEqual((order["lead_id"], order["customer"], order["customer_country"]),
                         ("lead1", "Original Buyer", "Portugal"))
        self.assertEqual(order["status"], "draft")
        self.assertEqual(await self.db.finance.count_documents({}), 0)
        self.assertEqual(await self.db.leads.count_documents({}), 2)
        self.assertEqual((await self.db.products.find_one({"id": "p"}))["stock"], 10)
        listed = await self.client.get("/api/orders", headers=self.headers())
        self.assertEqual(listed.json()[0]["lead_id"], "lead1")

    async def test_unknown_malformed_and_invalid_company_rejected_before_order_write(self):
        for value, expected in (("missing", 404), ({"$ne": None}, 422), ("x" * 201, 422), ("bad\x00id", 422)):
            response = await self.create({**self.body, "lead_id": value})
            self.assertEqual(response.status_code, expected, response.text)
        await self.db.leads.update_one({"id": "lead1"}, {"$set": {"company": "  "}})
        self.assertEqual((await self.create()).status_code, 400)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_legacy_duplicate_crm_ids_are_not_linked_arbitrarily(self):
        await self.db.leads.insert_one({"id": "lead1", "company": "Ambiguous Buyer", "country": "Spain"})
        response = await self.create()
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_anonymous_member_and_forged_role_cannot_create_or_list_orders(self):
        response = await self.client.post("/api/orders", json=self.body)
        self.assertEqual(response.status_code, 401)
        for user in ("owner", "stranger"):
            response = await self.client.post("/api/orders", headers={**self.headers(user), "X-User-Role": "admin"}, json=self.body)
            self.assertEqual(response.status_code, 403)
            self.assertEqual((await self.client.get("/api/orders", headers=self.headers(user))).status_code, 403)
        self.assertEqual(await self.db.orders.count_documents({}), 0)

    async def test_snapshot_survives_crm_change_and_omitted_link_from_old_client(self):
        order = (await self.create()).json()
        await self.db.leads.update_one({"id": "lead1"}, {"$set": {"company": "Renamed Buyer", "country": "Spain"}})
        old_client = {key: value for key, value in order.items() if key != "lead_id"}
        response = await self.update({**old_client, "customer": "Forged", "customer_country": "Wrong", "notes": "Updated"})
        self.assertEqual(response.status_code, 200, response.text)
        updated = response.json()
        self.assertEqual((updated["lead_id"], updated["customer"], updated["customer_country"]),
                         ("lead1", "Original Buyer", "Portugal"))
        self.assertEqual(updated["notes"], "Updated")
        self.assertEqual(updated["created_at"], order["created_at"])
        self.assertEqual((await self.update(order)).status_code, 409)

    async def test_draft_can_relink_but_confirmed_customer_cannot_be_swapped_or_cleared(self):
        order = (await self.create()).json()
        response = await self.update({**order, "lead_id": "lead2"})
        self.assertEqual(response.status_code, 200, response.text)
        order = response.json()
        self.assertEqual(order["customer"], "Second Buyer")
        response = await self.update({**order, "status": "confirmed", "order_date": "2026-10-19",
                                      "receivable_due_date": "2026-11-19",
                                      "items": [{"product_id": "p", "offer_id": "offer", "quantity": 2, "unit_price": 3}]})
        self.assertEqual(response.status_code, 200, response.text)
        order = response.json()
        for link in ("lead1", ""):
            self.assertEqual((await self.update({**order, "lead_id": link})).status_code, 409)
        response = await self.update({**order, "status": "shipped", "customer": "Injected"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["customer"], "Second Buyer")
        self.assertEqual(len(await server.all_finance_entries()), 1)

    async def test_manual_legacy_orders_work_and_draft_can_clear_relationship(self):
        manual = await self.create({"id": "manual", "customer": "Manual customer", "customer_country": "Brazil"})
        self.assertEqual(manual.status_code, 200, manual.text)
        self.assertEqual(manual.json()["lead_id"], "")
        order = (await self.create()).json()
        response = await self.update({**order, "lead_id": "", "customer": "Manual replacement", "customer_country": "Italy"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["customer"], "Manual replacement")
        self.assertEqual((await self.client.delete("/api/leads/lead1", headers=self.headers("owner"))).status_code, 200)

    async def test_linked_lead_deletion_blocked_even_when_order_archived_without_info_leak(self):
        await self.create()
        for user, expected in (("stranger", 404), ("owner", 409), ("admin", 409)):
            response = await self.client.delete("/api/leads/lead1", headers=self.headers(user))
            self.assertEqual(response.status_code, expected, response.text)
            self.assertNotIn("sale", response.text)
        self.assertEqual((await self.client.delete("/api/orders/sale", headers=self.headers())).status_code, 200)
        self.assertEqual((await self.client.delete("/api/leads/lead1", headers=self.headers())).status_code, 409)
        self.assertEqual(await self.db.leads.count_documents({"id": "lead1"}), 1)

    async def test_concurrent_order_create_and_lead_delete_never_leave_orphan(self):
        results = await asyncio.gather(self.create(), self.client.delete("/api/leads/lead1", headers=self.headers()))
        self.assertTrue(all(r.status_code in {200, 404, 409} for r in results))
        order = await self.db.orders.find_one({"id": "sale"})
        if order:
            self.assertIsNotNone(await self.db.leads.find_one({"id": order["lead_id"]}))
        self.assertEqual(await self.db.finance.count_documents({}), 0)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class RealMongoOrderCrmLinkTests(OrderCrmLinkTests):
    real_mongo = True
