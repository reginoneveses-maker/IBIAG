import unittest
from unittest.mock import patch
import buyer_discovery as discovery
from test_buyer_discovery import business_page

class BuyerQualificationTests(unittest.TestCase):
    def test_negative_and_hypothetical_claims_are_not_verified(self):
        for relationship,clause in [('seller','We do not supply Acerola.'),('seller','We no longer manufacture Acerola.'),('user','Our drink does not contain Acerola.'),('user','Acerola can be used in food ingredients.'),('user','Our drinks may contain Acerola.'),('user','Não utilizamos Acerola em nossos ingredientes.')]:
            with self.subTest(clause=clause):
                page=business_page(relationship=relationship)
                page['markdown']='Acme Ingredients is a food manufacturer. '+clause
                page['json']['product_quote']=clause
                self.assertIsNone(discovery._verified_business({'url':'https://acme.test/product'},page,'Acerola','Portugal'))
    def test_positive_evidence_does_not_claim_purchase(self):
        for relationship,qualification in [('seller','seller_only'),('user','ingredient_user')]:
            result=discovery._verified_business({'url':'https://acme.test/product'},business_page(relationship=relationship),'Acerola','Portugal')
            self.assertEqual(result['buyer_qualification'],qualification)
            self.assertFalse(result['purchasing_verified'])
    def test_company_domain_is_canonical_and_lookalikes_remain_distinct(self):
        self.assertEqual(discovery._extract_domain('https://WWW.Example.com.:443/a?ref=1'),'example.com')
        self.assertNotEqual(discovery._extract_domain('https://example.com.evil.test/a'),'example.com')
    def test_duplicate_default_ports_and_trailing_dot_return_one_company(self):
        rows=[{'url':'https://example.com/a','title':'Acerola supplier'},{'url':'https://www.example.com.:443/b','title':'Acerola supplier'}]
        with patch.object(discovery,'_search',return_value=rows),patch.object(discovery,'_scrape_business',return_value=business_page()):
            self.assertEqual(len(discovery.discover_buyers('Acerola','Portugal')),1)
    def test_negative_ai_excerpt_does_not_override_published_sentence(self):
        page=business_page()
        page['markdown']='Acme Ingredients is a food manufacturer. We do not supply Acerola.'
        page['json']['product_quote']='supply Acerola'
        self.assertIsNone(discovery._verified_business({'url':'https://acme.test/product'},page,'Acerola','Portugal'))
    def test_without_other_ingredient_does_not_discard_real_use(self):
        for clause in ['Our drink contains Acerola without sugar.','We not only supply Acerola but also Mango.']:
            page=business_page()
            page['markdown']='Acme Ingredients is a food manufacturer. '+clause
            page['json']['product_quote']=clause
            page['json']['relationship']='user' if 'drink' in clause else 'seller'
            self.assertIsNotNone(discovery._verified_business({'url':'https://acme.test/product'},page,'Acerola','Portugal'))
