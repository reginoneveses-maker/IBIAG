import asyncio
import unittest
from unittest.mock import patch
from mongomock_motor import AsyncMongoMockClient
import discovery_jobs as jobs

class MarketsTests(unittest.TestCase):
    def test_names_codes_regions_and_deduplication(self):
        self.assertEqual([x["code"] for x in jobs.resolve_markets("Alemanha; Spain, PT,DE")],["DE","ES","PT"])
        self.assertEqual(len(jobs.resolve_markets(region="Europa")),51)
        self.assertEqual(len(jobs.resolve_markets(region="Ásia")),50)
        with self.assertRaises(ValueError): jobs.resolve_markets("Atlantis")

class CancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_queue_does_not_call_provider(self):
        db=AsyncMongoMockClient()["jobs"]
        job={"id":"cancel","product":"Acerola","limit":10,"targets":jobs.resolve_markets("DE,ES,PT"),"cancel_requested":True}
        await db.buyer_search_jobs.insert_one(dict(job))
        def unexpected(*args): self.fail("Cancelled job called the provider")
        with patch.object(jobs,"SLOTS",asyncio.Semaphore(3)):
            await jobs.run_discovery_job(db,job,unexpected)
        saved=await db.buyer_search_jobs.find_one({"id":"cancel"})
        self.assertEqual(saved["status"],"cancelled")


class ReliabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_credit_failure_stops_queued_countries_without_provider_calls(self):
        from buyer_discovery import ProviderError
        db=AsyncMongoMockClient()["jobs"]
        job={"id":"credits","product":"Acerola","limit":10,"targets":jobs.resolve_markets("DE,ES,PT")}
        await db.buyer_search_jobs.insert_one(dict(job))
        calls=[]
        def discover(product,country,limit):
            calls.append(country)
            raise ProviderError("Créditos acabaram", "credits", True)
        with patch.object(jobs,"SLOTS",asyncio.Semaphore(1)):
            await jobs.run_discovery_job(db,job,discover)
        saved=await db.buyer_search_jobs.find_one({"id":"credits"})
        self.assertEqual(calls,["Germany"])
        self.assertEqual(saved["status"],"failed")
        self.assertEqual(saved["service_error_code"],"credits")
        self.assertEqual(saved["progress"]["ES"]["status"],"blocked")

    async def test_retry_retains_successful_and_partial_results_even_when_retry_fails(self):
        db=AsyncMongoMockClient()["jobs"]
        all_targets=jobs.resolve_markets("DE,ES,PT")
        base=[{"company":"German Company","website":"https://de.test","country_code":"DE"},
              {"company":"Partial Company","website":"https://es.test","country_code":"ES"}]
        job={"id":"retry","product":"Acerola","limit":10,"targets":[all_targets[1]],"result_targets":all_targets,"base_results":base}
        await db.buyer_search_jobs.insert_one(dict(job))
        def discover(*args): raise RuntimeError("Still unavailable")
        with patch.object(jobs,"SLOTS",asyncio.Semaphore(1)):
            await jobs.run_discovery_job(db,job,discover)
        saved=await db.buyer_search_jobs.find_one({"id":"retry"})
        self.assertEqual([r["company"] for r in saved["results"]],["German Company","Partial Company"])
