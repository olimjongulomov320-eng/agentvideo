# -*- coding: utf-8 -*-
"""Tests: the automated visual-QA workflow.

Covers the frame heuristics (blank/contrast/margin), the *motion* comparison
(the signal that distinguishes animation from static slides), contact-sheet
generation, and report emission. A tiny real render is used for the end-to-end
case; everything else is pure image analysis so the suite stays fast.
"""
import json
import os
import shutil
import tempfile
import unittest

from PIL import Image, ImageDraw

from agent_system.video import common, design, qa


class TestSampling(unittest.TestCase):
    def test_sample_times_are_inside_the_runtime(self):
        times = qa.sample_times(10.0, 12)
        self.assertEqual(len(times), 12)
        self.assertTrue(all(0.0 <= t <= 10.0 for t in times))
        self.assertEqual(times, sorted(times))

    def test_sample_times_are_evenly_spaced(self):
        times = qa.sample_times(12.0, 4)
        deltas = [round(b - a, 3) for a, b in zip(times, times[1:])]
        self.assertTrue(all(abs(d - deltas[0]) < 0.02 for d in deltas), deltas)

    def test_sample_times_handles_very_short_or_zero_duration(self):
        self.assertTrue(len(qa.sample_times(0.0, 4)) >= 2)
        self.assertTrue(all(t >= 0.0 for t in qa.sample_times(0.05, 4)))


class TestFrameMetrics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-frame-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _save(self, img, name):
        p = os.path.join(self.tmp, name)
        img.save(p)
        return p

    def test_flat_frame_is_flagged_near_blank(self):
        p = self._save(Image.new("RGB", (320, 180), (14, 45, 62)), "flat.png")
        info = qa.analyze_frame(p)
        self.assertTrue(info["near_blank"])
        self.assertTrue(info["low_contrast"])

    def test_detailed_frame_is_not_near_blank(self):
        img = Image.new("RGB", (320, 180), (14, 45, 62))
        d = ImageDraw.Draw(img)
        for i in range(0, 320, 20):
            d.line([(i, 0), (i, 180)], fill=(248, 246, 241), width=3)
        d.rectangle([40, 40, 280, 140], outline=(201, 169, 110), width=4)
        p = self._save(img, "busy.png")
        info = qa.analyze_frame(p)
        self.assertFalse(info["near_blank"], info)
        self.assertGreater(info["edge_density"], 0.01)

    def test_frame_dimensions_and_aspect_are_reported(self):
        p = self._save(Image.new("RGB", (640, 360), (10, 10, 10)), "size.png")
        info = qa.analyze_frame(p)
        self.assertEqual((info["width"], info["height"]), (640, 360))
        self.assertAlmostEqual(info["aspect"], 16.0 / 9.0, places=3)

    def test_margin_check_detects_content_at_the_edge(self):
        bg = (14, 45, 62)
        safe = Image.new("RGB", (400, 225), bg)
        ImageDraw.Draw(safe).rectangle([200, 100, 220, 120], fill=(255, 255, 255))
        edge = Image.new("RGB", (400, 225), bg)
        ImageDraw.Draw(edge).line([(0, 221), (400, 221)], fill=(255, 255, 255), width=8)
        safe_v = qa.margin_edge_density(safe)
        edge_v = qa.margin_edge_density(edge)
        self.assertEqual(safe_v, 0.0, "centred content must not register in the edge ring")
        self.assertGreater(edge_v, safe_v,
                           "content at the frame edge should score higher than centred content")
        self.assertGreater(edge_v, qa.MARGIN_EDGE_MAX)

    def test_empty_background_has_no_edge_response(self):
        """The frame border itself must not be mistaken for content."""
        bg = design.build_background(640, 360, "navy")
        self.assertLess(qa.margin_edge_density(bg), 0.005)
        self.assertLess(qa._edge_density(bg), 0.005)

    def test_margin_ok_flag_reflects_the_threshold(self):
        bg = (14, 45, 62)
        img = Image.new("RGB", (400, 225), bg)
        ImageDraw.Draw(img).line([(0, 220), (400, 220)], fill=(255, 255, 255), width=8)
        p = self._save(img, "tight.png")
        self.assertFalse(qa.analyze_frame(p)["margin_ok"])

    def test_solid_block_flush_with_the_edge_is_detected(self):
        """A solid fill has no internal edges — the mean-step signal must catch it."""
        bg = (14, 45, 62)
        img = Image.new("RGB", (400, 225), bg)
        ImageDraw.Draw(img).rectangle([0, 215, 400, 225], fill=(255, 255, 255))
        edge, step = qa.margin_metrics(img)
        self.assertLessEqual(edge, qa.MARGIN_EDGE_MAX,
                             "a solid fill has no internal edges to detect")
        self.assertGreater(step, qa.MARGIN_STEP_MAX,
                           "the mean-step signal should catch the solid fill")

    def test_smooth_gradient_at_the_edge_is_not_a_breach(self):
        """A background gradient reaching the edge must not be flagged."""
        img = Image.new("RGB", (400, 225), (10, 10, 10))
        px = img.load()
        for x in range(400):
            v = int(10 + 120 * (x / 399.0))
            for y in range(225):
                px[x, y] = (v, v, v)
        edge, step = qa.margin_metrics(img)
        self.assertLessEqual(step, qa.MARGIN_STEP_MAX,
                             "a smooth gradient should not read as content at the edge")
        self.assertTrue(qa.analyze_frame(self._save(img, "grad.png"))["margin_ok"])

    def test_clean_background_is_within_both_margin_thresholds(self):
        for variant in design.VARIANTS:
            bg = design.build_background(640, 360, variant)
            p = os.path.join(self.tmp, "bg_%s.png" % variant)
            bg.save(p)
            info = qa.analyze_frame(p)
            self.assertTrue(info["margin_ok"],
                            "an empty %s ground should not breach the margin check: %s"
                            % (variant, info))

    def test_identical_images_have_zero_difference(self):
        a = Image.new("RGB", (80, 45), (30, 30, 30))
        b = a.copy()
        self.assertEqual(qa._mean_abs_diff(a, b), 0.0)

    def test_different_images_have_positive_difference(self):
        a = Image.new("RGB", (80, 45), (0, 0, 0))
        b = Image.new("RGB", (80, 45), (255, 255, 255))
        self.assertGreater(qa._mean_abs_diff(a, b), 0.5)

    def test_partial_change_is_measured_not_just_mean_brightness(self):
        """A small local change must register (this is what catches static slides)."""
        a = Image.new("RGB", (100, 100), (10, 10, 10))
        b = a.copy()
        ImageDraw.Draw(b).rectangle([0, 0, 49, 99], fill=(255, 255, 255))
        self.assertGreater(qa._mean_abs_diff(a, b), 0.4)


class TestContactSheet(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="qa-sheet-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_contact_sheet_is_written_with_all_cells(self):
        frames = []
        for i, t in enumerate((1.0, 2.0, 3.0, 4.0, 5.0)):
            p = os.path.join(self.tmp, "f%d.png" % i)
            Image.new("RGB", (320, 180), (i * 30, 60, 90)).save(p)
            frames.append((t, p))
        out = os.path.join(self.tmp, "sheet.png")
        got = qa.contact_sheet(frames, out, cols=3, cell_w=200, title="test sheet")
        self.assertEqual(got, out)
        self.assertTrue(os.path.isfile(out))
        sheet = Image.open(out)
        # 3 columns x 2 rows of cells plus padding/header.
        self.assertGreater(sheet.width, 3 * 200)
        self.assertGreater(sheet.height, 2 * 180)

    def test_contact_sheet_returns_none_for_no_frames(self):
        self.assertIsNone(qa.contact_sheet([], os.path.join(self.tmp, "none.png")))


@unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
class TestQaVideoEndToEnd(unittest.TestCase):
    """Render a tiny real clip once, then exercise the whole QA pass on it."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="qa-e2e-")
        cls.clip = os.path.join(cls.tmp, "clip.mp4")
        w, h, fps, secs = 192, 108, 12, 1.5

        def frames():
            for i in range(int(fps * secs)):
                img = Image.new("RGB", (w, h), (14, 45, 62))
                d = ImageDraw.Draw(img)
                # Deliberate motion so the static-stretch check stays clear.
                x = int((w - 40) * (i / float(fps * secs)))
                d.rectangle([x, 30, x + 40, 78], fill=(248, 246, 241))
                d.rectangle([10, 90, 182, 96], fill=(201, 169, 110))
                yield img
        common.encode_frames_to_video(frames(), cls.clip, w, h, fps, profile="preview")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_qa_video_produces_a_full_report_and_contact_sheet(self):
        out_dir = os.path.join(self.tmp, "report")
        report = qa.qa_video(self.clip, out_dir, expect_width=192, expect_height=108,
                             expect_fps=12, require_audio=False, samples=6,
                             label="unit test clip")
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "qa_report.json")))
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "qa_report.md")))
        self.assertTrue(os.path.isfile(report["contact_sheet"]))
        self.assertEqual(report["technical"]["width"], 192)
        self.assertEqual(report["technical"]["height"], 108)
        self.assertGreaterEqual(report["frames_sampled"], 2)
        self.assertIn("motion_summary", report)
        self.assertIsInstance(report["frames"], list)
        # Requiring audio on a video-only clip must fail, not silently pass.
        audio_report = qa.qa_video(self.clip, os.path.join(self.tmp, "r2"),
                                   require_audio=True, samples=3)
        self.assertTrue(audio_report["errors"])

    def test_qa_report_json_is_valid_and_lists_thresholds(self):
        out_dir = os.path.join(self.tmp, "json")
        qa.qa_video(self.clip, out_dir, require_audio=False, samples=6)
        with open(os.path.join(out_dir, "qa_report.json"), encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertIn("thresholds", data)
        self.assertTrue(data["heuristics_only"])
        self.assertIn("note", data)

    def test_qa_video_reports_a_missing_file_rather_than_raising(self):
        out_dir = os.path.join(self.tmp, "missing")
        report = qa.qa_video(os.path.join(self.tmp, "nope.mp4"), out_dir)
        self.assertTrue(report["errors"])
        self.assertTrue(os.path.isfile(os.path.join(out_dir, "qa_report.json")))

    def test_qa_flags_a_static_clip(self):
        """A clip whose frames never change must trip the static-stretch check."""
        static_clip = os.path.join(self.tmp, "static.mp4")
        w, h, fps, secs = 160, 90, 10, 2.0

        def static_frames():
            for _ in range(int(fps * secs)):
                img = Image.new("RGB", (w, h), (14, 45, 62))
                ImageDraw.Draw(img).rectangle([20, 20, 60, 60], fill=(248, 246, 241))
                yield img
        common.encode_frames_to_video(static_frames(), static_clip, w, h, fps,
                                      profile="preview")
        report = qa.qa_video(static_clip, os.path.join(self.tmp, "static_qa"),
                             require_audio=False, samples=6)
        self.assertTrue(report["static_stretches"],
                        "a completely static clip should be flagged")


if __name__ == "__main__":
    unittest.main()
