"""Bounded imports before writes, repeated with disposable MongoDB in CI."""
import os
import unittest
import uuid
from urllib.parse import urlparse
from unittest.mock import patch, AsyncMock
import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from mongomock_motor import AsyncMongoMockClient
from test_tabular_imports import workbook_bytes
import tabular_imports as tables

with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"table_http_test",
                            "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class TabularImportHttpTests(unittest.IsolatedAsyncioTestCase):
    def make_database(self): return AsyncMongoMockClient()["isolated"]

    async def asyncSetUp(self):
        self.db=self.make_database()
        self.db_patch=patch.object(server,"db",self.db);self.db_patch.start()
        await self.db.users.insert_many([{"id":"admin","role":"admin"},{"id":"member","role":"user"},{"id":"other","role":"user"}])
        await self.db.leads.insert_one({"id":"keep","company":"Import CSV","owner_id":"other","phone":"0099"})
        for name in ("products","suppliers","product_offers","documents","settings"):
            await self.db[name].insert_one({"id":"keep","name":"Preserve existing","marker":"keep"})
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose();self.db_patch.stop()

    def headers(self,user): return {"Authorization":"Bearer "+server.create_token(user,"test@example.com")}

    async def snapshot(self):
        return {name:await self.db[name].find({}).to_list(None) for name in
                ("leads","products","suppliers","product_offers","documents","settings","orders","purchases","invoices")}

    async def upload(self,path,raw,name,user="admin",**kwargs):
        return await self.client.post("/api"+path,files={"file":(name,raw)},headers=self.headers(user),**kwargs)

    async def test_csv_and_xlsx_imports_preserve_phones_ownership_and_deduplication(self):
        for name,raw in (("leads.csv",b"Company,Phone\nImport CSV,001234\n"),
                         ("leads.xlsx",workbook_bytes([["Company","Phone"],["Import XLSX","001234"]]))):
            response=await self.upload("/leads/import",raw,name,"member")
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["imported"],1)
            response=await self.upload("/leads/import",raw,name,"member")
            self.assertEqual(response.status_code,200,response.text)
            self.assertEqual(response.json()["imported"],0)
            self.assertEqual(response.json()["updated"]+response.json()["skipped"],1)
        own=await self.db.leads.find({"owner_id":"member"}).to_list(None)
        self.assertEqual(len(own),2)
        self.assertEqual({row["phone"] for row in own},{"001234"})
        self.assertEqual((await self.db.leads.find_one({"id":"keep"}))["phone"],"0099")

    async def test_portfolio_and_commission_header_three_remain_functional(self):
        raw=workbook_bytes([["Intro"],[],["Produto","Fornecedor","Comissão","Preço Exportação"],
                            ["Synthetic Acai","Synthetic Supplier","10%","USD 12/kg"]],"IBIAG")
        response=await self.upload("/portfolio/import-xlsx",raw,"portfolio.xlsx",params={"replace":"false"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["source_rows"],1)
        offer=await self.db.product_offers.find_one({"product_name":"Synthetic Acai"})
        self.assertAlmostEqual(offer["commission"],0.1)
        raw=workbook_bytes([["Intro"],[],["Produto","Fornecedor","Comissão"],
                            ["Synthetic Acai","Synthetic Supplier","15%"]],"IBIAG")
        response=await self.upload("/portfolio/restore-commissions",raw,"commissions.xlsx",params={"dry_run":"false"})
        self.assertEqual(response.status_code,200,response.text)
        after=await self.db.product_offers.find_one({"id":offer["id"]})
        self.assertAlmostEqual(after["commission"],0.15)
        for field in ("id","product_id","supplier_id","export_price_text"):
            self.assertEqual(after[field],offer[field])
        self.assertIsNotNone(await self.db.products.find_one({"id":"keep"}))

    async def test_oversized_tables_do_not_replace_or_update_any_existing_data(self):
        before=await self.snapshot()
        crm=b"Company\nA\nB\n"
        portfolio=workbook_bytes([["Intro"],[],["Produto","Fornecedor","Comissão"],["A","X","1%"],["B","Y","2%"]],"IBIAG")
        with patch.object(tables,"MAX_ROWS",1),patch.object(tables,"load_workbook",side_effect=AssertionError("loader must not run")) as loader:
            for path,raw,name in (("/leads/import",crm,"data.csv"),("/portfolio/import-xlsx",portfolio,"data.xlsx"),
                                  ("/portfolio/restore-commissions",portfolio,"data.xlsx")):
                response=await self.upload(path,raw,name)
                self.assertEqual(response.status_code,413,(path,response.text))
            loader.assert_not_called()
        self.assertEqual(await self.snapshot(),before)

    async def test_malformed_imports_have_generic_errors_and_never_delete_data(self):
        before=await self.snapshot()
        for path,name,raw in (("/leads/import","data.csv",b'Company\n"private-canary'),
                              ("/portfolio/import-xlsx","data.xlsx",b"private-canary"),
                              ("/portfolio/restore-commissions","data.xlsx",b"private-canary")):
            response=await self.upload(path,raw,name)
            self.assertEqual(response.status_code,400,response.text)
            self.assertEqual(response.json(),{"detail":tables.INVALID_TABLE})
        self.assertEqual(await self.snapshot(),before)

    async def test_unauthorized_imports_never_invoke_table_reader(self):
        with patch.object(server,"read_table",new_callable=AsyncMock,side_effect=AssertionError("reader must not run")) as reader:
            for path in ("/leads/import","/portfolio/import-xlsx","/portfolio/restore-commissions"):
                response=await self.client.post("/api"+path,files={"file":("data.xlsx",b"unused")})
                self.assertEqual(response.status_code,401)
            for path in ("/portfolio/import-xlsx","/portfolio/restore-commissions"):
                response=await self.upload(path,b"unused","data.xlsx","member")
                self.assertEqual(response.status_code,403)
            reader.assert_not_awaited()


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"),"Disposable MongoDB not configured")
class TabularImportMongoTests(TabularImportHttpTests):
    def make_database(self):
        url=os.environ["TEST_MONGO_URL"]
        if urlparse(url).hostname not in {"localhost","127.0.0.1","mongo"}:
            raise RuntimeError("Only disposable local MongoDB is allowed")
        self.mongo=AsyncIOMotorClient(url,serverSelectionTimeoutMS=5000)
        self.database_name="ibiag_test_tables_"+uuid.uuid4().hex
        return self.mongo[self.database_name]

    async def asyncTearDown(self):
        try: await super().asyncTearDown()
        finally:
            await self.mongo.drop_database(self.database_name)
            self.mongo.close()
