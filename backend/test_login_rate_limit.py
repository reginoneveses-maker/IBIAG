"""Test the real login function with an atomic Mongo-like counter."""
import ast
import asyncio
import hashlib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi import HTTPException
from pymongo import ReturnDocument


class Counter:
    def __init__(self):
        self.data = {}
        self.lock = asyncio.Lock()

    async def find_one_and_update(self, query, update, upsert=False, return_document=None):
        async with self.lock:
            key = query["_id"]
            record = self.data.setdefault(key, {"_id": key, **update["$setOnInsert"], "count": 0})
            record["count"] += update["$inc"]["count"]
            return dict(record)


def load_login(db):
    tree = ast.parse(Path(__file__).with_name("server.py").read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "login")
    ns = {"api": SimpleNamespace(post=lambda _: lambda fn: fn),
          "db": db, "datetime": datetime, "timezone": timezone, "LoginBody": SimpleNamespace,
          "hashlib": hashlib, "HTTPException": HTTPException,
          "ReturnDocument": ReturnDocument, "LOGIN_WINDOW_SECONDS": 900,
          "LOGIN_MAX_ATTEMPTS": 5, "LOGIN_IP_MAX_ATTEMPTS": 30, "Request": SimpleNamespace,
          "verify_pw": lambda supplied, stored: supplied == stored,
          "create_token": lambda uid, email: "test-token"}
    exec(compile(ast.Module(body=[fn], type_ignores=[]), "login_under_test", "exec"), ns)
    return ns["login"]


class LoginLimiterTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.counter = Counter()
        self.db = SimpleNamespace(
            login_attempts=self.counter,
            users=SimpleNamespace(find_one=AsyncMock(return_value={
                "id": "u1", "password_hash": "correct", "name": "User", "role": "user"
            })),
        )
        self.raw_login = load_login(self.db)
        self.login = lambda body: self.raw_login(body, SimpleNamespace(client=SimpleNamespace(host="192.0.2.1")))
        self.body = SimpleNamespace(email="USER@example.com", password="wrong")

    async def test_five_failures_then_429(self):
        for _ in range(5):
            with self.assertRaises(HTTPException) as result:
                await self.login(self.body)
            self.assertEqual(result.exception.status_code, 401)
        with self.assertRaises(HTTPException) as result:
            await self.login(SimpleNamespace(email="user@example.com", password="correct"))
        self.assertEqual(result.exception.status_code, 429)
        self.assertEqual(result.exception.headers["Retry-After"], "900")
        self.assertNotIn("user@example.com", str(self.counter.data))

    async def test_parallel_requests_cannot_bypass_limit(self):
        outcomes = await asyncio.gather(*(self.login(self.body) for _ in range(10)), return_exceptions=True)
        self.assertEqual(sum(isinstance(e, HTTPException) and e.status_code == 401 for e in outcomes), 5)
        self.assertEqual(sum(isinstance(e, HTTPException) and e.status_code == 429 for e in outcomes), 5)

    async def test_peer_limit_across_different_accounts(self):
        outcomes = []
        for index in range(31):
            body = SimpleNamespace(email=f"account{index}@example.com", password="wrong")
            try:
                await self.login(body)
            except HTTPException as exc:
                outcomes.append(exc.status_code)
        self.assertEqual(outcomes.count(401), 30)
        self.assertEqual(outcomes.count(429), 1)

    async def test_different_peers_have_independent_limits(self):
        for index in range(30):
            body = SimpleNamespace(email=f"account{index}@example.com", password="wrong")
            with self.assertRaises(HTTPException) as result:
                await self.raw_login(body, SimpleNamespace(client=SimpleNamespace(host="192.0.2.1")))
            self.assertEqual(result.exception.status_code, 401)
        with self.assertRaises(HTTPException) as result:
            await self.raw_login(SimpleNamespace(email="other@example.com", password="wrong"),
                                 SimpleNamespace(client=SimpleNamespace(host="198.51.100.2")))
        self.assertEqual(result.exception.status_code, 401)
        self.assertNotIn("192.0.2.1", str(self.counter.data))
        self.assertNotIn("198.51.100.2", str(self.counter.data))

    async def test_forwarded_headers_cannot_bypass_peer_limit(self):
        # The login handler reads only request.client.host, never headers.
        source = Path(__file__).with_name("server.py").read_text()
        tree = ast.parse(source)
        fn = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "login")
        self.assertNotIn("X-Forwarded-For", ast.unparse(fn))

    async def test_successful_login_before_threshold(self):
        response = await self.login(SimpleNamespace(email="user@example.com", password="correct"))
        self.assertEqual(response["access_token"], "test-token")
