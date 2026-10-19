"""Atomic login counters against CI's disposable MongoDB, never production."""
import asyncio
import os
import unittest
import uuid
from types import SimpleNamespace
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException
from test_login_rate_limit import load_login


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class LoginMongoTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        url = os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost", "127.0.0.1", "mongo"}:
            raise RuntimeError("Only local disposable MongoDB is allowed")
        self.client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        self.name = "ibiag_test_login_" + uuid.uuid4().hex
        self.db = self.client[self.name]
        self.login = load_login(self.db)
        # A test run crossing a fixed-window boundary must remain deterministic.
        real_datetime = self.login.__globals__["datetime"]
        fixed = real_datetime.fromtimestamp(1800000000, tz=self.login.__globals__["timezone"].utc)
        class Clock:
            @staticmethod
            def now(tz=None): return fixed
            fromtimestamp = staticmethod(real_datetime.fromtimestamp)
        self.login.__globals__["datetime"] = Clock

    async def asyncTearDown(self):
        await self.client.drop_database(self.name)
        self.client.close()

    async def attempt(self, email, peer):
        try:
            await self.login(SimpleNamespace(email=email, password="wrong"),
                             SimpleNamespace(client=SimpleNamespace(host=peer)))
        except HTTPException as exc:
            return exc.status_code

    async def test_parallel_accounts_cannot_bypass_shared_peer_counter(self):
        results = await asyncio.gather(*(self.attempt(f"u{i}@example.com", "192.0.2.1") for i in range(31)))
        self.assertEqual(results.count(401), 30)
        self.assertEqual(results.count(429), 1)
        stored = await self.db.login_attempts.find({}).to_list(None)
        self.assertNotIn("192.0.2.1", str(stored))
        self.assertNotIn("@example.com", str(stored))

    async def test_parallel_peers_cannot_bypass_account_counter(self):
        results = await asyncio.gather(*(self.attempt("user@example.com", f"192.0.2.{i+1}") for i in range(10)))
        self.assertEqual(results.count(401), 5)
        self.assertEqual(results.count(429), 5)

    async def test_separate_peers_remain_independent(self):
        for index in range(30):
            self.assertEqual(await self.attempt(f"u{index}@example.com", "192.0.2.1"), 401)
        self.assertEqual(await self.attempt("next@example.com", "192.0.2.1"), 429)
        self.assertEqual(await self.attempt("other@example.com", "192.0.2.2"), 401)
