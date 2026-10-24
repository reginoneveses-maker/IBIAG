import os
"""Prepared commercial profile grants only the explicit commercial surface."""
import unittest
import test_integrated_workspace as native
import server
from commercial_access import PROFILE

class CommercialProfileTests(native.IntegratedWorkspaceTests):
    def headers(self,user="operator"):
        return {"Authorization":"Bearer "+server.create_token(user,user+"@example.com")}
    async def asyncSetUp(self):
        await super().asyncSetUp()
        await self.db.users.insert_one({"id":"operator","email":"operator@example.com","role":"user","commercial_profile":PROFILE})
    async def test_profile_cannot_administer_backup_delete_catalog_or_finance(self):
        denied=[("GET","/auth/users",None),("GET","/admin/backup",None),("GET","/finance",None),
          ("DELETE","/orders/missing",None),("DELETE","/products/p",None),
          ("PATCH","/auth/users/owner/commercial-profile",{"profile":PROFILE,"confirmed":True}),
          ("POST","/suppliers",{"name":"Unauthorized"})]
        for method,path,body in denied:
            r=await self.client.request(method,"/api"+path,headers=self.headers(),**({"json":body} if body else {}))
            self.assertEqual(r.status_code,403,(path,r.text))
        directory=self.ok(await self.req("GET","/operators"))
        self.assertFalse(any("email" in row or "password_hash" in row for row in directory))
    async def test_login_returns_explicit_profile_without_elevating_role(self):
        await self.db.users.update_one({"id":"operator"},{"$set":{"password_hash":server.hash_pw("synthetic-password")}})
        response=await self.client.post("/api/auth/login",json={"email":"operator@example.com","password":"synthetic-password"})
        data=self.ok(response)
        self.assertEqual(data["user"]["role"],"user")
        self.assertEqual(data["user"]["commercial_profile"],PROFILE)

    async def test_only_admin_can_assign_or_remove_profile_and_sessions_are_revoked(self):
        path="/api/auth/users/owner/commercial-profile"
        body={"profile":PROFILE,"confirmed":False}
        r=await self.client.patch(path,headers=self.headers("admin"),json=body)
        self.assertEqual(r.status_code,400)
        body["confirmed"]=True
        user=self.ok(await self.client.patch(path,headers=self.headers("admin"),json=body))
        self.assertEqual(user["role"],"user")
        self.assertEqual(user["commercial_profile"],PROFILE)
        self.assertNotIn("password_hash",user)
        self.assertEqual((await self.client.get("/api/integrated/catalog",headers=self.headers("owner"))).status_code,401)
        fresh={"Authorization":"Bearer "+server.create_token("owner","owner@example.com",session_version=user["session_version"])}
        self.assertEqual((await self.client.get("/api/integrated/catalog",headers=fresh)).status_code,200)
        self.ok(await self.client.patch(path,headers=self.headers("admin"),json={"profile":"none","confirmed":True}))
        self.assertEqual((await self.client.get("/api/integrated/catalog",headers=fresh)).status_code,401)
        latest={"Authorization":"Bearer "+server.create_token("owner","owner@example.com",session_version=user["session_version"]+1)}
        self.assertEqual((await self.client.get("/api/integrated/catalog",headers=latest)).status_code,403)

@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Requires disposable MongoDB")
class RealMongoCommercialProfileTests(CommercialProfileTests):
    real_mongo=True
