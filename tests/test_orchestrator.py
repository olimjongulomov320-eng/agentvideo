# -*- coding: utf-8 -*-
"""Tests: the end-to-end orchestrator (offline, mocked network, short render).

Also protects the pre-existing GSP deliverables from accidental modification —
this upgrade must not damage earlier work.
"""
import json
import os
import shutil
import tempfile
import unittest

from agent_system.config import Config
from agent_system.jobs import JobStore
from agent_system.orchestrator import JobRequest, run_job, sanitize_request
from tests.fakes import html_pages

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FIRM_HTML = """<html><head><title>Acme Legal LLP</title></head><body>
<h1>About</h1>
<p>Acme Legal LLP was founded in 2010 in Tashkent.</p>
<p>Acme Legal LLP advises on corporate law, tax law and IT law.</p>
</body></html>"""


class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="orch_test_")
        self._env = {k: os.environ.get(k) for k in ("OUTPUT_DIR", "PROJECT_ROOT")}
        os.environ["OUTPUT_DIR"] = os.path.join(self.tmp, "output")
        os.environ["PROJECT_ROOT"] = self.tmp
        self.cfg = Config.from_env(project_root=self.tmp, detect=False)
        self.cfg.ensure_dirs()
        self.store = JobStore(self.cfg.db_path)
        self.fetcher = html_pages({"https://acme.uz": FIRM_HTML})

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _run(self, **kw):
        req = sanitize_request(dict({"firm_name": "Acme Legal LLP",
                                     "website": "https://acme.uz",
                                     "language": "uz", "style": "motion",
                                     "duration_sec": 21}, **kw))
        jid = self.store.create(1, req.style, req.language, req.firm_name,
                                req.duration_sec, 1, params=req.to_dict())
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=lambda payload: True,
                         overrides={"width": 320, "height": 180, "fps": 8},
                         enable_preview=False)
        return jid, result

    def test_full_job_produces_every_declared_artifact(self):
        jid, result = self._run()
        self.assertEqual(result["status"], "completed", result.get("errors"))
        job_dir = self.cfg.job_dir(jid)
        for name in ("research_report.md", "evidence_ledger.csv", "concepts.md",
                     "script.md", "storyboard.md", "scene_manifest.json",
                     "render_manifest.json", "delivery_report.md", "final.mp4"):
            self.assertTrue(os.path.isfile(os.path.join(job_dir, name)),
                            "missing artifact: %s" % name)

    def test_final_video_is_really_validated(self):
        _jid, result = self._run()
        v = result["validation"]
        self.assertTrue(v["ok"], v["errors"])
        self.assertEqual((v["width"], v["height"]), (320, 180))
        self.assertEqual(v["video_codec"], "h264")
        self.assertIsNotNone(v["audio_codec"])
        self.assertGreater(v["duration_sec"], 5)

    def test_research_artifacts_are_cited(self):
        jid, _ = self._run()
        ledger = open(os.path.join(self.cfg.job_dir(jid), "evidence_ledger.csv"),
                      encoding="utf-8").read()
        self.assertIn("https://acme.uz", ledger)
        self.assertIn("source_url", ledger.splitlines()[0])

    def test_delivery_report_lists_sources_gaps_and_limitations(self):
        jid, _ = self._run()
        report = open(os.path.join(self.cfg.job_dir(jid), "delivery_report.md"),
                      encoding="utf-8").read()
        self.assertIn("Sources actually accessed", report)
        self.assertIn("https://acme.uz", report)
        self.assertIn("Gaps the script had to leave open", report)
        self.assertIn("Limitations", report)
        self.assertIn("Next steps for a human", report)
        # the report must record the real outcome, not a stale in-progress state
        self.assertIn("**COMPLETED**", report)
        self.assertNotIn("**RUNNING**", report)

    def test_job_status_ends_completed(self):
        jid, _ = self._run()
        self.assertEqual(self.store.get(jid)["status"], "completed")
        self.assertEqual(self.store.get(jid)["progress"], 100)

    def test_rejected_storyboard_performs_no_render(self):
        req = sanitize_request({"firm_name": "Acme Legal LLP",
                                "website": "https://acme.uz", "style": "motion",
                                "duration_sec": 21})
        jid = self.store.create(1, "motion", "en", "Acme", 21, 1)
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=lambda payload: False, enable_preview=False)
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(os.path.isfile(os.path.join(self.cfg.job_dir(jid), "final.mp4")))
        self.assertEqual(self.store.get(jid)["status"], "cancelled")

    def test_unavailable_backend_fails_with_a_report_and_no_false_claim(self):
        req = sanitize_request({"firm_name": "Acme Legal LLP",
                                "website": "https://acme.uz", "style": "blender3d",
                                "duration_sec": 21})
        jid = self.store.create(1, "blender3d", "en", "Acme", 21, 1)
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=lambda payload: True,
                         overrides={"width": 320, "height": 180, "fps": 8},
                         enable_preview=False)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["errors"])
        self.assertIn("Blender", " ".join(result["errors"]))
        self.assertFalse(os.path.isfile(os.path.join(self.cfg.job_dir(jid), "final.mp4")))
        report = open(os.path.join(self.cfg.job_dir(jid), "delivery_report.md"),
                      encoding="utf-8").read()
        self.assertIn("FAILED", report)

    def test_cancellation_stops_the_job(self):
        req = sanitize_request({"firm_name": "Acme Legal LLP",
                                "website": "https://acme.uz", "style": "motion",
                                "duration_sec": 21})
        jid = self.store.create(1, "motion", "en", "Acme", 21, 1)
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         cancel=lambda: True, approve=lambda p: True,
                         enable_preview=False)
        self.assertEqual(result["status"], "cancelled")
        self.assertFalse(os.path.isfile(os.path.join(self.cfg.job_dir(jid), "final.mp4")))

    def test_preview_only_skips_the_full_render(self):
        req = sanitize_request({"firm_name": "Acme Legal LLP",
                                "website": "https://acme.uz", "style": "motion",
                                "duration_sec": 21, "preview_only": True})
        jid = self.store.create(1, "motion", "en", "Acme", 21, 1)
        result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                         approve=lambda p: True,
                         overrides={"width": 320, "height": 180, "fps": 8},
                         enable_preview=True)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(os.path.isfile(os.path.join(self.cfg.job_dir(jid), "preview.mp4")))
        self.assertFalse(os.path.isfile(os.path.join(self.cfg.job_dir(jid), "final.mp4")))

    def test_unreadable_site_yields_gaps_not_inventions(self):
        req = sanitize_request({"firm_name": "Ghost LLP", "website": "https://ghost.uz",
                                "style": "motion", "duration_sec": 21})
        jid = self.store.create(1, "motion", "en", "Ghost", 21, 1)
        result = run_job(self.cfg, self.store, jid, req,
                         fetcher=html_pages({}),   # everything 404
                         approve=lambda p: True,
                         overrides={"width": 320, "height": 180, "fps": 8},
                         enable_preview=False)
        self.assertEqual(result["status"], "completed")
        with open(os.path.join(self.cfg.job_dir(jid), "scene_manifest.json"),
                  encoding="utf-8") as fh:
            manifest = json.load(fh)
        self.assertTrue(manifest["gaps"], "unreadable sources must appear as gaps")
        self.assertTrue(any(s["placeholder"] for s in manifest["scenes"]))
        self.assertTrue(any("No readable public claims" in w
                            for w in result.get("warnings", [])))


class TestExistingWorkUntouched(unittest.TestCase):
    """The upgrade must not have damaged the earlier GSP deliverables."""

    def test_reference_deliverables_still_present(self):
        for rel in ("research/01_source_inventory.md",
                    "research/10_fact_verification_log.md",
                    "production/03_final_video_script.md",
                    "production/06_russian_master_narration.md",
                    ".opencode/agents/law-firm-researcher.md",
                    ".opencode/commands/law-firm-run.md"):
            self.assertTrue(os.path.isfile(os.path.join(PROJECT_ROOT, rel)), rel)

    def test_existing_demo_videos_still_probe_correctly(self):
        from agent_system.video import common
        pairs = [("demo/GSP_demo_UZ.mp4", 143.4), ("demo/GSP_demo_RU.mp4", 143.4)]
        for rel, expected in pairs:
            path = os.path.join(PROJECT_ROOT, rel)
            if not os.path.isfile(path):
                self.skipTest("demo video not present: %s" % rel)
            report = common.validate_mp4(path, 1920, 1080, 30)
            self.assertTrue(report["ok"], report["errors"])
            self.assertAlmostEqual(report["duration_sec"], expected, delta=1.5)
            self.assertEqual(report["audio_codec"], "aac")

    def test_existing_agent_files_unchanged_in_content(self):
        path = os.path.join(PROJECT_ROOT, ".opencode/agents/law-firm-researcher.md")
        text = open(path, encoding="utf-8").read()
        # frontmatter + the safety contract must remain intact
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("# Law Firm Research & Video Script Agent", text)
        for rule in ("Never fabricate.", "Never claim access you did not have.",
                     "Cite everything.", "Never contact anyone."):
            self.assertIn(rule, text, "agent safety rule removed: %s" % rule)
        self.assertIn("effect: deny", text, "permission blocks were removed")
        self.assertGreater(len(text), 2000)


if __name__ == "__main__":
    unittest.main()
