import os
import unittest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone, timedelta
import httpx
from mongomock_motor import AsyncMongoMockClient

with patch.dict(os.environ,{"MONGO_URL":"mongodb://localhost:27017","DB_NAME":"erp_permissions_test",
                            "JWT_SECRET":"test-secret-only-32-characters-long"}):
    import server


class ErpPermissionsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=AsyncMongoMockClient()["isolated"]
        await self.db.users.insert_many([{"id":"admin","email":"admin@example.com","role":"admin"},
                                        {"id":"member","email":"member@example.com","role":"user"}])
        self.patch=patch.object(server,"db",self.db);self.patch.start()
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test")

    async def asyncTearDown(self):
        await self.client.aclose();self.patch.stop()

    def headers(self,user): return {"Authorization":"Bearer "+server.create_token(user,user+"@example.com")}

    async def test_member_cannot_read_sensitive_company_datasets(self):
        for path in ("/finance","/finance/cashflow","/invoices","/orders","/purchases","/contracts","/gestao/stats","/prices","/product-offers"):
            response=await self.client.get("/api"+path,headers=self.headers("member"))
            self.assertEqual(response.status_code,403,(path,response.text))

    async def test_member_mutations_are_rejected_before_writes(self):
        routes=[("POST","/finance"),("PATCH","/finance/id/toggle-paid"),("DELETE","/finance/id"),
                ("POST","/invoices"),("DELETE","/invoices/id"),("POST","/invoices/parse-xml"),
                ("POST","/orders"),("PUT","/orders/id"),("DELETE","/orders/id"),("POST","/orders/id/restore"),
                ("POST","/purchases"),("PUT","/purchases/id"),("DELETE","/purchases/id"),("POST","/purchases/id/restore"),
                ("POST","/contracts"),("PUT","/contracts/id"),("DELETE","/contracts/id"),
                ("POST","/suppliers"),("PUT","/suppliers/id"),("DELETE","/suppliers/id"),
                ("POST","/specs"),("PUT","/specs/id"),("DELETE","/specs/id"),
                ("POST","/certifications"),("PUT","/certifications/id"),("DELETE","/certifications/id"),
                ("POST","/prices"),("PUT","/prices/id"),("DELETE","/prices/id"),
                ("POST","/product-offers"),("PUT","/product-offers/id"),("DELETE","/product-offers/id")]
        for method,path in routes:
            response=await self.client.request(method,"/api"+path,headers={**self.headers("member"),"X-User-Role":"admin"},json={"role":"admin"})
            self.assertEqual(response.status_code,403,(path,response.text))
        for name in ("finance","invoices","orders","purchases","contracts","suppliers","specs","certifications","prices","product_offers"):
            self.assertEqual(await self.db[name].count_documents({}),0,name)

    async def test_admin_can_create_pay_and_read_finance(self):
        response=await self.client.post("/api/finance",headers=self.headers("admin"),json={"description":"Account","amount":12.5,"currency":"USD","due_date":"2026-10-18"})
        self.assertEqual(response.status_code,200,response.text)
        entry=response.json()
        paid=await self.client.patch("/api/finance/"+entry["id"]+"/toggle-paid",headers=self.headers("admin"),json={"paid":True})
        self.assertEqual(paid.status_code,200,paid.text)
        self.assertTrue(paid.json()["paid"])
        for path in ("/finance","/finance/cashflow","/invoices","/orders","/purchases","/contracts","/gestao/stats","/prices","/product-offers"):
            self.assertEqual((await self.client.get("/api"+path,headers=self.headers("admin"))).status_code,200,path)

    async def test_dashboard_does_not_query_or_expose_financial_data_for_member(self):
        with patch.object(server,"all_finance_entries",new_callable=AsyncMock) as ledger:
            response=await self.client.get("/api/dashboard/stats",headers=self.headers("member"))
        self.assertEqual(response.status_code,200,response.text)
        ledger.assert_not_called()
        data=response.json()
        self.assertFalse(data["can_view_erp"])
        for field in ("invoices","orders_pending","finance_receivable","finance_payable","contracts_expiring"):
            self.assertIsNone(data[field])
        self.assertEqual(data["finance_by_currency"],[])

    async def test_database_role_overrides_token_claims_and_existing_sessions(self):
        token=server.jwt.encode({"sub":"member","role":"admin","exp":datetime.now(timezone.utc)+timedelta(hours=1)},server.JWT_SECRET,algorithm=server.JWT_ALG)
        self.assertEqual((await self.client.get("/api/finance",headers={"Authorization":"Bearer "+token})).status_code,403)
        headers=self.headers("admin")
        await self.db.users.update_one({"id":"admin"},{"$set":{"role":"user"}})
        self.assertEqual((await self.client.get("/api/finance",headers=headers)).status_code,403)

    async def test_financial_legal_and_unknown_documents_are_private_even_to_old_uploader(self):
        private=[]
        for index,category in enumerate(("Financeiro & Fiscal","Societário","finance","Unknown Restricted")):
            path=f"{server.APP_NAME}/uploads/member/{index}.pdf";private.append(path)
            await self.db.documents.insert_one({"id":str(index),"title":"Private","file_name":"private.pdf","file_path":path,"category":category})
        contract_path=f"{server.APP_NAME}/uploads/member/contract.pdf";private.append(contract_path)
        await self.db.contracts.insert_one({"id":"contract","title":"Legal","file_path":contract_path})
        await self.db.documents.insert_one({"id":"alias","title":"General alias","file_name":"alias.pdf","file_path":contract_path})
        with patch.object(server,"get_object",new_callable=AsyncMock,return_value=(b"%PDF-private","application/pdf")) as storage:
            for path in private:
                self.assertEqual((await self.client.get("/api/files/"+path,headers=self.headers("member"))).status_code,404)
            storage.assert_not_called()
            self.assertEqual((await self.client.get("/api/files/"+contract_path,headers=self.headers("admin"))).status_code,200)
        self.assertEqual((await self.client.get("/api/documents",headers=self.headers("member"))).json(),[])
        self.assertEqual(len((await self.client.get("/api/documents",headers=self.headers("admin"))).json()),5)

    async def test_member_can_manage_own_crm_but_cannot_publish_company_documents(self):
        headers=self.headers("member")
        lead=await self.client.post("/api/leads",headers=headers,json={"company":"Owned"})
        self.assertEqual(lead.status_code,200,lead.text)
        path=f"{server.APP_NAME}/uploads/member/test.pdf"
        with patch.object(server,"get_object",new_callable=AsyncMock,return_value=(b"%PDF","application/pdf")):
            own=await self.client.post("/api/documents",headers=headers,json={"title":"Owned doc","file_name":"test.pdf","file_path":path,"lead_id":lead.json()["id"]})
            self.assertEqual(own.status_code,200,own.text)
            shared=await self.client.post("/api/documents",headers=headers,json={"title":"Publish","file_name":"test.pdf","file_path":path})
            self.assertEqual(shared.status_code,403,shared.text)
        for path in ("/products","/suppliers","/tasks"):
            self.assertEqual((await self.client.get("/api"+path,headers=headers)).status_code,200,path)
