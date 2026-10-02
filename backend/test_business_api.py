"""Exercise the actual API workflow functions without production credentials."""
import ast
import asyncio
import copy
import unittest
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from pymongo.errors import DuplicateKeyError
from business_workflow import normalize_order, normalize_purchase, inventory_balances, validate_balances, linked_finance


class HTTPException(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def matches(record, query):
    for key, expected in query.items():
        value = record.get(key)
        if isinstance(expected, dict):
            if "$in" in expected and value not in expected["$in"]: return False
            if "$lte" in expected and not value <= expected["$lte"]: return False
            if "$gt" in expected and not value > expected["$gt"]: return False
        elif value != expected:
            return False
    return True


class Cursor:
    def __init__(self, records): self.records = records
    async def to_list(self, length): return copy.deepcopy(self.records)


class Collection:
    def __init__(self, records=()):
        self.records = copy.deepcopy(list(records))
        self.guard = asyncio.Lock()
        self.fail_write = False
    def find(self, query, projection=None):
        return Cursor([r for r in self.records if matches(r, query)])
    async def find_one(self, query, projection=None):
        return next((copy.deepcopy(r) for r in self.records if matches(r, query)), None)
    async def insert_one(self, record):
        if self.fail_write: raise RuntimeError("Simulated write failure")
        self.records.append(copy.deepcopy(record))
    async def replace_one(self, query, record):
        if self.fail_write: raise RuntimeError("Simulated write failure")
        for i, r in enumerate(self.records):
            if matches(r, query):
                self.records[i] = copy.deepcopy(record)
                return SimpleNamespace(matched_count=1)
        return SimpleNamespace(matched_count=0)
    async def update_one(self, query, update, upsert=False):
        async with self.guard:
            record = next((r for r in self.records if matches(r, query)), None)
            if record is None and upsert:
                record = {**query, **update.get("$setOnInsert", {})}
                self.records.append(record)
            if record is None: return SimpleNamespace(matched_count=0)
            record.update(copy.deepcopy(update.get("$set", {})))
            for key in update.get("$unset", {}): record.pop(key, None)
            return SimpleNamespace(matched_count=1)
    async def find_one_and_update(self, query, update, return_document=None):
        async with self.guard:
            record = next((r for r in self.records if matches(r, query)), None)
            if record is None: return None
            record.update(copy.deepcopy(update.get("$set", {})))
            return copy.deepcopy(record)


def load_api(db):
    names = {"OrderItem", "SalesOrder", "Purchase", "business_write_lock", "business_snapshot", "version_query", "save_order_workflow", "save_purchase_workflow", "toggle_paid"}
    tree = ast.parse(Path(__file__).with_name("server.py").read_text())
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name in names]
    for node in nodes:
        if isinstance(node, ast.AsyncFunctionDef):
            node.decorator_list = [d for d in node.decorator_list if isinstance(d, ast.Name) and d.id == "asynccontextmanager"]
            node.returns = None
            for arg in node.args.args: arg.annotation = None
            # Depends is irrelevant to direct calls; explicit user is supplied.
            node.args.defaults = [ast.Constant(None) if isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "Depends" else d for d in node.args.defaults]
    env = dict(db=db, BaseModel=BaseModel, Field=Field, ConfigDict=ConfigDict, List=List, Optional=Optional,
               now_iso=lambda: datetime.now(timezone.utc).isoformat(), uuid=uuid, HTTPException=HTTPException, DuplicateKeyError=DuplicateKeyError,
               asynccontextmanager=asynccontextmanager, datetime=datetime, timezone=timezone, timedelta=timedelta,
               ReturnDocument=SimpleNamespace(AFTER=True), normalize_order=normalize_order, normalize_purchase=normalize_purchase,
               inventory_balances=inventory_balances, validate_balances=validate_balances, linked_finance=linked_finance)
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])), "workflow_api", "exec"), env)
    return SimpleNamespace(**env)


class BusinessApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.db = SimpleNamespace(products=Collection([{"id":"p","name":"Açaí","unit":"kg","stock":10}]),
                                 product_offers=Collection([{"id":"o","product_id":"p","active":True,"supplier_id":"s","supplier_name":"Fornecedor"}]),
                                 suppliers=Collection([{"id":"s","name":"Fornecedor"}]), orders=Collection(), purchases=Collection(),
                                 finance=Collection(), workflow_locks=Collection())
        self.api = load_api(self.db)
        self.body = {"id":"order1","customer":"Teste","status":"confirmed","track_stock":True,"order_date":"2026-10-02",
                     "receivable_due_date":"2026-11-02","items":[{"product_id":"p","offer_id":"o","quantity":6,"unit_price":2}]}

    async def test_create_ship_deliver_and_idempotent_payment(self):
        record = await self.api.save_order_workflow(self.api.SalesOrder(**self.body), create=True)
        self.assertEqual(record["version"], 1)
        record = await self.api.save_order_workflow(self.api.SalesOrder(**{**record,"status":"shipped"}))
        record = await self.api.save_order_workflow(self.api.SalesOrder(**{**record,"status":"delivered"}))
        account = await self.api.toggle_paid("order:order1", {"paid":True}, {})
        repeated = await self.api.toggle_paid("order:order1", {"paid":True}, {})
        self.assertEqual(account, repeated)
        products, orders, purchases = await self.api.business_snapshot()
        self.assertEqual(inventory_balances(products, orders, purchases)["p"]["stock"], 4)
        self.assertEqual(len(linked_finance(orders, purchases)), 1)
        self.assertEqual(len(self.db.finance.records), 0)

    async def test_duplicate_create_and_stale_update_rejected(self):
        original = self.api.SalesOrder(**self.body)
        record = await self.api.save_order_workflow(original, create=True)
        with self.assertRaises(HTTPException) as duplicate:
            await self.api.save_order_workflow(original, create=True)
        self.assertEqual(duplicate.exception.status_code, 409)
        await self.api.toggle_paid("order:order1", {"paid":True}, {})
        with self.assertRaises(HTTPException) as stale:
            await self.api.save_order_workflow(self.api.SalesOrder(**record))
        self.assertEqual(stale.exception.status_code, 409)
        self.assertEqual(len(self.db.orders.records), 1)

    async def test_second_order_rejected_without_partial_account_or_stock(self):
        await self.api.save_order_workflow(self.api.SalesOrder(**self.body), create=True)
        with self.assertRaises(HTTPException) as shortage:
            await self.api.save_order_workflow(self.api.SalesOrder(**{**self.body,"id":"order2"}), create=True)
        self.assertEqual(shortage.exception.status_code, 400)
        self.assertEqual(len(self.db.orders.records), 1)
        self.assertEqual(self.db.products.records[0]["stock"], 10)
        self.assertEqual(len(linked_finance(self.db.orders.records, [])), 1)

    async def test_write_failure_leaves_no_movements_and_unlocks(self):
        self.db.orders.fail_write = True
        with self.assertRaises(RuntimeError):
            await self.api.save_order_workflow(self.api.SalesOrder(**self.body), create=True)
        self.assertEqual(self.db.orders.records, [])
        self.assertEqual(linked_finance(self.db.orders.records, []), [])
        self.assertEqual(self.db.workflow_locks.records[0]["locked_until"], "")

    async def test_process_lock_blocks_competing_writer(self):
        async with self.api.business_write_lock():
            with self.assertRaises(HTTPException) as competing:
                async with self.api.business_write_lock(): pass
            self.assertEqual(competing.exception.status_code, 409)
        async with self.api.business_write_lock() as ensure_owned:
            await ensure_owned()

    async def test_purchase_receipt_and_finance_payment_share_source(self):
        body = {"id":"buy1","supplier_id":"s","product_id":"p","product":"Açaí","quantity":5,"unit_price":3,
                "date":"2026-10-02","due_date":"2026-11-02","status":"received","track_stock":True}
        record = await self.api.save_purchase_workflow(self.api.Purchase(**body), create=True)
        await self.api.toggle_paid("purchase:buy1", {"paid":True}, {})
        products, orders, purchases = await self.api.business_snapshot()
        self.assertEqual(inventory_balances(products, orders, purchases)["p"]["stock"], 15)
        self.assertTrue(linked_finance([], purchases)[0]["paid"])
        self.assertEqual(self.db.purchases.records[0]["version"], record["version"]+1)


if __name__ == "__main__": unittest.main()
