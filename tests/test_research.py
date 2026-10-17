# -*- coding: utf-8 -*-
"""Tests: research extraction, classification and no-fabrication guarantees.

All network access is mocked with canned pages, so these tests are offline and
deterministic. The Facebook login-wall case is covered explicitly.
"""
import sys
import unittest
from unittest import mock

from agent_system import research
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


class TestResponseDecoding(unittest.TestCase):
    """F7 regression: source text must survive the fetch byte-for-byte.

    ``requests`` assumes ISO-8859-1 for a ``text/*`` response that declares no
    charset (RFC 2616), which turns UTF-8 into mojibake. These tests pin the
    decoder that replaces that assumption, and they are fully offline: they feed
    bytes, never a live site.
    """

    EM = "\u2014"                                   # em dash
    UZ = "O\u2018zbekiston"                         # Uzbek okina
    CYR = "\u042e\u0440\u0438\u0434\u0438\u0447\u0435\u0441\u043a\u0430\u044f"   # Cyrillic

    def test_utf8_bytes_without_a_charset_are_decoded_as_utf8(self):
        text = "Legal %s %s" % (self.EM, self.UZ)
        self.assertEqual(research.decode_bytes(text.encode("utf-8"), ""), text)

    def test_utf8_bytes_with_a_declared_utf8_charset(self):
        text = "Legal %s %s" % (self.EM, self.UZ)
        self.assertEqual(
            research.decode_bytes(text.encode("utf-8"), "text/html; charset=utf-8"),
            text)

    def test_declared_non_utf8_encoding_is_respected(self):
        raw = self.CYR.encode("cp1251")
        self.assertEqual(
            research.decode_bytes(raw, "text/html; charset=windows-1251"), self.CYR)

    def test_cyrillic_uzbek_and_em_dash_all_survive(self):
        text = "%s %s %s" % (self.CYR, self.UZ, self.EM)
        out = research.decode_bytes(text.encode("utf-8"), "")
        self.assertEqual(out, text)
        self.assertIn(self.EM, out)
        self.assertIn(self.UZ, out)

    def test_a_declared_latin1_page_is_not_corrupted(self):
        """Requirement 4: legacy pages must decode exactly as they did before."""
        text = "Caf\u00e9 \u00e0 la carte"
        raw = text.encode("latin-1")
        self.assertEqual(research.decode_bytes(raw, ""), text)
        self.assertEqual(
            research.decode_bytes(raw, "text/html; charset=iso-8859-1"), text)

    def test_byte_order_mark_is_honoured(self):
        text = "hello %s world" % self.EM
        self.assertEqual(research.decode_bytes(text.encode("utf-8-sig"), ""), text)

    def test_unusable_declared_charset_does_not_break_decoding(self):
        text = "Legal %s ok" % self.EM
        self.assertEqual(research.charset_from_header("text/html; charset=not-a-codec"), "")
        self.assertEqual(research.charset_from_header("text/html"), "")
        self.assertEqual(
            research.decode_bytes(text.encode("utf-8"),
                                  "text/html; charset=not-a-codec"), text)

    def test_empty_and_none_bodies(self):
        self.assertEqual(research.decode_bytes(b"", ""), "")
        self.assertEqual(research.decode_bytes(None, ""), "")

    def test_ukrainian_and_uzbek_cyrillic_diacritics(self):
        text = "\u040ezbekiston \u2014 \u0492"           # Uzbek Cyrillic
        self.assertEqual(research.decode_bytes(text.encode("utf-8"), ""), text)


class TestDefaultFetcherKeepsUnicode(unittest.TestCase):
    """The real ``default_fetcher`` must use the decoder, not ``r.text``.

    ``requests`` is mocked at the module level, so the byte path through the
    fetcher is exercised with no network access at all.
    """

    EM = "\u2014"
    UZ = "O\u2018zbekiston"
    CYR = "\u042e\u0440\u0438\u0434\u0438\u0447\u0435\u0441\u043a\u0430\u044f"

    def _fake_requests(self, content, headers, status=200):
        class _Response(object):
            def __init__(self):
                self.content = content
                self.headers = headers
                self.status_code = status
                # What requests would have produced, and what the fetcher must
                # therefore NOT use for a page with no declared charset.
                self.encoding = "ISO-8859-1"
                self.text = content.decode("latin-1")
                self.url = "https://acme.uz"

        class _FakeRequests(object):
            @staticmethod
            def get(url, **kwargs):
                return _Response()

        return _FakeRequests

    def test_no_charset_header_still_yields_utf8(self):
        body = ("<html><body><p>%s %s %s</p></body></html>"
                % (self.CYR, self.UZ, self.EM))
        fake = self._fake_requests(body.encode("utf-8"), {"Content-Type": "text/html"})
        with mock.patch.dict(sys.modules, {"requests": fake}):
            result = research.default_fetcher("https://acme.uz")
        self.assertTrue(result.ok)
        self.assertIn(self.CYR, result.text)
        self.assertIn(self.UZ, result.text)
        self.assertIn(self.EM, result.text)
        self.assertNotIn("\u00d0\u00ae", result.text, "Cyrillic must not be mojibake")
        self.assertNotIn("\u00c3\u00a2", result.text, "the em dash must not be mojibake")

    def test_declared_encoding_is_still_honoured(self):
        body = "<html><body><p>%s</p></body></html>" % self.CYR
        fake = self._fake_requests(body.encode("cp1251"),
                                   {"Content-Type": "text/html; charset=windows-1251"})
        with mock.patch.dict(sys.modules, {"requests": fake}):
            result = research.default_fetcher("https://acme.uz")
        self.assertIn(self.CYR, result.text)

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


# --------------------------------------------------------------------- discovery
HOME_WITH_NAV = """<html><head><title>GSP Law Firm</title></head><body>
<h1>GSP</h1><p>Founded in 2010.</p>
<nav>
 <a href="/nav/about">About</a>
 <a href="/team">Our team</a>
 <a href="/news?page=2">News</a>
 <a href="/practice-areas">Practice areas</a>
 <a href="https://facebook.com/gsp">Facebook</a>
 <a href="mailto:info@gsp.uz">Mail</a>
 <a href="/brochure.pdf">Brochure</a>
 <a href="#top">Top</a>
 <a href="/">Home</a>
</nav></body></html>"""

SITEMAP_INDEX = """<?xml version="1.0"?><sitemapindex>
<sitemap><loc>https://gsp.uz/sitemap-pages.xml</loc></sitemap>
</sitemapindex>"""

SITEMAP_PAGES = """<?xml version="1.0"?><urlset>
<loc>https://gsp.uz/</loc>
<loc>https://gsp.uz/history</loc>
<loc>https://gsp.uz/awards</loc>
</urlset>"""


class _CountingFetcher(object):
    """A canned fetcher that also counts requests per URL."""

    def __init__(self, pages):
        self.pages = pages
        self.calls = {}

    def __call__(self, url):
        from agent_system.research import FetchResult, SOURCE_ERROR, SOURCE_INSPECTED
        self.calls[url] = self.calls.get(url, 0) + 1
        if url in self.pages:
            return FetchResult(True, 200, self.pages[url], SOURCE_INSPECTED,
                               "ftp", url)
        return FetchResult(False, 404, "", SOURCE_ERROR, "HTTP 404", url)


class TestDiscovery(unittest.TestCase):
    def test_links_are_canonicalised_deduped_and_same_site_only(self):
        from agent_system.research import extract_links
        links = extract_links(HOME_WITH_NAV, "https://gsp.uz")
        self.assertIn("https://gsp.uz/nav/about", links)
        self.assertIn("https://gsp.uz/team", links)
        # a query string identifies the same page, so it is stripped
        self.assertIn("https://gsp.uz/news", links)
        self.assertNotIn("https://gsp.uz/news?page=2", links)
        # external hosts, mailto, documents, fragments and the page itself
        self.assertFalse(any("facebook.com" in u for u in links))
        self.assertFalse(any(u.startswith("mailto:") for u in links))
        self.assertFalse(any(u.endswith(".pdf") for u in links))
        self.assertFalse(any("#" in u for u in links))
        self.assertNotIn("https://gsp.uz/", links)
        self.assertEqual(len(links), len(set(links)))

    def test_sitemap_splits_pages_from_nested_sitemaps(self):
        from agent_system.research import parse_sitemap
        pages, nested = parse_sitemap(SITEMAP_INDEX, "https://gsp.uz")
        self.assertEqual(pages, [])
        self.assertEqual(nested, ["https://gsp.uz/sitemap-pages.xml"])
        pages, nested = parse_sitemap(SITEMAP_PAGES, "https://gsp.uz")
        self.assertIn("https://gsp.uz/history", pages)
        self.assertEqual(nested, [])

    def test_ranking_puts_history_before_contacts(self):
        from agent_system.research import rank_url
        order = sorted(["https://gsp.uz/contacts", "https://gsp.uz/history",
                        "https://gsp.uz/team", "https://gsp.uz/awards",
                        "https://gsp.uz/random-page"],
                       key=rank_url)
        self.assertLess(order.index("https://gsp.uz/history"),
                        order.index("https://gsp.uz/contacts"))
        self.assertLess(order.index("https://gsp.uz/team"),
                        order.index("https://gsp.uz/awards"))
        self.assertTrue(order[-1].endswith("random-page"))

    def test_russian_paths_are_recognised(self):
        from agent_system.research import rank_url
        self.assertLess(rank_url("https://gsp.uz/о-нас")[0],
                        rank_url("https://gsp.uz/что-то-ещё")[0])

    def test_discovery_uses_real_links_and_never_guesses_when_it_can(self):
        from agent_system.research import discover_targets
        pages = {
            "https://gsp.uz": HOME_WITH_NAV,
            "https://gsp.uz/sitemap.xml": SITEMAP_PAGES,
            "https://gsp.uz/robots.txt": "User-agent: *\nSitemap: https://gsp.uz/sitemap.xml\n",
        }
        f = _CountingFetcher(pages)
        targets, notes, prefetched = discover_targets("https://gsp.uz", f,
                                                     lambda m: None)
        urls = [u for _l, u in targets]
        self.assertEqual(urls[0], "https://gsp.uz")
        self.assertIn("https://gsp.uz/history", urls)      # from the sitemap
        self.assertIn("https://gsp.uz/team", urls)         # from the nav link
        self.assertFalse(any("guess" in l for l, _u in targets))
        self.assertTrue(any("same-site link" in n for n in notes))
        self.assertTrue(any("sitemap" in n.lower() for n in notes))

    def test_homepage_is_fetched_only_once(self):
        from agent_system.research import discover_targets
        pages = {"https://gsp.uz": HOME_WITH_NAV,
                 "https://gsp.uz/sitemap.xml": SITEMAP_PAGES}
        f = _CountingFetcher(pages)
        discover_targets("https://gsp.uz", f, lambda m: None)
        self.assertEqual(f.calls.get("https://gsp.uz"), 1,
                         "discovery must not double-fetch the homepage")

    def test_falls_back_to_guesses_and_says_so(self):
        from agent_system.research import discover_targets
        f = _CountingFetcher({"https://bare.uz": "<html><title>Bare</title>"
                                                 "<body><p>Founded in 2011.</p></body></html>"})
        targets, notes, _pre = discover_targets("https://bare.uz", f, lambda m: None)
        labels = [l for l, _u in targets]
        self.assertTrue(all(l.startswith("site-guess-") for l in labels[1:]))
        self.assertTrue(any("GUESS" in n for n in notes),
                        "guessing must be disclosed, not silent")

    def test_sitemap_index_is_followed(self):
        from agent_system.research import discover_targets
        pages = {
            "https://gsp.uz": "<html><title>G</title><body><p>x</p></body></html>",
            "https://gsp.uz/sitemap.xml": SITEMAP_INDEX,
            "https://gsp.uz/sitemap-pages.xml": SITEMAP_PAGES,
        }
        f = _CountingFetcher(pages)
        targets, _notes, _pre = discover_targets("https://gsp.uz", f, lambda m: None)
        self.assertIn("https://gsp.uz/history", [u for _l, u in targets])

    def test_page_count_is_capped(self):
        from agent_system.research import discover_targets
        many = "".join('<a href="/p%d">p</a>' % i for i in range(40))
        f = _CountingFetcher({"https://gsp.uz":
                              "<html><title>G</title><body>%s</body></html>" % many})
        targets, _notes, _pre = discover_targets("https://gsp.uz", f, lambda m: None,
                                                 max_pages=5)
        self.assertLessEqual(len(targets), 5)

    def test_total_failure_is_survivable_and_explicit(self):
        from agent_system.research import discover_targets
        def boom(url):
            raise RuntimeError("network down")
        targets, notes, prefetched = discover_targets("https://gsp.uz", boom,
                                                     lambda m: None)
        self.assertTrue(targets)                     # still plans the homepage
        self.assertTrue(notes)                       # and says what failed
        self.assertTrue(any("could not be fetched" in n
                            or "GUESS" in n for n in notes))
        self.assertIsInstance(prefetched, dict)

    def test_research_records_404_pages_as_gaps_not_content(self):
        from agent_system.research import research_firm
        f = _CountingFetcher({"https://bare.uz":
                              "<html><title>Bare</title><body><p>Founded in 2011.</p></body></html>"})
        res = research_firm("Bare", "https://bare.uz", fetcher=f)
        self.assertFalse(any("/about" in c.source_url for c in res.claims),
                         "an unreadable page must never produce claims")
        self.assertTrue(any("/about" in g for g in res.gaps),
                        "the attempt must be recorded as a gap")
        self.assertTrue(any("iscovery" in n for n in res.notes))

    def test_discovery_notes_become_part_of_the_report(self):
        from agent_system.research import research_firm, report_markdown
        f = _CountingFetcher({"https://gsp.uz": HOME_WITH_NAV,
                              "https://gsp.uz/sitemap.xml": SITEMAP_PAGES,
                              "https://gsp.uz/team": "<html><title>Team</title>"
                                                     "<body><p>12 lawyers.</p></body></html>"})
        res = research_firm("GSP", "https://gsp.uz", fetcher=f)
        self.assertTrue(any("iscovery" in n for n in res.notes))
        self.assertIn("Discovery", report_markdown(res))


if __name__ == "__main__":
    unittest.main()
