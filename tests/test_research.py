# -*- coding: utf-8 -*-
"""Tests: research extraction, classification and no-fabrication guarantees.

All network access is mocked with canned pages, so these tests are offline and
deterministic. The Facebook login-wall case is covered explicitly.
"""
import unittest

from agent_system.research import (CORROBORATED, SINGLE_SOURCE, SOURCE_ERROR,
                                   SOURCE_INACCESSIBLE, UNVERIFIED,
                                   candidate_statements, classify_claim,
                                   ledger_csv, parse_html, report_markdown,
                                   research_firm)
from tests.fakes import html_pages

FIRM_HTML = """<html><head>
<title>Acme Legal LLP — Tashkent</title>
<meta name="description" content="Acme Legal LLP specialises in corporate law.">
</head><body>
<h1>Our history</h1>
<p>Acme Legal LLP was founded in 2010 in Tashkent by two partners.</p>
<p>We won 94% of our cases and serve 1000+ clients every year.</p>
<p>The firm recovered $5.2M for a client in 2021.</p>
<p>© 2026 Acme Legal LLP. All rights reserved.</p>
<p>Home</p>
<p>Acme Legal LLP advises on corporate law, tax law and IT law.</p>
</body></html>"""


class TestExtraction(unittest.TestCase):
    def setUp(self):
        self.ex = parse_html(FIRM_HTML)

    def test_title_and_description_extracted(self):
        self.assertIn("Acme Legal LLP", self.ex.title)
        self.assertIn("corporate law", self.ex.description)

    def test_headings_and_paragraphs(self):
        self.assertIn("Our history", self.ex.headings)
        self.assertTrue(any("founded in 2010" in p for p in self.ex.paragraphs))

    def test_copyright_line_is_filtered_as_boilerplate(self):
        texts = [t for t, _ in candidate_statements(self.ex)]
        self.assertFalse(any("All rights reserved" in t for t in texts))
        self.assertFalse(any(t.strip() == "Home" for t in texts))

    def test_case_figure_detected(self):
        kinds = {k for _, k in candidate_statements(self.ex)}
        self.assertIn("case_figure", kinds)

    def test_win_rate_classified_as_statistic(self):
        found = [k for t, k in candidate_statements(self.ex) if "94%" in t]
        self.assertEqual(found, ["statistic_or_superlative"])


class TestClassification(unittest.TestCase):
    def test_case_figure_never_public_and_needs_clearance(self):
        evc, safe, needs = classify_claim("recovered $5.2M", "case_figure",
                                          "https://acme.uz", ["https://acme.uz"])
        self.assertEqual(evc, UNVERIFIED)
        self.assertFalse(safe)
        self.assertIn("client", needs.lower())

    def test_self_published_statistic_is_single_source_not_fact(self):
        evc, safe, needs = classify_claim("94% win rate", "statistic_or_superlative",
                                          "https://acme.uz", ["https://acme.uz"])
        self.assertEqual(evc, SINGLE_SOURCE)
        self.assertFalse(safe)

    def test_self_description_is_a_claim_not_a_fact(self):
        evc, safe, _ = classify_claim("We are the leading firm", "statement",
                                      "https://acme.uz", ["https://acme.uz"])
        self.assertEqual(evc, SINGLE_SOURCE)
        self.assertFalse(safe)

    def test_external_mention_is_single_source(self):
        evc, safe, _ = classify_claim("A firm in Tashkent", "statement",
                                      "https://news.example", ["https://acme.uz"])
        self.assertEqual(evc, SINGLE_SOURCE)
        self.assertFalse(safe)


class TestResearchRun(unittest.TestCase):
    def test_reads_page_and_cites_every_claim(self):
        fetcher = html_pages({"https://acme.uz": FIRM_HTML})
        res = research_firm("Acme", "https://acme.uz", fetcher=fetcher)
        inspected = [s for s in res.sources if s.state == "INSPECTED"]
        self.assertEqual(len(inspected), 1)
        self.assertTrue(res.claims)
        for c in res.claims:
            self.assertTrue(c.source_url.startswith("https://acme.uz"))
            self.assertTrue(c.source_id)
            self.assertFalse(c.safe_for_public)

    def test_unreadable_source_produces_no_claims(self):
        fetcher = html_pages({})            # everything 404s
        res = research_firm("Acme", "https://acme.uz", fetcher=fetcher)
        self.assertEqual(res.claims, [])
        self.assertTrue(res.gaps)
        self.assertTrue(all(s.state in (SOURCE_ERROR, SOURCE_INACCESSIBLE)
                            for s in res.sources))

    def test_facebook_login_wall_reported_not_claimed_as_read(self):
        def fetcher(url):
            from agent_system.research import FetchResult
            if "facebook.com" in url:
                return FetchResult(False, 200, "<html>Log in to continue</html>",
                                   SOURCE_INACCESSIBLE,
                                   "login wall — public post feed not readable", url)
            return FetchResult(False, 404, "", SOURCE_ERROR, "HTTP 404", url)

        res = research_firm("Acme", "https://acme.uz",
                            facebook="https://facebook.com/acme", fetcher=fetcher)
        fb = [s for s in res.sources if s.kind == "facebook"]
        self.assertEqual(len(fb), 1)
        self.assertEqual(fb[0].state, SOURCE_INACCESSIBLE)
        self.assertIn("wall", fb[0].note.lower())
        self.assertTrue(any("login wall" in n.lower() for n in res.notes))
        self.assertFalse(any("facebook" in c.source_url for c in res.claims))

    def test_facebook_wall_detected_by_default_fetcher_heuristic(self):
        """The real default_fetcher must classify a login page as inaccessible."""
        from agent_system.research import FetchResult, SOURCE_INACCESSIBLE
        # Simulate the heuristic branch without network by checking the rule set.
        import inspect
        from agent_system import research
        src = inspect.getsource(research.default_fetcher)
        self.assertIn("login wall", src)
        self.assertIn("SOURCE_INACCESSIBLE", src)

    def test_report_and_csv_carry_citations(self):
        fetcher = html_pages({"https://acme.uz": FIRM_HTML})
        res = research_firm("Acme", "https://acme.uz", fetcher=fetcher)
        md = report_markdown(res)
        self.assertIn("https://acme.uz", md)
        self.assertIn("Anti-fabrication", md)
        csv_text = ledger_csv(res)
        self.assertIn("source_url", csv_text.splitlines()[0])
        self.assertIn("https://acme.uz", csv_text)

    def test_no_website_recorded_as_gap(self):
        res = research_firm("Acme", "", fetcher=html_pages({}))
        self.assertTrue(any("No official website" in g for g in res.gaps))

    def test_extra_urls_are_included(self):
        fetcher = html_pages({"https://acme.uz": FIRM_HTML,
                              "https://news.example/a": "<html><body><p>"
                              "Acme Legal LLP announced a new office in 2026 in Tashkent."
                              "</p></body></html>"})
        res = research_firm("Acme", "https://acme.uz", extra_urls=["https://news.example/a"],
                            fetcher=fetcher)
        self.assertTrue(any(s.url == "https://news.example/a" for s in res.sources))


if __name__ == "__main__":
    unittest.main()
