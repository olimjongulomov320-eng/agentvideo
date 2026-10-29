# -*- coding: utf-8 -*-
"""test_integration.py — mocked end-to-end wiring tests.

What this module proves, deterministically and offline:

* an **authorised** user goes through validate → sanitise → unique job id →
  lifecycle states → (mocked) orchestrator → (mocked) render metadata →
  delivery callbacks on a fake Telegram bot;
* an **unauthorised** user is rejected *before* any job row is created;
* **duplicate** Telegram updates do not start a second job;
* **malformed** requests and **unavailable styles** fail safely with no job;
* a **render failure** marks the job failed with a non-sensitive error;
* **cancellation** keeps job status and user-facing messages consistent;
* **no-render mode** produces research/script artifacts and starts no render.

Hard rules honoured here:
  * no real Telegram API call is made — only ``tests.fakes`` objects;
  * no bot token or real user id is used (placeholder ids only);
  * every job runs in a temp directory; nothing is written to the repo;
  * renders are mocked or skipped — no long jobs, no ffmpeg, no network.
"""
import asyncio
import json
import os
import shutil
import tempfile
import time
import types
import unittest
from unittest import mock

from telegram.ext import ApplicationHandlerStop

from agent_system import orchestrator
from agent_system import security
from agent_system import video
from agent_system.config import Config
from agent_system.jobs import JobStore
from agent_system.telegrambot import bot as bot_mod
from agent_system.telegrambot import parsing
from tests.fakes import FakeBot, FakeContext, FakeUpdate, html_pages

# Authorised placeholder ids — deliberately not real accounts.
USER_A = 111
USER_B = 222
INTRUDER = 999

REQ_TEXT = ("Create a 2-minute animated history video for GSP Law Firm. "
            "Website: gsplaw.co.uz. Language: Uzbek. Style: motion graphics.")

PAGES = {
    "https://gsplaw.co.uz": (
        "<html><head><title>GSP Law Firm</title></head><body>"
        "<h1>GSP Law Firm</h1><p>Founded in 2010.</p>"
        "<a href='/about'>About</a></body></html>"),
    "https://gsplaw.co.uz/about": (
        "<html><head><title>About — GSP</title></head><body>"
        "<h2>Our history</h2><p>The firm was established in 2010.</p>"
        "</body></html>"),
}

TERMINAL = ("completed", "failed", "cancelled")


def _write(path, data=b"x"):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(data)
    return path


class _Recorder(object):
    """Collects coroutines instead of talking to Telegram."""

    def __init__(self):
        self.coros = []

    def __call__(self, coro):
        self.coros.append(coro)


class IntegrationBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="agent-int-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.recorder = _Recorder()

    # ------------------------------------------------------------------ helpers
    def make_cfg(self, token=""):
        cfg = Config.from_env(project_root=self.tmp, detect=False)
        cfg.output_dir = os.path.join(self.tmp, "output")
        cfg.allowed_user_ids = [USER_A, USER_B]
        cfg.max_concurrent_jobs = 1
        cfg.fast_render = True
        cfg.telegram_bot_token = token
        cfg.capabilities = None
        cfg.ensure_dirs()
        os.makedirs(cfg.output_dir, exist_ok=True)
        return cfg

    def make_service(self, cfg):
        svc = bot_mod.BotService(cfg, JobStore(cfg.db_path))
        svc.app = types.SimpleNamespace(bot=FakeBot())
        svc.loop = None                      # never used: _schedule is replaced
        svc._schedule = self.recorder
        return svc

    def run_async(self, coro):
        """Run a coroutine on the process-wide loop (Python 3.9 compatible)."""
        return asyncio.get_event_loop().run_until_complete(coro)

    async def drain(self, svc):
        """Run every coroutine the service handed to the fake scheduler."""
        for _ in range(50):
            pending, self.recorder.coros = self.recorder.coros, []
            if not pending:
                return
            await asyncio.gather(*pending)

    async def wait_terminal(self, svc, job_id, timeout=30.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            job = svc.store.get(job_id)
            if job and job["status"] in TERMINAL:
                return job
            await asyncio.sleep(0.02)
        self.fail("job %s did not reach a terminal state" % job_id)

    def requests(self, svc, user_id):
        return svc.store.list_for_user(user_id)

    def sent_text(self, svc):
        return "\n".join(m["text"] for m in svc.app.bot.messages)

    def sent_docs(self, svc):
        return [d["name"] for d in svc.app.bot.documents]


class TestAuthorisation(IntegrationBase):
    def test_unauthorised_user_is_rejected_before_job_creation(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)

        upd = FakeUpdate(user_id=INTRUDER, chat_id=INTRUDER, text=REQ_TEXT)
        self.run_async(svc.on_text(upd, FakeContext()))

        self.assertEqual(self.requests(svc, INTRUDER), [])
        self.assertEqual(svc.store.active_count(), 0)
        self.assertEqual(len(svc.app.bot.messages), 0)   # nothing outbound at all
        replies = [m["text"] for m in upd.effective_message.sent]
        self.assertTrue(any("Not authorised" in r for r in replies), replies)

    def test_unauthorised_user_is_rejected_for_commands_and_callbacks(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)

        for handler in (svc.cmd_start, svc.cmd_styles, svc.cmd_status):
            upd = FakeUpdate(user_id=INTRUDER, chat_id=INTRUDER)
            self.run_async(handler(upd, FakeContext()))
            self.assertTrue(any("Not authorised" in m["text"]
                                for m in upd.effective_message.sent))

        cb = FakeUpdate(user_id=INTRUDER, chat_id=INTRUDER,
                        callback_data="approve:JXXXX")
        self.run_async(svc.on_callback(cb, FakeContext()))
        self.assertEqual(svc.store.active_count(), 0)

    def test_configured_allowed_ids_govern_access(self):
        cfg = self.make_cfg()
        self.assertTrue(cfg.is_authorized(USER_A))
        self.assertFalse(cfg.is_authorized(INTRUDER))
        self.assertFalse(cfg.is_authorized(None))


class TestRequestIntake(IntegrationBase):
    def test_malformed_request_is_handled_safely(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)

        for text in ("hello", "", "please make a video", "🏛️" * 5):
            upd = FakeUpdate(user_id=USER_A, chat_id=USER_A, text=text)
            self.run_async(svc.on_text(upd, FakeContext()))
            self.assertTrue(upd.effective_message.sent, "expected a reply for %r" % text)

        self.assertEqual(self.requests(svc, USER_A), [])
        self.assertEqual(svc.store.active_count(), 0)

    def test_unavailable_style_reports_honestly_and_creates_no_job(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)
        parsed = parsing.parse_request_text(REQ_TEXT)
        parsed["style"] = "blender3d"          # not ready on this machine

        upd = FakeUpdate(user_id=USER_A, chat_id=USER_A, text=REQ_TEXT)
        self.run_async(svc._start_job(upd, parsed))

        self.assertEqual(self.requests(svc, USER_A), [])
        self.assertEqual(svc.store.active_count(), 0)
        replies = [m["text"] for m in upd.effective_message.sent]
        self.assertTrue(any("not available" in r for r in replies), replies)

    def test_unknown_style_falls_back_to_motion(self):
        req = orchestrator.sanitize_request({"style": "banana", "firm_name": "F"})
        self.assertEqual(req.style, "motion")

    def test_job_ids_are_unique(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)
        a = svc.store.create(USER_A, "motion", "uz", "A", 120, USER_A)
        b = svc.store.create(USER_A, "motion", "uz", "B", 120, USER_A)
        self.assertNotEqual(a, b)
        self.assertEqual(len({a, b}), 2)

    def test_duplicate_update_does_not_start_a_second_job(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)

        first = FakeUpdate(update_id=7, user_id=USER_A, chat_id=USER_A, text=REQ_TEXT)
        self.run_async(svc._on_any_update(first, FakeContext()))   # passes

        dup = FakeUpdate(update_id=7, user_id=USER_A, chat_id=USER_A, text=REQ_TEXT)
        with self.assertRaises(ApplicationHandlerStop):
            self.run_async(svc._on_any_update(dup, FakeContext()))

        # The stopped handler never reached _start_job: no job exists.
        self.assertEqual(self.requests(svc, USER_A), [])


class TestAuthorisedFlow(IntegrationBase):
    """Authorised request → sanitised → job → lifecycle → mocked delivery."""

    def _fake_run_job(self, cfg, store, job_id, req, **kwargs):
        self.seen_request = req
        self.seen_kwargs = kwargs
        job_dir = cfg.job_dir(job_id)
        os.makedirs(job_dir, exist_ok=True)

        store.set_status(job_id, "researching", "reading public sources", 5)
        store.set_status(job_id, "awaiting_approval", "waiting for storyboard approval", 60)
        store.set_status(job_id, "rendering", "rendering full video", 65)

        for name in ("research_report.md", "evidence_ledger.csv", "concepts.md",
                     "script.md", "storyboard.md", "scene_manifest.json"):
            _write(os.path.join(job_dir, name))
        out = _write(os.path.join(job_dir, "final.mp4"), b"\x00" * 4096)

        store.set_status(job_id, "completed", "finished", 100)
        return {
            "job_id": job_id, "output_dir": job_dir, "status": "completed",
            "errors": [], "warnings": [], "artifacts": ["final.mp4"],
            "output": out,
            "validation": {"ok": True, "width": 960, "height": 540, "fps": 24,
                           "duration_sec": 12.5, "size_bytes": 4096,
                           "audio_codec": "aac", "audio_channels": 2,
                           "checks": ["container ok", "streams ok"], "note": "mocked"},
        }

    def test_authorised_request_runs_full_mocked_pipeline(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)

        async def flow():
            upd = FakeUpdate(user_id=USER_A, chat_id=USER_A, text=REQ_TEXT)
            await svc.on_text(upd, FakeContext())
            jobs = svc.store.list_for_user(USER_A)
            self.assertEqual(len(jobs), 1, "exactly one job expected")
            job_id = jobs[0]["id"]
            await self.wait_terminal(svc, job_id)
            await asyncio.sleep(0.15)         # let the worker finish delivery
            await self.drain(svc)
            return upd, job_id

        with mock.patch.object(bot_mod, "run_job", self._fake_run_job):
            upd, job_id = self.run_async(flow())

        job = svc.store.get(job_id)
        self.assertEqual(job["status"], "completed")
        self.assertEqual(job["progress"], 100)
        self.assertEqual(len(job_id), 9)

        # sanitise_request ran: the bare domain became an absolute URL.
        self.assertIn("https://gsplaw.co.uz", job["params_json"])
        self.assertEqual(self.seen_request.language, "uz")

        # The mocked Telegram bot received the status narration and the delivery.
        text = self.sent_text(svc)
        self.assertIn("completed", text)
        self.assertIn("ffprobe checks", text)
        # ...and the job-created notice went back on the originating message.
        created = "\n".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("Job <code>%s</code> created" % job_id, created)

        docs = self.sent_docs(svc)
        # Only the finished film is sent; the working documents stay on disk.
        self.assertEqual(docs, ["final.mp4"])

    def test_authorised_new_command_path_also_works(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)

        async def flow():
            upd = FakeUpdate(user_id=USER_B, chat_id=USER_B)
            ctx = FakeContext(args=REQ_TEXT.split())
            await svc.cmd_new(upd, ctx)
            jobs = svc.store.list_for_user(USER_B)
            job_id = jobs[0]["id"] if jobs else None
            if job_id:
                await self.wait_terminal(svc, job_id)
            await self.drain(svc)
            return job_id

        with mock.patch.object(bot_mod, "run_job", self._fake_run_job):
            job_id = self.run_async(flow())

        self.assertIsNotNone(job_id)
        self.assertEqual(svc.store.get(job_id)["status"], "completed")


class TestFailureAndCancel(IntegrationBase):
    def test_mocked_render_failure_marks_job_failed_without_secrets(self):
        # A realistic-length token (35-char suffix) so pattern redaction applies,
        # and registered exactly as production does at startup.
        secret = "8123456789:AAFakeTokenThatMustNeverLeak0123456789"
        security.register_secret(secret)
        cfg = self.make_cfg(token=secret)
        svc = self.make_service(cfg)

        def exploding_run_job(cfg_, store, job_id, req, **kwargs):
            store.set_status(job_id, "rendering", "rendering full video", 65)
            # Mirrors production: the orchestrator redacts before recording/failing.
            msg = security.redact("RenderError: boom %s" % secret)
            store.fail(job_id, msg)
            return {"job_id": job_id, "output_dir": cfg_.job_dir(job_id),
                    "status": "failed", "errors": [msg], "warnings": [],
                    "artifacts": []}

        async def flow():
            upd = FakeUpdate(user_id=USER_A, chat_id=USER_A, text=REQ_TEXT)
            await svc.on_text(upd, FakeContext())
            job_id = svc.store.list_for_user(USER_A)[0]["id"]
            await self.wait_terminal(svc, job_id)
            await asyncio.sleep(0.15)
            await self.drain(svc)
            return job_id

        with mock.patch.object(bot_mod, "run_job", exploding_run_job):
            job_id = self.run_async(flow())

        job = svc.store.get(job_id)
        self.assertEqual(job["status"], "failed")
        self.assertTrue(job["error"])
        self.assertNotIn(secret, job["error"])
        self.assertIn("REDACTED", job["error"])

        # The user-facing failure notice is non-sensitive: no token, no traceback.
        text = self.sent_text(svc)
        self.assertIn("failed", text.lower())
        self.assertNotIn(secret, text)
        self.assertNotIn("Traceback", text)

    def test_cancellation_keeps_status_and_message_consistent(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)
        job_id = svc.store.create(USER_A, "motion", "uz", "GSP", 120, USER_A)

        svc._request_cancel(job_id)
        self.assertTrue(svc.store.is_cancelled(job_id))

        req = orchestrator.sanitize_request(parsing.parse_request_text(REQ_TEXT))
        svc._deliver(USER_A, job_id, req, {"status": "cancelled", "errors": []})
        self.run_async(self.drain(svc))

        self.assertIn("cancelled", self.sent_text(svc).lower())
        self.assertEqual(svc.store.get(job_id)["status"], "cancelled")

    def test_cancel_command_reports_when_nothing_is_running(self):
        cfg = self.make_cfg()
        svc = self.make_service(cfg)
        upd = FakeUpdate(user_id=USER_A, chat_id=USER_A)
        self.run_async(svc.cmd_cancel(upd, FakeContext()))
        self.assertTrue(any("no active job" in m["text"].lower()
                            for m in upd.effective_message.sent))


class TestNoRenderMode(IntegrationBase):
    """enable_render=False must stop before any ffmpeg subprocess is started."""

    def _request(self):
        return orchestrator.sanitize_request(parsing.parse_request_text(REQ_TEXT))

    def test_no_render_completes_without_starting_a_render(self):
        cfg = self.make_cfg()
        store = JobStore(cfg.db_path)
        req = self._request()
        job_id = store.create(USER_A, req.style, req.language, req.firm_name,
                              req.duration_sec, USER_A, params=req.to_dict())
        job_dir = cfg.job_dir(job_id)

        def forbidden(*a, **k):
            raise AssertionError("render_style must not be called in no-render mode")

        with mock.patch.object(video, "render_style", forbidden):
            result = orchestrator.run_job(cfg, store, job_id, req,
                                          fetcher=html_pages(PAGES),
                                          enable_render=False)

        self.assertEqual(result["status"], "completed")
        self.assertTrue(result.get("no_render"))
        self.assertFalse(os.path.exists(os.path.join(job_dir, "final.mp4")))
        self.assertFalse(os.path.exists(os.path.join(job_dir, "preview.mp4")))

        for name in ("research_report.md", "script.md", "storyboard.md",
                     "delivery_report.md"):
            self.assertTrue(os.path.isfile(os.path.join(job_dir, name)), name)

        report = open(os.path.join(job_dir, "delivery_report.md"),
                      encoding="utf-8").read()
        self.assertIn("No video was rendered", report)
        self.assertEqual(store.get(job_id)["status"], "completed")

    def test_env_var_also_disables_rendering(self):
        cfg = self.make_cfg()
        store = JobStore(cfg.db_path)
        req = self._request()
        job_id = store.create(USER_A, req.style, req.language, req.firm_name,
                              req.duration_sec, USER_A, params=req.to_dict())

        def forbidden(*a, **k):
            raise AssertionError("render_style must not be called")

        with mock.patch.dict(os.environ, {"AGENT_NO_RENDER": "1"}):
            with mock.patch.object(video, "render_style", forbidden):
                result = orchestrator.run_job(cfg, store, job_id, req,
                                              fetcher=html_pages(PAGES))
        self.assertTrue(result.get("no_render"))
        self.assertEqual(result["status"], "completed")

    def test_render_enabled_still_exercises_the_render_path(self):
        cfg = self.make_cfg()
        store = JobStore(cfg.db_path)
        req = self._request()
        job_id = store.create(USER_A, req.style, req.language, req.firm_name,
                              req.duration_sec, USER_A, params=req.to_dict())
        calls = []

        def fake_render(spec, out_path, work_dir, **kwargs):
            calls.append(spec.style)
            _write(out_path, b"\x00" * 2048)
            return {"validation": {"ok": True, "width": 960, "height": 540,
                                   "fps": 24, "duration_sec": 8.0,
                                   "size_bytes": 2048, "audio_codec": "aac",
                                   "audio_channels": 2, "checks": []},
                    "manifest": {"style": spec.style, "mocked": True}}

        with mock.patch.object(video, "render_style", fake_render):
            result = orchestrator.run_job(cfg, store, job_id, req,
                                          fetcher=html_pages(PAGES),
                                          enable_preview=False,
                                          enable_render=True)

        self.assertEqual(calls, ["motion"])
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["output"].endswith("final.mp4"))
        self.assertTrue(result["validation"]["ok"])
        self.assertIn("final.mp4", result["artifacts"])


if __name__ == "__main__":
    unittest.main()
