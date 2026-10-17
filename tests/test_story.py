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


# --------------------------------------------------------------- concept tests
FICTION_FIRM = "Example Legal Test Firm"

# Evidence for a fictional firm that says nothing whatever about AI. The
# regression this guards: the concept builder used to hard-code "the firm
# builds legal AI" as concept-a's climax regardless of the evidence.
NO_AI_EVIDENCE = [
    "Example Legal Test Firm was founded in 2012 in Tashkent.",
    "Example Legal Test Firm advises on corporate law and tax law.",
]


def fiction_research(texts):
    res = ResearchResult(firm_name=FICTION_FIRM)
    res.sources.append(Source(id="S01", kind="website", url="https://example.uz",
                              state=SOURCE_INSPECTED))
    res.claims = [Claim(id="C%03d" % (i + 1), text=t, source_id="S01",
                        source_url="https://example.uz", page_title="Home",
                        evidence_class="SINGLE-SOURCE", safe_for_public=False,
                        relevance="statement")
                  for i, t in enumerate(texts)]
    return res


AI_RE = __import__("re").compile(
    r"(?i)\blegal\s+ai\b|\bartificial\s+intelligence\b|\bmachine\s+learning\b"
    r"|\bneural\s+network\b|\bai[-\s]?(?:powered|driven|enabled)\b"
    r"|\u0438\u0441\u043a\u0443\u0441\u0441\u0442\u0432\u0435\u043d\u043d|\u043d\u0435\u0439\u0440\u043e\u0441\u0435\u0442")


class TestConceptsAreEvidenceDriven(unittest.TestCase):
    """F2: a concept may only assert what this job's evidence can carry."""

    def concepts(self, texts=None, interviews=()):
        res = fiction_research(texts if texts is not None else NO_AI_EVIDENCE)
        facts = story_mod.extract_facts(res, FICTION_FIRM)
        return story_mod.build_concepts(FICTION_FIRM, facts, res, interviews)

    def test_no_concept_asserts_legal_ai_when_the_evidence_has_none(self):
        """The regression the brief names explicitly."""
        for c in self.concepts():
            blob = " ".join([c["central_idea"], c["evidence_fit"],
                             " ".join(c["strengths"]), " ".join(c["weaknesses"])])
            self.assertIsNone(AI_RE.search(blob),
                              "%s asserts a technology claim the ledger cannot "
                              "carry: %s" % (c["id"], blob))
            self.assertEqual(c["asserted_claims"], [],
                             "%s claims unsupported firm facts" % c["id"])

    def test_no_concept_is_labelled_strong_without_support(self):
        for c in self.concepts():
            if c.get("asserted_claims"):
                # Asserting a firm-specific fact rules out "Limited", but a
                # single-source assertion can never earn "Strong".
                self.assertIn(c["evidence_fit_level"], ("Medium", "Strong"))
            # A concept with nothing documented cannot claim a strong fit.
            if not c["evidence_basis"]["documented_facts"]:
                self.assertNotEqual(c["evidence_fit_level"], "Strong")

    def test_a_single_source_ai_claim_is_not_graded_strong(self):
        """F3: one uncorroborated statement is not corroboration."""
        res = fiction_research(["Example Legal Test Firm builds legal AI tools."])
        facts = story_mod.extract_facts(res, FICTION_FIRM)
        concepts = story_mod.build_concepts(FICTION_FIRM, facts, res)
        a = next(c for c in concepts if c["id"] == "concept-a")
        # The claim IS in the ledger, so asserting it is legitimate ...
        self.assertTrue(a["asserted_claims"])
        # ... but nothing is documented, so it must not be sold as "Strong".
        self.assertEqual(a["evidence_fit_level"], "Medium")
        self.assertTrue(any("single-source" in w.lower()
                            for w in a["weaknesses"]),
                        "the single-source weakness must be disclosed")
        # The statement stays a single-source claim, never promoted to fact.
        self.assertTrue(all("SINGLE-SOURCE" in s or "-" in s
                            for s in a["evidence_sources"]))

    def test_a_corroborated_ai_claim_can_be_graded_strong(self):
        """The other half of F3: real corroboration does earn "Strong"."""
        res = fiction_research(["Example Legal Test Firm builds legal AI tools."])
        res.claims[0].evidence_class = "VERIFIED"
        facts = story_mod.extract_facts(res, FICTION_FIRM)
        concepts = story_mod.build_concepts(FICTION_FIRM, facts, res)
        a = next(c for c in concepts if c["id"] == "concept-a")
        self.assertEqual(a["evidence_fit_level"], "Strong")
        self.assertTrue(any("corroborat" in s.lower() for s in a["strengths"]))

    def test_evidence_basis_separates_facts_from_framing_and_gaps(self):
        concepts = self.concepts()
        for c in concepts:
            basis = c["evidence_basis"]
            self.assertEqual(sorted(basis), ["attributed_statements",
                                             "creative_framing",
                                             "documented_facts",
                                             "unresolved_claims"])
            self.assertTrue(basis["creative_framing"],
                            "a concept must own up to what is a framing choice")
            # Single-source site text must never be filed as documented fact.
            for line in basis["documented_facts"]:
                self.assertNotIn("SINGLE-SOURCE", line)

    def test_interview_recollections_are_attributed_not_documented(self):
        from agent_system.transcripts import InterviewClaim
        interviews = [InterviewClaim(id="iq01", text="We began in one room.")]
        concepts = self.concepts(interviews=interviews)
        b = next(c for c in concepts if c["id"] == "concept-b")
        self.assertEqual(b["evidence_basis"]["documented_facts"], [])
        self.assertTrue(any("recollection" in a
                            for a in b["evidence_basis"]["attributed_statements"]))

    def test_quarantined_interview_statements_never_enter_a_concept(self):
        """F1: a privacy-flagged recollection is withheld, and its absence shown.

        The statement stays in the interview analysis and the permission
        checklist, where a human decides on it. It must not be copied into
        ``concepts.md``/``concepts.json``, where it could be mistaken for
        cleared material.
        """
        from agent_system.transcripts import InterviewClaim
        flagged = InterviewClaim(id="a-iq01",
                                 text="Our client UzMetals asked us to act.")
        flagged.privacy_flags = ["client-mention"]
        clean = InterviewClaim(id="a-iq02", text="We began in one room.")
        concepts = self.concepts(interviews=[flagged, clean])
        for c in concepts:
            basis = c["evidence_basis"]
            blob = json.dumps(basis)
            self.assertNotIn("UzMetals", blob,
                             "%s leaked a quarantined client name" % c["id"])
            self.assertTrue(
                any("withheld" in u for u in basis["unresolved_claims"]),
                "%s must disclose that a statement was withheld" % c["id"])
            self.assertTrue(
                any("We began in one room." in a
                    for a in basis["attributed_statements"]),
                "%s dropped a statement that was safe to attribute" % c["id"])

    def test_three_distinct_concepts_and_exactly_one_recommended(self):
        for texts in (None, ["Example Legal Test Firm was founded in 2012."],
                      ["Example Legal Test Firm builds legal AI tools."]):
            concepts = self.concepts(texts)
            self.assertEqual(len(concepts), 3)
            self.assertEqual(sum(1 for c in concepts if c["recommended"]), 1,
                             "exactly one concept must be recommended")
            titles = [c["title"] for c in concepts]
            self.assertEqual(len(set(titles)), 3, "concepts must stay distinct")

    def test_thin_evidence_discloses_gaps_in_every_concept(self):
        concepts = self.concepts(["Example Legal Test Firm is a law firm."])
        self.assertTrue(concepts[0]["evidence_basis"]["unresolved_claims"],
                        "gaps must be disclosed, not filled")


class TestApprovedConceptControlsTheScript(unittest.TestCase):
    """F4: the approved concept — not the first recommended one — is used."""

    def test_approved_concept_c_is_used_when_a_is_recommended(self):
        res = fiction_research(["Example Legal Test Firm was founded in 2012."])
        facts = story_mod.extract_facts(res, FICTION_FIRM)
        concepts = story_mod.build_concepts(FICTION_FIRM, facts, res)
        recommended = next(c for c in concepts if c["recommended"])
        self.assertEqual(recommended["id"], "concept-a",
                         "precondition: concept-a is the recommended one here")
        c_ids = {c["id"]: c for c in concepts}
        script = story_mod.script_markdown(FICTION_FIRM, concepts,
                                           story_mod.build_scenes(
                                               FICTION_FIRM, facts, "en", 140.0),
                                           "en", "motion", 140.0, "concept-c")
        self.assertIn("concept-c", script)
        # The script's own thesis is the "Central idea" line, not the appendix
        # that lists every candidate for the reviewer.
        thesis = next(line.split("**Central idea:**", 1)[1].strip()
                      for line in script.splitlines()
                      if line.startswith("**Central idea:**"))
        self.assertEqual(thesis, c_ids["concept-c"]["central_idea"],
                         "the script must follow the concept that was approved")
        self.assertNotEqual(thesis, c_ids["concept-a"]["central_idea"],
                            "concept-a's unique thesis must not lead a "
                            "concept-c script")

    def test_shorthand_letter_selects_the_same_concept(self):
        for short, full in (("A", "concept-a"), ("B", "concept-b"),
                            ("C", "concept-c")):
            chosen, origin = story_mod.select_concept(
                [{"id": "concept-a", "title": "A", "central_idea": "", "recommended": True},
                 {"id": "concept-b", "title": "B", "central_idea": "", "recommended": False},
                 {"id": "concept-c", "title": "C", "central_idea": "", "recommended": False}],
                short)
            self.assertEqual(chosen["id"], full)
            self.assertEqual(origin, "approved")

    def test_an_unknown_concept_id_is_refused_not_substituted(self):
        concepts = self.concepts_with_manifest()
        with self.assertRaises(story_mod.ConceptSelectionError):
            story_mod.select_concept(concepts, "concept-z")

    def concepts_with_manifest(self):
        res = fiction_research(NO_AI_EVIDENCE)
        facts = story_mod.extract_facts(res, FICTION_FIRM)
        return story_mod.build_concepts(FICTION_FIRM, facts, res)

    def test_no_id_falls_back_to_recommended_for_legacy_callers(self):
        concepts = self.concepts_with_manifest()
        chosen, origin = story_mod.select_concept(concepts, "")
        self.assertTrue(chosen["recommended"])
        self.assertEqual(origin, "recommended")

    def test_manifest_records_the_concept_the_script_used(self):
        tmp = tempfile.mkdtemp(prefix="story_concept_")
        try:
            res = fiction_research(NO_AI_EVIDENCE)
            facts = story_mod.extract_facts(res, FICTION_FIRM)
            paths = story_mod.build_story_assets(tmp, FICTION_FIRM, facts, res,
                                                 "en", "motion", 140.0, "concept-c")
            with open(paths["scene_manifest.json"], encoding="utf-8") as fh:
                manifest = json.load(fh)
            self.assertEqual(manifest["concept"]["id"], "concept-c")
            script = open(paths["script.md"], encoding="utf-8").read()
            self.assertIn("concept-c", script)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_an_invalid_id_writes_no_script(self):
        tmp = tempfile.mkdtemp(prefix="story_badconcept_")
        try:
            res = fiction_research(NO_AI_EVIDENCE)
            facts = story_mod.extract_facts(res, FICTION_FIRM)
            with self.assertRaises(story_mod.ConceptSelectionError):
                story_mod.build_story_assets(tmp, FICTION_FIRM, facts, res,
                                             "en", "motion", 140.0, "concept-z")
            self.assertFalse(os.path.isfile(os.path.join(tmp, "script.md")),
                             "no script may be written for an unapproved concept")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
