# -*- coding: utf-8 -*-
"""Tests: configuration, secret redaction, request validation."""
import os
import unittest

from agent_system import security
from agent_system.config import Config, parse_user_ids
from agent_system.orchestrator import sanitize_request


class TestSecurityRedaction(unittest.TestCase):
    def test_telegram_token_is_masked(self):
        token = "1234567890:AAFakeBotTokenValueForTesting_abc"
        security.register_secret(token)
        out = security.redact("token=%s done" % token)
        self.assertNotIn(token, out)
        self.assertIn("REDACTED", out)

    def test_token_pattern_masked_without_registration(self):
        out = security.redact("bot 9876543210:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw sent")
        self.assertNotIn("9876543210:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw", out)
        self.assertIn("REDACTED", out)

    def test_bearer_header_masked(self):
        out = security.redact("Authorization: Bearer abc123def456")
        self.assertNotIn("abc123def456", out)

    def test_plain_text_untouched(self):
        self.assertEqual(security.redact("hello world"), "hello world")


class TestConfig(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in
                       ("TELEGRAM_BOT_TOKEN", "TELEGRAM_ALLOWED_USER_IDS",
                        "MAX_CONCURRENT_JOBS", "MAX_UPLOAD_MB", "OUTPUT_DIR")}

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def test_parse_user_ids(self):
        self.assertEqual(parse_user_ids("111, 222"), [111, 222])
        self.assertEqual(parse_user_ids("111 222"), [111, 222])
        self.assertEqual(parse_user_ids(""), [])

    def test_parse_user_ids_rejects_non_numeric(self):
        with self.assertRaises(ValueError):
            parse_user_ids("111,abc")

    def test_missing_credentials_fail_safely(self):
        os.environ.pop("TELEGRAM_BOT_TOKEN", None)
        os.environ.pop("TELEGRAM_ALLOWED_USER_IDS", None)
        cfg = Config.from_env(detect=False)
        problems = cfg.validate_for_service()
        self.assertTrue(any("TELEGRAM_BOT_TOKEN" in p for p in problems))
        self.assertTrue(any("TELEGRAM_ALLOWED_USER_IDS" in p for p in problems))
        # and no token is ever produced
        self.assertEqual(cfg.telegram_bot_token, "")

    def test_authorization_uses_allowlist_only(self):
        os.environ["TELEGRAM_ALLOWED_USER_IDS"] = "111,222"
        cfg = Config.from_env(detect=False)
        self.assertTrue(cfg.is_authorized(111))
        self.assertTrue(cfg.is_authorized(222))
        self.assertFalse(cfg.is_authorized(333))
        self.assertFalse(cfg.is_authorized(None))

    def test_summary_never_contains_the_token(self):
        os.environ["TELEGRAM_BOT_TOKEN"] = "1234567890:AAFakeBotTokenValueForTesting_abc"
        os.environ["TELEGRAM_ALLOWED_USER_IDS"] = "111"
        cfg = Config.from_env(detect=False)
        blob = str(cfg.summary())
        self.assertNotIn("1234567890:AAFakeBotTokenValueForTesting_abc", blob)
        self.assertIn("token_set", blob)

    def test_concurrency_and_upload_limits_read_from_env(self):
        os.environ["MAX_CONCURRENT_JOBS"] = "3"
        os.environ["MAX_UPLOAD_MB"] = "40"
        cfg = Config.from_env(detect=False)
        self.assertEqual(cfg.max_concurrent_jobs, 3)
        self.assertEqual(cfg.max_upload_mb, 40)

    def test_bad_numeric_env_falls_back(self):
        os.environ["MAX_CONCURRENT_JOBS"] = "not-a-number"
        cfg = Config.from_env(detect=False)
        self.assertGreaterEqual(cfg.max_concurrent_jobs, 1)


class TestRequestSanitizing(unittest.TestCase):
    def test_invalid_style_falls_back_to_motion(self):
        req = sanitize_request({"firm_name": "X", "style": "hologram"})
        self.assertEqual(req.style, "motion")

    def test_invalid_language_falls_back_to_english(self):
        req = sanitize_request({"firm_name": "X", "language": "klingon"})
        self.assertEqual(req.language, "en")

    def test_duration_clamped(self):
        self.assertEqual(sanitize_request({"duration_sec": 5}).duration_sec, 20)
        self.assertEqual(sanitize_request({"duration_sec": 99999}).duration_sec, 400)

    def test_urls_normalised_and_bounded(self):
        req = sanitize_request({"firm_name": "X", "website": "example.com",
                                "extra_urls": ["a"] * 50})
        self.assertTrue(req.website.startswith("https://"))
        self.assertLessEqual(len(req.extra_urls), 5)

    def test_unknown_fields_ignored(self):
        req = sanitize_request({"firm_name": "X", "malicious": "__import__('os')"})
        self.assertFalse(hasattr(req, "malicious"))

    def test_non_string_extra_urls_dropped(self):
        req = sanitize_request({"firm_name": "X", "extra_urls": [None, 5, "ok"]})
        self.assertEqual(req.extra_urls, ["ok"])


if __name__ == "__main__":
    unittest.main()
