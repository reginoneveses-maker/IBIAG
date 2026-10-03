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

    def test_buyer_deduplication_by_company_and_domain(self):
        rows=[{"url":"https://example.com/a","title":"Example | Açaí ingredient importer"},{"url":"https://www.example.com/b","title":"Example | Açaí"}]
        with patch.object(discovery,"_search",return_value=rows):
            result=discovery.discover_buyers("Açaí","Canada")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["source_url"],rows[0]["url"])


    def test_hyphenated_company_and_shared_directory_are_preserved(self):
        rows = [{"url": "https://directory.test/a", "title": "ABC-Ingredients | Acerola importer"},
                {"url": "https://directory.test/b", "title": "Other Company | Acerola importer"}]
        with patch.object(discovery, "_search", return_value=rows):
            results = discovery.discover_buyers("Acerola", "Portugal")
        self.assertEqual([x["company"] for x in results], ["ABC-Ingredients", "Other Company"])

    def test_invalid_json_is_a_provider_error(self):
        with patch.object(discovery, "FIRECRAWL_KEY", "test"), patch.object(discovery.requests, "post", return_value=Mock(json=Mock(side_effect=ValueError("invalid")), raise_for_status=lambda: None)):
            with self.assertRaisesRegex(RuntimeError, "JSON inválido"): discovery._search("test")

    def test_decision_source_is_separate_from_company_source(self):
        with patch.object(discovery, "_search", return_value=[{"url": "https://example.com/team", "title": "Ana Silva - Procurement Manager", "description": "ana@example.com"}]):
            result = discovery.discover_decision_maker("Example", "Portugal", "Acerola")
        self.assertNotIn("source_url", result)
        self.assertEqual(result["decision_source_url"], "https://example.com/team")
        self.assertEqual(result["validation_status"], "needs_validation")
