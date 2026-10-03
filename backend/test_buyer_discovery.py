import unittest
from unittest.mock import patch, Mock
import buyer_discovery as discovery

class BuyerDiscoveryTests(unittest.TestCase):
    def test_v1_and_v2_results_supported(self):
        item={"url":"https://example.com","title":"Example ingredient importer"}
        for payload in [{"success":True,"data":[item]},{"success":True,"data":{"web":[item]}},{"web":[item]}]:
            with self.subTest(payload=payload), patch.object(discovery,"FIRECRAWL_KEY","test-only"),patch.object(discovery.requests,"post",return_value=Mock(json=lambda:payload,raise_for_status=lambda:None)):
                self.assertEqual(discovery._search("example"),[item])
    def test_invalid_provider_response_and_missing_configuration(self):
        with patch.object(discovery,"FIRECRAWL_KEY",""):
            with self.assertRaisesRegex(RuntimeError,"não configurada"): discovery._search("example")
        with patch.object(discovery,"FIRECRAWL_KEY","test-only"),patch.object(discovery.requests,"post",return_value=Mock(json=lambda:{"success":False},raise_for_status=lambda:None)):
            with self.assertRaises(RuntimeError): discovery._search("example")
    def test_linkedin_lookalike_domain_rejected(self):
        self.assertEqual(discovery._linkedin([{"url":"https://linkedin.com.attacker.test/in/person"}]),"")
        self.assertEqual(discovery._linkedin([{"url":"https://www.linkedin.com/in/person"}]),"https://www.linkedin.com/in/person")
    def test_accented_product_normalization(self):
        self.assertEqual(discovery._normalize("Açaí em pó"), "acai em po")
        self.assertEqual(discovery._normalize("Guaraná"), "guarana")

    def test_discovery_expands_raw_candidate_pool(self):
        rows=[{"url":"https://example.com/acai","title":"Acai powder importer distributor"}]
        with patch.object(discovery,"_search",return_value=rows) as search:
            result=discovery.discover_buyers("Açaí Powder","United States",limit=5)
        self.assertTrue(result)
        self.assertEqual(search.call_args.args[1],15)

    def test_buyer_deduplication_by_domain(self):
        rows=[{"url":"https://example.com/a","title":"Example ingredient importer"},{"url":"https://www.example.com/b","title":"Example"}]
        with patch.object(discovery,"_search",return_value=rows):
            result=discovery.discover_buyers("Açaí","Canada")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["source_url"],rows[0]["url"])
