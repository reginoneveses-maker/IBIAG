"""Denomination validation, immutable currency and legacy USD snapshot parity."""
import copy
import unittest
from sale_currency import sale_amount, sale_fields
from commercial_invoices import commercial_snapshot
from business_workflow import normalize_order, linked_finance
import test_business_workflow as fixtures

class SaleCurrencyTests(unittest.TestCase):
 def test_invalid_or_mixed_denominations_cannot_be_read_as_money(self):
  for record in ({"currency":"JPY","total_amount":1},{"currency":"EUR","total_usd":2,"total_amount":10},{"currency":"EUR"},{"currency":"USD","total_usd":2,"total_amount":3},{"currency":"EUR","total_amount":float("nan")},{"currency":"EUR","total_amount":-1}):
   with self.subTest(record=record),self.assertRaises(ValueError):sale_amount(record)
 def test_currency_is_not_mutable_and_finance_uses_the_same_amount(self):
  f=fixtures.BusinessWorkflowTests();f.setUp()
  for currency in ("USD","BRL","EUR"):
   body={**f.order,"currency":currency,"items":[{"product_id":"p","offer_id":"o","quantity":5,"unit_price":2.35,"unit":"kg"}],"status":"confirmed","receivable_due_date":"2099-12-31"}
   normalized=normalize_order(body,None,f.products,f.offers)
   self.assertEqual(float(sale_amount(normalized)),11.75)
   self.assertEqual(linked_finance([normalized],[])[0]["currency"],currency)
   for other in ("USD","BRL","EUR"):
    if other!=currency:
     with self.assertRaises(ValueError):normalize_order({**normalized,"currency":other},normalized,f.products,f.offers)
   snapshot=commercial_snapshot({**normalized,"incoterm":"EXW"})
   if currency=="USD":
    self.assertNotIn("total_amount",snapshot)
    legacy=copy.deepcopy(normalized);legacy.pop("currency")
    self.assertEqual(commercial_snapshot({**legacy,"incoterm":"EXW"}),snapshot)
   else:
    self.assertEqual(snapshot["total_usd"],0)
    self.assertEqual(snapshot["total_amount"],11.75)
