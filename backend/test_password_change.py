"""Password rotation, bounded reauthentication and create-only bootstrap."""
import asyncio
import os
import unittest
from unittest.mock import patch
import test_account_suspension as fixtures


class PasswordChangeTests(unittest.IsolatedAsyncioTestCase):
    make_database = fixtures.AccountSuspensionTests.make_database
    asyncSetUp = fixtures.AccountSuspensionTests.asyncSetUp
    asyncTearDown = fixtures.AccountSuspensionTests.asyncTearDown
    headers = fixtures.AccountSuspensionTests.headers

    async def change(self, **overrides):
        return await self.client.post("/api/auth/password", headers=self.member,
            json={"current_password":"valid-test-password", "new_password":"updated-test-password", **overrides})

    async def test_rotation_revokes_all_sessions_and_requires_new_password(self):
        other = self.headers("member")
        response = await self.change()
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json(),{"ok":True})
        for headers in (self.member,other):
            self.assertEqual((await self.client.get("/api/auth/me",headers=headers)).status_code,401)
        for password, code in (("valid-test-password",401),("updated-test-password",200)):
            login = await self.client.post("/api/auth/login",json={"email":"member@example.com","password":password})
            self.assertEqual(login.status_code,code,login.text)
            if code == 200:
                self.assertEqual((await self.client.get("/api/auth/me",headers={"Authorization":"Bearer "+login.json()["access_token"]})).status_code,200)
        record = await self.db.users.find_one({"id":"member"})
        self.assertEqual(record["session_version"],1)
        self.assertIn("password_changed_at",record)
        self.assertEqual(record["role"],"user")

    async def test_wrong_password_is_bounded_across_sessions_without_changing_credentials(self):
        initial = await self.db.users.find_one({"id":"member"})
        for i in range(6):
            response = await self.client.post("/api/auth/password",headers=self.headers("member"),
                json={"current_password":"wrong-test-password","new_password":"updated-test-password"})
            self.assertEqual(response.status_code,400 if i<5 else 429,response.text)
        self.assertEqual(response.headers["retry-after"],"900")
        after = await self.db.users.find_one({"id":"member"})
        self.assertEqual(initial,after)
        counters = await self.db.login_attempts.find({}).to_list(20)
        self.assertEqual(len(counters),1)
        self.assertNotIn("member",counters[0]["_id"])

    async def test_invalid_passwords_and_extra_fields_are_redacted_before_update(self):
        for body in ({"new_password":"short"},{"new_password":"á"*37},{"new_password":"canary\x00password"},
                     {"new_password":9},{"current_password":"x"*73},{"role":"admin"}):
            response = await self.change(**body)
            self.assertEqual(response.status_code,422,response.text)
            self.assertEqual(response.json(),{"detail":"Dados de autenticação inválidos."})
        self.assertNotIn("session_version", await self.db.users.find_one({"id":"member"}))

    async def test_same_password_is_refused(self):
        response = await self.change(new_password="valid-test-password")
        self.assertEqual(response.status_code,400)
        self.assertNotIn("session_version",await self.db.users.find_one({"id":"member"}))

    async def test_missing_and_suspended_sessions_cannot_change_password(self):
        response = await self.client.post("/api/auth/password",json={"current_password":"valid-test-password","new_password":"updated-test-password"})
        self.assertEqual(response.status_code,401)
        await self.client.patch("/api/auth/users/member/active",json={"active":False},headers=self.admin)
        self.assertEqual((await self.change()).status_code,401)
        record = await self.db.users.find_one({"id":"member"})
        self.assertTrue(fixtures.server.verify_pw("valid-test-password",record["password_hash"]))

    async def test_concurrent_rotations_cannot_overwrite_newer_credentials(self):
        responses = await asyncio.gather(self.change(new_password="updated-password-one"),self.change(new_password="updated-password-two"))
        self.assertEqual(sum(r.status_code==200 for r in responses),1,[r.text for r in responses])
        self.assertTrue(all(r.status_code in {200,400,401,409} for r in responses))
        self.assertEqual((await self.db.users.find_one({"id":"member"}))["session_version"],1)

    async def test_bootstrap_never_restores_environment_password_or_promotes_existing_account(self):
        for uid,email in (("member","member@example.com"),("admin","admin@example.com")):
            await self.db.users.update_one({"id":uid},{"$set":{"password_hash":fixtures.server.hash_pw("changed-by-user"),"session_version":3}})
            before = await self.db.users.find_one({"id":uid})
            with patch.dict(os.environ,{"ADMIN_EMAIL":email,"ADMIN_PASSWORD":"stale-environment-password"}):
                await fixtures.server.seed_admin()
            self.assertEqual(await self.db.users.find_one({"id":uid}),before)

    async def test_bootstrap_creates_once_under_concurrency(self):
        with patch.dict(os.environ,{"ADMIN_EMAIL":"new-admin@example.com","ADMIN_PASSWORD":"initial-test-password"}):
            await asyncio.gather(fixtures.server.seed_admin(),fixtures.server.seed_admin())
        records = await self.db.users.find({"email":"new-admin@example.com"}).to_list(10)
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["role"],"admin")
        self.assertTrue(fixtures.server.verify_pw("initial-test-password",records[0]["password_hash"]))


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class PasswordChangeMongoTests(PasswordChangeTests):
    make_database = fixtures.AccountSuspensionMongoTests.make_database
    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
