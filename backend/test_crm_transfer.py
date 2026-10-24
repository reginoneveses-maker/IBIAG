import unittest
from crm_transfer import build_crm_transfer

class CRMTransferTests(unittest.TestCase):
    def test_explicit_fields_only_without_inferred_contacts_or_commercial_values(self):
        source=[{"id":"a","company":"Empresa","country":"Portugal","contact_name":"Ana","email":"ana@example.test",
                 "owner_id":"private","notes":"private","decision_maker_email":"unconfirmed@example.test","deal_value":900}]
        result=build_crm_transfer(source)
        self.assertEqual(result["companies"][0]["contact"]["email"],"ana@example.test")
        self.assertNotIn("private",str(result))
        self.assertNotIn("unconfirmed",str(result))
        self.assertNotIn("900",str(result))
        self.assertEqual(source[0]["owner_id"],"private")
    def test_duplicate_empty_and_oversized_identifiers_rejected(self):
        for source in [[{"id":"","company":"A"}],[{"id":"x","company":"A"},{"id":"x","company":"B"}],
                       [{"id":"x","company":"A"*181}],[{"id":"x","company":"A","email":5}],{}]:
            with self.subTest(source=source),self.assertRaises(ValueError):build_crm_transfer(source)
    def test_no_stage_currency_or_product_is_silently_translated(self):
        result=build_crm_transfer([{"id":"a","company":"A","stage":"won","deal_value":1,"product_interest":"Acai"}])
        self.assertNotIn("stage",str(result));self.assertNotIn("product",str(result))
        self.assertEqual(result["companies"][0]["contact"],{"name":"","email":"","phone":""})
