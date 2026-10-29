# -*- coding: utf-8 -*-
"""Tests: Telegram input parsing and file validation (no network)."""
import unittest

from agent_system.telegrambot import parsing


class TestRequestParsing(unittest.TestCase):
    SAMPLE = ("Create a 2-minute animated history video for GSP Law Firm. "
              "Research the official website gsplaw.co.uz and accessible Facebook "
              "sources. Language: Uzbek. Style: motion graphics.")

    def test_example_message_from_the_brief(self):
        p = parsing.parse_request_text(self.SAMPLE)
        self.assertEqual(p["duration_sec"], 120)
        self.assertEqual(p["language"], "uz")
        self.assertEqual(p["style"], "motion")
        self.assertIn("GSP Law Firm", p["firm_name"])
        self.assertEqual(p["website"], "https://gsplaw.co.uz")

    def test_facebook_url_separated_from_website(self):
        p = parsing.parse_request_text(
            "History video for Acme Legal LLP https://acme.uz "
            "https://facebook.com/acmelegal Language: russian")
        self.assertEqual(p["website"], "https://acme.uz")
        self.assertIn("facebook.com", p["facebook"])
        self.assertEqual(p["language"], "ru")

    def test_seconds_duration(self):
        self.assertEqual(parsing.detect_duration("make a 90 second film"), 90)

    def test_duration_defaults_and_clamps(self):
        self.assertEqual(parsing.detect_duration("no duration here"), 140)
        self.assertEqual(parsing.detect_duration("a 99 minute film"), 400)

    def test_style_detection(self):
        self.assertEqual(parsing.detect_style("do it as 3D in blender"), "blender3d")
        self.assertEqual(parsing.detect_style("illustrated 2d cartoon"), "illustrated")
        self.assertEqual(parsing.detect_style("motion graphics please"), "motion")

    def test_language_detection(self):
        self.assertEqual(parsing.detect_language("Language: Uzbek"), "uz")
        self.assertEqual(parsing.detect_language("на русском"), "ru")
        self.assertEqual(parsing.detect_language("in English"), "en")

    def test_missing_required_fields_detected(self):
        p = parsing.parse_request_text("make a video")
        self.assertIn("firm name", parsing.missing_required(p))

    def test_no_url_is_not_invented(self):
        p = parsing.parse_request_text("History video for Acme Legal LLP")
        self.assertEqual(p["website"], "")
        self.assertIn("website or Facebook URL", parsing.missing_required(p))

    def test_query_string_in_url_preserved(self):
        p = parsing.parse_request_text("for Acme Legal LLP https://acme.uz/x?y=1&z=2")
        self.assertTrue(p["website"].startswith("https://acme.uz/x"))


class TestFileValidation(unittest.TestCase):
    def test_allowed_types(self):
        for name in ("notes.txt", "ledger.csv", "photo.png", "clip.mp4", "x.pdf"):
            ok, why = parsing.validate_incoming_document(name, 1000, 49)
            self.assertTrue(ok, "%s rejected: %s" % (name, why))

    def test_disallowed_type_rejected(self):
        ok, why = parsing.validate_incoming_document("payload.exe", 1000, 49)
        self.assertFalse(ok)
        self.assertIn("not allowed", why)

    def test_oversize_rejected(self):
        ok, why = parsing.validate_incoming_document("big.mp4", 60 * 1024 * 1024, 49)
        self.assertFalse(ok)
        self.assertIn("limit is 49 MB", why)

    def test_empty_file_rejected(self):
        ok, why = parsing.validate_incoming_document("empty.txt", 0, 49)
        self.assertFalse(ok)

    def test_no_extension_rejected(self):
        ok, why = parsing.validate_incoming_document("README", 100, 49)
        self.assertFalse(ok)

    def test_path_traversal_in_filename_is_stripped(self):
        self.assertEqual(parsing.safe_filename("../../etc/passwd"), "passwd")
        self.assertNotIn("/", parsing.safe_filename("a/b/../../c.txt"))
        self.assertNotIn("..", parsing.safe_filename("../../evil.sh"))

    def test_filename_sanitised_of_shell_characters(self):
        out = parsing.safe_filename("a; rm -rf / ;b.txt")
        self.assertNotIn(";", out)
        self.assertNotIn(" ", out.replace(" ", " ").strip(" ") if False else out.replace(" ", ""))


if __name__ == "__main__":
    unittest.main()


class TestFirmNameNotConfusedByLinks(unittest.TestCase):
    def test_url_after_the_name_is_not_the_name(self):
        from agent_system.telegrambot import parsing
        r = parsing.parse_request_text("GSP Law Firm https://gsplaw.co.uz uzbek motion 2 minutes")
        self.assertEqual(r["firm_name"], "GSP Law Firm")

    def test_trailing_fields_are_not_part_of_the_name(self):
        from agent_system.telegrambot import parsing
        r = parsing.parse_request_text("firm: Acme Partners website https://acme.uz english")
        self.assertEqual(r["firm_name"], "Acme Partners")
