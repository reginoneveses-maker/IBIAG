import unittest
from fastapi import FastAPI, HTTPException
import httpx
from safe_errors import install_error_handlers

CANARY = "private-provider-token-and-internal-host"


class SafeErrorsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = FastAPI()
        install_error_handlers(self.app)

        @self.app.get("/upstream")
        async def upstream():
            raise HTTPException(502, CANARY, headers={"X-Provider-Secret":CANARY})

        @self.app.get("/unexpected")
        async def unexpected():
            raise RuntimeError(CANARY)

        @self.app.get("/limit")
        async def limit():
            raise HTTPException(429, "Too many attempts", headers={"Retry-After":"900"})

        self.client = httpx.AsyncClient(transport=httpx.ASGITransport(app=self.app, raise_app_exceptions=False),
                                        base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_upstream_and_unhandled_errors_are_redacted(self):
        for path, code in (("/upstream",502), ("/unexpected",500)):
            with self.assertLogs("safe_errors", level="ERROR") as logs:
                response = await self.client.get(path)
            self.assertEqual(response.status_code, code)
            self.assertNotIn(CANARY, response.text + str(response.headers) + str(logs.output))
            self.assertEqual(len(response.json()["incident_id"]),32)
            self.assertEqual(response.headers["cache-control"], "no-store")

    async def test_rate_limit_contract_is_preserved(self):
        response = await self.client.get("/limit")
        self.assertEqual(response.status_code,429)
        self.assertEqual(response.headers["retry-after"],"900")
        self.assertEqual(response.json(), {"detail":"Too many attempts"})
