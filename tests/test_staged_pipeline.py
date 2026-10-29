# -*- coding: utf-8 -*-
"""test_staged_pipeline.py — regression + integration tests for the staged,
human-gated documentary workflow (``agent_system/pipeline.py``).

What this module proves, deterministically and offline:

* the staged workflow **stops after research** and writes *no* script and *no*
  video before a human approves the research gate;
* no script is written and no video rendered before the **concept** gate is
  approved either — the ordering the brief requires is actually enforced;
* each gate is mandatory: advancing without the approval changes nothing;
* a job paused today is **resumable later** from the job directory alone (a new
  process, no in-memory carry-over), and the resumed render uses the *same*
  effective render spec (caller overrides survive);
* **duplicate execution is prevented**: a second concurrent/duplicate call loses
  the atomic claim and does no work; a completed job is never re-run;
* **artifacts are isolated** between jobs and each re-run writes a new
  ``revisions/rN`` directory rather than overwriting an approved file;
* the pre-existing single-pass workflow is **unchanged** when ``staged`` is off;
* privacy safeguards hold: a statement flagged as client-identifying is kept out
  of the public-safe set and the permission checklist is produced;
* interview statements enter the chronology as ``SINGLE-SOURCE`` and never
  upgrade a documented event to "corroborated".

Hard rules honoured here:
  * no real Telegram API call, no bot token, no real user id;
  * every job runs in a temp directory; nothing is written into the repo;
  * no network: the research fetcher is injected and canned;
  * renders are small (320x180@8) or skipped, and are always verified with
    ffprobe when they do run.
"""
import json
import os
import shutil
import tempfile
import unittest

from agent_system import chronology as chronology_mod
from agent_system import pipeline
from agent_system import story as story_mod
from agent_system import transcripts as transcripts_mod
from agent_system.config import Config
from agent_system.jobs import JobStore
from agent_system.orchestrator import (
    JobRequest, _preview_spec, final_qa_checks, run_job, sanitize_request,
)
from agent_system.video import spec as video_spec
from tests.fakes import html_pages

FIRM = "Acme Legal LLP"
SITE = "https://acme.uz"

PAGE = """<html><head><title>Acme Legal LLP</title></head><body>
<h1>Acme Legal LLP</h1>
<p>Acme Legal LLP was founded in 2010 in Tashkent.</p>
<p>In 2016 the firm opened a second office in Navoi.</p>
<p>In 2019 the firm was ranked by a legal directory.</p>
<p>Acme advises on corporate law, tax law and IT law, including labour disputes.</p>
</body></html>"""

# A transcript with: a hedged date, a named client (privacy), and a dated event.
TRANSCRIPT = """1
00:00:01,000 --> 00:00:06,000
[Managing Partner]: The firm was founded in 2010, I think, in a single room.

2
00:00:07,000 --> 00:00:12,000
[Managing Partner]: Our client UzMetals then asked us to handle a dispute.

3
00:00:13,000 --> 00:00:18,000
[Managing Partner]: We opened the Navoi office in 2016 with three lawyers.
"""

# Deliberately overlaps the 2010 founding claim with a *different* year, to make
# the conflict detector fire (2010 vs 2011).
CONFLICTING = """1
00:00:01,000 --> 00:00:05,000
[Founding Partner]: Actually the firm was established in 2011.
"""

SMALL = {"width": 320, "height": 180, "fps": 8}


class StagedBase(unittest.TestCase):
    """A temp project root per test: nothing touches the real repository."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="staged_test_")
        self._env = {k: os.environ.get(k) for k in
                     ("OUTPUT_DIR", "PROJECT_ROOT", "AGENT_NO_RENDER")}
        os.environ["OUTPUT_DIR"] = os.path.join(self.tmp, "output")
        os.environ["PROJECT_ROOT"] = self.tmp
        os.environ.pop("AGENT_NO_RENDER", None)
        self.cfg = Config.from_env(project_root=self.tmp, detect=False)
        self.cfg.ensure_dirs()
        self.store = JobStore(self.cfg.db_path)
        self.fetcher = html_pages({SITE: PAGE})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    # ------------------------------------------------------------------ helpers
    def make_job(self, **kw):
        raw = {"firm_name": FIRM, "website": SITE, "language": "uz",
               "style": "motion", "duration_sec": 21, "staged": True}
        raw.update(kw)
        req = sanitize_request(raw)
        jid = self.store.create(1, req.style, req.language, req.firm_name,
                                req.duration_sec, 1, params=req.to_dict())
        return jid, req

    def transcript_file(self, text=TRANSCRIPT, name="mp.srt"):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def advance(self, jid, req=None, **kw):
        kw.setdefault("fetcher", self.fetcher)
        kw.setdefault("overrides", SMALL)
        kw.setdefault("enable_preview", False)
        return pipeline.advance_staged(self.cfg, self.store, jid, req, **kw)

    def job_dir(self, jid):
        return self.cfg.job_dir(jid)

    def exists(self, jid, name):
        return os.path.exists(os.path.join(self.job_dir(jid), name))


class TestGateOrdering(StagedBase):
    """The brief's central rule: no script, no video, before approval."""

    def test_first_advance_stops_at_the_research_gate(self):
        jid, req = self.make_job()
        result = self.advance(jid, req)
        self.assertEqual(result["status"], pipeline.STATUS_EVIDENCE_GATE)
        self.assertEqual(result["gate"], "research")
        self.assertEqual(self.store.get(jid)["status"],
                         pipeline.STATUS_EVIDENCE_GATE)

    def test_no_script_and_no_video_after_research(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        for name in ("script.md", "storyboard.md", "final.mp4", "preview.mp4"):
            self.assertFalse(self.exists(jid, name),
                             "%s must not exist before the gates" % name)

    def test_research_evidence_is_written(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        for name in ("research_report.md", "evidence_ledger.csv",
                     "research_raw.json", "research_review.md",
                     "research_summary.json"):
            self.assertTrue(self.exists(jid, name), "missing %s" % name)
        for name in ("chronology.md", "chronology.json"):
            self.assertTrue(os.path.isfile(
                os.path.join(self.job_dir(jid), "chronology", name)))
        for name in ("questionnaireManagingPartner.md",
                     "questionnaireFoundingPartners.md",
                     "questionnairePartners.md", "interview_plans.json"):
            self.assertTrue(os.path.isfile(
                os.path.join(self.job_dir(jid), "interviews", name)))

    def test_advancing_without_approval_does_nothing(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        before = sorted(os.listdir(self.job_dir(jid)))
        again = self.advance(jid)
        self.assertEqual(again["status"], pipeline.STATUS_EVIDENCE_GATE)
        self.assertEqual(sorted(os.listdir(self.job_dir(jid))), before)
        self.assertEqual(pipeline.read_state(self.job_dir(jid))["completed"],
                         ["evidence"])

    def test_script_requires_the_concept_gate(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.assertEqual(self.store.get(jid)["status"],
                         pipeline.STATUS_CONCEPT_GATE)
        self.assertTrue(self.exists(jid, "concepts.md"))
        self.assertFalse(self.exists(jid, "script.md"),
                         "the script must wait for concept approval")

    def test_render_requires_the_storyboard_gate(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        self.assertEqual(self.store.get(jid)["status"],
                         pipeline.STATUS_STORY_GATE)
        self.assertTrue(self.exists(jid, "script.md"))
        self.assertTrue(self.exists(jid, "storyboard.md"))
        self.assertFalse(self.exists(jid, "final.mp4"),
                         "no video may be rendered before storyboard approval")

    def test_full_staged_run_completes_and_validates(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        result = self.advance(jid, approve_storyboard=True)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        self.assertTrue(self.exists(jid, "final.mp4"))
        v = result["validation"]
        self.assertTrue(v["ok"], v.get("errors"))
        self.assertEqual((v["width"], v["height"]), (320, 180))
        self.assertEqual(v["video_codec"], "h264")
        self.assertIsNotNone(v["audio_codec"])
        self.assertGreater(v["duration_sec"], 5)

    def test_completed_job_records_every_step(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        self.advance(jid, approve_storyboard=True)
        state = pipeline.read_state(self.job_dir(jid))
        for step in ("evidence", "concepts", "script", "render"):
            self.assertIn(step, state["completed"])
        self.assertEqual(pipeline.current_step(state), "done")


class TestNoRenderMode(StagedBase):
    def test_no_render_stops_before_ffmpeg(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True, enable_render=False)
        self.advance(jid, approve_concept="A", enable_render=False)
        result = self.advance(jid, approve_storyboard=True, enable_render=False)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result.get("no_render"))
        self.assertFalse(self.exists(jid, "final.mp4"))
        self.assertFalse(self.exists(jid, "preview.mp4"))
        report = open(os.path.join(self.job_dir(jid), "delivery_report.md"),
                      encoding="utf-8").read()
        self.assertIn("No video was rendered", report)

    def test_no_render_forces_preview_off(self):
        """enable_render=False must imply enable_preview=False (existing rule)."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True, enable_render=False,
                     enable_preview=True)
        self.advance(jid, approve_concept="A", enable_render=False,
                     enable_preview=True)
        self.advance(jid, approve_storyboard=True, enable_render=False,
                     enable_preview=True)
        self.assertFalse(self.exists(jid, "preview.mp4"))


class TestResumability(StagedBase):
    """A paused job must be resumable from disk, in a fresh process/state."""

    def test_resume_from_status_alone(self):
        """Resume passing no request object: it is rebuilt from params_json."""
        jid, req = self.make_job()
        self.advance(jid, req)
        # A brand-new pipeline call with request=None must rebuild the request.
        result = pipeline.advance_staged(self.cfg, self.store, jid, None,
                                         fetcher=self.fetcher, overrides=SMALL,
                                         enable_preview=False,
                                         approve_research=True)
        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE)

    def test_resume_uses_a_fresh_revision_directory(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        revs = os.listdir(os.path.join(self.job_dir(jid), "revisions"))
        self.assertEqual(revs, ["r1"])
        # Force a second concepts round by clearing just that step.
        state = pipeline.read_state(self.job_dir(jid))
        state["completed"] = [s for s in state["completed"] if s != "concepts"]
        pipeline.write_state(self.job_dir(jid), completed=state["completed"])
        self.advance(jid)
        revs = sorted(os.listdir(os.path.join(self.job_dir(jid), "revisions")))
        self.assertEqual(revs, ["r1", "r2"])

    def test_resume_preserves_the_effective_render_spec(self):
        """Overrides chosen before a pause must still apply after it."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        # Resume in a call that does NOT carry overrides; the persisted spec wins.
        result = pipeline.advance_staged(
            self.cfg, self.store, jid, None, fetcher=self.fetcher,
            enable_preview=False, approve_storyboard=True)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        v = result["validation"]
        self.assertEqual((v["width"], v["height"], v["fps"]), (320, 180, 8))

    def test_resumed_job_is_visible_as_active(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        active = [j["id"] for j in self.store.list_active()]
        self.assertIn(jid, active,
                      "a paused job is still in flight and must block duplicates")
        self.assertEqual(self.store.find_active_for_user(1)["id"], jid)

    def test_paused_job_survives_a_simulated_restart(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        # recover_interrupted() marks mid-work jobs failed; a paused (human-gated)
        # job must NOT be touched, or a reviewed pause would be destroyed.
        recovered = self.store.recover_interrupted()
        self.assertNotIn(jid, recovered)
        self.assertEqual(self.store.get(jid)["status"],
                         pipeline.STATUS_EVIDENCE_GATE)

    def test_failed_job_needs_explicit_force(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        self.store.fail(jid, "simulated crash")
        blocked = self.advance(jid, approve_research=True)
        self.assertEqual(blocked["status"], "failed")
        forced = self.advance(jid, approve_research=True, force=True)
        self.assertEqual(forced["status"], pipeline.STATUS_CONCEPT_GATE)


class TestDuplicateExecution(StagedBase):
    def test_claim_transition_is_single_winner(self):
        jid, _req = self.make_job()
        self.assertTrue(self.store.claim_transition(jid, ("queued",), "researching"))
        self.assertFalse(self.store.claim_transition(jid, ("queued",), "researching"),
                         "the second claim must lose")

    def test_claim_transition_rejects_unknown_status(self):
        jid, _req = self.make_job()
        with self.assertRaises(ValueError):
            self.store.claim_transition(jid, ("queued",), "not-a-status")

    def test_completed_job_is_not_advanced_again(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        self.advance(jid, approve_storyboard=True)
        stamp = os.path.getmtime(os.path.join(self.job_dir(jid), "final.mp4"))
        again = self.advance(jid, approve_research=True, approve_concept="A",
                             approve_storyboard=True)
        self.assertEqual(again["status"], "completed")
        self.assertEqual(
            os.path.getmtime(os.path.join(self.job_dir(jid), "final.mp4")), stamp,
            "a completed job must not be re-rendered")

    def test_cancelled_job_is_not_advanced(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        self.store.request_cancel(jid)
        result = self.advance(jid, approve_research=True)
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(self.exists(jid, "concepts.md"))

    def test_concurrent_workers_only_one_does_work(self):
        """Simulate two workers racing: the loser must do nothing."""
        jid, req = self.make_job()
        self.advance(jid, req)                 # now paused at the research gate
        # Worker A wins the claim...
        won = self.store.claim_transition(jid, pipeline.RESUMABLE_STATES,
                                          "researching", "worker A")
        self.assertTrue(won)
        # ...so worker B (a duplicate delivery) cannot start.
        result = self.advance(jid, approve_research=True)
        self.assertEqual(result["status"], "busy")
        self.assertTrue(result["warnings"])
        self.assertNotIn("concepts", pipeline.read_state(
            self.job_dir(jid))["completed"])


class TestEvidenceIntegrity(StagedBase):
    """Interview material must never be laundered into established fact."""

    def test_interview_statements_are_single_source(self):
        jid, req = self.make_job()
        path = self.transcript_file()
        self.advance(jid, req, approve_research=True, transcripts=[path])
        analysis_dir = os.path.join(self.job_dir(jid), "interviews", "analysis")
        self.assertTrue(os.path.isdir(analysis_dir))
        analysed = [n for n in os.listdir(analysis_dir)
                    if n.endswith(".json")]
        self.assertTrue(analysed, "the transcript should have been analysed")
        with open(os.path.join(analysis_dir, analysed[0]), encoding="utf-8") as fh:
            payload = json.load(fh)
        self.assertTrue(payload["claims"])
        for claim in payload["claims"]:
            self.assertEqual(claim["evidence_class"], "SINGLE-SOURCE")
            self.assertFalse(claim["safe_for_public"],
                             "no interview claim is public-safe without review")

    def test_interview_statements_cannot_corroborate_an_event(self):
        """A 2010 public claim + a 2010 interview claim is NOT corroboration."""
        jid, req = self.make_job()
        path = self.transcript_file()
        self.advance(jid, req, approve_research=True, transcripts=[path])
        state = pipeline.read_state(self.job_dir(jid))
        rev = "r%d" % state["revision"]
        with open(os.path.join(self.job_dir(jid), "revisions", rev,
                               "chronology.json"), encoding="utf-8") as fh:
            payload = json.load(fh)
        for entry in payload["entries"]:
            if entry["year"] == 2010:
                self.assertFalse(
                    entry["documented"],
                    "an interview statement must not make 2010 'documented'")

    def test_client_identifying_statement_is_flagged(self):
        jid, req = self.make_job()
        path = self.transcript_file()
        self.advance(jid, req, approve_research=True, transcripts=[path])
        analysis_dir = os.path.join(self.job_dir(jid), "interviews", "analysis")
        text = ""
        for name in os.listdir(analysis_dir):
            with open(os.path.join(analysis_dir, name), encoding="utf-8") as fh:
                text += fh.read()
        self.assertIn("UzMetals", text,
                      "the named client should surface so a human can review it")
        self.assertIn("permission", text.lower())

    def test_permission_checklist_is_written(self):
        jid, req = self.make_job()
        path = self.transcript_file()
        self.advance(jid, req, approve_research=True, transcripts=[path])
        analysis_dir = os.path.join(self.job_dir(jid), "interviews", "analysis")
        names = os.listdir(analysis_dir)
        self.assertTrue(any(n.startswith("permission_checklist_") for n in names),
                        names)

    def test_missing_transcript_is_reported_not_ignored(self):
        jid, req = self.make_job()
        result = self.advance(jid, req, approve_research=True,
                              transcripts=[os.path.join(self.tmp, "nope.srt")])
        self.assertTrue(any("not analysed" in w for w in result["warnings"]),
                        result["warnings"])

    def test_no_interview_material_still_permits_concepts(self):
        """Absent interviews must not block the workflow, but must be stated."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        body = open(os.path.join(self.job_dir(jid), "concepts.md"),
                    encoding="utf-8").read()
        self.assertIn("No interview material was supplied", body)

    def test_open_gaps_are_carried_into_the_concepts_round(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        with open(os.path.join(self.job_dir(jid), "research_summary.json"),
                  encoding="utf-8") as fh:
            summary = json.load(fh)
        self.assertIn("question", summary)
        self.assertTrue(summary["question"].endswith("approve."))


class TestArtifactIsolation(StagedBase):
    def test_two_jobs_never_share_a_directory(self):
        a, req = self.make_job()
        b, _ = self.make_job()
        self.assertNotEqual(self.job_dir(a), self.job_dir(b))
        self.advance(a, req)
        self.advance(b, req)
        self.assertTrue(self.exists(a, "research_report.md"))
        self.assertTrue(self.exists(b, "research_report.md"))
        self.assertNotEqual(
            os.path.join(self.job_dir(a), "research_report.md"),
            os.path.join(self.job_dir(b), "research_report.md"))

    def test_approved_concepts_file_is_not_overwritten(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        path = os.path.join(self.job_dir(jid), "concepts.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("HUMAN-EDITED CONCEPTS — DO NOT CLOBBER\n")
        self.advance(jid, approve_concept="A")
        self.assertEqual(open(path, encoding="utf-8").read(),
                         "HUMAN-EDITED CONCEPTS — DO NOT CLOBBER\n")

    def test_reviewed_interview_plan_is_not_overwritten(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        plan = os.path.join(self.job_dir(jid), "interviews",
                            "questionnaireManagingPartner.md")
        with open(plan, "w", encoding="utf-8") as fh:
            fh.write("REVIEWED BY THE FIRM\n")
        # Force the evidence step to run again.
        pipeline.write_state(self.job_dir(jid), completed=[])
        self.advance(jid, req)
        self.assertEqual(open(plan, encoding="utf-8").read(), "REVIEWED BY THE FIRM\n")

    def test_artifacts_are_listed_relative_and_never_absolute_paths(self):
        jid, req = self.make_job()
        result = self.advance(jid, req, approve_research=True)
        for name in result["artifacts"]:
            self.assertFalse(os.path.isabs(name),
                             "artifact list should be relative: %s" % name)


class TestBackwardCompatibility(StagedBase):
    """The original single-pass workflow must be untouched when staged is off."""

    def test_staged_defaults_to_false(self):
        self.assertFalse(JobRequest().staged)
        self.assertEqual(JobRequest().transcripts, [])
        self.assertEqual(JobRequest().concept, "")
        self.assertFalse(sanitize_request({"firm_name": "X"}).staged)

    def test_legacy_job_still_runs_in_one_pass(self):
        req = sanitize_request({"firm_name": FIRM, "website": SITE,
                                "language": "uz", "style": "motion",
                                "duration_sec": 21})
        self.assertFalse(req.staged)
        jid = self.store.create(1, req.style, req.language, req.firm_name,
                                req.duration_sec, 1, params=req.to_dict())
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=lambda payload: True, overrides=SMALL,
                         enable_preview=False)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        for name in ("research_report.md", "concepts.md", "script.md",
                     "storyboard.md", "scene_manifest.json", "final.mp4",
                     "delivery_report.md"):
            self.assertTrue(self.exists(jid, name), "missing %s" % name)
        # The legacy path must NOT have produced staged-only markers.
        self.assertFalse(self.exists(jid, "pipeline_state.json"))

    def test_legacy_job_does_not_pause_at_staged_gates(self):
        req = sanitize_request({"firm_name": FIRM, "website": SITE,
                                "language": "uz", "style": "motion",
                                "duration_sec": 21})
        jid = self.store.create(1, req.style, req.language, req.firm_name,
                                req.duration_sec, 1, params=req.to_dict())
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=lambda payload: True, overrides=SMALL,
                         enable_preview=False)
        self.assertNotIn(result["status"], pipeline.PAUSED_STATUSES)

    def test_sanitize_bounds_transcript_and_concept_input(self):
        req = sanitize_request({"firm_name": FIRM, "staged": True,
                                "transcripts": ["a.srt", "", "  ", "b.vtt"],
                                "concept": "  A  "})
        self.assertTrue(req.staged)
        self.assertEqual(req.transcripts, ["a.srt", "b.vtt"])
        self.assertEqual(req.concept, "A")

    def test_sanitize_caps_transcript_count(self):
        req = sanitize_request({"firm_name": FIRM,
                                "transcripts": ["t%d.srt" % i for i in range(40)]})
        self.assertLessEqual(len(req.transcripts), 24)

    def test_legacy_approval_callback_still_used_for_the_final_gate(self):
        """A staged job with an approve callback consults it before rendering."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        seen = {}

        def approve(payload):
            seen["gaps"] = payload.get("gaps")
            seen["scenes"] = payload.get("scenes")
            return True

        result = self.advance(jid, approve=approve)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        self.assertIn("gaps", seen)
        self.assertIsInstance(seen["scenes"], list)

    def test_declining_the_final_callback_cancels_without_rendering(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        result = self.advance(jid, approve=lambda payload: False)
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(self.exists(jid, "final.mp4"))


class TestAutoApproveCannotBypassGates(StagedBase):
    """Investigation result, pinned as a regression test.

    ``JobRequest.auto_approve`` defaults to True and ``to_dict()`` persists it
    into every job's ``params_json``, so *every* stored job carries
    ``auto_approve: true``. That looks alarming, but no code path reads the
    field:

      * ``cmd_run_job`` reads the *CLI argument* ``args.auto_approve``, not
        ``request.auto_approve``;
      * the bot's gate is the injected ``approve`` callback that waits for a
        Telegram button press;
      * the staged gates are driven only by the explicit ``approve_research`` /
        ``approve_concept`` / ``approve_storyboard`` arguments and the
        ``approvals`` map in ``pipeline_state.json``.

    These tests fail loudly if anyone ever wires the stored field to a gate,
    which would silently auto-approve every pre-existing job.
    """

    def make_job_auto(self, auto_approve=True, **kw):
        return self.make_job(auto_approve=auto_approve, **kw)

    def test_field_is_persisted_on_every_job(self):
        jid, req = self.make_job_auto()
        self.assertIn("auto_approve", req.to_dict())
        stored = json.loads(self.store.get(jid)["params_json"])
        self.assertTrue(stored["auto_approve"],
                        "the field is persisted, which is why it must be inert")

    def test_auto_approve_does_not_skip_the_research_gate(self):
        jid, req = self.make_job_auto(auto_approve=True)
        self.assertTrue(req.auto_approve)
        result = self.advance(jid, req)
        self.assertEqual(result["status"], pipeline.STATUS_EVIDENCE_GATE,
                         "a stored auto_approve=true must not skip the research gate")
        self.assertFalse(self.exists(jid, "script.md"))
        self.assertFalse(self.exists(jid, "final.mp4"))

    def test_auto_approve_does_not_skip_the_concept_gate(self):
        jid, req = self.make_job_auto(auto_approve=True)
        self.advance(jid, req, approve_research=True)
        result = self.advance(jid, approve_research=True)
        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE,
                         "a stored auto_approve=true must not skip the concept gate")
        self.assertFalse(self.exists(jid, "script.md"))

    def test_auto_approve_does_not_skip_the_storyboard_gate(self):
        jid, req = self.make_job_auto(auto_approve=True)
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        result = self.advance(jid, approve_concept="A")
        self.assertEqual(result["status"], pipeline.STATUS_STORY_GATE)
        self.assertFalse(self.exists(jid, "final.mp4"))

    def test_field_is_inert_in_both_directions(self):
        """auto_approve=False must not block either, because nothing reads it."""
        jid, req = self.make_job_auto(auto_approve=False)
        self.assertFalse(req.auto_approve)
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        result = self.advance(jid, approve_storyboard=True)
        self.assertEqual(result["status"], "completed", result.get("errors"))

    def test_legacy_gate_uses_the_callback_not_the_field(self):
        req = sanitize_request({"firm_name": FIRM, "website": SITE,
                                "language": "uz", "style": "motion",
                                "duration_sec": 21, "auto_approve": False})
        self.assertFalse(req.auto_approve)
        jid = self.store.create(1, req.style, req.language, req.firm_name,
                                req.duration_sec, 1, params=req.to_dict())
        asked = {"n": 0}

        def approve(payload):
            asked["n"] += 1
            return True

        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=approve, overrides=SMALL, enable_preview=False)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        self.assertEqual(asked["n"], 1,
                         "the callback is the gate; auto_approve=False does not "
                         "suppress it")
        self.assertEqual(result["status"], "completed")


class TestStateFileRobustness(StagedBase):
    def test_corrupt_state_file_is_not_fatal(self):
        jid, req = self.make_job()
        self.advance(jid, req)
        with open(pipeline.state_path(self.job_dir(jid)), "w",
                  encoding="utf-8") as fh:
            fh.write("{not json at all")
        state = pipeline.read_state(self.job_dir(jid))
        self.assertEqual(state["completed"], [])
        result = self.advance(jid, req)
        self.assertIn(result["status"],
                      (pipeline.STATUS_EVIDENCE_GATE, "busy"))

    def test_missing_research_is_reported_clearly(self):
        jid, _req = self.make_job()
        # Jump straight to the concepts step with no evidence on disk.
        pipeline.write_state(self.job_dir(jid),
                             completed=["evidence"], approvals={"research": {}})
        with self.assertRaises(pipeline.PipelineError):
            self.advance(jid)

    def test_step_plan_depends_on_transcripts(self):
        self.assertEqual(pipeline._steps_for({}),
                         ["evidence", "concepts", "script", "render"])
        self.assertEqual(pipeline._steps_for({"transcripts": ["a.srt"]}),
                         ["evidence", "transcripts", "concepts", "script", "render"])


class TestChronologyFromTranscripts(StagedBase):
    """Unit-level guard on the merge rule used by the concepts step."""

    def test_conflicting_years_are_reported_not_averaged(self):
        claims = [
            transcripts_mod.InterviewClaim(id="q1", text="founded in 2010",
                                           evidence_class="SINGLE-SOURCE"),
            transcripts_mod.InterviewClaim(id="q2", text="established in 2011",
                                           evidence_class="SINGLE-SOURCE"),
        ]
        timeline = chronology_mod.build_timeline(FIRM, claims)
        self.assertTrue(timeline.conflicts,
                        "two different years for one event must be flagged")
        self.assertEqual(sorted(e.year for e in timeline.entries), [2010, 2011])

    def test_undated_statements_are_parked_not_dated(self):
        claims = [transcripts_mod.InterviewClaim(
            id="q1", text="we opened a new office", evidence_class="SINGLE-SOURCE")]
        timeline = chronology_mod.build_timeline(FIRM, claims)
        self.assertEqual(timeline.entries, [])
        self.assertEqual(len(timeline.undated), 1)


class TestStatusReportsCurrentContradictions(StagedBase):
    """F1: job-status must report the current chronology, not a stale snapshot.

    The research-step summary is written once, before transcripts are read, so a
    contradiction introduced by an interview appears in ``chronology.json``
    while ``research_summary.json`` still says zero. The research snapshot was
    what the status report printed, which is the bug this class pins.
    """

    def _status_text(self, jid):
        import contextlib
        import io
        from agent_system import cli
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli._print_job_plan(self.cfg, self.store, jid)
        return buf.getvalue()

    def test_research_summary_says_zero_but_transcript_adds_a_contradiction(self):
        jid, req = self.make_job()
        # The website says "founded 2010"; the interview says "established 2011".
        conflict = self.transcript_file(CONFLICTING, name="founding_partner.srt")
        self.advance(jid, req, approve_research=True, transcripts=[conflict])

        # The stale research-stage snapshot still reports no contradiction ...
        with open(os.path.join(self.job_dir(jid), "research_summary.json"),
                  encoding="utf-8") as fh:
            summary = json.load(fh)
        self.assertEqual(summary.get("conflicts"), [])

        # ... but the current chronology has one.
        with open(os.path.join(self.job_dir(jid), "chronology", "chronology.json"),
                  encoding="utf-8") as fh:
            chrono = json.load(fh)
        self.assertEqual(len(chrono["conflicts"]), 1, chrono["conflicts"])

        text = self._status_text(jid)
        self.assertIn("1 conflict(s)", text,
                      "the status must count the current contradictions:\n" + text)
        self.assertIn(chrono["conflicts"][0][:40], text,
                      "the status must show the contradiction, not just count it")

    def test_a_missing_chronology_falls_back_to_a_labelled_snapshot(self):
        jid, _req = self.make_job()
        os.makedirs(self.job_dir(jid), exist_ok=True)
        # A summary exists but no chronology has been written yet.
        with open(os.path.join(self.job_dir(jid), "research_summary.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"conflicts": [], "dated_events": 0, "undated_claims": 0}, fh)
        text = self._status_text(jid)
        # The snapshot may be shown, but only clearly labelled as a snapshot —
        # never as the current count.
        self.assertIn("snapshot", text)
        self.assertIn("no chronology on disk yet", text)

    def test_no_readable_record_at_all_is_reported_as_unknown(self):
        jid, _req = self.make_job()
        os.makedirs(self.job_dir(jid), exist_ok=True)
        text = self._status_text(jid)
        self.assertIn("unknown", text)
        self.assertNotIn("0 conflict(s)", text)

    def test_a_corrupt_chronology_is_reported_as_unknown_not_as_zero(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        with open(os.path.join(self.job_dir(jid), "chronology", "chronology.json"),
                  "w", encoding="utf-8") as fh:
            fh.write("{not json")
        text = self._status_text(jid)
        self.assertIn("unknown", text)
        self.assertNotIn("0 conflict(s)", text,
                         "a corrupt chronology must not be quietly replaced by a "
                         "stale zero")


class TestTranscriptRetry(StagedBase):
    """F5: a transcript that could not be read must not be treated as analysed.

    These tests pin the whole recovery path: the interviews step stays open, the
    same job can retry once the file appears, the retry is idempotent, and a
    *changed* file is re-analysed rather than reused as if it were current.
    """

    def analysis_dir(self, jid):
        return os.path.join(self.job_dir(jid), "interviews", "analysis")

    def analysis_names(self, jid):
        d = self.analysis_dir(jid)
        return sorted(n for n in os.listdir(d)) if os.path.isdir(d) else []

    def test_missing_transcript_keeps_the_step_open(self):
        jid, req = self.make_job()
        missing = os.path.join(self.tmp, "not_yet.srt")
        result = self.advance(jid, req, approve_research=True, transcripts=[missing])
        self.assertEqual(result["status"], pipeline.STATUS_EVIDENCE_GATE)
        state = pipeline.read_state(self.job_dir(jid))
        self.assertNotIn("transcripts", state["completed"],
                         "an unread transcript must not complete the step")
        self.assertEqual(state["transcripts_status"][os.path.abspath(missing)]["status"],
                         "missing")
        self.assertEqual(self.analysis_names(jid), [],
                         "nothing may be recorded as analysed")
        self.assertTrue(any("not analysed" in w for w in result["warnings"]))

    def test_retry_after_the_transcript_appears_analyses_it(self):
        jid, req = self.make_job()
        missing = os.path.join(self.tmp, "not_yet.srt")
        self.advance(jid, req, approve_research=True, transcripts=[missing])
        # The operator finds the file and re-runs the same job — no new job.
        self.transcript_file(TRANSCRIPT, name="not_yet.srt")
        result = self.advance(jid)
        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE,
                         result.get("errors") or result.get("warnings"))
        state = pipeline.read_state(self.job_dir(jid))
        self.assertIn("transcripts", state["completed"])
        self.assertTrue(self.analysis_names(jid), "the retry must analyse the file")
        self.assertEqual(
            state["transcripts_status"][os.path.abspath(missing)]["status"], "analysed")

    def test_repeating_the_retry_does_not_duplicate_findings_or_chronology(self):
        jid, req = self.make_job()
        path = self.transcript_file()
        self.advance(jid, req, approve_research=True, transcripts=[path])
        before_files = self.analysis_names(jid)
        with open(os.path.join(self.job_dir(jid), "chronology", "chronology.json"),
                  encoding="utf-8") as fh:
            before_chrono = json.load(fh)

        # Force the interviews step to run again, as a retry would.
        state = pipeline.read_state(self.job_dir(jid))
        pipeline.write_state(
            self.job_dir(jid),
            completed=[s for s in state["completed"] if s != "transcripts"])
        self.advance(jid)

        self.assertEqual(self.analysis_names(jid), before_files,
                         "an unchanged transcript must not add a second analysis")
        with open(os.path.join(self.job_dir(jid), "chronology", "chronology.json"),
                  encoding="utf-8") as fh:
            after_chrono = json.load(fh)
        self.assertEqual([e["year"] for e in after_chrono["entries"]],
                         [e["year"] for e in before_chrono["entries"]],
                         "the chronology must not accumulate duplicate entries")
        self.assertEqual(len(after_chrono["undated"]), len(before_chrono["undated"]))
        state = pipeline.read_state(self.job_dir(jid))
        self.assertTrue(state["transcripts_status"][os.path.abspath(path)]["reused"],
                        "an unchanged transcript should be reused, not rewritten")

    def test_an_edited_transcript_is_reanalysed_not_reused(self):
        jid, req = self.make_job()
        path = self.transcript_file()
        self.advance(jid, req, approve_research=True, transcripts=[path])
        # The operator fixes the transcript (2010 -> 2011).
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(CONFLICTING)
        state = pipeline.read_state(self.job_dir(jid))
        pipeline.write_state(
            self.job_dir(jid),
            completed=[s for s in state["completed"] if s != "transcripts"])
        self.advance(jid)
        state = pipeline.read_state(self.job_dir(jid))
        record = state["transcripts_status"][os.path.abspath(path)]
        self.assertFalse(record["reused"],
                         "changed bytes must be re-analysed, never reused as current")
        with open(os.path.join(self.job_dir(jid), "chronology", "chronology.json"),
                  encoding="utf-8") as fh:
            chrono = json.load(fh)
        self.assertTrue(chrono["conflicts"],
                        "the corrected transcript must reach the chronology")

    def test_accepting_the_gap_lets_the_job_continue(self):
        jid, req = self.make_job()
        missing = os.path.join(self.tmp, "never.srt")
        self.advance(jid, req, approve_research=True, transcripts=[missing])
        result = self.advance(jid, allow_missing_transcripts=True)
        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE,
                         result.get("errors") or result.get("warnings"))
        state = pipeline.read_state(self.job_dir(jid))
        self.assertIn("transcripts", state["completed"])
        self.assertIn(os.path.abspath(missing), state["transcripts_accepted"])
        # The gap is recorded, so it stays visible to a reviewer.
        self.assertEqual(state["transcripts_status"][os.path.abspath(missing)]["status"],
                         "missing")

    def test_the_step_still_completes_for_a_readable_transcript(self):
        jid, req = self.make_job()
        path = self.transcript_file()
        result = self.advance(jid, req, approve_research=True, transcripts=[path])
        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE)
        state = pipeline.read_state(self.job_dir(jid))
        self.assertIn("transcripts", state["completed"])
        self.assertEqual(
            state["transcripts_status"][os.path.abspath(path)]["status"], "analysed")

    def test_a_second_transcript_added_later_is_analysed_not_silently_skipped(self):
        jid, req = self.make_job()
        first = self.transcript_file(TRANSCRIPT, name="first.srt")
        self.advance(jid, req, approve_research=True, transcripts=[first])
        self.assertIn("transcripts",
                      pipeline.read_state(self.job_dir(jid))["completed"])

        # A second interview arrives after the step already ran. Supplying it must
        # reopen the step rather than be skipped because "transcripts" is done.
        second = self.transcript_file(CONFLICTING, name="second.srt")
        self.advance(jid, transcripts=[second])

        state = pipeline.read_state(self.job_dir(jid))
        self.assertEqual(
            state["transcripts_status"][os.path.abspath(second)]["status"], "analysed")
        jsons = [n for n in self.analysis_names(jid) if n.endswith(".json")]
        self.assertEqual(len(jsons), 2, jsons)
        # Both statements reach the chronology, so the contradiction surfaces.
        with open(os.path.join(self.job_dir(jid), "chronology", "chronology.json"),
                  encoding="utf-8") as fh:
            chrono = json.load(fh)
        self.assertTrue(chrono["conflicts"], chrono["conflicts"])


class TestApprovedConceptControlsThePipeline(StagedBase):
    """F4: the approved concept governs the script — end to end, through the CLI.

    The bug this pins: approving concept-c recorded the decision in
    ``chosen_concept.md`` but the script was still drafted from the
    *recommended* concept, so the approval was recorded and ignored.
    """

    def read(self, jid, name):
        with open(os.path.join(self.job_dir(jid), name), encoding="utf-8") as fh:
            return fh.read()

    def recommended_id(self, jid):
        for line in self.read(jid, "concepts.md").splitlines():
            if line.startswith("## ") and "(recommended)" in line:
                return line[3:].split(" —")[0].strip()
        return ""

    def test_approving_concept_c_scripts_concept_c_not_the_recommended_one(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        # Precondition: the *recommended* concept is concept-a, not concept-c.
        self.assertEqual(self.recommended_id(jid), "concept-a")

        self.advance(jid, approve_concept="C")

        script = self.read(jid, "script.md")
        manifest = json.loads(self.read(jid, "scene_manifest.json"))
        chosen_note = self.read(jid, "chosen_concept.md")
        state = pipeline.read_state(self.job_dir(jid))

        # The four records must agree on one concept.
        self.assertEqual(manifest["concept"]["id"], "concept-c")
        self.assertIn("concept-c", chosen_note)
        self.assertEqual(state["approvals"]["concept"]["concept"], "C")
        self.assertIn("**Concept:** concept-c", script)

        # The script's own thesis is the approved concept's, so it cannot be
        # drafting the recommended one while claiming otherwise.
        thesis = next(line.split("**Central idea:**", 1)[1].strip()
                      for line in script.splitlines()
                      if line.startswith("**Central idea:**"))
        self.assertEqual(thesis, manifest["concept"]["central_idea"])

        # Both markers are shown, and they mark different concepts.
        self.assertIn("recommended", script)
        self.assertIn("selected for this script", script)

    def test_an_invalid_concept_id_stops_the_job_without_writing_a_script(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        result = self.advance(jid, approve_concept="concept-z")

        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE,
                         result.get("errors"))
        self.assertNotIn("script",
                         pipeline.read_state(self.job_dir(jid))["completed"])
        self.assertFalse(self.exists(jid, "script.md"))
        self.assertFalse(self.exists(jid, "scene_manifest.json"))
        # The refusal names the bad id and asks for a valid selection.
        blob = " ".join(result.get("errors", []) + result.get("warnings", []))
        self.assertIn("concept-z", blob)
        self.assertIn("Re-approve", blob)

    def test_the_job_recovers_once_a_valid_concept_is_approved(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="concept-z")
        self.advance(jid, approve_concept="B")
        manifest = json.loads(self.read(jid, "scene_manifest.json"))
        self.assertEqual(manifest["concept"]["id"], "concept-b")

    def test_a_concept_is_never_scripted_before_the_gate_is_passed(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid)                       # no concept approval at all
        self.assertFalse(self.exists(jid, "script.md"))
        result = self.advance(jid)
        self.assertEqual(result["status"], pipeline.STATUS_CONCEPT_GATE)


class TestChangedEvidenceRequiresReapproval(StagedBase):
    """An approval cannot outlive the evidence it was given for.

    When a corrected transcript arrives after a storyboard was approved, the
    storyboard that was signed off no longer describes what will be rendered, so
    the approval is withdrawn and the job stops at that gate again.
    """

    def test_changed_evidence_withdraws_the_storyboard_approval(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")

        # The operator approves the storyboard while a corrected transcript
        # arrives. The approval is written first, then the new evidence is
        # analysed — so the approval is now given for statements that are about
        # to be contradicted.
        corrected = self.transcript_file(CONFLICTING, name="corrected.srt")
        result = self.advance(jid, approve_storyboard=True,
                              transcripts=[corrected], enable_render=False)

        approvals = pipeline.read_state(self.job_dir(jid))["approvals"]
        self.assertNotIn("storyboard", approvals,
                         "an approval given for superseded evidence must be withdrawn")
        self.assertTrue(any("withdrawn" in w for w in result.get("warnings", [])),
                        result.get("warnings"))
        # The job stops at that gate instead of rendering on stale sign-off.
        self.assertEqual(result["status"], pipeline.STATUS_STORY_GATE)
        self.assertFalse(self.exists(jid, "final.mp4"))

    def test_a_new_storyboard_approval_still_works_after_the_withdrawal(self):
        """The gate is not jammed: the operator can simply approve again."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        corrected = self.transcript_file(CONFLICTING, name="corrected_b.srt")
        self.advance(jid, approve_storyboard=True,
                     transcripts=[corrected], enable_render=False)
        result = self.advance(jid, approve_storyboard=True, enable_render=False)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        self.assertIn("storyboard",
                      pipeline.read_state(self.job_dir(jid))["approvals"])

    def test_the_concept_choice_survives_changed_evidence(self):
        """A decision about *approach* is not invalidated by new statements."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="C")
        self.assertIn("concept", pipeline.read_state(self.job_dir(jid))["approvals"])

        corrected = self.transcript_file(CONFLICTING, name="corrected2.srt")
        result = self.advance(jid, approve_storyboard=True,
                              transcripts=[corrected], enable_render=False)

        approvals = pipeline.read_state(self.job_dir(jid))["approvals"]
        self.assertIn("concept", approvals,
                      "the concept selection is a choice of approach and survives")
        self.assertNotIn("storyboard", approvals)
        self.assertEqual(result["status"], pipeline.STATUS_STORY_GATE)


class TestCriticalRepairRegressions(StagedBase):
    """Regression tests for the critical-repair changes (fixes A–F).

    Each test is offline and self-contained: temp DB, canned fetcher, no
    network, no real Telegram call. They cover, in order:

    * **B** — approvals are durable, hash-bound and fail-closed;
    * **C** — delivery readiness is reported honestly, separately from
      ``status``;
    * **D** — captions and on-screen text are localised, with a synchronised
      subtitle file;
    * **E** — a preview is never presented as the final film;
    * **F** — final QA is fail-closed and blocks on unresolved evidence.
    """

    # ------------------------------------------------------ Fix B: approvals
    def test_approval_is_persisted_to_the_database(self):
        jid, req = self.make_job()
        self.advance(jid, req)                    # evidence runs → pauses at the gate
        self.advance(jid, approve_research=True)  # now the artefacts exist to bind
        rec = self.store.approve_record(jid, "research")
        self.assertIsNotNone(rec, "the research decision must be durable, not just in memory")
        self.assertEqual(rec["decision"], 1)
        self.assertTrue(rec["artifact_hash"],
                        "the decision must bind the artefact hash it was given for")

    def test_render_is_blocked_without_a_persisted_approval(self):
        """A state-file approval with no matching DB record is not trusted."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")            # stops at the render gate

        # Forge a storyboard approval into the marker file only — exactly what a
        # legacy job or a hand-edited state file would look like.
        state = pipeline.read_state(self.job_dir(jid))
        state["approvals"]["storyboard"] = {"at": "1970-01-01T00:00:00",
                                            "note": "forged"}
        pipeline.write_state(self.job_dir(jid), approvals=state["approvals"])

        result = self.advance(jid, enable_render=False)
        self.assertEqual(result["status"], pipeline.STATUS_STORY_GATE)
        self.assertFalse(self.exists(jid, "final.mp4"),
                         "no render may start on an unpersisted approval")
        self.assertNotIn("storyboard",
                         pipeline.read_state(self.job_dir(jid))["approvals"],
                         "the unpersisted approval must be withdrawn")
        self.assertTrue(any("withdrawn" in w for w in result.get("warnings", [])),
                        result.get("warnings"))

    def test_changed_artifacts_withdraw_a_persisted_approval(self):
        """An approval cannot outlive the exact artefacts it signed off."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        jdir = self.job_dir(jid)

        # Approve the storyboard against the current artefacts.
        current = pipeline._artifact_hash(jdir, pipeline.STORYBOARD_ARTIFACTS)
        self.assertTrue(current)
        self.store.record_approval(jid, "storyboard", 1, actor_ref="1",
                                   artifact_hash=current)
        state = pipeline.read_state(jdir)
        state["approvals"]["storyboard"] = {"at": "x", "artifact_hash": current}
        pipeline.write_state(jdir, approvals=state["approvals"])

        # The signed-off script now changes.
        with open(os.path.join(jdir, "script.md"), "a", encoding="utf-8") as fh:
            fh.write("\n<!-- edited after approval -->\n")

        result = self.advance(jid, enable_render=False)
        self.assertNotIn("storyboard",
                         pipeline.read_state(jdir)["approvals"])
        self.assertIsNone(self.store.approve_record(jid, "storyboard"),
                          "the stale DB record must be deleted, not left valid")
        self.assertEqual(result["status"], pipeline.STATUS_STORY_GATE)

    def test_reapproval_replaces_the_record_without_error(self):
        """Re-signing a stage (restart / force) must not raise on the UNIQUE key."""
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        self.advance(jid, approve_storyboard=True, enable_render=False)
        self.assertIsNotNone(self.store.approve_record(jid, "storyboard"))

        # A second decision for the same (job, stage) replaces the first.
        self.store.record_approval(jid, "storyboard", 1, actor_ref="1",
                                   artifact_hash="second-hash")
        rec = self.store.approve_record(jid, "storyboard")
        self.assertEqual(rec["artifact_hash"], "second-hash")

    # --------------------------------------------------- Fix C: delivery_state
    def test_paused_job_reports_paused_delivery_state(self):
        jid, req = self.make_job()
        result = self.advance(jid, req)                   # no approval → pauses
        self.assertEqual(result["status"], pipeline.STATUS_EVIDENCE_GATE)
        self.assertEqual(result["delivery_state"], "paused")

    def test_no_render_job_reports_no_render_delivery_state(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True, enable_render=False)
        self.advance(jid, approve_concept="A", enable_render=False)
        result = self.advance(jid, approve_storyboard=True, enable_render=False)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["delivery_state"], "no_render",
                         "a script-only run must never claim a finished film")

    def test_completed_run_reports_delivery_state_consistent_with_final_qa(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        result = self.advance(jid, approve_storyboard=True)
        self.assertEqual(result["status"], "completed", result.get("errors"))
        self.assertIn("final_qa", result)
        expected = ("final_ready" if result["final_qa"]["certified"]
                    else "final_not_certified")
        self.assertEqual(result["delivery_state"], expected)

    # -------------------------------------- Fix D: localisation and subtitles
    def test_subtitles_are_written_in_the_target_language(self):
        jid, req = self.make_job(language="uz")
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A")
        path = os.path.join(self.job_dir(jid), "subtitles.srt")
        self.assertTrue(os.path.isfile(path), "a subtitle file must accompany the script")
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("Har kuni odamlar", text, "the captions must be in Uzbek")
        self.assertNotIn("Every day, people", text,
                         "no English source text may leak into the Uzbek output")

    def test_scene_headings_are_localised(self):
        facts = story_mod.Facts(firm_name="Acme Legal LLP")
        uz = [s["heading"] for s in story_mod.build_scenes("Acme Legal LLP", facts,
                                                           "uz", 21.0)]
        en = [s["heading"] for s in story_mod.build_scenes("Acme Legal LLP", facts,
                                                           "en", 21.0)]
        self.assertIn("Faoliyat", uz)
        self.assertIn("Practice", en)
        self.assertNotIn("Practice", uz,
                         "an English heading must never appear in an Uzbek film")

    def test_srt_cues_follow_the_scene_timeline(self):
        facts = story_mod.Facts(firm_name="Acme Legal LLP")
        scenes = story_mod.build_scenes("Acme Legal LLP", facts, "en", 21.0)
        srt = story_mod.srt_from_scenes(scenes)
        cues = [b for b in srt.strip().split("\n\n") if b.strip()]
        self.assertGreaterEqual(len(cues), 1)
        self.assertTrue(cues[0].startswith("1\n00:00:00,000 -->"), cues[0])
        for cue in cues:
            start, end = cue.splitlines()[1].split(" --> ")
            self.assertLess(start, end, "every cue must have a positive duration")

    # -------------------------------------------- Fix E: preview vs final
    def test_preview_is_never_named_final(self):
        jid, req = self.make_job()
        self.advance(jid, req, approve_research=True)
        self.advance(jid, approve_concept="A", enable_preview=True)
        self.advance(jid, approve_storyboard=True, enable_preview=True)
        self.assertTrue(self.exists(jid, "preview.mp4"))
        self.assertTrue(self.exists(jid, "final.mp4"))
        self.assertNotEqual(
            os.path.getsize(os.path.join(self.job_dir(jid), "preview.mp4")),
            os.path.getsize(os.path.join(self.job_dir(jid), "final.mp4")),
            "the preview and the final must be distinct files")

        with open(os.path.join(self.job_dir(jid), "scene_manifest.json"),
                  "r", encoding="utf-8") as fh:
            spec, _errs = video_spec.validate_render_spec(json.load(fh))
        preview = _preview_spec(spec)
        self.assertEqual(preview.output_name, "preview.mp4",
                         "a preview must name itself preview.mp4")
        self.assertEqual(preview.watermark, "", "films carry no watermark")

    # ------------------------------------------------- Fix F: fail-closed QA
    def _spec_with(self, scenes):
        manifest = {"firm_name": "Acme Legal LLP", "language": "en",
                    "style": "motion", "scenes": scenes,
                    "watermark": "DEMO / CONCEPT PREVIEW"}
        spec, _errs = video_spec.validate_render_spec(manifest)
        return spec

    def _srt_dir(self):
        d = tempfile.mkdtemp(prefix="qa_srt_")
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, "subtitles.srt"), "w", encoding="utf-8") as fh:
            fh.write("1\n00:00:00,000 --> 00:00:01,000\nhello\n")
        return d

    def test_final_qa_blocks_on_gap_markers(self):
        facts = story_mod.Facts(firm_name="Acme Legal LLP")     # no facts → gaps
        scenes = story_mod.build_scenes("Acme Legal LLP", facts, "en", 21.0)
        spec = self._spec_with(scenes)
        qa = final_qa_checks(spec, {"ok": True, "audio_codec": "aac"},
                             self._srt_dir(), JobRequest())
        self.assertFalse(qa["certified"])
        self.assertTrue(any("gap marker" in b for b in qa["blockers"]),
                        qa["blockers"])

    def test_final_qa_certifies_a_clean_spec(self):
        facts = story_mod.Facts(firm_name="Acme Legal LLP")
        scenes = story_mod.build_scenes("Acme Legal LLP", facts, "en", 21.0)
        for s in scenes:                                        # fill every gap
            s["needs"] = []
            s["placeholder"] = False
        spec = self._spec_with(scenes)
        qa = final_qa_checks(spec, {"ok": True, "audio_codec": "aac"},
                             self._srt_dir(), JobRequest())
        self.assertTrue(qa["certified"], qa["blockers"])


if __name__ == "__main__":
    unittest.main()
