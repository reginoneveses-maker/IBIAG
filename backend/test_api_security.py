import os
import traceback
import unittest
from unittest.mock import patch, AsyncMock
import httpx
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from mongomock_motor import AsyncMongoMockClient
from api_security import cors_origins_from, documentation_options, validate_jwt_secret, SecurityResponseMiddleware
from safe_errors import install_error_handlers, failure_response
from serve import server_options

with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"api_security_test",
                            "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class ApiConfigurationTests(unittest.TestCase):
    def test_cors_rejects_broad_credentialed_or_non_origin_configuration(self):
        for value in ("*","null","https://*.example.com","https://u:private-canary@example.com",
                      "https://example.com/path","https://example.com?q=1","http://example.com","https://example.com:99999"):
            with self.subTest(origin_type=value.split(':')[0]),self.assertRaises(ValueError) as error:
                cors_origins_from({"CORS_ORIGINS":value})
            self.assertNotIn("private-canary",str(error.exception))

    def test_cors_canonicalizes_explicit_origins_and_loopback_only_http(self):
        self.assertEqual(cors_origins_from({"CORS_ORIGINS":"https://EXAMPLE.com:443/,https://example.com,http://localhost:80,http://[::1]:3000"}),
                         ["https://example.com","http://localhost","http://[::1]:3000"])
        self.assertEqual(cors_origins_from({}),["http://localhost:3000","http://localhost"])

    def test_secret_policy_and_documentation_defaults(self):
        for secret in ("short"," "*32,"x"*32+"\n"):
            with self.assertRaises(ValueError): validate_jwt_secret(secret)
        self.assertEqual(validate_jwt_secret("x"*32),"x"*32)
        self.assertFalse(documentation_options({"DEBUG":"true"})["debug"])
        self.assertIsNone(documentation_options({})["openapi_url"])
        self.assertEqual(documentation_options({"ENABLE_API_DOCS":"true"})["docs_url"],"/docs")
        self.assertFalse(server_options({})["server_header"])
        self.assertFalse(server_options({})["access_log"])


class ApiResponsePolicyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        app=FastAPI()
        install_error_handlers(app)
        app.add_middleware(CORSMiddleware,allow_origins=["https://approved.example"],allow_methods=["POST"],
                           allow_headers=["Authorization","Content-Type"],allow_credentials=False)
        app.add_middleware(SecurityResponseMiddleware,error_response=failure_response,allowed_origins=["https://approved.example"])
        @app.get("/api/broken")
        async def broken(): raise RuntimeError("private-exception-canary")
        @app.get("/api/stream")
        async def stream():
            async def data():
                yield b"partial"
                raise RuntimeError("private-exception-canary")
            return StreamingResponse(data())
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url="http://test")

    async def asyncTearDown(self): await self.client.aclose()

    async def test_preflight_approves_only_explicit_origin_and_headers(self):
        headers={"Origin":"https://approved.example","Access-Control-Request-Method":"POST",
                 "Access-Control-Request-Headers":"authorization,content-type"}
        response=await self.client.options("/api/auth/login",headers=headers)
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.headers["access-control-allow-origin"],"https://approved.example")
        self.assertNotIn("access-control-allow-credentials",response.headers)
        self.assertEqual(response.headers["x-content-type-options"],"nosniff")
        response=await self.client.options("/api/auth/login",headers={**headers,"Origin":"https://other.example"})
        self.assertEqual(response.status_code,400)
        self.assertNotIn("access-control-allow-origin",response.headers)
        response=await self.client.options("/api/auth/login",headers={**headers,"Access-Control-Request-Headers":"x-forged-header"})
        self.assertEqual(response.status_code,400)

    async def test_not_found_and_unhandled_failures_receive_safe_headers_without_exception_escape(self):
        for path,status in (("/api/missing",404),("/api/broken",500)):
            response=await self.client.get(path,headers={"Origin":"https://approved.example"})
            self.assertEqual(response.status_code,status)
            self.assertEqual(response.headers["access-control-allow-origin"],"https://approved.example")
            self.assertEqual(response.headers["cache-control"],"no-store")
            self.assertEqual(response.headers["x-frame-options"],"DENY")
            self.assertIn("default-src 'none'",response.headers["content-security-policy"])
            self.assertNotIn("private-exception-canary",response.text)

    async def test_stream_failure_does_not_escape_with_private_exception_text(self):
        try: await self.client.get("/api/stream")
        except RuntimeError as error:
            self.assertEqual(str(error),"Response stream interrupted")
            self.assertNotIn("private-exception-canary","".join(traceback.format_exception(error)))
        else: self.fail("Stream failure must interrupt the response")

    async def test_download_forces_inert_attachment_without_trusting_stored_mime(self):
        db=AsyncMongoMockClient()["isolated"]
        await db.users.insert_one({"id":"admin","email":"admin@example.com","role":"admin"})
        token=server.create_token("admin","admin@example.com")
        with patch.object(server,"db",db),patch.object(server,"get_object",new_callable=AsyncMock,return_value=(b"<script>active</script>","text/html")):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test") as client:
                response=await client.get("/api/files/test.html",headers={"Authorization":"Bearer "+token})
                self.assertEqual(response.status_code,200,response.text)
                self.assertEqual(response.headers["content-type"],"application/octet-stream")
                self.assertIn("attachment",response.headers["content-disposition"])
                self.assertIn("sandbox",response.headers["content-security-policy"])
                self.assertEqual(response.headers["cache-control"],"no-store")
                self.assertEqual((await client.get("/docs")).status_code,404)
                self.assertEqual((await client.get("/openapi.json")).status_code,404)
