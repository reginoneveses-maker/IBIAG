"""Exercise literal trade search through HTTP and disposable MongoDB in CI."""
import os
import unittest
import uuid
from urllib.parse import urlparse
from unittest.mock import patch

import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from mongomock_motor import AsyncMongoMockClient

with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost:27017", "DB_NAME": "trade_search_test",
                             "JWT_SECRET": "test-secret-only-32-characters-long"}):
    import server


class TradeSearchSecurityTests(unittest.IsolatedAsyncioTestCase):
    def make_database(self):
        return AsyncMongoMockClient()["isolated"]

    async def asyncSetUp(self):
        self.db = self.make_database()
        self.db_patch = patch.object(server, "db", self.db)
        self.db_patch.start()
        await self.db.users.insert_one({"id": "member", "email": "member@example.com", "role": "user"})
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")
        self.headers = {"Authorization": "Bearer " + server.create_token("member", "member@example.com")}
        self.records = []
        for index, name in enumerate(("Acme [Ingredients]", "Ordinary company", "Literal (a+)+$", "Dotted .* supplier")):
            self.records.append({"id": str(index), "importer_company": name, "importer_country": "Germany",
                                 "country_code": "DE", "hs_code": "1234", "product_description": "Açaí Powder",
                                 "volume_kg": 1, "value_usd": 1, "last_shipment_date": "2026-01-01",
                                 "industry_segment": "food_service"})
        await self.db.trade_data.insert_many(self.records)

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db_patch.stop()

    async def test_regex_operators_are_literal_and_malformed_patterns_do_not_fail(self):
        for search, expected in (("[", ["0"]), ("(a+)+$", ["2"]), (".*", ["3"]), ("^", [])):
            response = await self.client.get("/api/trade-data", params={"search": search}, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([row["id"] for row in response.json()], expected)

    async def test_company_and_product_substrings_and_exact_filters_remain_available(self):
        for params, expected in (({"search": "acme"}, ["0"]), ({"search": "powder", "country": "DE"}, ["0", "1", "2", "3"]),
                                 ({"search": "powder", "industry": "other"}, []), ({"country": "DE.*"}, [])):
            response = await self.client.get("/api/trade-data", params=params, headers=self.headers)
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([row["id"] for row in response.json()], expected)

    async def test_oversized_filters_are_rejected_before_query_and_authentication_is_required(self):
        with patch.object(self.db.trade_data, "find", side_effect=AssertionError("must not query")):
            for key, maximum in (("search", 128), ("country", 8), ("industry", 64)):
                response = await self.client.get("/api/trade-data", params={key: "x" * (maximum + 1)}, headers=self.headers)
                self.assertEqual(response.status_code, 422, response.text)
        response = await self.client.get("/api/trade-data", params={"search": "acme"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(await self.db.trade_data.count_documents({}), 4)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class TradeSearchMongoTests(TradeSearchSecurityTests):
    def make_database(self):
        url = os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost", "127.0.0.1", "mongo"}:
            raise RuntimeError("Only disposable local MongoDB is allowed")
        self.mongo = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        self.database_name = "ibiag_test_trade_search_" + uuid.uuid4().hex
        return self.mongo[self.database_name]

    async def asyncTearDown(self):
        try:
            await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
