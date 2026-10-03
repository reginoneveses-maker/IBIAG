"""HTTP regression tests using an isolated in-memory database and storage.

No production credentials, provider requests or application startup are used.
"""
import json
import asyncio
import discovery_jobs
import os
import unittest
from unittest.mock import patch
import httpx
from mongomock_motor import AsyncMongoMockClient

# The ASGI transport does not run startup, and all persistence is patched per test.
with patch.dict(os.environ, {"MONGO_URL": "mongodb://localhost:27017", "DB_NAME": "ibiag_http_test", "JWT_SECRET": "test-secret-only-32-characters-long"}):
    import server


class CompanyDocumentsApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = AsyncMongoMockClient()["isolated"]
        self.user = {"id": "u", "email": "test@example.com", "role": "admin"}
        await self.db.users.insert_one(self.user.copy())
        self.objects = {}
        async def put(path, data, ct):
            self.objects[path] = (data, ct)
            return {"path": path, "size": len(data), "content_type": ct}
        async def get(path):
            if path not in self.objects:
                raise server.HTTPException(404, "Arquivo não encontrado")
            return self.objects[path]
        async def delete(path): self.objects.pop(path, None)
        self.patches = [patch.object(server, "db", self.db), patch.object(server, "put_object", put),
                        patch.object(server, "get_object", get), patch.object(server, "delete_object", delete)]
        for p in self.patches: p.start()
        token = server.create_token("u", "test@example.com")
        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test",
                                       headers={"Authorization": "Bearer " + token})

    async def asyncTearDown(self):
        await self.client.aclose()
        for p in reversed(self.patches): p.stop()

    async def upload(self, **metadata):
        return await self.client.post("/api/documents/upload", data={"metadata": json.dumps({"title": "Laudo", "category": "Produtos", **metadata})},
                                      files={"file": ("laudo.pdf", b"%PDF-1.4 test", "application/pdf")})

    async def test_multi_market_job_partial_results_and_owner_access(self):
        def discover(product, country, limit):
            if country == "Spain": raise RuntimeError("Provedor indisponível")
            return [{"company": "Acme", "website": "https://example.com"}]
        with patch.object(server, "discover_buyers", discover), patch.object(discovery_jobs, "SLOTS", asyncio.Semaphore(3)):
            response = await self.client.post("/api/buyer-discovery/search-jobs", json={"product":"Acerola","countries":["Alemanha","Espanha","Portugal"]})
        self.assertEqual(response.status_code, 200, response.text)
        job_id = response.json()["id"]
        job = (await self.client.get("/api/buyer-discovery/search-jobs/" + job_id)).json()
        self.assertEqual(job["status"], "partial")
        self.assertEqual(job["completed"], 3)
        self.assertEqual([r["country_code"] for r in job["results"]], ["DE", "PT"])
        self.assertEqual(job["progress"]["ES"]["status"], "failed")
        await self.db.users.insert_one({"id":"other","email":"other@example.com","role":"user"})
        response = await self.client.get("/api/buyer-discovery/search-jobs/"+job_id,headers={"Authorization":"Bearer "+server.create_token("other","other@example.com")})
        self.assertEqual(response.status_code,403)
        response = await self.client.post("/api/buyer-discovery/search-jobs",json={"product":"Acerola","countries":["Atlantis"]})
        self.assertEqual(response.status_code,400)

    async def test_crm_automatically_enriches_and_refreshes_existing_profile(self):
        facts={"company":"Acme Ingredients", "email":"info@acme.test", "phone":"+49 40 12345678", "website":"https://acme.test/", "country":"Germany", "enrichment_status":"complete", "contact_source_urls":["https://acme.test/contact"]}
        with patch.object(server,"enrich_company",return_value=facts):
            response=await self.client.post("/api/buyer-discovery/to-crm",json={"company":"Organic Acerola Extract", "country":"Germany", "website":"https://acme.test/products/acerola"})
            lead=response.json()
            self.assertEqual(response.status_code,200,response.text)
            for key in ("company","email","phone","website","country"):self.assertEqual(lead[key],facts[key])
            await self.db.leads.update_one({"id":lead["id"]},{"$set":{"email":"manual@acme.test"}})
            refreshed=await self.client.post("/api/leads/"+lead["id"]+"/enrich")
            self.assertEqual(refreshed.json()["id"],lead["id"])
            self.assertEqual(refreshed.json()["email"],"manual@acme.test")
            self.assertEqual(await self.db.leads.count_documents({}),1)

    async def test_protected_endpoints_reject_missing_and_invalid_token(self):
        for path in ["/interactions", "/templates", "/trade-data", "/dashboard/stats", "/documents", "/documents/page", "/document-folders", "/buyer-discovery/markets", "/buyer-discovery/search-jobs/missing"]:
            for token in ["", "Bearer invalid"]:
                response = await self.client.get("/api" + path, headers={"Authorization": token})
                self.assertEqual(response.status_code, 401, (path, response.text))

    async def test_upload_link_download_trash_restore(self):
        await self.db.leads.insert_one({"id": "lead", "company": "Empresa"})
        response = await self.upload(lead_id="lead", folder_path="Produtos/Acerola/COA")
        self.assertEqual(response.status_code, 200, response.text)
        doc = response.json()
        self.assertEqual(doc["lead_name"], "Empresa")
        self.assertEqual((await self.client.get("/api/document-folders")).json(), ["Produtos", "Produtos/Acerola", "Produtos/Acerola/COA"])
        linked = (await self.client.get("/api/documents", params={"lead_id": "lead"})).json()
        self.assertEqual([d["id"] for d in linked], [doc["id"]])
        download = await self.client.get("/api/files/" + doc["file_path"])
        self.assertEqual(download.content, b"%PDF-1.4 test")
        await self.client.delete("/api/documents/" + doc["id"])
        self.assertEqual((await self.client.get("/api/documents")).json(), [])
        self.assertIn(doc["file_path"], self.objects)
        await self.client.post("/api/documents/" + doc["id"] + "/restore")
        self.assertEqual(len((await self.client.get("/api/documents")).json()), 1)

    async def test_bad_metadata_and_links_do_not_upload(self):
        for metadata in [{"folder_path": "Produtos/../secret"}, {"lead_id": "missing"}, {"product_id": "missing"}, {"title": " "}]:
            response = await self.upload(**metadata)
            self.assertEqual(response.status_code, 400, response.text)
            self.assertEqual(self.objects, {})

    async def test_failed_database_write_cleans_uploaded_object(self):
        with patch.object(server.db, "documents", self.db.documents) as documents, patch.object(documents, "insert_one", side_effect=RuntimeError("write failed")):
            with self.assertRaisesRegex(RuntimeError, "write failed"):
                await self.upload()
        self.assertEqual(self.objects, {})

    async def test_paginated_search_and_empty_folder_persist(self):
        await self.db.documents.insert_many([{"id": str(i), "title": f"Doc {i}", "category": "Produtos", "file_path": "x", "file_name": "x.pdf"} for i in range(501)])
        response = (await self.client.get("/api/documents/page", params={"skip": 500, "limit": 250})).json()
        self.assertEqual(response["total"], 501)
        self.assertEqual(len(response["items"]), 1)
        search = (await self.client.get("/api/documents/page", params={"search": "Doc 500"})).json()
        self.assertEqual(search["total"], 1)
        await self.client.post("/api/document-folders", json={"path": "Empty/Child"})
        self.assertIn("Empty/Child", (await self.client.get("/api/document-folders")).json())
        invalid = await self.client.post("/api/document-folders", json={"path": "Empty/./Child"})
        self.assertEqual(invalid.status_code, 400)

    async def test_move_document_to_subfolder(self):
        doc = (await self.upload()).json()
        response = await self.client.patch(f"/api/documents/{doc['id']}/classification", json={"category": "Produtos", "folder_path": "Acerola/COA"})
        self.assertEqual(response.status_code, 200, response.text)
        reloaded = (await self.client.get("/api/documents")).json()[0]
        self.assertEqual(reloaded["folder_path"], "Acerola/COA")

    async def test_crm_preserves_contacts_sources_and_existing_manual_data(self):
        buyer = {"company": "ABC-Ingredients", "country": "Portugal", "priority_score": 80,
                 "website": "https://example.com", "source_url": "https://example.com/company",
                 "decision_source_url": "https://example.com/team", "decision_maker": "Ana Silva",
                 "decision_maker_email": "ana@example.com", "evidence_urls": ["https://example.com/team"]}
        first = await self.client.post("/api/buyer-discovery/to-crm", json=buyer)
        self.assertEqual(first.status_code, 200, first.text)
        lead = first.json()
        reloaded = (await self.client.get("/api/leads/" + lead["id"])).json()
        self.assertEqual(reloaded["decision_maker_email"], buyer["decision_maker_email"])
        self.assertEqual(reloaded["source_url"], buyer["source_url"])
        self.assertEqual(reloaded["decision_source_url"], buyer["decision_source_url"])
        repeat = (await self.client.post("/api/buyer-discovery/to-crm", json=buyer)).json()
        self.assertEqual(repeat["id"], lead["id"])
        self.assertEqual(await self.db.leads.count_documents({}), 1)
        invalid = await self.client.post("/api/buyer-discovery/to-crm", json={**buyer, "priority_score": "invalid"})
        self.assertEqual(invalid.status_code, 400)
        missing = await self.client.get("/api/leads/missing")
        self.assertEqual(missing.status_code, 404)

    async def test_shared_documents_access_but_not_private_uploads(self):
        doc = (await self.upload()).json()
        await self.db.users.insert_one({"id": "other", "email": "other@example.com", "role": "user"})
        headers = {"Authorization": "Bearer " + server.create_token("other", "other@example.com")}
        self.assertEqual((await self.client.get("/api/files/" + doc["file_path"], headers=headers)).status_code, 200)
        self.assertEqual((await self.client.get("/api/files/agrobrasil/uploads/u/private.pdf", headers=headers)).status_code, 403)
        self.assertEqual((await self.client.delete("/api/documents/" + doc["id"], headers=headers)).status_code, 403)
        await self.client.delete("/api/documents/" + doc["id"])
        self.assertEqual((await self.client.get("/api/files/" + doc["file_path"], headers=headers)).status_code, 403)

    async def test_offer_rejects_deleted_or_missing_document(self):
        for ids in [["missing"]]:
            offer = server.ProductOffer(product_id="p", form="Pulp", other_document_ids=ids)
            with self.assertRaises(server.HTTPException): await server.validate_offer_documents(offer)
        await self.db.documents.insert_one({"id": "deleted", "deleted_at": "2026-10-03"})
        with self.assertRaises(server.HTTPException):
            await server.validate_offer_documents(server.ProductOffer(product_id="p", form="Pulp", other_document_ids=["deleted"]))


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "MongoDB real de testes não configurado")
class RealDocumentStorageTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_gridfs_upload_download_and_folder_persistence(self):
        import uuid
        from urllib.parse import urlparse
        from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
        url = os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost", "127.0.0.1", "mongo"}:
            raise RuntimeError("Somente MongoDB local descartável")
        client = AsyncIOMotorClient(url, serverSelectionTimeoutMS=5000)
        name = "ibiag_documents_test_" + uuid.uuid4().hex
        db = client[name]
        try:
            await db.users.insert_one({"id": "u", "email": "test@example.com", "role": "admin"})
            await db.leads.create_index("discovery_key", unique=True, sparse=True)
            with patch.object(server, "db", db), patch.object(server, "gridfs", AsyncIOMotorGridFSBucket(db, bucket_name="ibiag_files")), patch.object(server, "STORAGE_PROVIDER", "gridfs"):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app), base_url="http://test", headers={"Authorization": "Bearer " + server.create_token("u", "test@example.com")}) as http:
                    response = await http.post("/api/documents/upload", data={"metadata": json.dumps({"title": "Original", "category": "Produtos", "folder_path": "Produtos/Acerola"})}, files={"file": ("original.pdf", b"%PDF-1.4 real storage", "application/pdf")})
                    self.assertEqual(response.status_code, 200, response.text)
                    doc = response.json()
                    await http.patch(f"/api/documents/{doc['id']}/classification", json={"category": "Produtos", "folder_path": "Produtos/Acerola/COA"})
                    reloaded = (await http.get("/api/documents/page")).json()["items"][0]
                    self.assertEqual(reloaded["folder_path"], "Produtos/Acerola/COA")
                    self.assertEqual((await http.get("/api/files/" + doc["file_path"])).content, b"%PDF-1.4 real storage")
                    self.assertEqual(await db["ibiag_files.files"].count_documents({}), 1)
                    self.assertGreater(await db["ibiag_files.chunks"].count_documents({}), 0)
        finally:
            await client.drop_database(name)
            client.close()
