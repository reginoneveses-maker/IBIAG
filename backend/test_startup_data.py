"""Real startup preserves business data, independent of legacy migration markers."""
import os
import unittest
import uuid
from unittest.mock import patch
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from mongomock_motor import AsyncMongoMockClient
import test_account_suspension as fixtures

server = fixtures.server
COLLECTIONS = ("products", "product_offers", "suppliers", "orders", "purchases", "finance",
               "trade_data", "leads", "interactions", "tasks", "documents", "templates", "settings")


class StartupDataTests(unittest.IsolatedAsyncioTestCase):
    def make_database(self): return AsyncMongoMockClient()["startup_data"]

    async def asyncSetUp(self):
        self.db = self.make_database()
        self.db_patch = patch.object(server, "db", self.db)
        self.db_patch.start()
        self.environment = patch.dict(os.environ, {"ADMIN_EMAIL":"", "ADMIN_PASSWORD":""})
        self.environment.start()

    async def asyncTearDown(self):
        self.environment.stop()
        self.db_patch.stop()

    async def snapshot(self):
        return {name: await self.db[name].find({}, {"_id":0}).sort("id", 1).to_list(None) for name in COLLECTIONS}

    async def existing_records(self):
        for name in COLLECTIONS:
            if name != "settings":
                await self.db[name].insert_one({"id":"keep-"+name,"label":"existing commercial data"})
        await self.db.product_offers.update_one({"id":"keep-product_offers"}, {"$set":{"product_id":"keep-products"}})
        await self.db.orders.update_one({"id":"keep-orders"}, {"$set":{"items":[{"product_id":"keep-products"}]}})
        # Neither old cleanup heuristics nor missing migration markers authorize deletion.
        await self.db.leads.insert_many([
            {"id":"example-domain", "email":"person@company.example", "owner_id":"member"},
            {"id":"matching-company", "source":"trade_data", "company":"Green Nordic Beverages AB", "owner_id":"member"},
        ])
        await self.db.documents.update_one({"id":"keep-documents"}, {"$set":{"lead_id":"matching-company"}})

    async def test_restart_without_migration_markers_preserves_catalog_crm_and_links(self):
        await self.existing_records()
        before = await self.snapshot()
        await server.startup()
        await server.startup()
        self.assertEqual(await self.snapshot(), before)
        self.assertEqual(await self.db.users.count_documents({}), 0)

    async def test_restart_with_existing_markers_preserves_records_and_marker_values(self):
        await self.existing_records()
        await self.db.settings.insert_many([
            {"key":"portfolio_version", "value":"operator-owned"},
            {"key":"prospecting-demo-cleanup-v1", "value":"do-not-rewrite"},
        ])
        before = await self.snapshot()
        await server.startup()
        self.assertEqual(await self.snapshot(), before)

    async def test_empty_installation_creates_only_configured_admin_not_business_data(self):
        before = await self.snapshot()
        with patch.dict(os.environ, {"ADMIN_EMAIL":"bootstrap@example.com", "ADMIN_PASSWORD":"synthetic-startup-password"}):
            await server.startup()
            admin = await self.db.users.find_one({"email":"bootstrap@example.com"})
            self.assertEqual(admin["role"], "admin")
            self.assertTrue(server.verify_pw("synthetic-startup-password", admin["password_hash"]))
            await server.startup()
            self.assertEqual(await self.db.users.count_documents({}), 1)
            self.assertEqual(await self.db.users.find_one({"id":admin["id"]}), admin)
        self.assertEqual(await self.snapshot(), before)
        for name in ("login_attempts", "revoked_access_tokens"):
            indexes = await self.db[name].index_information()
            self.assertTrue(any(index.get("expireAfterSeconds")==0 for index in indexes.values()))

    async def test_failed_unique_index_does_not_purge_business_records(self):
        await self.existing_records()
        await self.db.users.insert_many([{"email":"duplicate@example.com","role":"user"},
                                         {"email":"duplicate@example.com","role":"user"}])
        before = await self.snapshot()
        with self.assertRaises(DuplicateKeyError):
            await server.startup()
        self.assertEqual(await self.snapshot(), before)
        self.assertEqual(await self.db.users.count_documents({}), 2)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "MongoDB de testes não configurado")
class MongoStartupDataTests(StartupDataTests):
    def make_database(self):
        url = os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost", "127.0.0.1", "mongo"}:
            raise RuntimeError("Testes permitidos apenas no MongoDB local descartável")
        self.mongo_client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        self.database_name = "ibiag_startup_test_" + uuid.uuid4().hex
        return self.mongo_client[self.database_name]

    async def asyncTearDown(self):
        await super().asyncTearDown()
        await self.mongo_client.drop_database(self.database_name)
        self.mongo_client.close()
