"""Authentication and access checks through real HTTP routes, isolated DB."""
import os
import unittest
from unittest.mock import patch
import httpx
from mongomock_motor import AsyncMongoMockClient

with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost:27017", "DB_NAME": "auth_http_test",
                             "JWT_SECRET": "test-secret-only-32-characters-long"}):
    import server


class AuthHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient()["isolated"]
        self.db_patch = patch.object(server, "db", self.db)
        self.db_patch.start()
        await self.db.users.insert_one({"id":"u", "email":"user@example.com", "name":"User",
                                        "role":"user", "password_hash":server.hash_pw("test-password")})
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db_patch.stop()

    async def test_login_logout_and_second_session(self):
        body = {"email":"user@example.com", "password":"test-password"}
        first = await self.client.post("/api/auth/login", json=body)
        second = await self.client.post("/api/auth/login", json=body)
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        first_token = first.json()["access_token"]
        second_token = second.json()["access_token"]
        self.assertNotEqual(first_token, second_token)
        headers = {"Authorization":"Bearer " + first_token}
        self.assertEqual((await self.client.get("/api/auth/me", headers=headers)).status_code, 200)
        self.assertEqual((await self.client.post("/api/auth/logout", headers=headers)).status_code, 200)
        self.assertEqual((await self.client.get("/api/auth/me", headers=headers)).status_code, 401)
        self.assertEqual((await self.client.get("/api/auth/me", headers={"Authorization":"Bearer " + second_token})).status_code, 200)
        stored = await self.db.revoked_access_tokens.find_one({})
        self.assertNotIn(first_token, str(stored))

    async def test_anonymous_requests_and_user_cannot_admin(self):
        for path in ("/api/leads", "/api/documents", "/api/suppliers", "/api/prices", "/api/orders", "/api/auth/users"):
            self.assertEqual((await self.client.get(path)).status_code, 401, path)
        token = server.create_token("u", "user@example.com")
        headers = {"Authorization":"Bearer " + token}
        self.assertEqual((await self.client.get("/api/auth/users", headers=headers)).status_code, 403)
        denied = await self.client.post("/api/auth/users", headers=headers, json={
            "email":"attacker@example.com", "password":"test-password", "role":"admin"})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(await self.db.users.count_documents({}), 1)

    async def test_deleted_user_cannot_reuse_token(self):
        token = server.create_token("u", "user@example.com")
        await self.db.users.delete_one({"id":"u"})
        response = await self.client.get("/api/auth/me", headers={"Authorization":"Bearer " + token})
        self.assertEqual(response.status_code, 401)
