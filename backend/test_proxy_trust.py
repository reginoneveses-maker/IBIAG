"""Exercise the actual Uvicorn middleware, including forged forwarded chains."""
import unittest
from serve import server_options
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware


class ProxyConfigTests(unittest.TestCase):
    def test_default_ignores_ambient_uvicorn_trust(self):
        options = server_options({"FORWARDED_ALLOW_IPS": "*"})
        self.assertFalse(options["proxy_headers"])
        self.assertEqual(options["forwarded_allow_ips"], [])

    def test_rejects_ambiguous_or_broad_trust(self):
        for value in ("*", "10.0.0.0/8", "proxy.internal", "127.0.0.1,", ","):
            with self.subTest(value=value), self.assertRaises(ValueError):
                server_options({"TRUSTED_PROXY_IPS": value})

    def test_exact_ipv4_and_ipv6(self):
        options = server_options({"TRUSTED_PROXY_IPS": "10.1.2.3, ::1", "PORT": "8080"})
        self.assertEqual(options["forwarded_allow_ips"], ["10.1.2.3", "::1"])
        self.assertTrue(options["proxy_headers"])
        self.assertEqual(options["port"], 8080)


class ProxyMiddlewareTests(unittest.IsolatedAsyncioTestCase):
    async def resolved(self, peer, forwarded, trusted):
        seen = []
        async def endpoint(scope, receive, send):
            seen.append(scope["client"][0])
        middleware = ProxyHeadersMiddleware(endpoint, trusted_hosts=trusted)
        scope = {"type": "http", "client": (peer, 1234), "scheme": "http",
                 "headers": [(b"x-forwarded-for", forwarded.encode())]}
        await middleware(scope, None, None)
        return seen[0]

    async def test_direct_attacker_cannot_spoof(self):
        self.assertEqual(await self.resolved("198.51.100.1", "192.0.2.1", ["10.1.2.3"]), "198.51.100.1")

    async def test_verified_proxy_separates_clients(self):
        for client in ("192.0.2.1", "192.0.2.2"):
            self.assertEqual(await self.resolved("10.1.2.3", client, ["10.1.2.3"]), client)

    async def test_prepended_forgery_does_not_override_appended_client(self):
        self.assertEqual(await self.resolved("10.1.2.3", "203.0.113.9, 192.0.2.1", ["10.1.2.3"]), "192.0.2.1")

    async def test_empty_trust_ignores_headers(self):
        self.assertEqual(await self.resolved("10.1.2.3", "192.0.2.1", []), "10.1.2.3")
