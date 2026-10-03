import os, unittest
from unittest.mock import patch
import httpx
from mongomock_motor import AsyncMongoMockClient
with patch.dict(os.environ, {"MONGO_URL":"mongodb://localhost:27017", "DB_NAME":"price_test", "JWT_SECRET":"price-test-only-secret-32-characters"}):
    import server

class PricingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db=AsyncMongoMockClient()["prices"]
        self.dbpatch=patch.object(server,"db",self.db); self.dbpatch.start()
        await self.db.users.insert_one({"id":"u","email":"price@test.com","role":"admin"})
        await self.db.suppliers.insert_many([{"id":"s1","name":"Bona Fruit"},{"id":"s2","name":"Outro"}])
        await self.db.products.insert_one({"id":"p1","name":"Açaí liofilizado"})
        await self.db.product_offers.insert_many([
            {"id":"o1","product_id":"p1","product_name":"Açaí liofilizado","supplier_id":"s1","unit":"kg","active":True},
            {"id":"inactive","product_id":"p1","supplier_id":"s1","active":False}])
        self.client=httpx.AsyncClient(transport=httpx.ASGITransport(app=server.app),base_url="http://test",headers={"Authorization":"Bearer "+server.create_token("u","price@test.com")})
        self.body={"product_name":"Açaí","offer_id":"o1","product_id":"p1","supplier_id":"s1","quantity":1000,"supplier_price":17.5,"margin_pct":15,"taxes":[{"pct":6}],"exchange_rate":5.2}
    async def asyncTearDown(self):
        await self.client.aclose(); self.dbpatch.stop()
    async def test_supplier_filter_and_save_reload_edit_keep_quantity_and_totals(self):
        offers=await self.client.get("/api/product-offers",params={"supplier_id":"s1","active":"true"})
        self.assertEqual([x["id"] for x in offers.json()],["o1"])
        r=await self.client.post("/api/prices",json={**self.body,"supplier_price":"17,50","quantity":"1.000","supplier_name":"Errado","supplier_total":2})
        self.assertEqual(r.status_code,200,r.text); saved=r.json()
        self.assertEqual(saved["supplier_total"],17500);self.assertEqual(saved["quantity"],1000)
        self.assertEqual(saved["product_name"],"Açaí liofilizado");self.assertEqual(saved["supplier_name"],"Bona Fruit")
        self.assertEqual(saved["sell_price_brl"],22.1519);self.assertEqual(saved["sale_total_brl"],22151.90)
        self.assertEqual(saved["tax_total"],1329.11);self.assertEqual(saved["profit_total"],3322.79)
        loaded=(await self.client.get("/api/prices")).json()[0];self.assertEqual(loaded,saved)
        updated=await self.client.put('/api/prices/'+saved['id'],json={**saved,"quantity":500})
        self.assertEqual(updated.status_code,200,updated.text);self.assertEqual(updated.json()["supplier_total"],8750)
    async def test_fractional_quantity_markup_extras_and_usd(self):
        r=await self.client.post("/api/prices/calculate",json={**self.body,"quantity":2.5,"margin_mode":"markup","margin_pct":20,"supplier_price":10,"extras":[{"value":"2,50"}],"taxes":[{"pct":10}],"currency":"USD","exchange_rate":5})
        self.assertEqual(r.status_code,200,r.text);p=r.json()
        self.assertEqual(p["cost_total"],31.25);self.assertEqual(p["sell_price_brl"],16.6667)
        self.assertEqual(p["sale_total_brl"],41.67);self.assertEqual(p["sale_total_usd"],8.33)
    async def test_invalid_quantities_percentages_and_mismatched_offers_are_rejected(self):
        for change in [{"quantity":0},{"quantity":-1},{"quantity":"NaN"},{"supplier_price":-1},{"extras":[{"value":-1}]},{"margin_pct":94},{"taxes":[{"pct":100}]},{"supplier_id":"s2"},{"product_id":"other"},{"offer_id":"inactive"},{"currency":"USD","exchange_rate":0}]:
            with self.subTest(change=change):
                r=await self.client.post("/api/prices",json={**self.body,**change})
                self.assertIn(r.status_code,[400,422],r.text)
        self.assertEqual(await self.db.prices.count_documents({}),0)
    async def test_legacy_unit_text_and_invalid_saved_margin_remain_reviewable(self):
        await self.db.prices.insert_many([
            {"id":"old","product_name":"Legado","unit":"kg 1000","supplier_price":17.5,"taxes_pct":0,"margin_pct":0},
            {"id":"bad","product_name":"Margem antiga","unit":"kg","supplier_price":10,"margin_pct":100,"sell_price_brl":10}])
        rows={x["id"]:x for x in (await self.client.get("/api/prices")).json()}
        self.assertEqual(rows["old"]["quantity"],1000);self.assertEqual(rows["old"]["unit"],"kg");self.assertEqual(rows["old"]["supplier_total"],17500)
        self.assertTrue(rows["bad"]["calculation_error"])
        corrected = await self.client.put("/api/prices/bad", json={**rows["bad"], "margin_pct":15})
        self.assertEqual(corrected.status_code,200,corrected.text)
        self.assertEqual(corrected.json()["calculation_error"],"")
        self.assertEqual((await self.db.prices.find_one({"id":"old"}))["unit"],"kg 1000")
    async def test_anonymous_calculation_and_price_listing_require_login(self):
        for method,path in [('get','/api/prices'),('post','/api/prices/calculate')]:
            r=await self.client.request(method,path,json=self.body if method=='post' else None,headers={"Authorization":""})
            self.assertEqual(r.status_code,401)
