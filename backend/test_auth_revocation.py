"""Regression tests for server-side bearer-token revocation (no production DB)."""
import ast
import asyncio
import hashlib
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import jwt
from fastapi import HTTPException, Request, Depends

SECRET = "isolated-test-secret-never-used-in-production"


def load_auth(db):
    tree = ast.parse(Path(__file__).with_name("server.py").read_text())
    selected = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and n.name in {"get_current_user", "logout"}]
    ns = {"jwt": jwt, "JWT_SECRET": SECRET, "JWT_ALG": "HS256",
          "db": db, "hashlib": hashlib, "HTTPException": HTTPException,
          "Request": Request, "Depends": Depends, "datetime": datetime,
          "timezone": timezone, "api": SimpleNamespace(post=lambda _: lambda fn: fn)}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "auth_under_test", "exec"), ns)
    return ns


class RevokedCollection:
    def __init__(self):
        self.items = {}
    async def find_one(self, query):
        return self.items.get(query["_id"])
    async def update_one(self, query, update, upsert=False):
        self.items.setdefault(query["_id"], {"_id": query["_id"], **update["$setOnInsert"]})


class SessionRevocationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = SimpleNamespace(
            users=SimpleNamespace(find_one=AsyncMock(return_value={"id": "user-1", "role": "user"})),
            revoked_access_tokens=RevokedCollection(),
        )
        self.auth = load_auth(self.db)
        self.token = jwt.encode({"sub": "user-1", "exp": int(datetime.now(timezone.utc).timestamp()) + 3600}, SECRET, algorithm="HS256")
        self.request = SimpleNamespace(headers={"Authorization": "Bearer " + self.token})

    async def test_logout_invalidates_token_and_is_idempotent(self):
        user = await self.auth["get_current_user"](self.request)
        self.assertEqual(user["id"], "user-1")
        self.assertEqual(await self.auth["logout"](self.request, user), {"ok": True})
        digest = hashlib.sha256(self.token.encode()).hexdigest()
        self.assertIn(digest, self.db.revoked_access_tokens.items)
        self.assertNotIn(self.token, str(self.db.revoked_access_tokens.items))
        with self.assertRaises(HTTPException) as error:
            await self.auth["get_current_user"](self.request)
        self.assertEqual(error.exception.status_code, 401)

    async def test_invalid_and_missing_tokens_are_rejected(self):
        for auth in ("", "Bearer invalid-token"):
            with self.assertRaises(HTTPException) as error:
                await self.auth["get_current_user"](SimpleNamespace(headers={"Authorization": auth}))
            self.assertEqual(error.exception.status_code, 401)

    async def test_logout_requires_authentication_dependency(self):
        with self.assertRaises(HTTPException):
            await self.auth["get_current_user"](SimpleNamespace(headers={}))
