# -*- coding: utf-8 -*-
"""Tests: fixes from the whole-bot quality review.

Each test pins one defect seen in a real run: a firm name rendered as
"Untitled", Russian text leaking into an Uzbek film, duplicate pages doubling
the ledger, navigation labels recorded as claims, an unread Telegram channel,
and paused jobs nobody was reminded about.
"""
import os
import shutil
import tempfile
import time
import unittest

from agent_system import research, story
from agent_system.jobs import JobStore
from agent_system.telegrambot.bot import BotService
from agent_system.config import Config
from agent_system.video.spec import validate_render_spec


class TestFirmNameKey(unittest.TestCase):
    SCENE = {"id": "sc1", "kind": "statement", "dur": 6.0, "narration": "Salom."}

    def test_manifest_uses_firm_key(self):
        spec, _errors = validate_render_spec({
            "firm": "GSP Law Firm", "language": "uz", "style": "motion",
            "scenes": [self.SCENE]})
        self.assertEqual(spec.firm_name, "GSP Law Firm")

    def test_missing_name_still_falls_back(self):
        spec, _errors = validate_render_spec({"scenes": [self.SCENE]})
        self.assertEqual(spec.firm_name, "Untitled")


class TestLanguageGuard(unittest.TestCase):
    RU = "IT-право, корпоративное право, экономические споры."

    def test_russian_areas_translated_for_uzbek(self):
        out = story.localise_text(self.RU, "uz")
        self.assertIn("korporativ huquq", out)
        self.assertNotRegex(out, r"[Ѐ-ӿ]")

    def test_russian_kept_for_russian(self):
        self.assertEqual(story.localise_text(self.RU, "ru"), self.RU)

    def test_unknown_cyrillic_becomes_empty_not_leaked(self):
        self.assertEqual(story.localise_text("Профессионализм и доверие", "en"), "")

    def test_latin_text_untouched(self):
        self.assertEqual(story.localise_text("Corporate law", "uz"), "Corporate law")

    def test_scene_text_never_leaks_cyrillic(self):
        facts = story.Facts(firm_name="GSP")
        facts.items["practice_areas"] = story.Fact(
            "practice_areas", self.RU, "S01", "u", "SINGLE-SOURCE")
        t = story.scene_text("practice", facts, "uz")
        for v in (t["narration"], t["sub"], t["heading"]):
            self.assertNotRegex(v, r"[Ѐ-ӿ]")

    def test_untranslatable_areas_become_a_gap(self):
        facts = story.Facts(firm_name="GSP")
        facts.items["practice_areas"] = story.Fact(
            "practice_areas", "Мы лучшие в городе", "S01", "u", "SINGLE-SOURCE")
        t = story.scene_text("practice", facts, "en")
        self.assertIn("practice_areas", t["needs"])


class TestResearchNoise(unittest.TestCase):
    PAGE = ("<html><head><title>Firm</title></head><body>"
            "<h2>Свяжитесь с нами</h2><h2>Наша история</h2>"
            "<p>Фирма работает на рынке уже много лет и ведёт сложные дела.</p>"
            '<a href="index.html">x</a><a href="https://t.me/examplechan">tg</a>'
            "</body></html>")
    TG = ('<div class="tgme_widget_message_wrap">'
          '<div class="tgme_widget_message_text">Firm Example opened a new office in Tashkent today!</div>'
          '<a class="tgme_widget_message_date"><time datetime="2026-10-20T10:00:00+00:00"></time></a></div>'
          '<div class="tgme_widget_message_wrap">'
          '<div class="tgme_widget_message_text">A new tax law was signed by the government yesterday.</div>'
          '<a class="tgme_widget_message_date"><time datetime="2026-10-21T10:00:00+00:00"></time></a></div>')

    def fetcher(self, url):
        if url.startswith("https://t.me/s/"):
            return research.FetchResult(True, 200, self.TG, research.SOURCE_INSPECTED, "ok", url)
        if url.endswith("robots.txt") or url.endswith("sitemap.xml"):
            return research.FetchResult(False, 404, "", research.SOURCE_ERROR, "404", url)
        return research.FetchResult(True, 200, self.PAGE, research.SOURCE_INSPECTED, "ok", url)

    def run_research(self):
        return research.research_firm("Firm Example", "https://example.com",
                                      fetcher=self.fetcher)

    def test_duplicate_page_is_not_counted_twice(self):
        res = self.run_research()
        texts = [c.text for c in res.claims if c.source_url.startswith("https://example.com")]
        self.assertEqual(len(texts), len(set(texts)))
        self.assertTrue(any("duplicate" in s.note for s in res.sources))

    def test_navigation_headings_are_not_claims(self):
        res = self.run_research()
        self.assertFalse(any(c.text == "Свяжитесь с нами" for c in res.claims))

    def test_telegram_channel_read_with_dates(self):
        res = self.run_research()
        tg = [c for c in res.claims if "t.me/s/" in c.source_url]
        self.assertEqual(len(tg), 2)
        self.assertEqual({c.source_date for c in tg}, {"2026-10-20", "2026-10-21"})

    def test_only_firm_posts_are_statements(self):
        res = self.run_research()
        kinds = {c.text[:8]: c.relevance for c in res.claims if "t.me/s/" in c.source_url}
        self.assertEqual(kinds["Firm Exa"], "statement")
        self.assertEqual(kinds["A new ta"], "news")

    def test_channel_url_mapping(self):
        self.assertEqual(research.telegram_channel_url("https://t.me/abcde"),
                         "https://t.me/s/abcde")
        self.assertEqual(research.telegram_channel_url("https://t.me/joinchat"), "https://t.me/s/joinchat")
        self.assertEqual(research.telegram_channel_url("https://example.com"), "")


class TestStaleReviewReminder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="remind_test_")
        self._env = os.environ.copy()
        os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:AAFakeBotTokenValueForTesting_abc"
        os.environ["TELEGRAM_ALLOWED_USER_IDS"] = "111"
        os.environ["AGENT_OUTPUT_DIR"] = self.tmp
        self.store = JobStore(os.path.join(self.tmp, "jobs.sqlite3"))
        self.svc = BotService(Config.from_env(), self.store)
        self.sent = []
        self.svc._send = lambda chat_id, text, reply_markup=None: self.sent.append((chat_id, text))

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _paused_job(self, age_hours):
        jid = self.store.create(111, "motion", "uz", "Firm", 60, 111)
        self.store.set_status(jid, "awaiting_research_review")
        conn = self.store._connect()
        try:
            conn.execute("UPDATE jobs SET updated_at=? WHERE id=?",
                         (time.time() - age_hours * 3600, jid))
            conn.commit()
        finally:
            conn.close()
        return jid

    def test_fresh_review_not_reminded(self):
        self._paused_job(1)
        self.assertEqual(self.svc.remind_stale_reviews(), 0)

    def test_stale_review_reminded_once(self):
        jid = self._paused_job(30)
        self.assertEqual(self.svc.remind_stale_reviews(), 1)
        self.assertIn(jid, self.sent[0][1])
        self.assertEqual(self.svc.remind_stale_reviews(), 0)


if __name__ == "__main__":
    unittest.main()


class TestSiteDataAndScenes(unittest.TestCase):
    DATA_JS = """
const FIRM = {
  name: "X",
  address: { ru: "г. Ташкент, ул. Мирабад, 46а", uz: "Toshkent sh., Mirobod ko'chasi, 46a-uy", en: "46a Mirobod St., Tashkent" },
  stats: [
    { num: "16+", label: "лет опыта" },
    { num: "15", label: "адвокатов" },
    { num: "1000+", label: "клиентов" }
  ]
};
const SERVICES = [
  { icon: "a", title: "Корпоративное право и M&A", desc: "d" },
  { icon: "b", title: "Налоговая практика", desc: "d" }
];
const LAWYERS = [
  {
    id: 1,
    name: "Ali Valiyev",
    title: "Партнёр",
  }
];
"""

    def test_script_urls_are_same_site_and_skip_libraries(self):
        html = ('<script src="data.js?v=1"></script><script src="https://cdn.x.com/a.js"></script>'
                '<script src="/jquery.min.js"></script>')
        self.assertEqual(research.script_urls(html, "https://example.com/"),
                         ["https://example.com/data.js"])

    def test_data_claims_pick_the_requested_language(self):
        uz = [t for t, *_ in research.script_data_claims(self.DATA_JS, "uz")]
        self.assertIn("Address: Toshkent sh., Mirobod ko'chasi, 46a-uy", uz)
        en = [t for t, *_ in research.script_data_claims(self.DATA_JS, "en")]
        self.assertTrue(any("Mirobod St." in t for t in en))

    def _facts(self):
        claims = [research.Claim(id="C%d" % i, text=t, source_id="S01", source_url="u",
                                 evidence_class="SINGLE-SOURCE", relevance=k)
                  for i, (t, k, *_r) in enumerate(research.script_data_claims(self.DATA_JS, "uz"))]
        return story.extract_facts(research.ResearchResult("X", claims=claims), "X")

    def test_facts_from_site_data(self):
        f = self._facts()
        self.assertEqual(f.get("years_experience"), "16+")
        self.assertEqual(f.get("clients"), "1000+")
        self.assertEqual(f.get("team"), "Ali Valiyev")
        self.assertIn("Налоговая практика", f.get("practice_areas"))

    def test_scenes_complete_without_placeholders(self):
        f = self._facts()
        for lang in ("en", "ru", "uz"):
            for key in ("origin", "practice", "achievements", "people", "office"):
                t = story.scene_text(key, f, lang)
                self.assertEqual(t["needs"], "", (lang, key))
                self.assertNotIn("[", t["narration"] + t["heading"] + t["sub"])

    def test_gap_scenes_are_dropped_and_retimed(self):
        facts = story.Facts(firm_name="X")          # no facts at all
        scenes = story.build_scenes("X", facts, "uz", 60.0)
        kept, omitted = story.drop_gap_scenes(scenes, 60.0)
        self.assertTrue(omitted)
        self.assertTrue(all(not s["needs"] for s in kept))
        self.assertAlmostEqual(sum(s["dur"] for s in kept), 60.0, delta=0.2)
        self.assertEqual(kept[0]["start"], 0.0)


class TestCaptions(unittest.TestCase):
    def test_caption_skipped_when_text_already_on_screen(self):
        from agent_system.video import draw
        self.assertFalse(draw.narration_needs_caption(
            {"kind": "statement", "heading": "", "sub": "", "narration": "Hello there"}))
        self.assertFalse(draw.narration_needs_caption(
            {"kind": "title", "heading": "Hello there", "sub": "", "narration": "Hello there"}))
        self.assertFalse(draw.narration_needs_caption(
            {"kind": "endcard", "heading": "X", "sub": "", "narration": "X. Done."}))
        self.assertTrue(draw.narration_needs_caption(
            {"kind": "stat", "heading": "16+", "sub": "X", "narration": "X has 16 years."}))
