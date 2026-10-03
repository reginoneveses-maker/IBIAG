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
