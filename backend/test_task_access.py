"""Exercise task authorization through real routes with separate identities."""
import asyncio
import os
import unittest
import uuid
from urllib.parse import urlparse
from unittest.mock import patch
import httpx
from mongomock_motor import AsyncMongoMockClient
from motor.motor_asyncio import AsyncIOMotorClient

with patch.dict(os.environ, {"MONGO_URL":"mongodb://localhost:27017", "DB_NAME":"task_access_test",
                             "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class TaskAccessTests(unittest.IsolatedAsyncioTestCase):
    def make_database(self):
        return AsyncMongoMockClient()["isolated"]

    async def asyncSetUp(self):
        self.db = self.make_database()
        self.db_patch = patch.object(server,"db",self.db)
        self.db_patch.start()
        await self.db.users.insert_many([
            {"id":"alice","email":"alice@example.com","role":"user"},
            {"id":"bob","email":"bob@example.com","role":"user"},
            {"id":"admin","email":"admin@example.com","role":"admin"}])
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        self.db_patch.stop()

    def headers(self, user):
        return {"Authorization":"Bearer "+server.create_token(user,user+"@example.com")}

    async def create(self, user, **extra):
        response=await self.client.post("/api/tasks",headers=self.headers(user),json={"title":"Task "+user,**extra})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def test_list_isolates_users_and_admin_can_review(self):
        alice=await self.create("alice")
        bob=await self.create("bob")
        for user, expected in (("alice",{alice["id"]}),("bob",{bob["id"]}),("admin",{alice["id"],bob["id"]})):
            response=await self.client.get("/api/tasks",headers=self.headers(user))
            self.assertEqual({item["id"] for item in response.json()},expected)

    async def test_foreign_and_missing_ids_have_same_denial_without_writes(self):
        alice=await self.create("alice")
        for tid in (alice["id"],"missing"):
            for method,suffix in (("PATCH","/toggle"),("DELETE","")):
                response=await self.client.request(method,"/api/tasks/"+tid+suffix,headers=self.headers("bob"))
                self.assertEqual(response.status_code,404,response.text)
                self.assertEqual(response.json(),{"detail":"Not found"})
        stored=await self.db.tasks.find_one({"id":alice["id"]})
        self.assertFalse(stored["completed"])

    async def test_server_ignores_forged_owner_id_id_and_timestamp(self):
        original=await self.create("bob")
        forged=await self.create("alice",owner_id="bob",id=original["id"],created_at="forged")
        self.assertEqual(forged["owner_id"],"alice")
        self.assertNotEqual(forged["id"],original["id"])
        self.assertNotEqual(forged["created_at"],"forged")
        self.assertEqual(await self.db.tasks.count_documents({}),2)

    async def test_owner_toggle_and_delete_and_admin_override(self):
        task=await self.create("alice")
        for user,expected in (("alice",True),("admin",False)):
            response=await self.client.patch("/api/tasks/"+task["id"]+"/toggle",headers=self.headers(user))
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["completed"],expected)
        response=await self.client.delete("/api/tasks/"+task["id"],headers=self.headers("alice"))
        self.assertEqual(response.json(),{"deleted":1})
        self.assertEqual(await self.db.tasks.count_documents({}),0)

    async def test_legacy_tasks_are_preserved_for_administrator(self):
        await self.db.tasks.insert_one({"id":"legacy","title":"Existing task","completed":False})
        self.assertEqual((await self.client.get("/api/tasks",headers=self.headers("alice"))).json(),[])
        self.assertEqual((await self.client.patch("/api/tasks/legacy/toggle",headers=self.headers("alice"))).status_code,404)
        response=await self.client.get("/api/tasks",headers=self.headers("admin"))
        self.assertEqual([task["id"] for task in response.json()],["legacy"])
        self.assertEqual(await self.db.tasks.count_documents({}),1)

    async def test_concurrent_toggle_does_not_lose_state_changes(self):
        task=await self.create("alice")
        results=await asyncio.gather(*(self.client.patch("/api/tasks/"+task["id"]+"/toggle",headers=self.headers("alice")) for _ in range(10)))
        self.assertTrue(all(response.status_code==200 for response in results))
        self.assertFalse((await self.db.tasks.find_one({"id":task["id"]}))["completed"])

    async def test_anonymous_cannot_list_create_or_mutate(self):
        for method,path,kwargs in (("GET","/api/tasks",{}),("POST","/api/tasks",{"json":{"title":"Task"}}),
                                   ("PATCH","/api/tasks/any/toggle",{}),("DELETE","/api/tasks/any",{})):
            self.assertEqual((await self.client.request(method,path,**kwargs)).status_code,401)

    async def test_only_admin_can_assign_legacy_tasks_and_transfer_ownership(self):
        await self.db.tasks.insert_one({"id":"legacy","title":"Existing task","completed":False})
        path="/api/tasks/legacy/owner"
        self.assertEqual((await self.client.patch(path,headers=self.headers("alice"),json={"owner_id":"alice"})).status_code,403)
        self.assertEqual((await self.client.patch(path,headers=self.headers("admin"),json={"owner_id":"missing"})).status_code,400)
        response=await self.client.patch(path,headers=self.headers("admin"),json={"owner_id":"alice"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual([task["id"] for task in (await self.client.get("/api/tasks",headers=self.headers("alice"))).json()],["legacy"])
        await self.client.patch(path,headers=self.headers("admin"),json={"owner_id":"bob"})
        self.assertEqual((await self.client.patch("/api/tasks/legacy/toggle",headers=self.headers("alice"))).status_code,404)
        self.assertEqual((await self.client.patch("/api/tasks/legacy/toggle",headers=self.headers("bob"))).status_code,200)
        stored=await self.db.tasks.find_one({"id":"legacy"})
        self.assertEqual(stored["owner_updated_by"],"admin")


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class TaskAccessMongoTests(TaskAccessTests):
    def make_database(self):
        url=os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost","127.0.0.1","mongo"}:
            raise RuntimeError("Only disposable local MongoDB is allowed")
        self.mongo=AsyncIOMotorClient(url,serverSelectionTimeoutMS=5000)
        self.database_name="ibiag_test_tasks_"+uuid.uuid4().hex
        return self.mongo[self.database_name]

    async def asyncTearDown(self):
        try:
            await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
