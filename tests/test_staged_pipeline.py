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
from agent_system import transcripts as transcripts_mod
from agent_system.config import Config
from agent_system.jobs import JobStore
from agent_system.orchestrator import JobRequest, run_job, sanitize_request
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


if __name__ == "__main__":
    unittest.main()
