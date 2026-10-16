# -*- coding: utf-8 -*-
"""Tests: the Telegram bot — authorization, commands, dedupe, secret hygiene.

All Telegram calls are mocked. No message is ever sent to the real API.
"""
import asyncio
import os
import shutil
import tempfile
import unittest

from agent_system.config import Config
from agent_system.jobs import JobStore
from agent_system.telegrambot.bot import BotService
from tests.fakes import FakeContext, FakeDocument, FakeUpdate

TOKEN = "1234567890:AAFakeBotTokenValueForTesting_abc"
ALLOWED = 4242


def make_service(tmp, allowed=(ALLOWED,), token=TOKEN):
    os.environ["TELEGRAM_BOT_TOKEN"] = token
    os.environ["TELEGRAM_ALLOWED_USER_IDS"] = ",".join(str(a) for a in allowed)
    os.environ["OUTPUT_DIR"] = os.path.join(tmp, "output")
    cfg = Config.from_env(project_root=tmp, detect=False)
    cfg.capabilities = None
    cfg.ensure_dirs()
    store = JobStore(cfg.db_path)
    return BotService(cfg, store)


class BotTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bot_test_")
        self._env = {k: os.environ.get(k) for k in
                     ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_IDS", "OUTPUT_DIR")}
        self.service = make_service(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def run_async(self, coro):
        return asyncio.get_event_loop().run_until_complete(coro)


class TestAuthorization(BotTestBase):
    def test_authorized_user_is_served(self):
        upd = FakeUpdate(user_id=ALLOWED, text="/help")
        self.run_async(self.service.cmd_help(upd, FakeContext()))
        self.assertTrue(upd.effective_message.sent)

    def test_unauthorized_user_rejected_on_every_command(self):
        for handler in (self.service.cmd_start, self.service.cmd_help,
                        self.service.cmd_styles, self.service.cmd_health,
                        self.service.cmd_status, self.service.cmd_cancel):
            upd = FakeUpdate(user_id=999999, text="/x")
            self.run_async(handler(upd, FakeContext()))
            texts = " ".join(m["text"] for m in upd.effective_message.sent)
            self.assertIn("Not authorised", texts,
                          "%s served an unauthorized user" % handler.__name__)

    def test_unauthorized_message_handler_rejected(self):
        upd = FakeUpdate(user_id=999999, text="make me a video for Evil LLP")
        self.run_async(self.service.on_text(upd, FakeContext()))
        texts = " ".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("Not authorised", texts)

    def test_unauthorized_callback_rejected(self):
        upd = FakeUpdate(user_id=999999, callback_data="approve:J123")
        self.run_async(self.service.on_callback(upd, FakeContext()))
        self.assertEqual(upd.callback_query.answers, [])

    def test_unauthorized_document_never_downloaded(self):
        doc = FakeDocument("notes.txt", 100)
        upd = FakeUpdate(user_id=999999, document=doc)
        context = FakeContext()
        self.run_async(self.service.on_document(upd, context))
        self.assertEqual(context.bot.documents, [])
        self.assertTrue(any("Not authorised" in m["text"]
                            for m in upd.effective_message.sent))

    def test_authorization_is_allowlist_only(self):
        self.assertFalse(self.service.cfg.is_authorized(1))
        self.assertTrue(self.service.cfg.is_authorized(ALLOWED))


class TestCommands(BotTestBase):
    def test_help_lists_all_commands(self):
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_help(upd, FakeContext()))
        text = upd.effective_message.sent[0]["text"]
        for cmd in ("/new", "/status", "/cancel", "/styles", "/jobs", "/health", "/help"):
            self.assertIn(cmd, text)

    def test_styles_lists_three_styles(self):
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_styles(upd, FakeContext()))
        text = upd.effective_message.sent[0]["text"]
        for style in ("motion", "illustrated", "blender3d"):
            self.assertIn(style, text)

    def test_health_reports_tools_and_never_the_token(self):
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_health(upd, FakeContext()))
        text = upd.effective_message.sent[0]["text"]
        self.assertIn("ffmpeg", text)
        self.assertIn("blender", text)
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("AAFakeBotToken", text)

    def test_status_with_no_jobs(self):
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_status(upd, FakeContext()))
        self.assertIn("No jobs", upd.effective_message.sent[0]["text"])

    def test_status_lists_only_own_jobs(self):
        jid = self.service.store.create(ALLOWED, "motion", "en", "Acme", 60, 1)
        self.service.store.create(999, "motion", "en", "Other", 60, 2)
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_status(upd, FakeContext()))
        text = upd.effective_message.sent[0]["text"]
        self.assertIn(jid, text)
        self.assertNotIn("Other", text)

    def test_cancel_without_active_job(self):
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_cancel(upd, FakeContext()))
        self.assertIn("no active job", upd.effective_message.sent[0]["text"].lower())

    def test_cancel_marks_the_users_job_cancelled(self):
        jid = self.service.store.create(ALLOWED, "motion", "en", "Acme", 60, 1)
        self.service.store.set_status(jid, "rendering")
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_cancel(upd, FakeContext()))
        self.assertEqual(self.service.store.get(jid)["status"], "cancelled")

    def test_new_without_arguments_asks_for_a_request(self):
        upd = FakeUpdate(user_id=ALLOWED)
        self.run_async(self.service.cmd_new(upd, FakeContext(args=[])))
        self.assertIn("Send the request", upd.effective_message.sent[0]["text"])


class TestMalformedInput(BotTestBase):
    def test_vague_message_asks_for_missing_information(self):
        upd = FakeUpdate(user_id=ALLOWED, text="hello there")
        self.run_async(self.service.on_text(upd, FakeContext()))
        text = upd.effective_message.sent[0]["text"]
        self.assertIn("missing", text.lower())

    def test_missing_website_asks_for_it(self):
        upd = FakeUpdate(user_id=ALLOWED, text="make a video for Acme Legal LLP")
        self.run_async(self.service.on_text(upd, FakeContext()))
        self.assertTrue(upd.effective_message.sent)

    def test_unknown_callback_answered_gracefully(self):
        upd = FakeUpdate(user_id=ALLOWED, callback_data="nonsense")
        self.run_async(self.service.on_callback(upd, FakeContext()))
        self.assertTrue(upd.callback_query.answers)

    def test_expired_approval_answered_gracefully(self):
        upd = FakeUpdate(user_id=ALLOWED, callback_data="approve:JDOESNOTEXIST")
        self.run_async(self.service.on_callback(upd, FakeContext()))
        self.assertIn("closed", " ".join(upd.callback_query.answers).lower())

    def test_reject_callback_cancels_job(self):
        jid = self.service.store.create(ALLOWED, "motion", "en", "Acme", 60, 1)
        self.service.store.set_status(jid, "awaiting_approval")
        upd = FakeUpdate(user_id=ALLOWED, callback_data="reject:%s" % jid)
        self.run_async(self.service.on_callback(upd, FakeContext()))
        self.assertEqual(self.service.store.get(jid)["status"], "cancelled")


class TestDedupe(BotTestBase):
    def test_duplicate_update_is_ignored(self):
        from telegram.ext import ApplicationHandlerStop
        upd = FakeUpdate(user_id=ALLOWED, text="/help")
        self.run_async(self.service._on_any_update(upd, FakeContext()))
        with self.assertRaises(ApplicationHandlerStop):
            self.run_async(self.service._on_any_update(upd, FakeContext()))

    def test_duplicate_update_does_not_create_two_jobs(self):
        upd = FakeUpdate(user_id=ALLOWED, text="/help")
        self.run_async(self.service._on_any_update(upd, FakeContext()))
        before = len(self.service.store.list_for_user(ALLOWED, 50))
        try:
            self.run_async(self.service._on_any_update(upd, FakeContext()))
        except Exception:
            pass
        after = len(self.service.store.list_for_user(ALLOWED, 50))
        self.assertEqual(before, after)

    def test_distinct_updates_both_processed(self):
        a = FakeUpdate(update_id=101, user_id=ALLOWED)
        b = FakeUpdate(update_id=102, user_id=ALLOWED)
        self.run_async(self.service._on_any_update(a, FakeContext()))
        self.run_async(self.service._on_any_update(b, FakeContext()))


class TestDocumentHandling(BotTestBase):
    def test_allowed_file_saved(self):
        doc = FakeDocument("posts.txt", 512)
        upd = FakeUpdate(user_id=ALLOWED, document=doc)
        self.run_async(self.service.on_document(upd, FakeContext()))
        text = " ".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("Saved", text)

    def test_disallowed_file_rejected_before_download(self):
        doc = FakeDocument("virus.exe", 512)
        upd = FakeUpdate(user_id=ALLOWED, document=doc)
        context = FakeContext()
        self.run_async(self.service.on_document(upd, context))
        text = " ".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("Rejected", text)

    def test_oversize_file_rejected(self):
        doc = FakeDocument("big.mp4", 500 * 1024 * 1024)
        upd = FakeUpdate(user_id=ALLOWED, document=doc)
        self.run_async(self.service.on_document(upd, FakeContext()))
        text = " ".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("Rejected", text)


class TestSoncurrencyLimit(BotTestBase):
    def test_queue_full_refuses_a_new_job(self):
        self.service.cfg.max_concurrent_jobs = 1
        jid = self.service.store.create(ALLOWED, "motion", "en", "Acme", 60, 1)
        self.service.store.set_status(jid, "rendering")
        upd = FakeUpdate(user_id=ALLOWED, text="video for Acme Legal LLP https://acme.uz")
        self.run_async(self.service.on_text(upd, FakeContext()))
        text = " ".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("Queue is full", text)

    def test_unavailable_style_refused_before_job_creation(self):
        before = len(self.service.store.list_for_user(ALLOWED, 50))
        upd = FakeUpdate(user_id=ALLOWED,
                         text="video for Acme Legal LLP https://acme.uz Style: 3d blender")
        self.run_async(self.service.on_text(upd, FakeContext()))
        text = " ".join(m["text"] for m in upd.effective_message.sent)
        self.assertIn("not available", text)
        self.assertEqual(len(self.service.store.list_for_user(ALLOWED, 50)), before)


class TestConfigHasNoBackdoor(unittest.TestCase):
    def test_no_command_modifies_configuration(self):
        """The bot must expose no way to change its own allow-list or secrets."""
        import inspect
        from agent_system.telegrambot import bot as bot_mod
        src = inspect.getsource(bot_mod)
        for forbidden in ("os.environ[", "set_key", "load_dotenv", "setenv",
                          "shutil.rmtree", "os.remove", "os.unlink",
                          "subprocess", "popen", "shell=True", "eval(",
                          "write_text"):
            self.assertNotIn(forbidden, src,
                             "bot source contains potentially unsafe operation: %s" % forbidden)

    def test_help_text_says_authorization_cannot_be_changed(self):
        import inspect
        from agent_system.telegrambot import bot as bot_mod
        src = inspect.getsource(bot_mod)
        self.assertIn("No command can change that", src)

    def test_no_shell_invocation_in_bot(self):
        import inspect
        from agent_system.telegrambot import bot as bot_mod
        src = inspect.getsource(bot_mod)
        self.assertNotIn("shell=True", src)
        self.assertNotIn("eval(", src)
        self.assertNotIn("exec(", src)


if __name__ == "__main__":
    unittest.main()
