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

    async def test_spec_library_collects_existing_documents_and_offers_per_supplier(self):
        await self.db.suppliers.insert_many([{"id":"s1","name":"Nossa Fruta"},{"id":"s2","name":"Itaueira"}])
        await self.db.documents.insert_many([
            {"id":"d1","title":"Spec Acerola","file_name":"spec.pdf","file_path":"shared/spec.pdf","document_type":"Ficha Técnica","supplier_id":"s1","product_name":"Acerola"},
            {"id":"d2","title":"Spec Manga","file_path":"manga","document_type":"Ficha Técnica","supplier_name":"ITAUEIRA"},
            {"id":"d3","title":"Guarana","file_path":"guarana"},
            {"id":"d4","title":"Ficha Técnica Abacaxi","file_path":"orphan"},
            {"id":"d5","title":"Certificado","document_type":"Certificado","supplier_id":"s1","file_path":"cert"},
            {"id":"d6","title":"Spec excluída","document_type":"Ficha Técnica","supplier_id":"s1","file_path":"trash","deleted_at":"2026-10-03"}])
        await self.db.product_offers.insert_one({"id":"o","supplier_id":"s2","product_name":"Guaraná","spec_document_ids":["d3"]})
        result=(await self.client.get("/api/specs/library")).json()
        self.assertEqual(result["counts"],{"s1":1,"s2":2})
        self.assertEqual({row["document_id"] for row in result["items"]},{"d1","d2","d3"})
        self.assertEqual(result["unassigned"][0]["document_id"],"d4")
        self.assertEqual(await self.db.specs.count_documents({}),0)
        assigned=await self.client.patch("/api/specs/documents/d4/supplier",json={"supplier_id":"s1"})
        self.assertEqual(assigned.status_code,200,assigned.text)
        refreshed=(await self.client.get("/api/specs/library")).json()
        self.assertEqual(refreshed["counts"]["s1"],2)
        self.assertEqual(refreshed["unassigned_total"],0)
        self.assertEqual((await self.db.documents.find_one({"id":"d4"}))["file_path"],"orphan")
        conflict=await self.client.patch("/api/specs/documents/d1/supplier",json={"supplier_id":"s2"})
        self.assertEqual(conflict.status_code,409)

    async def test_spec_library_is_not_truncated_and_deduplicates_registered_paths(self):
        await self.db.suppliers.insert_one({"id":"s","name":"Fornecedor"})
        await self.db.documents.insert_many([{"id":str(i),"title":"Spec "+str(i),"supplier_id":"s","document_type":"Ficha Técnica","file_path":"path"+str(i)} for i in range(1001)])
        await self.db.specs.insert_one({"id":"original","supplier_id":"s","supplier_name":"Fornecedor","product_name":"Original","original_file_path":"path0"})
        result=(await self.client.get("/api/specs/library")).json()
        self.assertEqual(result["total"],1001)
        self.assertEqual(result["counts"]["s"],1001)
        self.assertEqual(result["unassigned_total"],0)
        self.assertEqual(await self.db.documents.count_documents({}),1001)

    async def test_specs_require_valid_supplier_and_share_only_registered_files(self):
        await self.db.suppliers.insert_one({"id":"s","name":"Fornecedor correto"})
        invalid=await self.client.post("/api/specs",json={"supplier_id":"missing","product_name":"Acerola"})
        self.assertEqual(invalid.status_code,400)
        self.objects["shared/spec.pdf"]=(b"%PDF-test","application/pdf")
        saved=await self.client.post("/api/specs",json={"supplier_id":"s","supplier_name":"errado","product_name":"Acerola","original_file_path":"shared/spec.pdf"})
        self.assertEqual(saved.status_code,200,saved.text)
        self.assertEqual(saved.json()["supplier_name"],"Fornecedor correto")
        await self.db.users.insert_one({"id":"team","email":"team@example.com","role":"user"})
        auth={"Authorization":"Bearer "+server.create_token("team","team@example.com")}
        downloaded=await self.client.get("/api/files/shared/spec.pdf",headers=auth)
        self.assertEqual(downloaded.status_code,200)
        self.assertEqual(downloaded.content,b"%PDF-test")
        denied=await self.client.post("/api/specs",json={"supplier_id":"s","product_name":"Outro","original_file_path":"unknown/private.pdf"},headers=auth)
        self.assertEqual(denied.status_code,403)
        manual=await self.client.patch("/api/specs/documents/missing/supplier",json={"supplier_id":"s"},headers=auth)
        self.assertEqual(manual.status_code,403)

    async def test_ambiguous_supplier_names_are_not_guessed(self):
        await self.db.suppliers.insert_many([{"id":"s1","name":"ACME"},{"id":"s2","name":"Acme"}])
        await self.db.documents.insert_one({"id":"d","title":"Spec Acerola","file_path":"d","supplier_name":"acme"})
        result=(await self.client.get("/api/specs/library")).json()
        self.assertEqual(result["total"],0)
        self.assertEqual(result["unassigned_total"],1)
        self.assertIn("ambíguo",result["unassigned"][0]["assignment_reason"])

    async def test_new_search_can_replace_own_active_job_without_blocking(self):
        await self.db.buyer_search_jobs.insert_many([
            {"id":"old","owner_id":"u","status":"running","cancel_requested":False},
            {"id":"other","owner_id":"another-user","status":"running","cancel_requested":False}])
        with patch.object(server,"discover_buyers",return_value=[]), patch.object(discovery_jobs,"SLOTS",asyncio.Semaphore(3)):
            blocked=await self.client.post("/api/buyer-discovery/search-jobs",json={"product":"Manga","countries":["PT","ES"]})
            self.assertEqual(blocked.status_code,409)
            fresh=await self.client.post("/api/buyer-discovery/search-jobs",json={"product":"Manga","countries":["PT","ES"],"replace_previous":True})
            self.assertEqual(fresh.status_code,200,fresh.text)
        self.assertTrue((await self.db.buyer_search_jobs.find_one({"id":"old"}))["cancel_requested"])
        self.assertFalse((await self.db.buyer_search_jobs.find_one({"id":"other"}))["cancel_requested"])
        self.assertEqual(fresh.json()["product"],"Manga")

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

    async def test_retry_only_failed_markets_preserves_results_and_checks_owner(self):
        targets=discovery_jobs.resolve_markets("DE,ES,PT")
        original={"id":"retry-original", "owner_id":"u", "product":"Acerola", "limit":10,
                  "targets":targets, "label":"Europa", "discovery_version":server.DISCOVERY_VERSION,
                  "status":"partial", "progress":{"DE":{"status":"complete"},"ES":{"status":"failed"},"PT":{"status":"complete"}},
                  "results":[{"company":"German Company", "website":"https://de.test", "country_code":"DE"}]}
        await self.db.buyer_search_jobs.insert_one(original)
        calls=[]
        def discover(product,country,limit):
            calls.append(country)
            return [{"company":"Spanish Company", "website":"https://es.test"}]
        with patch.object(server,"discover_buyers",discover),patch.object(discovery_jobs,"SLOTS",asyncio.Semaphore(1)):
            response=await self.client.post("/api/buyer-discovery/search-jobs/retry-original/retry")
        self.assertEqual(response.status_code,200,response.text)
        retry=(await self.client.get("/api/buyer-discovery/search-jobs/"+response.json()["id"])).json()
        self.assertEqual(calls,["Spain"])
        self.assertEqual(retry["total"],1)
        self.assertEqual(retry["status"],"complete")
        self.assertEqual([r["company"] for r in retry["results"]],["German Company","Spanish Company"])
        self.assertEqual((await self.db.buyer_search_jobs.find_one({"id":"retry-original"}))["status"],"partial")
        await self.db.users.insert_one({"id":"other","email":"other@example.com","role":"user"})
        denied=await self.client.post("/api/buyer-discovery/search-jobs/retry-original/retry",headers={"Authorization":"Bearer "+server.create_token("other","other@example.com")})
        self.assertEqual(denied.status_code,403)

    async def test_legacy_jobs_do_not_redisplay_unverified_titles_as_companies(self):
        await self.db.buyer_search_jobs.insert_one({"id":"legacy","owner_id":"u","status":"complete",
            "results":[{"company":"Acerola research book"}]})
        response=await self.client.get("/api/buyer-discovery/search-jobs/legacy")
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["status"],"outdated")
        self.assertEqual(response.json()["results"],[])
        self.assertIn("busque novamente",response.json()["validation_message"])
        self.assertEqual((await self.db.buyer_search_jobs.find_one({"id":"legacy"}))["results"][0]["company"],"Acerola research book")

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
        for path in ["/interactions", "/templates", "/trade-data", "/dashboard/stats", "/documents", "/documents/page", "/document-folders", "/buyer-discovery/markets", "/buyer-discovery/search-jobs/missing", "/specs/library"]:
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
                 "decision_maker_email": "ana@example.com", "evidence_urls": ["https://example.com/team"],
                 "product_relationship":"seller", "product_evidence":"We supply Acerola ingredients.", "relationship_verified":True}
        with patch.object(server,"enrich_company",return_value={"company":"Organic Acerola Extract with 32% Natural Vitamin C", "email":"info@example.com"}):
            first = await self.client.post("/api/buyer-discovery/to-crm", json=buyer)
        self.assertEqual(first.status_code, 200, first.text)
        lead = first.json()
        self.assertEqual(lead["company"],"ABC-Ingredients")
        self.assertEqual(lead["email"],"info@example.com")
        reloaded = (await self.client.get("/api/leads/" + lead["id"])).json()
        self.assertEqual(reloaded["decision_maker_email"], buyer["decision_maker_email"])
        self.assertEqual(reloaded["source_url"], buyer["source_url"])
        self.assertEqual(reloaded["decision_source_url"], buyer["decision_source_url"])
        self.assertTrue(reloaded["relationship_verified"])
        self.assertEqual(reloaded["product_evidence"],buyer["product_evidence"])
        self.assertEqual(reloaded["product_relationship"],"seller")
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
