import os
import unittest
from unittest.mock import patch, AsyncMock
import httpx
from mongomock_motor import AsyncMongoMockClient
from discovery_permissions import paid_discovery_enabled

with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"credit_guard_test",
                            "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class DiscoveryFlagTests(unittest.TestCase):
    def test_only_explicit_server_opt_in_enables_paid_operations(self):
        with patch.dict(os.environ,{},clear=True): self.assertFalse(paid_discovery_enabled())
        for value in ("false","","1","yes","*"):
            with patch.dict(os.environ,{"ALLOW_PAID_DISCOVERY":value}): self.assertFalse(paid_discovery_enabled())
        with patch.dict(os.environ,{"ALLOW_PAID_DISCOVERY":"true"}): self.assertTrue(paid_discovery_enabled())


class DiscoveryCreditGuardTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=AsyncMongoMockClient()["isolated"]
        await self.db.users.insert_one({"id":"admin","email":"admin@example.com","role":"admin"})
        await self.db.leads.insert_one({"id":"lead","owner_id":"admin","company":"Company","country":"Brazil"})
        self.patches=[patch.object(server,"db",self.db),patch.dict(os.environ,{"ALLOW_PAID_DISCOVERY":"false"}),
                      patch.object(server,"discover_buyers",return_value=[]),
                      patch.object(server,"discover_decision_maker",return_value={}),
                      patch.object(server,"enrich_company",return_value={}),
                      patch.object(server,"run_discovery_job",new_callable=AsyncMock)]
        for item in self.patches: item.start()
        token=server.create_token("admin","admin@example.com")
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test",
                                      headers={"Authorization":"Bearer "+token})

    async def asyncTearDown(self):
        await self.client.aclose()
        for item in reversed(self.patches): item.stop()

    def assert_no_provider_calls(self):
        server.discover_buyers.assert_not_called()
        server.discover_decision_maker.assert_not_called()
        server.enrich_company.assert_not_called()
        server.run_discovery_job.assert_not_called()

    async def test_disabled_search_jobs_retry_decision_and_enrichment_do_not_spend(self):
        for path,body in (("/buyer-discovery/search",{"product":"Acerola","country":"Portugal"}),
                          ("/buyer-discovery/search-jobs",{"product":"Acerola","country":"Portugal"}),
                          ("/buyer-discovery/search-jobs/old/retry",{}),
                          ("/buyer-discovery/Company/decision-maker",{}),
                          ("/leads/lead/enrich",{})):
            response=await self.client.post("/api"+path,json=body)
            self.assertEqual(response.status_code,403,(path,response.text))
        self.assert_no_provider_calls()
        self.assertEqual(await self.db.buyer_search_jobs.count_documents({}),0)

    async def test_saving_candidate_keeps_contacts_without_external_enrichment(self):
        response=await self.client.post("/api/buyer-discovery/to-crm",json={"company":"New Company",
            "country":"Portugal","email":"published@example.com","phone":"123","ALLOW_PAID_DISCOVERY":True})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["email"],"published@example.com")
        self.assertEqual(response.json()["enrichment_status"],"paused")
        self.assert_no_provider_calls()

    async def test_client_payload_cannot_enable_paid_search(self):
        response=await self.client.post("/api/buyer-discovery/search",json={"product":"Acerola","country":"Portugal",
            "ALLOW_PAID_DISCOVERY":True,"allow_paid_discovery":True})
        self.assertEqual(response.status_code,403)
        self.assert_no_provider_calls()

    async def test_previous_results_remain_readable_and_cancelable(self):
        await self.db.buyer_search_jobs.insert_one({"id":"old","owner_id":"admin","status":"running",
            "discovery_version":server.DISCOVERY_VERSION,"results":[{"company":"Already Found"}]})
        response=await self.client.get("/api/buyer-discovery/search-jobs/old")
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["results"][0]["company"],"Already Found")
        self.assertEqual((await self.client.post("/api/buyer-discovery/search-jobs/old/cancel")).status_code,200)
        self.assert_no_provider_calls()

    async def test_explicit_server_opt_in_still_uses_mocked_providers(self):
        with patch.dict(os.environ,{"ALLOW_PAID_DISCOVERY":"true"}):
            response=await self.client.post("/api/buyer-discovery/search",json={"product":"Acerola","country":"Portugal"})
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual((await self.client.post("/api/buyer-discovery/Company/decision-maker")).status_code,200)
            self.assertEqual((await self.client.post("/api/leads/lead/enrich")).status_code,200)
        server.discover_buyers.assert_called_once()
        server.discover_decision_maker.assert_called_once()
        server.enrich_company.assert_called_once()
