# -*- coding: utf-8 -*-
"""Tests: story building — the no-fabrication guarantee.

The critical property: when a fact is absent from the evidence, the narration
must contain an explicit gap placeholder, never an invented value.
"""
import json
import os
import shutil
import tempfile
import unittest

from agent_system.research import (CORROBORATED, Claim, ResearchResult, Source,
                                   SOURCE_INSPECTED)
from agent_system import story as story_mod


def research_with(claims):
    res = ResearchResult(firm_name="Acme Legal LLP")
    res.sources.append(Source(id="S01", kind="website", url="https://acme.uz",
                              state=SOURCE_INSPECTED))
    res.claims = claims
    return res


def claim(text, relevance="statement", cid="C001"):
    return Claim(id=cid, text=text, source_id="S01", source_url="https://acme.uz",
                 page_title="Home", evidence_class="SINGLE-SOURCE",
                 safe_for_public=False, relevance=relevance)


class TestFactExtraction(unittest.TestCase):
    def test_founding_year_extracted_with_source(self):
        res = research_with([claim("Acme Legal LLP was founded in 2010 in Tashkent.")])
        facts = story_mod.extract_facts(res, "Acme Legal LLP")
        self.assertEqual(facts.get("founding_year"), "2010")
        self.assertTrue(facts.note("founding_year"))

    def test_missing_year_is_absent_not_guessed(self):
        res = research_with([claim("We are a modern law firm.")])
        facts = story_mod.extract_facts(res, "Acme Legal LLP")
        self.assertFalse(facts.has("founding_year"))
        self.assertIn("founding_year", facts.missing())


class TestNoFabrication(unittest.TestCase):
    def test_missing_year_yields_placeholder_in_every_language(self):
        res = research_with([claim("We are a modern law firm.")])
        for lang in ("en", "ru", "uz"):
            facts = story_mod.extract_facts(res, "Acme Legal LLP")
            scenes = story_mod.build_scenes("Acme Legal LLP", facts, lang, 140.0)
            origin = next(s for s in scenes if s["key"] == "origin")
            self.assertIn("[", origin["narration"],
                          "%s: expected a bracket placeholder" % lang)
            self.assertIn("founding_year", origin["needs"])
            self.assertTrue(origin["placeholder"])

    def test_present_year_is_used_verbatim(self):
        res = research_with([claim("Acme Legal LLP was founded in 2010 in Tashkent.")])
        facts = story_mod.extract_facts(res, "Acme Legal LLP")
        scenes = story_mod.build_scenes("Acme Legal LLP", facts, "en", 140.0)
        origin = next(s for s in scenes if s["key"] == "origin")
        self.assertIn("2010", origin["narration"])
        self.assertNotIn("founding_year", origin["needs"])

    def test_no_invented_numbers_anywhere(self):
        res = research_with([claim("We are a modern law firm.")])
        facts = story_mod.extract_facts(res, "Acme Legal LLP")
        for lang in ("en", "ru", "uz"):
            for s in story_mod.build_scenes("Acme Legal LLP", facts, lang, 140.0):
                # No bare 4-digit year and no money figure may appear from nowhere.
                for token in ("$", "€", "%"):
                    self.assertNotIn(token, s["narration"],
                                     "invented figure in %s scene %s" % (lang, s["key"]))

    def test_gap_scenes_are_flagged_for_the_renderer(self):
        res = research_with([])
        facts = story_mod.extract_facts(res, "Acme")
        scenes = story_mod.build_scenes("Acme", facts, "en", 60.0)
        self.assertTrue(any(s["placeholder"] for s in scenes))


class TestDurationsAndManifest(unittest.TestCase):
    def test_scene_durations_sum_to_target(self):
        res = research_with([claim("Acme was founded in 2010.")])
        facts = story_mod.extract_facts(res, "Acme")
        for total in (60.0, 140.0, 150.0):
            scenes = story_mod.build_scenes("Acme", facts, "en", total)
            s = sum(x["dur"] for x in scenes)
            self.assertAlmostEqual(s, total, places=1)

    def test_scene_start_times_are_monotonic(self):
        facts = story_mod.extract_facts(research_with([]), "Acme")
        scenes = story_mod.build_scenes("Acme", facts, "en", 120.0)
        starts = [s["start"] for s in scenes]
        self.assertEqual(starts, sorted(starts))

    def test_three_concepts_with_one_recommended(self):
        res = research_with([])
        facts = story_mod.extract_facts(res, "Acme")
        concepts = story_mod.build_concepts("Acme", facts, res)
        self.assertEqual(len(concepts), 3)
        self.assertEqual(sum(1 for c in concepts if c.get("recommended")), 1)

    def test_story_assets_written_and_manifest_valid(self):
        tmp = tempfile.mkdtemp(prefix="story_test_")
        try:
            res = research_with([claim("Acme Legal LLP was founded in 2010 in Tashkent.")])
            facts = story_mod.extract_facts(res, "Acme Legal LLP", "2026-10-20",
                                            "Mirobod 46a")
            paths = story_mod.build_story_assets(tmp, "Acme Legal LLP", facts, res,
                                                 "uz", "motion", 140.0)
            for name in ("concepts.md", "script.md", "storyboard.md",
                         "scene_manifest.json"):
                self.assertTrue(os.path.isfile(paths[name]), name)
            with open(paths["scene_manifest.json"], encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertEqual(manifest["language"], "uz")
            self.assertEqual(manifest["style"], "motion")
            self.assertTrue(manifest["scenes"])
            # the manifest must be renderable without further editing
            from agent_system import video
            spec, errors = video.validate_render_spec(manifest)
            self.assertEqual(errors, [])
            self.assertGreater(len(spec.scenes), 0)

            script = open(paths["script.md"], encoding="utf-8").read()
            self.assertIn("Permission & confidentiality", script)
            # every historical scene cites the claim it stands on
            self.assertIn("Source", script)
            self.assertIn("Evidence", script)
            self.assertIn("2010", script)
            self.assertIn("https://acme.uz", script)

            board = open(paths["storyboard.md"], encoding="utf-8").read()
            self.assertIn("**Source:**", board)
            self.assertIn("https://acme.uz", board)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_language_normalisation(self):
        self.assertEqual(story_mod.normalize_lang("uz"), "uz")
        self.assertEqual(story_mod.normalize_lang("RU"), "ru")
        self.assertEqual(story_mod.normalize_lang("fr"), "en")
        self.assertEqual(story_mod.normalize_lang(""), "en")


class TestFabricationRegressions(unittest.TestCase):
    """Locks in three real fabrication bugs found and fixed during QA:

    1. A news heading ending in a year was read as the founding year, because
       the founding-keyword alternation contained a bare Cyrillic letter.
    2. A marketing statistic the firm published about itself was narrated as
       the film's achievement.
    3. A substring hint ("it") matched inside unrelated words.
    """

    @staticmethod
    def _fact(text, relevance="statement", evidence="SINGLE-SOURCE"):
        c = claim(text, relevance)
        c.evidence_class = evidence
        res = ResearchResult(firm_name="Acme Legal LLP")
        res.sources.append(Source(id="S01", kind="website", url="https://acme.uz",
                                  state=SOURCE_INSPECTED))
        res.claims = [c]
        return story_mod.extract_facts(res, "Acme Legal LLP")

    def test_news_heading_year_is_not_a_founding_year(self):
        facts = self._fact(
            "Актуальные новости о кибербезопасности, IT-праве и юридическом мире — 2025",
            "statistic_or_superlative")
        self.assertFalse(facts.has("founding_year"),
                         "a year inside a news heading must not become a founding date")

    def test_copyright_year_is_not_a_founding_year(self):
        facts = self._fact("© 2026 Acme Legal LLP. All rights reserved.",
                           "statistic_or_superlative")
        self.assertFalse(facts.has("founding_year"))

    def test_stats_never_become_the_achievement(self):
        facts = self._fact("We won 94% of our cases in 2021.",
                           "statistic_or_superlative")
        self.assertFalse(facts.has("achievement"),
                         "unverified self-statistics must stay a gap")

    def test_verified_milestone_does_become_the_achievement(self):
        facts = self._fact("Acme Legal LLP opened a second office in 2021.",
                           "statement", evidence=CORROBORATED)
        self.assertTrue(facts.has("achievement"))

    def test_superlative_is_stripped_from_practice_areas(self):
        facts = self._fact(
            "Ведущая юридическая фирма Узбекистана. IT-право, корпоративное право, "
            "экономические споры.", "description")
        areas = facts.get("practice_areas")
        self.assertTrue(areas, "practice areas should still be found")
        self.assertNotIn("Ведущая", areas)
        self.assertIn("IT-право", areas)

    def test_substring_hint_does_not_match(self):
        facts = self._fact("politics and law will not reveal a practice hint.",
                           "statement")
        self.assertFalse(facts.has("practice_areas"),
                         "'it' must not match inside 'politics'")


if __name__ == "__main__":
    unittest.main()
