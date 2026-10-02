"""Integration checks against a disposable MongoDB provided by CI."""
import asyncio
import os
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse
from bson import ObjectId
from pymongo import MongoClient
from motor.motor_asyncio import AsyncIOMotorClient
from backup import create_backup, restore_backup
from test_business_api import load_api, HTTPException


@unittest.skipUnless(os.environ.get("TEST_MONGO_URL"), "MongoDB de testes não configurado")
class MongoIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.url=os.environ["TEST_MONGO_URL"]
        if urlparse(self.url).hostname not in {"localhost","127.0.0.1","mongo"}:
            raise RuntimeError("Testes permitidos apenas no MongoDB local descartável")
        self.client=AsyncIOMotorClient(self.url,serverSelectionTimeoutMS=5000)
        self.name="ibiag_test_"+uuid.uuid4().hex
        self.target_name="ibiag_test_restore_"+uuid.uuid4().hex
        self.db=self.client[self.name]
        await self.db.products.insert_one({"id":"p","name":"Açaí","unit":"kg","stock":10})
        await self.db.product_offers.insert_one({"id":"o","product_id":"p","active":True,"supplier_id":"s","supplier_name":"Fornecedor"})
        await self.db.suppliers.insert_one({"id":"s","name":"Fornecedor"})
        self.api=load_api(self.db)
        self.body={"id":"sale","customer":"TESTE DESCARTÁVEL","status":"confirmed","track_stock":True,"order_date":"2026-10-02","receivable_due_date":"2026-11-02","items":[{"product_id":"p","offer_id":"o","quantity":6,"unit_price":2}]}

    async def asyncTearDown(self):
        await self.client.drop_database(self.name)
        await self.client.drop_database(self.target_name)
        self.client.close()

    async def test_real_database_create_ship_pay_and_repeat(self):
        record=await self.api.save_order_workflow(self.api.SalesOrder(**self.body),create=True)
        record=await self.api.save_order_workflow(self.api.SalesOrder(**{**record,"status":"shipped"}))
        paid=await self.api.toggle_paid("order:sale",{"paid":True},{})
        repeated=await self.api.toggle_paid("order:sale",{"paid":True},{})
        self.assertEqual(paid,repeated)
        products,orders,purchases=await self.api.business_snapshot()
        self.assertEqual(self.api.inventory_balances(products,orders,purchases)["p"]["stock"],4)
        self.assertEqual(await self.db.orders.count_documents({}),1)
        self.assertEqual(await self.db.finance.count_documents({}),0)

    async def test_real_lock_prevents_competing_reservations(self):
        results=await asyncio.gather(
            self.api.save_order_workflow(self.api.SalesOrder(**self.body),create=True),
            self.api.save_order_workflow(self.api.SalesOrder(**{**self.body,"id":"sale2"}),create=True),
            return_exceptions=True)
        self.assertEqual(sum(isinstance(x,dict) for x in results),1)
        self.assertEqual(sum(isinstance(x,HTTPException) for x in results),1)
        products,orders,purchases=await self.api.business_snapshot()
        self.assertEqual(self.api.inventory_balances(products,orders,purchases)["p"]["stock_available"],4)

    async def test_real_gridfs_backup_and_isolated_restore(self):
        oid=ObjectId()
        await self.db["ibiag_files.files"].insert_one({"_id":oid,"filename":"test.pdf","length":7,"chunkSize":4})
        await self.db["ibiag_files.chunks"].insert_many([{"files_id":oid,"n":0,"data":b"\x00\xffAB"},{"files_id":oid,"n":1,"data":b"CDE"}])
        await self.db["ibiag_files.chunks"].create_index([("files_id",1),("n",1)],unique=True)
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ,{"MONGO_URL":self.url,"DB_NAME":self.name,"RESTORE_MONGO_URL":self.url}):
            archive=await asyncio.to_thread(create_backup,folder)
            result=await asyncio.to_thread(restore_backup,archive,self.target_name,True)
        self.assertTrue(result["restored"])
        parts=await self.client[self.target_name]["ibiag_files.chunks"].find({"files_id":oid}).sort("n",1).to_list(None)
        self.assertEqual(b"".join(x["data"] for x in parts),b"\x00\xffABCDE")
        indexes=await self.client[self.target_name]["ibiag_files.chunks"].index_information()
        self.assertTrue(indexes["files_id_1_n_1"]["unique"])
