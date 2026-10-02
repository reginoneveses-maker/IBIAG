import unittest
from document_categories import normalize_document, matches_document, validate_classification
from finance_reporting import month_keys, cashflow_rows, pending_totals

class DocumentTests(unittest.TestCase):
    def test_legacy_sections_and_central_area_agree(self):
        doc = {"category":"pop", "title":"Manual", "file_name":"manual.pdf"}
        self.assertEqual(normalize_document(doc)["category"], "Qualidade & Compliance")
        self.assertTrue(matches_document(doc, "pop"))
        self.assertTrue(matches_document(doc, "Qualidade & Compliance"))
        self.assertFalse(matches_document(doc, "pop_signed"))

    def test_real_imported_titles_appear_in_sections(self):
        doc = {"category":"Qualidade & Compliance", "file_name":"POP-CQ-CATUP v.04 CÓPIA CONTROLADA.pdf"}
        self.assertTrue(matches_document(doc, "pop"))
        self.assertFalse(matches_document(doc, "pop_signed"))
        marketing = {"category":"Clientes & Comercial", "file_name":"Ibiag Ingredients Presentation 2026.pdf"}
        self.assertTrue(matches_document(marketing, "marketing"))

    def test_organic_certificate_not_assumed_to_belong_to_ibiag(self):
        doc = {"category":"Qualidade & Compliance", "title":"Organic certificate supplier"}
        self.assertFalse(matches_document(doc, "ibiag_organic"))

    def test_trash_never_appears_in_any_active_view(self):
        doc={"category":"pop", "deleted_at":"2026-10-02"}
        self.assertFalse(matches_document(doc))
        self.assertFalse(matches_document(doc,"pop"))

    def test_invalid_classification_rejected(self):
        with self.assertRaises(ValueError):validate_classification("Unknown","")
        with self.assertRaises(ValueError):validate_classification("Produtos","fake")

class FinanceTests(unittest.TestCase):
    def test_currencies_never_added_together(self):
        entries=[{"kind":"receivable","amount":100,"currency":"USD","due_date":"2026-10-01"},
                 {"kind":"receivable","amount":300,"currency":"BRL","due_date":"2026-10-01"},
                 {"kind":"payable","amount":40,"currency":"USD","due_date":"2026-10-01"}]
        self.assertEqual(cashflow_rows(entries,[],["2026-10"],"USD")[0]["balance"],60)
        self.assertEqual(cashflow_rows(entries,[],["2026-10"],"BRL")[0]["balance"],300)
        self.assertEqual(pending_totals(entries),[{"currency":"BRL","receivable":300,"payable":0},
                                                 {"currency":"USD","receivable":100,"payable":40}])

    def test_payment_date_is_distinct_from_due_date(self):
        entries=[{"kind":"receivable","amount":100,"currency":"BRL","due_date":"2026-09-30",
                  "paid":True,"paid_date":"2026-10-02"}]
        september,october=cashflow_rows(entries,[],["2026-09","2026-10"])
        self.assertEqual(september["receivable"],100)
        self.assertEqual(september["received"],0)
        self.assertEqual(october["received"],100)

    def test_cancelled_entries_ignored_and_nfe_is_brl(self):
        entries=[{"kind":"receivable","amount":1000,"currency":"USD","due_date":"2026-10-01","cancelled":True}]
        invoices=[{"kind":"saida","total":400,"issue_date":"2026-10-02"}]
        self.assertEqual(cashflow_rows(entries,invoices,["2026-10"],"USD")[0]["nf_saida"],0)
        self.assertEqual(cashflow_rows(entries,invoices,["2026-10"],"BRL")[0]["nf_saida"],400)
        self.assertEqual(pending_totals(entries),[])

if __name__ == "__main__":unittest.main()


class CashflowPeriodTests(unittest.TestCase):
    def test_future_months_cross_year(self):
        from datetime import date
        self.assertEqual(month_keys(date(2026, 12, 2), 3, "forecast"), ["2026-12", "2027-01", "2027-02"])

    def test_history_crosses_year(self):
        from datetime import date
        self.assertEqual(month_keys(date(2026, 1, 2), 3), ["2025-11", "2025-12", "2026-01"])

    def test_invalid_period(self):
        from datetime import date
        with self.assertRaises(ValueError): month_keys(date(2026, 1, 2), 12, "invalid")
