# -*- coding: utf-8 -*-
"""Regression tests for the staged documentary workflow.

Covers workflow stages C (interview preparation), D (transcription and interview
analysis), E (chronology) and the extended evidence ledger (stage B).

The tests all use synthetic fixtures. None of them contains real firm history,
real client names, a real Telegram token, or a real interviewee: the point is to
prove the *rules* hold, not to invent content for the film.

The rules these tests defend:

* the agent never invents missing dialogue;
* a quotation is evidence the speaker said it, never proof of the fact;
* nothing is auto-promoted to "verified";
* an unverified claim can never corroborate a verified one;
* the same website cannot corroborate itself;
* undated evidence is kept, not dated by guesswork;
* a finished questionnaire is never silently overwritten.
"""
import io
import json
import os
import tempfile
import unittest
from unittest import mock

from agent_system import chronology, interviews, transcripts
from agent_system.research import (Claim, ResearchResult, claims_from_ledger_csv,
                                   confidence_note, ledger_csv,
                                   privacy_requirement, source_key, stated_year)

SRT = """1
00:00:01,000 --> 00:00:07,500
Interviewer: When did the firm begin?

2
00:00:07,600 --> 00:00:20,000
Partner: I think we started around 2010, maybe 2011, in Tashkent.

3
00:00:20,100 --> 00:00:26,000
Partner: [inaudible]

4
00:00:26,100 --> 00:00:40,000
Partner: It was off the record, but the client Ahmed Karimov paid us in 2012.

5
00:00:40,100 --> 00:00:45,000
Partner: We had 12 employees and roughly 40 cases.

6
00:00:45,100 --> 00:00:50,000
Partner: Yes.
"""

VTT = """WEBVTT

00:00:01.000 --> 00:00:04.000
Interviewer: Who founded the firm?

00:00:04.500 --> 00:00:09.000
Founder: I founded it with two colleagues in 2010.
"""


def _claim(cid, text, url="https://a.example", evc="SINGLE-SOURCE"):
    return Claim(id=cid, text=text, source_id="S1", source_url=url,
                 evidence_class=evc)


class WorkflowTestBase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, content):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        return path


# ------------------------------------------------------------------ stage D
class TestSpeechBackendDetection(unittest.TestCase):
    def test_detection_is_honest_either_way(self):
        info = transcripts.detect_speech_backends()
        self.assertIn("available", info)
        self.assertIn("backends", info)
        self.assertIn("notes", info)
        self.assertIsInstance(info["available"], bool)
        if not info["available"]:
            # No engine: nothing may be claimed, and the notes must tell the
            # human what to do instead.
            self.assertEqual(info["backends"], [])
            self.assertTrue(any("transcript" in n.lower() for n in info["notes"]))
        else:
            for backend in info["backends"]:
                self.assertIn("engine", backend)
                # Nothing on this machine has been exercised end to end, so an
                # engine may never be advertised as verified.
                self.assertFalse(backend["verified"])

    def test_uzbek_limitation_is_always_stated(self):
        info = transcripts.detect_speech_backends()
        self.assertTrue(any("uzbek" in n.lower() for n in info["notes"]))

    def test_transcribe_raises_when_no_engine(self):
        info = transcripts.detect_speech_backends()
        if info["available"]:
            self.skipTest("a local engine is installed; the unavailable path "
                          "cannot be exercised here")
        with self.assertRaises(transcripts.TranscriptionUnavailable):
            transcripts.transcribe_audio("/tmp/does-not-exist.m4a")


class TestTranscribeInvocation(unittest.TestCase):
    """Exercise the command construction without any real engine installed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def _fake_backend(self):
        return {
            "available": True,
            "backends": [{"engine": "whisper.cpp", "binary": "whisper-cli",
                          "path": "/fake/whisper-cli", "verified": False,
                          "capabilities": transcripts.ENGINE_CAPABILITIES["whisper.cpp"]}],
            "ffmpeg": "/usr/bin/ffmpeg",
            "notes": [],
        }

    def test_argv_and_output_loading(self):
        audio = os.path.join(self.tmp, "interview.m4a")
        with open(audio, "wb") as fh:
            fh.write(b"\x00\x01fake audio")
        seen = {}

        class Proc(object):
            returncode = 0
            stdout = ""
            stderr = ""

        def runner(argv):
            seen["argv"] = argv
            # A real engine would write the transcript next to the audio.
            with open(os.path.join(self.tmp, "interview.srt"), "w",
                      encoding="utf-8") as fh:
                fh.write("1\n00:00:01,000 --> 00:00:03,000\nFounder: Hello.\n")
            return Proc()

        with mock.patch.object(transcripts, "detect_speech_backends",
                               self._fake_backend):
            tr = transcripts.transcribe_audio(audio, language="ru", runner=runner)

        argv = seen["argv"]
        self.assertEqual(argv[0], "/fake/whisper-cli")
        self.assertIn(audio, argv)
        self.assertIn("-l", argv)
        self.assertIn("ru", argv)
        self.assertEqual(tr.produced_by, "whisper.cpp")
        self.assertTrue(any("unverified" in n.lower() for n in tr.notes))

    def test_failure_is_reported_not_hidden(self):
        audio = os.path.join(self.tmp, "x.m4a")
        with open(audio, "wb") as fh:
            fh.write(b"x")

        class Bad(object):
            returncode = 2
            stdout = ""
            stderr = "model not found"

        with mock.patch.object(transcripts, "detect_speech_backends",
                               self._fake_backend):
            with self.assertRaises(transcripts.TranscriptionUnavailable) as ctx:
                transcripts.transcribe_audio(audio, runner=lambda a: Bad())
        self.assertIn("model not found", str(ctx.exception))


class TestTranscriptParsing(unittest.TestCase):
    def test_parse_timestamp_forms(self):
        self.assertAlmostEqual(transcripts.parse_timestamp("00:01:02,500"), 62.5)
        self.assertAlmostEqual(transcripts.parse_timestamp("01:02.5"), 62.5)
        self.assertAlmostEqual(transcripts.parse_timestamp("1:02:03.250"), 3723.25)
        with self.assertRaises(transcripts.TranscriptError):
            transcripts.parse_timestamp("not-a-time")

    def test_srt_speakers_timing_and_inaudible(self):
        segs = transcripts.parse_srt(SRT)
        self.assertEqual(len(segs), 6)
        self.assertEqual(segs[0].speaker, "Interviewer")
        self.assertEqual(segs[1].speaker, "Partner")
        self.assertAlmostEqual(segs[1].start, 7.6)
        self.assertAlmostEqual(segs[1].end, 20.0)
        # An inaudible segment is preserved and flagged, never filled in.
        self.assertTrue(segs[2].inaudible)
        self.assertIn("inaudible", segs[2].text.lower())

    def test_inaudible_is_never_treated_as_content(self):
        seg = transcripts.Segment(index=1, text="[inaudible]", inaudible=True)
        self.assertTrue(transcripts.is_inaudible(seg.text))
        self.assertTrue(transcripts.is_inaudible("..."))
        self.assertFalse(transcripts.is_inaudible("We founded the firm."))

    def test_vtt_parses_and_strips_webvtt_header(self):
        segs = transcripts.parse_vtt(VTT)
        self.assertEqual(len(segs), 2)
        self.assertEqual(segs[0].speaker, "Interviewer")

    def test_json_transcript(self):
        payload = json.dumps({"segments": [
            {"start": 1.0, "end": 4.0, "speaker": "Founder",
             "text": "I founded it in 2010."}]})
        segs = transcripts.parse_json(payload)
        self.assertEqual(len(segs), 1)
        self.assertEqual(segs[0].speaker, "Founder")

    def test_bad_json_is_an_error_not_silence(self):
        with self.assertRaises(transcripts.TranscriptError):
            transcripts.parse_json("{not json")
        with self.assertRaises(transcripts.TranscriptError):
            transcripts.parse_json('{"nothing": 1}')

    def test_plain_text_invents_no_timing(self):
        segs = transcripts.parse_txt("Founder: We began in 2010.")
        self.assertEqual(len(segs), 1)
        self.assertFalse(segs[0].timed)
        self.assertEqual(segs[0].stamp(), "")

    def test_hour_only_prefix_is_not_mistaken_for_a_speaker(self):
        speaker, text = transcripts._split_speaker("In 2010: we began")
        self.assertEqual(speaker, "")
        self.assertIn("we began", text)

    def test_missing_file_is_reported(self):
        with self.assertRaises(transcripts.TranscriptError):
            transcripts.load_transcript("/tmp/definitely-not-here.srt")


class TestInterviewAnalysis(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.path = os.path.join(self.tmp, "interview.srt")
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(SRT)
        self.analysis = transcripts.analyse_file(self.path, language="en")

    def tearDown(self):
        self._tmp.cleanup()

    def test_statements_are_attributed_and_never_auto_verified(self):
        self.assertTrue(self.analysis.claims)
        for c in self.analysis.claims:
            self.assertEqual(c.evidence_class, "SINGLE-SOURCE")
            self.assertFalse(c.safe_for_public)
            self.assertFalse(c.quoted_ok)
            self.assertEqual(c.review_required, "publication-review")
            self.assertTrue(c.attributed_to)

    def test_questions_are_not_stored_as_statements(self):
        # "When did the firm begin?" is the interviewer's wording and must not
        # be quotable as a claim about the firm.
        self.assertTrue(self.analysis.questions)
        for c in self.analysis.claims:
            self.assertFalse(c.text.strip().endswith("?"),
                             "a question leaked into the claims list")

    def test_answer_keeps_the_question_that_prompted_it(self):
        linked = [c for c in self.analysis.claims if c.preceded_by]
        self.assertTrue(linked)
        self.assertIn("begin", linked[0].preceded_by.lower())

    def test_timestamps_are_preserved(self):
        self.assertTrue(all(c.timestamp for c in self.analysis.claims))
        self.assertTrue(self.analysis.claims[0].start > 0)

    def test_hedges_are_flagged(self):
        hedged = [c for c in self.analysis.claims if c.uncertainty]
        self.assertTrue(hedged, "the 'I think … maybe' hedge was not detected")
        joined = " ".join(m for c in hedged for m in c.uncertainty)
        self.assertIn("i think", joined)

    def test_inaudible_segment_recorded_as_gap_not_content(self):
        self.assertIn(3, self.analysis.inaudible_segments)
        self.assertTrue(any("inaudible" in g.lower() for g in self.analysis.gaps))
        for c in self.analysis.claims:
            self.assertNotIn("[inaudible]", c.text.lower())

    def test_privacy_markers_quarantine_statements(self):
        self.assertIn("off the record", self.analysis.privacy_flags)
        self.assertIn("client-mention", self.analysis.privacy_flags)
        flagged = [c for c in self.analysis.claims if c.privacy_flags]
        self.assertTrue(flagged)
        self.assertTrue(any("confidentiality review" in n
                            for c in flagged for n in c.needs_confirmation))

    def test_names_dates_and_numbers_are_flagged_for_humans(self):
        terms = self.analysis.flagged_terms
        self.assertIn("2010", terms.get("years", []))
        self.assertIn("12", terms.get("numbers", []))
        self.assertIn("40", terms.get("numbers", []))
        self.assertIn("Ahmed Karimov", terms.get("proper_nouns", []))

    def test_years_are_not_double_reported_as_numbers(self):
        numbers = self.analysis.flagged_terms.get("numbers", [])
        for year in self.analysis.flagged_terms.get("years", []):
            self.assertNotIn(year, numbers)
        self.assertFalse(any(n.endswith(",") for n in numbers),
                         "trailing punctuation leaked into the numbers list")

    def test_short_filler_is_not_a_claim(self):
        self.assertFalse(any(c.text.strip().lower() == "yes."
                             for c in self.analysis.claims))

    def test_findings_and_permission_checklist_are_written(self):
        out = os.path.join(self.tmp, "out")
        paths = transcripts.write_analysis(out, self.analysis)
        for path in paths.values():
            self.assertTrue(os.path.exists(path))
        findings = open(paths["interview_findings.md"], encoding="utf-8").read()
        self.assertIn("not evidence that it is historically true", findings)
        self.assertIn("Anti-fabrication", findings)
        checklist = open(paths["permission_checklist.md"], encoding="utf-8").read()
        self.assertIn("Quote permitted?", checklist)
        payload = json.load(open(paths["interview_analysis.json"], encoding="utf-8"))
        self.assertEqual(payload["claim_count"], len(self.analysis.claims))

    def test_claim_ids_are_scoped_to_the_source_file(self):
        """F4: two interviews must never share a claim id.

        The chronology cites claim ids; when every transcript numbered its
        statements from ``iq01``, two interviewees looked like one source
        contradicting itself.
        """
        other = os.path.join(self.tmp, "second.srt")
        with open(other, "w", encoding="utf-8") as fh:
            fh.write(SRT.replace("Ahmed Karimov", "Dilnoza Yusupova"))
        a = transcripts.analyse_file(self.path, language="en")
        b = transcripts.analyse_file(other, language="en")
        self.assertTrue(a.claims and b.claims)
        for analysis, stem in ((a, "interview"), (b, "second")):
            self.assertTrue(all(c.id.startswith(stem + "-")
                                for c in analysis.claims),
                            "a claim id must name the file it came from")
            self.assertTrue(all(q["id"].startswith(stem + "-")
                                for q in analysis.questions))
        overlap = {c.id for c in a.claims} & {c.id for c in b.claims}
        self.assertEqual(overlap, set(),
                         "claim ids collided across transcripts: %s" % overlap)

    def test_no_speakers_labels_produce_a_gap(self):
        p = os.path.join(self.tmp, "nolabels.txt")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("The firm began in 2010 and grew steadily over the years.")
        a = transcripts.analyse_file(p)
        self.assertEqual(a.speakers, [])
        self.assertTrue(any("speaker" in g.lower() for g in a.gaps))
        for c in a.claims:
            # Unattributed speech must not be presented as a named person's words.
            self.assertEqual(c.attributed_to, "unattributed speaker")


# ------------------------------------------------------------------ stage C
class TestInterviewPreparation(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name

    def tearDown(self):
        self._tmp.cleanup()

    def test_every_gap_gets_a_question_with_a_corroboration_path(self):
        missing = ["founding_year", "achievement", "new_office"]
        plans = interviews.build_all("Firm (synthetic)", missing_facts=missing)
        for plan in plans:
            gap_qs = [q for q in plan.questions if q.closes_gap]
            for q in gap_qs:
                self.assertTrue(q.corroboration,
                                "gap question without a corroboration path")
                self.assertTrue(q.addresses)
            closed = {q.closes_gap for q in gap_qs}
            for gap in missing:
                self.assertIn(gap, closed,
                              "%s is not addressed in the %s plan" % (gap, plan.role))
            # No gap may be asked about twice — the narrative questions already
            # close some of them.
            self.assertEqual(len(closed), len(gap_qs),
                             "the %s plan asks about the same gap more than once"
                             % plan.role)

    def test_core_enquiry_areas_are_all_covered(self):
        plan = interviews.build_plan(interviews.ROLE_MANAGING, "Firm (synthetic)")
        text = " ".join(q.text.lower() for q in plan.questions)
        for theme in ("began", "office", "hardest", "changed", "principle",
                      "going next"):
            self.assertIn(theme, text)

    def test_followups_cover_vague_dates_conflicts_and_confidentiality(self):
        plan = interviews.build_plan(interviews.ROLE_FOUNDING, "Firm (synthetic)")
        blob = " ".join(f.lower() for q in plan.questions for f in q.followups)
        self.assertIn("which year", blob)
        self.assertIn("disagree", blob)
        self.assertIn("privileged", blob)

    def test_founding_role_gets_founding_questions_and_partners_do_not(self):
        founding = interviews.build_plan(interviews.ROLE_FOUNDING, "F")
        partners = interviews.build_plan(interviews.ROLE_PARTNERS, "F")
        self.assertTrue(any(q.id.startswith("T1") for q in founding.questions))
        self.assertFalse(any(q.id.startswith("T1") for q in partners.questions))

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            interviews.build_plan("chief_executive", "F")

    def test_finished_questionnaire_is_never_overwritten(self):
        plans = interviews.build_all("Firm (synthetic)")
        first = interviews.write_plans(self.tmp, plans)
        target = first[interviews.ROLE_PARTNERS]
        self.assertTrue(target)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("FINAL — human reviewed, do not replace\n")
        before = open(target, encoding="utf-8").read()
        again = interviews.write_plans(self.tmp, plans)
        self.assertEqual(again[interviews.ROLE_PARTNERS], "")
        self.assertEqual(open(target, encoding="utf-8").read(), before)

    def test_force_is_required_to_replace(self):
        plans = interviews.build_all("Firm (synthetic)")
        interviews.write_plans(self.tmp, plans)
        target = os.path.join(self.tmp, interviews.ROLE_FILENAMES[interviews.ROLE_PARTNERS])
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("changed\n")
        forced = interviews.write_plans(self.tmp, plans, force=True)
        self.assertTrue(forced[interviews.ROLE_PARTNERS])
        self.assertIn("Interview plan", open(target, encoding="utf-8").read())

    def test_plan_markdown_has_no_duplicate_sections(self):
        plan = interviews.build_plan(interviews.ROLE_MANAGING, "Firm (synthetic)",
                                     missing_facts=["founding_year"])
        md = interviews.plan_markdown(plan)
        headings = [ln for ln in md.splitlines() if ln.startswith("###")]
        self.assertEqual(len(headings), len(set(headings)))
        self.assertIn("DRAFT", md)
        self.assertIn("does not contact", md)

    def test_plan_states_the_agent_does_not_interview(self):
        plans = interviews.build_all("Firm (synthetic)")
        for plan in plans:
            md = interviews.plan_markdown(plan)
            self.assertIn("human interviewer", md)


# ------------------------------------------------------------------ stage E
class TestChronology(unittest.TestCase):
    def test_undated_claims_are_kept_not_dropped(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "The firm was founded in 2010."),
            _claim("C2", "We serve clients across the region."),
        ])
        self.assertEqual(len(tl.entries), 1)
        self.assertEqual(len(tl.undated), 1)
        self.assertTrue(any("no year" in g for g in tl.gaps))

    def test_unverified_claim_cannot_corroborate_a_verified_one(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "Founded in 2010.", "https://a.example", "VERIFIED"),
            _claim("C2", "Founded around 2010.", "https://b.example", "UNVERIFIED"),
        ])
        for entry in tl.entries:
            self.assertNotIn("corroborated by", entry.confidence)

    def test_two_independent_publishers_do_corroborate(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "Founded in 2010.", "https://a.example", "VERIFIED"),
            _claim("C2", "Founded in 2010.", "https://b.example", "CORROBORATED"),
        ])
        self.assertTrue(any("corroborated by 2 independent" in e.confidence
                            for e in tl.entries))

    def test_one_website_cannot_corroborate_itself(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "Founded in 2010.", "https://firm.example/page-a", "VERIFIED"),
            _claim("C2", "Founded in 2010.", "https://www.firm.example/page-b", "VERIFIED"),
        ])
        for entry in tl.entries:
            self.assertNotIn("corroborated by", entry.confidence)

    def test_conflicting_years_are_reported_not_averaged(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "The firm was founded in 2010."),
            _claim("C2", "The firm was founded in 2011."),
        ])
        self.assertTrue(tl.conflicts)
        self.assertTrue(any("2010" in c and "2011" in c for c in tl.conflicts))

    def test_multi_year_claim_is_flagged_ambiguous(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "Founded sometime in 2010 or 2012."),
        ])
        entry = tl.entries[0]
        self.assertEqual(entry.year, 2010)
        self.assertIn("several years", entry.ambiguity)

    def test_documented_and_interpretation_are_separate_sections(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "The firm was founded in 2010.", "https://x.example", "VERIFIED"),
        ])
        md = chronology.timeline_markdown(tl)
        self.assertIn("Documented history", md)
        self.assertIn("Proposed interpretation (NOT evidence)", md)
        self.assertLess(md.index("Documented history"),
                        md.index("Proposed interpretation"))

    def test_significance_never_upgrades_an_evidence_class(self):
        tl = chronology.build_timeline("F", [
            _claim("C1", "The firm was founded in 2010.", "https://x.example",
                   "SINGLE-SOURCE"),
        ])
        entry = tl.entries[0]
        self.assertFalse(entry.documented)
        self.assertIn("single-source", entry.significance.lower())

    def test_timeline_files_are_written(self):
        tl = chronology.build_timeline("F", [_claim("C1", "Founded in 2010.")])
        with tempfile.TemporaryDirectory() as d:
            paths = chronology.write_timeline(d, tl)
            self.assertTrue(os.path.exists(paths["markdown"]))
            payload = json.load(open(paths["json"], encoding="utf-8"))
            self.assertEqual(payload["firm_name"], "F")
            self.assertIn("Anti-fabrication",
                          open(paths["markdown"], encoding="utf-8").read())

    def test_attributed_interview_claims_can_be_timelined(self):
        seg = transcripts.Segment(index=1, start=1.0, end=4.0, speaker="Founder",
                                  text="We founded the firm in 2010.")
        analysis = transcripts.analyse_transcript(
            transcripts.Transcript(kind="txt", language="en",
                                   source_path="i.srt", segments=[seg]))
        tl = chronology.build_timeline("F", analysis.claims)
        self.assertEqual(len(tl.entries), 1)
        # An interview statement is single-source, so it is never "documented".
        self.assertFalse(tl.entries[0].documented)


# ------------------------------------------------------- stage B (the ledger)
class TestExtendedEvidenceLedger(unittest.TestCase):
    def test_claim_has_the_extended_fields(self):
        c = Claim(id="C1", text="t", source_id="S", source_url="u")
        for field in ("excerpt", "source_date", "event_date", "confidence",
                      "contradiction", "privacy_review"):
            self.assertTrue(hasattr(c, field))

    def test_ledger_csv_carries_the_extended_columns(self):
        res = ResearchResult(firm_name="F")
        res.claims.append(Claim(id="C1", text="Founded in 2010.", source_id="S1",
                                source_url="https://a.example",
                                evidence_class="SINGLE-SOURCE",
                                excerpt="Founded in 2010. Three lawyers.",
                                confidence=confidence_note("SINGLE-SOURCE"),
                                event_date="2010",
                                privacy_review=privacy_requirement("statement", False)))
        header = ledger_csv(res).splitlines()[0]
        for col in ("excerpt", "source_date", "event_date", "confidence",
                    "contradiction", "privacy_review"):
            self.assertIn(col, header)

    def test_ledger_round_trips_losslessly(self):
        res = ResearchResult(firm_name="F")
        original = Claim(id="C1", text="Founded in 2010.", source_id="S1",
                         source_url="https://a.example", page_title="About",
                         evidence_class="CORROBORATED", safe_for_public=True,
                         relevance="statement", needs="none",
                         excerpt="Founded in 2010 in Tashkent.",
                         confidence=confidence_note("CORROBORATED"),
                         event_date="2010",
                         privacy_review=privacy_requirement("statement", True))
        res.claims.append(original)
        back = claims_from_ledger_csv(ledger_csv(res))
        self.assertEqual(len(back), 1)
        for field in ("id", "text", "source_id", "source_url", "page_title",
                      "evidence_class", "safe_for_public", "relevance", "needs",
                      "excerpt", "confidence", "event_date", "privacy_review"):
            self.assertEqual(getattr(back[0], field), getattr(original, field))

    def test_old_ledger_without_new_columns_still_loads(self):
        old = ("claim_id,claim,evidence_class,safe_for_public,source_id,"
               "source_url,page_title,relevance,needs\n"
               "C001,Founded in 2010.,SINGLE-SOURCE,no,S1,https://a.example,"
               "About,statement,\n")
        claims = claims_from_ledger_csv(old)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].evidence_class, "SINGLE-SOURCE")
        self.assertEqual(claims[0].confidence, "")

    def test_stated_year_reads_only_what_the_source_says(self):
        self.assertEqual(stated_year("Founded in 2010."), "2010")
        self.assertEqual(stated_year("I think 2010 or 2012."), "2010")
        self.assertEqual(stated_year("No year here."), "")
        # A copyright footer is not a founding year; the caller must not treat
        # this as one, and the field is documented as "as stated by source".
        self.assertEqual(stated_year("© 2026 Acme"), "2026")

    def test_privacy_requirement_never_clears_client_matter(self):
        text = privacy_requirement("case_figure", True)
        self.assertIn("client", text.lower())
        self.assertNotIn("cleared for public", text.lower())

    def test_source_key_detects_the_same_publisher(self):
        self.assertEqual(source_key("https://www.acme.uz/a"),
                         source_key("https://acme.uz/b"))
        self.assertNotEqual(source_key("https://acme.uz/a"),
                            source_key("https://other.uz/a"))
        self.assertEqual(source_key("Founder Name"), "founder name")
        self.assertEqual(source_key(""), "")

    def test_report_lists_verification_and_permission_detail(self):
        from agent_system.research import report_markdown
        res = ResearchResult(firm_name="F")
        res.claims.append(Claim(id="C1", text="Founded in 2010.", source_id="S1",
                                source_url="https://a.example",
                                confidence=confidence_note("SINGLE-SOURCE"),
                                privacy_review=privacy_requirement("statement", False)))
        md = report_markdown(res)
        self.assertIn("Verification and permission detail", md)
        self.assertIn("Single source only", md)


if __name__ == "__main__":
    unittest.main()
