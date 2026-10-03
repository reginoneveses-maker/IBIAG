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

    def test_directory_sources_are_labelled_and_provider_query_changes_with_inputs(self):
        rows=[{"url":"https://www.europages.co.uk/company/acme.html","title":"Acme | Acerola importer"}]
        with patch.object(discovery,"_search",return_value=rows) as search:
            result=discovery.discover_buyers("Acerola","Portugal")
            discovery.discover_buyers("Mango","Spain")
        self.assertTrue(result[0]["is_directory"])
        self.assertIn('"Acerola"',search.call_args_list[0].args[0])
        self.assertIn('"Mango"',search.call_args_list[1].args[0])
        self.assertIn('"Spain"',search.call_args_list[1].args[0])
        self.assertFalse(discovery._is_directory_domain("europages.co.uk.evil.test"))

    def test_invalid_json_is_a_provider_error(self):
        with patch.object(discovery, "FIRECRAWL_KEY", "test"), patch.object(discovery.requests, "post", return_value=Mock(json=Mock(side_effect=ValueError("invalid")), raise_for_status=lambda: None)):
            with self.assertRaisesRegex(RuntimeError, "JSON inválido"): discovery._search("test")

    def test_decision_source_is_separate_from_company_source(self):
        with patch.object(discovery, "_search", return_value=[{"url": "https://example.com/team", "title": "Ana Silva - Procurement Manager", "description": "ana@example.com"}]):
            result = discovery.discover_decision_maker("Example", "Portugal", "Acerola")
        self.assertNotIn("source_url", result)
        self.assertEqual(result["decision_source_url"], "https://example.com/team")
        self.assertEqual(result["validation_status"], "needs_validation")


class CompanyEnrichmentTests(unittest.TestCase):
    def test_company_identity_and_contacts_come_from_home_and_contact_page(self):
        home = {"markdown": "Acme Ingredients GmbH Germany", "json": {"company":"Acme Ingredients GmbH","country":"Germany"},"links":["https://acme.test/kontakt"]}
        contact = {"markdown":"Acme Ingredients GmbH Contact info@acme.test Phone +49 40 12345678 Germany", "json":{"email":"info@acme.test","phone":"+49 40 12345678"}}
        with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery,"_scrape_company",side_effect=[home,contact]):
            result=discovery.enrich_company({"company":"Organic Acerola Extract 32%", "website":"https://acme.test/products/acerola", "country":"Alemanha"})
        self.assertEqual(result["company"],"Acme Ingredients GmbH")
        self.assertEqual(result["email"],"info@acme.test")
        self.assertEqual(result["phone"],"+49 40 12345678")
        self.assertEqual(result["website"],"https://acme.test/")
        self.assertEqual(result["country"],"Germany")
        self.assertEqual(result["enrichment_status"],"complete")

    def test_unpublished_extracted_values_are_not_saved(self):
        with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery,"_scrape_company",return_value={"markdown":"Acerola powder 32% 2026-10-03", "json":{"email":"invented@acme.test","phone":"+49 12345678","company":"Fake Company","country":"Germany"}}):
            result=discovery.enrich_company({"website":"https://acme.test"})
        for field in ("company","email","phone","country"):self.assertNotIn(field,result)
        self.assertEqual(result["enrichment_status"],"partial")

    def test_known_directory_does_not_enrich_contacts_from_directory_operator(self):
        with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery,"_scrape_company") as scrape:
            result=discovery.enrich_company({"website":"https://europages.com/company/acme"})
        scrape.assert_not_called()
        self.assertIn("diretório",result["enrichment_message"])
        self.assertNotIn("email",result)

    def test_private_and_malformed_urls_are_rejected(self):
        for url in ("http://localhost/", "http://127.0.0.1/", "http://169.254.169.254/", "https://host.internal/", "https://user:secret@acme.test/", "https://acme.test:bad/"):
            self.assertEqual(discovery._public_url(url),"")

    def test_provider_failure_returns_explicit_status(self):
        with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery,"_scrape_company",side_effect=RuntimeError("Temporariamente indisponível")):
            result=discovery.enrich_company({"website":"https://acme.test"})
        self.assertEqual(result["enrichment_status"],"unavailable")

    def test_directory_operator_is_not_saved_as_candidate_company(self):
        with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery,"_scrape_company",return_value={"markdown":"Directory Ltd sales@directory.test", "json":{"is_directory":True,"company":"Directory Ltd","email":"sales@directory.test"}}):
            result=discovery.enrich_company({"website":"https://directory.test/products/acerola"})
        self.assertNotIn("company",result)
        self.assertNotIn("email",result)
        self.assertIn("diretório",result["enrichment_message"])
