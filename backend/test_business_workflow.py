import copy
import unittest
from business_workflow import normalize_order, normalize_purchase, inventory_balances, validate_balances, linked_finance
from finance_reporting import pending_totals, cashflow_rows


class BusinessWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.products = {"p": {"id": "p", "name": "Açaí", "unit": "kg", "stock": 20}}
        self.offers = {"o": {"id": "o", "product_id": "p", "supplier_id": "s", "supplier_name": "Fornecedor", "active": True}}
        self.suppliers = {"s": {"id": "s", "name": "Fornecedor"}}
        self.order = {"id": "sale", "customer": "Comprador", "status": "draft", "track_stock": True,
                      "items": [{"product_id": "p", "offer_id": "o", "quantity": 5, "unit_price": 2.35, "unit": "kg"}],
                      "order_date": "2026-10-02", "receivable_due_date": "2026-11-02", "total_usd": 0}
        self.purchase = {"id": "buy", "product_id": "p", "supplier_id": "s", "product": "Açaí", "unit": "kg",
                         "quantity": 10, "unit_price": 3.25, "currency": "BRL", "date": "2026-10-02",
                         "due_date": "2026-11-02", "status": "ordered", "track_stock": True, "stock_received": False}

    def sale(self, body, previous=None):
        return normalize_order(body, previous, self.products, self.offers)

    def buy(self, body, previous=None):
        return normalize_purchase(body, previous, self.products, self.suppliers)

    def balance(self, sales=(), purchases=()):
        return inventory_balances(list(self.products.values()), sales, purchases)["p"]

    def test_reservation_shipment_delivery_and_repeat(self):
        draft = self.sale(self.order)
        self.assertEqual(self.balance([draft])["stock_available"], 20)
        confirmed = self.sale({**draft, "status": "confirmed"}, draft)
        self.assertEqual((self.balance([confirmed])["stock"], self.balance([confirmed])["stock_reserved"]), (20, 5))
        shipped = self.sale({**confirmed, "status": "shipped"}, confirmed)
        delivered = self.sale({**shipped, "status": "delivered"}, shipped)
        repeated = self.sale(copy.deepcopy(delivered), delivered)
        self.assertEqual(self.balance([repeated])["stock"], 15)
        self.assertEqual(self.balance([repeated])["stock_reserved"], 0)
        self.assertEqual(len(linked_finance([repeated], [])), 1)

    def test_cancellation_releases_reservation_and_account(self):
        confirmed = self.sale({**self.order, "status": "confirmed"})
        cancelled = self.sale({**confirmed, "status": "cancelled"}, confirmed)
        self.assertEqual(self.balance([cancelled])["stock_available"], 20)
        self.assertEqual(linked_finance([cancelled], []), [])

    def test_two_orders_cannot_oversell(self):
        a = self.sale({**self.order, "status": "confirmed", "items": [{**self.order["items"][0], "quantity": 15}]})
        b = {**a, "id": "sale2"}
        with self.assertRaisesRegex(ValueError, "Estoque insuficiente"):
            validate_balances(inventory_balances(list(self.products.values()), [a, b], []))

    def test_purchase_receipt_payment_and_repeat_stock_once(self):
        ordered = self.buy(self.purchase)
        self.assertEqual(self.balance(purchases=[ordered])["stock"], 20)
        received = self.buy({**ordered, "status": "received"}, ordered)
        paid = self.buy({**received, "status": "paid", "updated_at": "2026-10-02T10:00:00+00:00"}, received)
        repeat = self.buy(copy.deepcopy(paid), paid)
        self.assertEqual(self.balance(purchases=[repeat])["stock"], 30)
        account = linked_finance([], [repeat])[0]
        self.assertEqual((account["id"], account["amount"], account["paid"]), ("purchase:buy", 32.5, True))
        self.assertEqual(account["paid_date"], "2026-10-02T10:00:00+00:00")

    def test_direct_supplier_delivery_has_accounts_without_stock(self):
        sale = self.sale({**self.order, "status": "confirmed", "track_stock": False})
        buy = self.buy({**self.purchase, "status": "received", "track_stock": False})
        self.assertEqual(self.balance([sale], [buy])["stock_available"], 20)
        self.assertEqual(len(linked_finance([sale], [buy])), 2)

    def test_payment_does_not_imply_stock_receipt(self):
        buy = self.buy({**self.purchase, "status": "paid", "updated_at": "2026-10-02T10:00:00+00:00"})
        self.assertFalse(buy["stock_received"])
        self.assertEqual(self.balance(purchases=[buy])["stock"], 20)

    def test_existing_order_can_ship_after_offer_deactivated(self):
        sale = self.sale({**self.order, "status": "confirmed"})
        self.offers["o"]["active"] = False
        shipped = self.sale({**sale, "status": "shipped"}, sale)
        self.assertEqual(shipped["items"], sale["items"])
        with self.assertRaises(ValueError):
            self.sale({**self.order, "status": "confirmed"})

    def test_total_computed_from_items_decimal_rounding(self):
        sale = self.sale({**self.order, "total_usd": 9999, "items": [{**self.order["items"][0], "quantity": 3, "unit_price": 0.335}]})
        self.assertEqual(sale["total_usd"], 1.01)
        buy = self.buy({**self.purchase, "quantity": 3, "unit_price": 0.335, "total": 9999})
        self.assertEqual(buy["total"], 1.01)

    def test_invalid_values_offer_units_and_dates(self):
        for change in [{"quantity": 0}, {"quantity": float("nan")}, {"unit_price": -1}, {"offer_id": "missing"}, {"unit": "ton"}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.sale({**self.order, "items": [{**self.order["items"][0], **change}]})
        with self.assertRaises(ValueError):
            self.sale({**self.order, "status": "confirmed", "receivable_due_date": "2026-02-30"})
        with self.assertRaises(ValueError):
            self.buy({**self.purchase, "supplier_id": "missing"})

    def test_shipped_and_received_cannot_reverse(self):
        shipped = self.sale({**self.order, "status": "shipped"})
        with self.assertRaises(ValueError):
            self.sale({**shipped, "status": "cancelled"}, shipped)
        with self.assertRaises(ValueError):
            self.sale({**shipped, "items": []}, shipped)
        received = self.buy({**self.purchase, "status": "received"})
        with self.assertRaises(ValueError):
            self.buy({**received, "status": "cancelled"}, received)
        with self.assertRaises(ValueError):
            self.buy({**received, "quantity": 12}, received)

    def test_paid_order_cannot_disappear_or_change_party(self):
        sale = {**self.sale({**self.order, "status": "confirmed"}), "finance_paid": True}
        for change in [{"status": "draft"}, {"status": "cancelled"}, {"customer": "Outro"}, {"receivable_due_date": "2026-12-01"}]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.sale({**sale, **change}, sale)

    def test_client_cannot_hide_or_mark_order_paid(self):
        sale = self.sale({**self.order, "deleted_at": "2026-10-02", "finance_paid": True})
        self.assertFalse(sale["finance_paid"])
        self.assertFalse(sale["deleted_at"])

    def test_legacy_and_archived_records_do_not_move_stock(self):
        legacy = {**self.order, "status": "shipped"}
        archived = {**self.sale({**self.order, "status": "shipped"}), "deleted_at": "2026-10-02"}
        self.assertEqual(self.balance([legacy, archived])["stock"], 20)
        self.assertEqual(linked_finance([legacy, archived], []), [])

    def test_accounts_remain_separate_by_currency(self):
        sale = self.sale({**self.order, "status": "confirmed"})
        buy = self.buy(self.purchase)
        totals = {row["currency"]: row for row in pending_totals(linked_finance([sale], [buy]))}
        self.assertEqual(totals["USD"]["receivable"], 11.75)
        self.assertEqual(totals["BRL"]["payable"], 32.5)


if __name__ == "__main__":
    unittest.main()
