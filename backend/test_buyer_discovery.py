import unittest
from unittest.mock import patch, Mock
import buyer_discovery as discovery

def business_page(company="Acme Ingredients", product="Acerola", relationship="seller"):
    identity=f"{company} is a food manufacturer."
    quote=f"We supply {product} ingredients." if relationship=="seller" else f"Our drink contains {product}."
    return {"markdown":identity+"\n"+quote, "json":{"company":company,"is_company":True,"is_directory":False,
        "page_type":"company_product","relationship":relationship,"company_quote":identity,"product_quote":quote}}

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
        with patch.object(discovery,"_search",return_value=rows) as search, patch.object(discovery,"_scrape_business",return_value=business_page(product="Acai powder")):
            result=discovery.discover_buyers("Açaí Powder","United States",limit=5)
        self.assertTrue(result)
        self.assertEqual(search.call_args.args[1],15)

    def test_buyer_deduplication_by_company_and_domain(self):
        rows=[{"url":"https://example.com/a","title":"Example | Açaí ingredient importer"},{"url":"https://www.example.com/b","title":"Example | Açaí"}]
        with patch.object(discovery,"_search",return_value=rows), patch.object(discovery,"_scrape_business",return_value=business_page(company="Example",product="Açaí")):
            result=discovery.discover_buyers("Açaí","Canada")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["source_url"],rows[0]["url"])


    def test_hyphenated_company_is_extracted_from_page_not_product_title(self):
        rows = [{"url": "https://abc.test/a", "title": "Organic Acerola Extract - product"},
                {"url": "https://other.test/b", "title": "Acerola importer"}]
        pages={rows[0]["url"]:business_page("ABC-Ingredients"),rows[1]["url"]:business_page("Other Company")}
        with patch.object(discovery, "_search", return_value=rows), patch.object(discovery,"_scrape_business",side_effect=lambda url,product:pages[url]):
            results = discovery.discover_buyers("Acerola", "Portugal")
        self.assertEqual({x["company"] for x in results}, {"ABC-Ingredients", "Other Company"})

    def test_directory_sources_are_excluded_and_provider_query_changes_with_inputs(self):
        rows=[{"url":"https://www.europages.co.uk/company/acme.html","title":"Acme | Acerola importer"}]
        with patch.object(discovery,"_search",return_value=rows) as search, patch.object(discovery,"_scrape_business") as scrape:
            result=discovery.discover_buyers("Acerola","Portugal")
            discovery.discover_buyers("Mango","Spain")
        self.assertEqual(result,[])
        scrape.assert_not_called()
        self.assertIn('"Acerola"',search.call_args_list[0].args[0])
        self.assertIn('"Mango"',search.call_args_list[2].args[0])
        self.assertIn('"Spain"',search.call_args_list[2].args[0])
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

    def test_sellers_and_actual_product_users_have_visible_grounded_evidence(self):
        rows=[{"url":"https://seller.test/products/acerola","title":"Acerola powder"},
              {"url":"https://drink.test/beverages","title":"Acerola drink ingredients"}]
        pages={rows[0]["url"]:business_page("Ingredient Supplier"),rows[1]["url"]:business_page("Drink Company",relationship="user")}
        with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"_scrape_business",side_effect=lambda url,product:pages[url]):
            found=discovery.discover_buyers("Acerola","Portugal")
        self.assertEqual({x["company"] for x in found},{"Ingredient Supplier","Drink Company"})
        self.assertEqual({x["product_relationship"] for x in found},{"seller","user"})
        self.assertTrue(all(x["relationship_verified"] and x["product_evidence"] for x in found))
        self.assertEqual(next(x["website"] for x in found if x["company"]=="Drink Company"),"https://drink.test/")

    def test_books_papers_generic_articles_and_directory_operator_are_not_companies(self):
        rows=[{"url":"https://books.google.com/books/123","title":"Acerola ingredient book"},
              {"url":"https://pubmed.ncbi.nlm.nih.gov/123","title":"Acerola powder research"},
              {"url":"https://europages.com/acai","title":"Acerola suppliers"},
              {"url":"https://health.test/benefits","title":"Acerola health benefits"},
              {"url":"https://acme.test/blog/acerola","title":"Acerola market research"}]
        page=business_page();page["json"].update(page_type="other",relationship="none")
        with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"_scrape_business",return_value=page) as scrape:
            self.assertEqual(discovery.discover_buyers("Acerola","Portugal"),[])
        self.assertEqual(scrape.call_count,2)

    def test_hallucinated_identity_or_relationship_and_product_title_are_rejected(self):
        item={"url":"https://acme.test/acerola","title":"Acerola"}
        for field,value in [("company","Fake Company")]:
            page=business_page();page["json"][field]=value
            self.assertIsNone(discovery._verified_business(item,page,"Acerola","Portugal"))
        self.assertIsNone(discovery._verified_business(item,business_page(company="Acerola"),"Acerola","Portugal"))
        self.assertIsNone(discovery._verified_business(item,business_page(company="Organic Acerola Extract with 32% Natural Vitamin C"),"Acerola","Portugal"))
        page=business_page();page["json"]["is_directory"]=True
        self.assertIsNone(discovery._verified_business(item,page,"Acerola","Portugal"))
        page=business_page(product="Mango")
        self.assertIsNone(discovery._verified_business(item,page,"Acerola","Portugal"))

    def test_a_product_mention_without_business_action_is_rejected(self):
        page=business_page();page["markdown"]="Acme Ingredients is a food manufacturer. Acerola is a source of vitamin C."
        page["json"]["product_quote"]="Acerola is a source of vitamin C."
        self.assertIsNone(discovery._verified_business({"url":"https://acme.test/article"},page,"Acerola","Portugal"))

    def test_company_product_heading_with_its_published_quote_action_is_accepted_but_an_article_is_not(self):
        page=business_page();page["markdown"]="Acme Ingredients is a food manufacturer.\nAcerola powder\nRequest a quote"
        page["json"].update(product_quote="Acerola powder",business_quote="Request a quote")
        item={"url":"https://acme.test/acerola"}
        verified=discovery._verified_business(item,page,"Acerola","Portugal")
        self.assertTrue(verified["relationship_verified"])
        self.assertIn("Request a quote",verified["product_evidence"])
        page["json"]["page_type"]="other"
        self.assertIsNone(discovery._verified_business(item,page,"Acerola","Portugal"))
        page["json"].update(page_type="company_product",business_quote="Buy now")
        verified=discovery._verified_business(item,page,"Acerola","Portugal")
        self.assertIn("Request a quote",verified["product_evidence"])
        self.assertNotIn("Buy now",verified["product_evidence"])

    def test_provider_verification_failure_never_falls_back_to_search_titles(self):
        rows=[{"url":"https://acme.test/acerola","title":"Acme sells Acerola"}]
        with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"_scrape_business",side_effect=RuntimeError("offline")):
            with self.assertRaisesRegex(RuntimeError,"conferir os sites"): discovery.discover_buyers("Acerola","Portugal")

    def test_candidate_page_requests_are_bounded_and_domains_are_deduplicated(self):
        rows=[{"url":f"https://acme.test/acerola/{i}","title":"Acerola supplier"} for i in range(40)]
        with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"_scrape_business",return_value=business_page()) as scrape:
            found=discovery.discover_buyers("Acerola","Portugal",20)
        self.assertEqual(len(found),1)
        self.assertEqual(scrape.call_count,12)

    def test_verification_queue_timeout_does_not_call_provider_or_accept_snippets(self):
        rows=[{"url":"https://acme.test/acerola","title":"Acme sells Acerola"}]
        slot=Mock(acquire=Mock(return_value=False))
        with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"BUSINESS_PAGE_SLOTS",slot),patch.object(discovery,"_scrape_business") as scrape:
            with self.assertRaises(RuntimeError): discovery.discover_buyers("Acerola","Portugal")
        scrape.assert_not_called();slot.release.assert_not_called()

    def test_portuguese_ingredients_match_english_evidence_without_partial_word_matches(self):
        self.assertTrue(discovery._is_product_relevant({"markdown":"We supply guava pulp."},"Goiaba polpa"))
        self.assertTrue(discovery._is_product_relevant({"markdown":"Our drink contains mango."},"Manga"))
        self.assertFalse(discovery._is_product_relevant({"markdown":"We supply mangosteen."},"Mango"))
        self.assertFalse(discovery._is_product_relevant({"markdown":"We supply coconut oil."},"CocoA"))

    def test_scrape_extraction_uses_product_specific_schema_and_preserves_v1_compatibility(self):
        for base in ["https://api.firecrawl.dev/v1","https://api.firecrawl.dev/v2"]:
            with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery,"FIRECRAWL_URL",base),patch.object(discovery.requests,"post",return_value=Mock(json=lambda:{"success":True,"data":business_page()},raise_for_status=lambda:None)) as post:
                self.assertEqual(discovery._scrape_business("https://acme.test/acerola","Acerola"),business_page())
            body=post.call_args.kwargs["json"]
            prompt=body["jsonOptions"]["prompt"] if base.endswith("v1") else body["formats"][1]["prompt"]
            self.assertIn("Acerola",prompt);self.assertIn("verbatim",prompt)

    def test_identity_and_long_ai_quote_can_be_recovered_from_literal_page_content(self):
        page=business_page("ABC Ingredients")
        page["json"].update(company_quote="We are an expert.", product_quote="Invented offer not on the page")
        page["markdown"]="ABC Ingredients\nOur B2B distribution supplies Acerola fruit powder and Acerola lozenges to retailers, wholesalers, and bulk customers for resale in industrial food quality tested and certified."
        row=discovery._verified_business({"url":"https://abc.test/acerola"},page,"Acerola","Germany")
        self.assertTrue(row)
        self.assertLessEqual(len(row["product_evidence"].split()),25)
        self.assertIn(row["product_evidence"],page["markdown"])
        self.assertNotIn("Invented",row["product_evidence"])
        page["json"]["page_type"]="other"
        self.assertIsNone(discovery._verified_business({"url":"https://abc.test/article"},page,"Acerola","Germany"))

    def test_markdown_link_urls_do_not_break_literal_evidence_or_supply_identity(self):
        page=business_page("ABC Ingredients")
        page["markdown"]="[ABC Ingredients](https://abc.test)\nWe supply [Acerola](https://abc.test/acerola) ingredients."
        self.assertTrue(discovery._verified_business({"url":"https://abc.test/acerola"},page,"Acerola","Germany"))
        page["json"]["company"]="inventedcompany"
        page["markdown"] += " https://inventedcompany.test"
        self.assertIsNone(discovery._verified_business({"url":"https://abc.test/acerola"},page,"Acerola","Germany"))

    def test_company_country_is_not_the_query_and_verified_foreign_address_is_excluded(self):
        page=business_page();item={"url":"https://acme.test/acerola"}
        row=discovery._verified_business(item,page,"Acerola","Bulgaria")
        self.assertEqual(row["country"],"")
        self.assertEqual(row["search_country"],"Bulgaria")
        page["markdown"] += "\nContact address: New York, United States."
        page["json"].update(country="United States",country_quote="Contact address: New York, United States.")
        self.assertIsNone(discovery._verified_business(item,page,"Acerola","Bulgaria"))
        row=discovery._verified_business(item,page,"Acerola","United States")
        self.assertTrue(row["country_verified"])
        self.assertEqual(row["company_country"],"United States")

    def test_provider_rate_limit_retries_and_credit_failure_is_typed_terminal(self):
        import requests
        limited=Mock(status_code=429,headers={"Retry-After":"1"})
        limited.raise_for_status.side_effect=requests.HTTPError(response=limited)
        okay=Mock(json=lambda:{"success":True,"data":{"web":[]}},raise_for_status=lambda:None)
        clock=[100.0]
        with patch.object(discovery,"PROVIDER_PAUSE_UNTIL",0),patch.object(discovery.time,"monotonic",side_effect=lambda:clock[0]),patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery.requests,"post",side_effect=[limited,okay]) as post,patch.object(discovery.time,"sleep",side_effect=lambda delay:clock.__setitem__(0,clock[0]+delay)) as sleep:
            self.assertEqual(discovery._search("Acerola"),[])
            self.assertEqual(post.call_count,2)
            sleep.assert_called_once_with(1)
        empty=Mock(status_code=402,headers={})
        empty.raise_for_status.side_effect=requests.HTTPError(response=empty)
        with patch.object(discovery,"FIRECRAWL_KEY","test"),patch.object(discovery.requests,"post",return_value=empty) as post:
            with self.assertRaises(discovery.ProviderError) as error: discovery._search("Acerola")
        self.assertTrue(error.exception.terminal)
        self.assertEqual(error.exception.code,"credits")
        self.assertEqual(post.call_count,1)

    def test_job_page_cache_checks_one_url_once_across_markets(self):
        context=discovery.DiscoveryContext();token=discovery.JOB_CONTEXT.set(context)
        rows=[{"url":"https://acme.test/acerola","title":"Acerola powder supplier"}]
        try:
            with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"_scrape_business",return_value=business_page()) as scrape:
                self.assertTrue(discovery.discover_buyers("Acerola","Germany"))
                self.assertTrue(discovery.discover_buyers("Acerola","Spain"))
                self.assertEqual(scrape.call_count,1)
        finally: discovery.JOB_CONTEXT.reset(token)

    def test_partial_page_failures_are_reported_alongside_verified_results(self):
        rows=[{"url":"https://acme.test/acerola","title":"Acerola powder supplier"},{"url":"https://other.test/acerola","title":"Acerola powder supplier"}]
        def page(url, product):
            if "other.test" in url: raise RuntimeError("Site indisponível")
            return business_page()
        with patch.object(discovery,"_search",return_value=rows),patch.object(discovery,"_scrape_business",side_effect=page):
            result=discovery.discover_buyers("Acerola","Germany")
        self.assertEqual(len(result),1)
        self.assertIn("Site indisponível",result.warnings)


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
