import io
import os
import unittest
import zipfile
from unittest.mock import patch
from fastapi import HTTPException, UploadFile
import httpx
from mongomock_motor import AsyncMongoMockClient
import upload_limits

with patch.dict(os.environ, {"MONGO_URL":"mongodb://localhost:27017", "DB_NAME":"upload_test",
                             "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class UploadLimitsTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_empty_and_over_limit(self):
        with patch.object(upload_limits, "MAX_IMPORT_BYTES", 16):
            for data in (b"", b"a" * 17):
                with self.assertRaises(HTTPException) as error:
                    await upload_limits.read_import(UploadFile(io.BytesIO(data), filename="data.csv"))
                self.assertEqual(error.exception.status_code,413)
            self.assertEqual(await upload_limits.read_import(UploadFile(io.BytesIO(b"a" * 16))), b"a" * 16)

    async def test_compressed_workbook_expansion_is_bounded(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("xl/worksheets/sheet1.xml", b"a" * 10000)
        with patch.object(upload_limits, "MAX_EXPANDED_BYTES", 100):
            with self.assertRaises(HTTPException) as error:
                await upload_limits.read_import(UploadFile(io.BytesIO(buffer.getvalue())))
            self.assertEqual(error.exception.status_code,413)

    async def test_all_import_routes_reject_before_parser_or_writes(self):
        db = AsyncMongoMockClient()["isolated"]
        await db.users.insert_one({"id":"admin","email":"test@example.com","role":"admin"})
        token = server.create_token("admin","test@example.com")
        with patch.object(server,"db",db), patch.object(upload_limits,"MAX_IMPORT_BYTES",16), \
             patch.object(server.pd,"read_excel",side_effect=AssertionError("parser must not run")), \
             patch.object(server.pd,"read_csv",side_effect=AssertionError("parser must not run")):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test",
                                        headers={"Authorization":"Bearer "+token}) as client:
                for path in ("/api/leads/import", "/api/portfolio/import-xlsx", "/api/portfolio/restore-commissions", "/api/invoices/parse-xml"):
                    response = await client.post(path,files={"file":("data.xlsx",b"a"*17)})
                    self.assertEqual(response.status_code,413,(path,response.text))
        for collection in ("leads","products","suppliers","product_offers","invoices"):
            self.assertEqual(await db[collection].count_documents({}),0)
