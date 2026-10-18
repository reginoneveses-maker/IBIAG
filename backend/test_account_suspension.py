"""Account suspension and session generations through HTTP and real CI MongoDB."""
import asyncio
import os
import unittest
import uuid
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from unittest.mock import patch

import httpx
import jwt
from motor.motor_asyncio import AsyncIOMotorClient
from mongomock_motor import AsyncMongoMockClient

with patch.dict(os.environ, {"MONGO_URL":"mongodb://localhost:27017", "DB_NAME":"account_suspend_test",
                             "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class AccountSuspensionTests(unittest.IsolatedAsyncioTestCase):
    def make_database(self): return AsyncMongoMockClient()["isolated"]

    async def asyncSetUp(self):
        self.db = self.make_database()
        self.db_patch = patch.object(server, "db", self.db)
        self.db_patch.start()
        await self.db.users.insert_many([
            {"id":"admin", "email":"admin@example.com", "role":"admin"},
            {"id":"other-admin", "email":"other@example.com", "role":"admin"},
            {"id":"member", "email":"member@example.com", "role":"user", "password_hash":server.hash_pw("valid-test-password")},
        ])
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test")
        self.admin = self.headers("admin")
        self.member = self.headers("member")

    def headers(self, uid): return {"Authorization":"Bearer " + server.create_token(uid, uid+"@example.com")}

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db_patch.stop()

    async def change(self, active):
        return await self.client.patch("/api/auth/users/member/active", json={"active":active}, headers=self.admin)

    async def test_suspend_and_reactivate_revoke_all_old_sessions_without_removing_data(self):
        legacy = jwt.encode({"sub":"member", "exp":datetime.now(timezone.utc)+timedelta(hours=1)}, server.JWT_SECRET, algorithm=server.JWT_ALG)
        sessions = [self.member, self.headers("member"), {"Authorization":"Bearer "+legacy}]
        await self.db.leads.insert_one({"id":"keep", "company":"Private", "owner_id":"member"})
        for headers in sessions:
            self.assertEqual((await self.client.get("/api/auth/me", headers=headers)).status_code, 200)
        response = await self.change(False)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("password_hash", response.text)
        self.assertNotIn("_id", response.json())
        self.assertEqual(response.json()["access_changed_by"], "admin")
        self.assertEqual(response.json()["session_version"], 1)
        for headers in sessions:
            self.assertEqual((await self.client.get("/api/leads", headers=headers)).status_code, 401)
        self.assertEqual((await self.change(True)).status_code, 200)
        for headers in sessions:
            self.assertEqual((await self.client.get("/api/auth/me", headers=headers)).status_code, 401)
        login = await self.client.post("/api/auth/login", json={"email":"member@example.com", "password":"valid-test-password"})
        self.assertEqual(login.status_code, 200, login.text)
        new_headers = {"Authorization":"Bearer "+login.json()["access_token"]}
        self.assertEqual((await self.client.get("/api/auth/me", headers=new_headers)).status_code, 200)
        self.assertEqual((await self.db.leads.find_one({"id":"keep"}))["owner_id"], "member")

    async def test_only_admin_can_change_common_accounts_and_admins_are_protected(self):
        path = "/api/auth/users/member/active"
        for headers, code in (({}, 401), (self.member, 403)):
            self.assertEqual((await self.client.patch(path, json={"active":False}, headers=headers)).status_code, code)
        for target, code in (("admin",403), ("other-admin",403), ("missing",404)):
            response = await self.client.patch(f"/api/auth/users/{target}/active", json={"active":False}, headers=self.admin)
            self.assertEqual(response.status_code, code)
        self.assertNotIn("active", await self.db.users.find_one({"id":"member"}))

    async def test_strict_body_cannot_change_role_or_supply_session_version(self):
        for body in ({"active":"false"}, {"active":0}, {"active":None}, {"active":False,"role":"admin"}, {"active":True,"session_version":0}):
            response = await self.client.patch("/api/auth/users/member/active", json=body, headers=self.admin)
            self.assertEqual(response.status_code,422,response.text)
        self.assertNotIn("session_version", await self.db.users.find_one({"id":"member"}))

    async def test_suspended_login_does_not_disclose_account_state(self):
        await self.change(False)
        for email, password in (("member@example.com","valid-test-password"), ("member@example.com","wrong-password"), ("missing@example.com","valid-test-password")):
            response = await self.client.post("/api/auth/login", json={"email":email,"password":password})
            self.assertEqual(response.status_code,401,response.text)
            self.assertEqual(response.json(), {"detail":"Invalid credentials"})

    async def test_cannot_assign_new_work_to_suspended_owner(self):
        lead = await self.client.post("/api/leads", json={"company":"Keep"}, headers=self.admin)
        task = await self.client.post("/api/tasks", json={"title":"Keep"}, headers=self.admin)
        await self.change(False)
        for prefix, item in (("leads",lead), ("tasks",task)):
            response = await self.client.patch(f"/api/{prefix}/{item.json()['id']}/owner", json={"owner_id":"member"}, headers=self.admin)
            self.assertEqual(response.status_code,400,response.text)
            self.assertEqual((await self.db[prefix].find_one({"id":item.json()["id"]}))["owner_id"],"admin")

    async def test_concurrent_changes_increment_generation_atomically(self):
        responses = await asyncio.gather(self.change(False), self.change(False))
        self.assertEqual([r.status_code for r in responses], [200,200])
        record = await self.db.users.find_one({"id":"member"})
        self.assertEqual(record["session_version"],2)
        self.assertFalse(record["active"])

    async def test_invalid_signed_subject_and_generation_are_rejected(self):
        for claims in ({}, {"sub":42}, {"sub":"member","sv":"0"}, {"sub":"member","sv":True}, {"sub":"member","sv":99}):
            token = jwt.encode({**claims, "exp":datetime.now(timezone.utc)+timedelta(hours=1)},server.JWT_SECRET,algorithm=server.JWT_ALG)
            response = await self.client.get("/api/auth/me", headers={"Authorization":"Bearer "+token})
            self.assertEqual(response.status_code,401,response.text)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class AccountSuspensionMongoTests(AccountSuspensionTests):
    def make_database(self):
        url = os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost","127.0.0.1","mongo"}:
            raise RuntimeError("Only disposable local MongoDB is allowed")
        self.mongo = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        self.database_name = "ibiag_test_accounts_"+uuid.uuid4().hex
        return self.mongo[self.database_name]

    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
