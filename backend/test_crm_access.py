"""HTTP authorization regressions, repeated against disposable MongoDB in CI."""
import asyncio
import json
import os
import unittest
import uuid
from urllib.parse import urlparse
from unittest.mock import patch
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from mongomock_motor import AsyncMongoMockClient

with patch.dict(os.environ, {"MONGO_URL":"mongodb://localhost:27017", "DB_NAME":"crm_access_test",
                             "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class CrmAccessTests(unittest.IsolatedAsyncioTestCase):
    def make_database(self): return AsyncMongoMockClient()["isolated"]

    async def asyncSetUp(self):
        self.db=self.make_database()
        self.objects={}
        async def get(path):
            if path not in self.objects: raise server.HTTPException(404,"Arquivo não encontrado")
            return self.objects[path]
        async def put(path,data,ct):
            self.objects[path]=(data,ct)
            return {"path":path,"size":len(data),"content_type":ct}
        self.patches=[patch.object(server,"db",self.db),patch.object(server,"get_object",get),
                      patch.object(server,"put_object",put),patch.object(server,"enrich_company",return_value={})]
        for item in self.patches: item.start()
        await self.db.users.insert_many([{"id":user,"email":user+"@example.com","role":"admin" if user=="admin" else "user"} for user in ("alice","bob","admin")])
        await self.db.leads.create_index("discovery_key",unique=True,sparse=True)
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches): item.stop()

    def headers(self,user): return {"Authorization":"Bearer "+server.create_token(user,user+"@example.com")}

    async def request(self,user,method,path,**kwargs):
        return await self.client.request(method,"/api"+path,headers=self.headers(user),**kwargs)

    async def create(self,user,**extra):
        response=await self.request(user,"POST","/leads",json={"company":"Company "+user,**extra})
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    async def attach(self,lead,user="alice"):
        path=f"{server.APP_NAME}/uploads/{user}/private.pdf"
        self.objects[path]=(b"%PDF-private","application/pdf")
        await self.db.documents.insert_one({"id":"private-doc","title":"PRIVATE CRM SPEC", "file_name":"private.pdf",
            "file_path":path,"lead_id":lead["id"],"lead_name":lead["company"],"owner_id":user,
            "category":"Clientes & Comercial","document_type":"Ficha Técnica","folder_path":"PRIVATE-CRM"})
        return path

    async def test_list_count_dashboard_and_history_are_scoped(self):
        alice=await self.create("alice",deal_value=10,industry="beverage")
        bob=await self.create("bob",deal_value=9000,industry="hidden-industry")
        for user,lead in (("alice",alice),("bob",bob)):
            await self.request(user,"POST","/interactions",json={"lead_id":lead["id"],"subject":user})
        rows=(await self.request("alice","GET","/leads")).json()
        self.assertEqual([lead["id"] for lead in rows],[alice["id"]])
        self.assertEqual((await self.request("alice","GET","/leads/count")).json(),{"total":1})
        stats=(await self.request("alice","GET","/dashboard/stats")).json()
        self.assertEqual(stats["pipeline_value"],10)
        self.assertNotIn("hidden-industry",stats["by_industry"])
        self.assertEqual([row["subject"] for row in (await self.request("alice","GET","/interactions")).json()],["alice"])
        self.assertEqual(len((await self.request("admin","GET","/leads")).json()),2)

    async def test_foreign_and_missing_ids_are_denied_without_mutations(self):
        lead=await self.create("alice")
        await self.request("alice","POST","/interactions",json={"lead_id":lead["id"],"subject":"keep"})
        for lid in (lead["id"],"missing"):
            for method,suffix,body in (("GET","",None),("PATCH","/stage",{"stage":"closed_lost"}),
                                       ("PUT","",{"company":"overwrite","owner_id":"bob"}),("DELETE","",None),
                                       ("POST","/enrich",None)):
                response=await self.request("bob",method,"/leads/"+lid+suffix,**({"json":body} if body else {}))
                self.assertEqual(response.status_code,404,(method,response.text))
            self.assertEqual((await self.request("bob","GET","/interactions",params={"lead_id":lid})).status_code,404)
            self.assertEqual((await self.request("bob","POST","/interactions",json={"lead_id":lid})).status_code,404)
        self.assertEqual((await self.db.leads.find_one({"id":lead["id"]}))["company"],"Company alice")
        self.assertEqual(await self.db.interactions.count_documents({}),1)
        server.enrich_company.assert_not_called()

    async def test_forged_create_and_update_cannot_change_owner_or_id(self):
        lead=await self.create("alice",id="forged",owner_id="bob",created_at="forged")
        self.assertNotEqual(lead["id"],"forged")
        self.assertEqual(lead["owner_id"],"alice")
        self.assertNotEqual(lead["created_at"],"forged")
        response=await self.request("alice","PUT","/leads/"+lead["id"],json={"id":"other","company":"Changed","owner_id":"bob"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["owner_id"],"alice")
        self.assertEqual(response.json()["created_at"],lead["created_at"])
        self.assertEqual(response.json()["id"],lead["id"])

    async def test_import_deduplication_does_not_read_or_update_another_owner(self):
        other=await self.create("alice",company="Shared Name",country="Brazil",email="private@example.com")
        raw=b"company,email,country,owner_id\nShared Name,public@example.com,Brazil,alice\n"
        for _ in range(2):
            response=await self.request("bob","POST","/leads/import",files={"file":("leads.csv",raw,"text/csv")})
            self.assertEqual(response.status_code,200,response.text)
        bob=(await self.request("bob","GET","/leads")).json()
        self.assertEqual(len(bob),1)
        self.assertEqual(bob[0]["owner_id"],"bob")
        self.assertEqual(bob[0]["email"],"public@example.com")
        self.assertEqual((await self.db.leads.find_one({"id":other["id"]}))["email"],"private@example.com")

    async def test_discovery_creation_is_scoped_and_concurrently_idempotent(self):
        await self.create("alice",company="Shared Name",country="Brazil",email="private@example.com")
        payload={"company":"Shared Name","country":"Brazil","owner_id":"alice","email":"public@example.com"}
        results=await asyncio.gather(*(self.request("bob","POST","/buyer-discovery/to-crm",json=payload) for _ in range(5)))
        self.assertTrue(all(result.status_code==200 for result in results),[result.text for result in results])
        self.assertEqual(len({result.json()["id"] for result in results}),1)
        self.assertTrue(all(result.json()["owner_id"]=="bob" for result in results))
        self.assertEqual(await self.db.leads.count_documents({}),2)

    async def test_trade_to_crm_uses_callers_scope(self):
        await self.create("alice",company="Shared Name")
        await self.db.trade_data.insert_one({"id":"trade","importer_company":"Shared Name","importer_country":"Brazil",
            "country_code":"BR","industry_segment":"beverage","value_usd":5,"hs_code":"1","volume_kg":1})
        response=await self.request("bob","POST","/trade-data/trade/add-to-crm")
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["owner_id"],"bob")

    async def test_documents_files_folders_specs_and_offer_links_cannot_bypass_scope(self):
        lead=await self.create("alice")
        path=await self.attach(lead)
        await self.db.document_folders.insert_one({"path":"PRIVATE-CRM","owner_id":"alice"})
        await self.db.suppliers.insert_one({"id":"supplier","name":"Supplier"})
        await self.db.specs.insert_one({"id":"private-spec","supplier_id":"supplier","product_name":"PRIVATE CRM SPEC","original_file_path":path})
        await self.db.certifications.insert_one({"id":"private-cert","supplier_id":"supplier","name":"PRIVATE CRM CERT","file_path":path})
        # A second, general record for the same file must not declassify it.
        await self.db.documents.insert_one({"id":"alias","title":"PRIVATE ALIAS","file_name":"alias.pdf","file_path":path})
        await self.db.product_offers.insert_one({"id":"offer","spec_document_ids":["private-doc"],"spec_ids":["private-spec"],"certification_ids":["private-cert"]})
        for url in ("/documents","/specs","/certifications","/product-offers/offer/documents"):
            response=await self.request("bob","GET",url)
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json(),[],url)
        page=(await self.request("bob","GET","/documents/page")).json()
        self.assertEqual(page["total"],0)
        self.assertNotIn("PRIVATE-CRM",(await self.request("bob","GET","/document-folders")).json())
        self.assertEqual((await self.request("bob","GET","/specs/library")).json()["total"],0)
        self.assertEqual((await self.request("bob","GET","/files/"+path)).status_code,404)
        self.assertEqual((await self.request("bob","GET","/documents",params={"lead_id":lead["id"]})).status_code,404)

    async def test_private_spec_and_certificate_cannot_be_modified_or_republished(self):
        lead=await self.create("alice")
        path=await self.attach(lead)
        await self.db.suppliers.insert_one({"id":"supplier","name":"Supplier"})
        await self.db.specs.insert_one({"id":"spec","supplier_id":"supplier","product_name":"Private","original_file_path":path})
        await self.db.certifications.insert_one({"id":"cert","supplier_id":"supplier","name":"Private","file_path":path})
        for url,body in (("/specs/spec",{"supplier_id":"supplier","product_name":"Overwrite"}),
                         ("/certifications/cert",{"supplier_id":"supplier","name":"Overwrite"})):
            self.assertEqual((await self.request("bob","PUT",url,json=body)).status_code,403)
            self.assertEqual((await self.request("bob","DELETE",url)).status_code,403)
        for url,body in (("/specs",{"supplier_id":"supplier","product_name":"Copy","original_file_path":path}),
                         ("/certifications",{"supplier_id":"supplier","name":"Copy","file_path":path})):
            self.assertEqual((await self.request("bob","POST",url,json=body)).status_code,403)
        self.assertEqual(await self.db.specs.count_documents({}),1)
        self.assertEqual(await self.db.certifications.count_documents({}),1)

    async def test_anonymous_cannot_read_crm_or_assign_owner(self):
        for method,url,body in (("GET","/leads",None),("GET","/leads/count",None),("GET","/interactions",None),
                                 ("PATCH","/leads/any/owner",{"owner_id":"alice"})):
            response=await self.client.request(method,"/api"+url,**({"json":body} if body else {}))
            self.assertEqual(response.status_code,401,response.text)

    async def test_attachment_forgery_is_rejected_before_storage(self):
        lead=await self.create("alice")
        response=await self.request("bob","POST","/documents/upload",data={"metadata":json.dumps({
            "title":"Forged","category":"Clientes & Comercial","lead_id":lead["id"]})},files={"file":("file.pdf",b"%PDF-test")})
        self.assertEqual(response.status_code,400,response.text)
        self.assertEqual(self.objects,{})
        self.assertEqual(await self.db.documents.count_documents({}),0)

    async def test_transfer_revokes_former_uploader_and_moves_linked_history(self):
        lead=await self.create("alice")
        path=await self.attach(lead)
        await self.request("alice","POST","/interactions",json={"lead_id":lead["id"],"subject":"History"})
        route="/leads/"+lead["id"]+"/owner"
        self.assertEqual((await self.request("alice","PATCH",route,json={"owner_id":"bob"})).status_code,403)
        self.assertEqual((await self.request("admin","PATCH",route,json={"owner_id":"missing"})).status_code,400)
        self.assertEqual((await self.request("admin","PATCH",route,json={"owner_id":"bob"})).status_code,200)
        self.assertEqual((await self.request("alice","GET","/files/"+path)).status_code,404)
        self.assertEqual((await self.request("alice","GET","/leads/"+lead["id"])).status_code,404)
        self.assertEqual((await self.request("bob","GET","/files/"+path)).content,b"%PDF-private")
        self.assertEqual(len((await self.request("bob","GET","/interactions")).json()),1)
        # The original upload prefix cannot republish the transferred document.
        response=await self.request("alice","POST","/documents",json={"title":"Repub","file_name":"private.pdf","file_path":path})
        self.assertEqual(response.status_code,403,response.text)

    async def test_legacy_is_preserved_and_explicitly_assignable(self):
        await self.db.leads.insert_one({"id":"legacy","company":"Existing Company"})
        self.assertEqual((await self.request("alice","GET","/leads")).json(),[])
        self.assertEqual(len((await self.request("admin","GET","/leads")).json()),1)
        response=await self.request("admin","PATCH","/leads/legacy/owner",json={"owner_id":"alice"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(len((await self.request("alice","GET","/leads")).json()),1)

    async def test_transfer_releases_old_creation_key(self):
        payload={"company":"Discovered","country":"Brazil"}
        first=(await self.request("alice","POST","/buyer-discovery/to-crm",json=payload)).json()
        await self.request("admin","PATCH","/leads/"+first["id"]+"/owner",json={"owner_id":"bob"})
        response=await self.request("alice","POST","/buyer-discovery/to-crm",json=payload)
        self.assertEqual(response.status_code,200,response.text)
        self.assertNotEqual(response.json()["id"],first["id"])

    async def test_general_team_documents_remain_shared(self):
        self.objects["shared/spec.pdf"]=(b"%PDF-shared","application/pdf")
        await self.db.documents.insert_one({"id":"shared","title":"Shared Spec","file_name":"spec.pdf","file_path":"shared/spec.pdf","folder_path":"Shared"})
        self.assertEqual(len((await self.request("bob","GET","/documents")).json()),1)
        self.assertEqual((await self.request("bob","GET","/files/shared/spec.pdf")).status_code,200)


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "Disposable MongoDB not configured")
class CrmAccessMongoTests(CrmAccessTests):
    def make_database(self):
        url=os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost","127.0.0.1","mongo"}: raise RuntimeError("Only local disposable MongoDB is allowed")
        self.mongo=AsyncIOMotorClient(url,serverSelectionTimeoutMS=5000)
        self.database_name="ibiag_test_crm_"+uuid.uuid4().hex
        return self.mongo[self.database_name]

    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
