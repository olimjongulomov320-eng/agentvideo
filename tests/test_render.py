# -*- coding: utf-8 -*-
"""Tests: real rendering per backend, ffprobe validation, exit-state guarantees.

These are true renders (not mocks) but deliberately tiny: 320x180 @ 8 fps for
~2 s per scene, so the suite stays fast. Blender is covered for its *honest
unavailability*, which is the correct behaviour on this machine.
"""
import os
import shutil
import tempfile
import unittest

from agent_system import video
from agent_system.video import blender3d, common

SCENES = [
    {"id": "s1", "key": "hook", "kind": "statement", "dur": 2.0,
     "heading": "Test Film", "sub": "", "narration": "test", "placeholder": False},
    {"id": "s2", "key": "stat", "kind": "stat", "dur": 2.0,
     "heading": "2010", "sub": "supporting line", "narration": "test",
     "placeholder": False},
    {"id": "s3", "key": "office", "kind": "title", "dur": 2.0,
     "heading": "New office", "sub": "Tashkent", "narration": "test",
     "placeholder": False},
    {"id": "s4", "key": "closing", "kind": "endcard", "dur": 2.0,
     "heading": "Test Firm", "sub": "DEMO", "narration": "test",
     "placeholder": False},
]


def base_raw(style, **kw):
    raw = {"firm_name": "Test Firm", "language": "en", "style": style,
           "width": 320, "height": 180, "fps": 8, "scenes": [dict(s) for s in SCENES],
           "watermark": "DEMO / CONCEPT PREVIEW"}
    raw.update(kw)
    return raw


class TestRealRenders(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="render_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _render(self, style):
        spec, errors = video.validate_render_spec(base_raw(style))
        self.assertEqual(errors, [])
        out = os.path.join(self.tmp, "%s.mp4" % style)
        result = video.render_style(spec, out, os.path.join(self.tmp, "work_" + style))
        return out, result

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_motion_graphics_renders_a_real_mp4(self):
        out, result = self._render("motion")
        self.assertTrue(os.path.isfile(out))
        v = result["validation"]
        self.assertTrue(v["ok"], v["errors"])
        self.assertEqual(v["width"], 320)
        self.assertEqual(v["height"], 180)
        self.assertEqual(v["video_codec"], "h264")
        self.assertIsNotNone(v["audio_codec"])
        self.assertGreater(v["size_bytes"], 1024)
        # 4 scenes x 2 s with 3 x 0.7 s crossfade overlaps => 8.0 - 2.1 = 5.9 s
        self.assertGreater(v["duration_sec"], 5.5)
        self.assertLess(v["duration_sec"], 7.5)

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_illustrated_renders_a_real_mp4(self):
        out, result = self._render("illustrated")
        v = result["validation"]
        self.assertTrue(v["ok"], v["errors"])
        self.assertEqual(v["video_codec"], "h264")
        self.assertIsNotNone(v["audio_codec"])

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_render_manifest_is_written_real_and_labeled(self):
        out, result = self._render("motion")
        manifest = result["manifest"]
        self.assertEqual(manifest["backend"], "motion")
        self.assertEqual(manifest["demo_label"], "DEMO / CONCEPT PREVIEW")
        self.assertIn("ffmpeg", manifest["engine"])
        self.assertTrue(manifest["limitations"])
        self.assertEqual(manifest["audio"]["license"], "synthesized_temporary")

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_music_metadata_declares_synthesis_not_a_licence(self):
        _out, result = self._render("motion")
        detail = result["manifest"].get("audio_detail", {})
        self.assertEqual(detail.get("music_license"), "synthesized_temporary")
        self.assertTrue(any("NOT licensed" in m for m in detail.get("mixing", [])))

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_placeholder_scenes_are_visually_flagged(self):
        raw = base_raw("motion")
        raw["scenes"][0]["placeholder"] = True
        raw["scenes"][0]["needs"] = ["founding_year"]
        spec, _ = video.validate_render_spec(raw)
        out = os.path.join(self.tmp, "ph.mp4")
        result = video.render_style(spec, out, os.path.join(self.tmp, "w_ph"))
        self.assertTrue(result["validation"]["ok"])

    def test_frame_renderer_error_does_not_deadlock(self):
        """A failing frame generator must raise promptly, never hang ffmpeg."""
        import time
        from agent_system.video.common import RenderError, encode_frames_to_video

        def broken():
            yield _img()
            raise RuntimeError("renderer exploded")

        def _img():
            from PIL import Image
            return Image.new("RGB", (64, 36), (0, 0, 0))

        started = time.time()
        with self.assertRaises(RenderError) as ctx:
            encode_frames_to_video(broken(), os.path.join(self.tmp, "broken.mp4"),
                                   64, 36, 8)
        self.assertIn("renderer exploded", str(ctx.exception))
        self.assertLess(time.time() - started, 60.0, "encoder deadlocked")

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_backend_rejects_ffmpeg_missing_scenario(self):
        """With ffmpeg hidden, backends must report honestly instead of producing junk."""
        original = common.FFMPEG
        common.FFMPEG = "definitely-not-ffmpeg"
        # ffmpeg_available() consults shutil.which on the module constant
        try:
            self.assertFalse(common.ffmpeg_available())
            spec, _ = video.validate_render_spec(base_raw("motion"))
            with self.assertRaises(common.RenderError):
                video.render_style(spec, os.path.join(self.tmp, "x.mp4"),
                                   os.path.join(self.tmp, "w_x"))
        finally:
            common.FFMPEG = original


class TestBlenderHonesty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="blender_test_")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_availability_report_is_accurate(self):
        avail = blender3d.availability()
        self.assertIn("available", avail)
        self.assertEqual(avail["available"], blender3d.blender_available())
        if not avail["available"]:
            self.assertTrue(avail["install_steps"])
            self.assertIn("brew install --cask blender", " ".join(avail["install_steps"]))

    @unittest.skipIf(blender3d.blender_available(), "Blender is installed here")
    def test_render_fails_honestly_and_still_writes_the_script(self):
        spec, _ = video.validate_render_spec(base_raw("blender3d"))
        work = os.path.join(self.tmp, "w3d")
        with self.assertRaises(common.RenderError) as ctx:
            video.render_style(spec, os.path.join(self.tmp, "o.mp4"), work)
        msg = str(ctx.exception)
        self.assertIn("Blender is not installed", msg)
        self.assertIn("brew install", msg)
        self.assertTrue(os.path.isfile(os.path.join(work, "scene_3d.py")),
                        "the generated Blender script should be kept for later use")

    def test_blender_script_is_real_python_bpy_source(self):
        spec, _ = video.validate_render_spec(base_raw("blender3d"))
        path = blender3d.write_blender_script(spec, os.path.join(self.tmp, "s.py"),
                                              os.path.join(self.tmp, "frames"))
        src = open(path, encoding="utf-8").read()
        for needle in ("import bpy", "bpy.ops.render.render", "scene.camera",
                       "def main():", "Test Firm", "add_emblem"):
            self.assertIn(needle, src, "missing %r in generated Blender script" % needle)

    def test_no_3d_output_is_claimed_when_blender_is_absent(self):
        info = video.backend_info("blender3d")
        if not blender3d.blender_available():
            self.assertFalse(info["ready"])
            self.assertTrue(info["limitations"])


class TestFfprobeValidation(unittest.TestCase):
    def test_probe_of_missing_file_reports_an_error_not_a_crash(self):
        report = common.validate_mp4("/nonexistent/file.mp4")
        self.assertFalse(report["ok"])
        self.assertTrue(report["errors"])
        self.assertEqual(report["checks"], [])

    @unittest.skipUnless(common.ffmpeg_available() and common.ffprobe_available(),
                         "ffmpeg/ffprobe not installed")
    def test_validation_reports_wrong_dimensions(self):
        tmp = tempfile.mkdtemp(prefix="probe_test_")
        try:
            spec, _ = video.validate_render_spec(base_raw("motion"))
            out = os.path.join(tmp, "v.mp4")
            video.render_style(spec, out, os.path.join(tmp, "w"))
            report = common.validate_mp4(out, expect_width=1920, expect_height=1080)
            self.assertFalse(report["ok"])
            self.assertTrue(any("width" in e for e in report["errors"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_validation_note_requires_human_review(self):
        tmp = tempfile.mkdtemp(prefix="probe2_")
        try:
            spec, _ = video.validate_render_spec(base_raw("motion"))
            out = os.path.join(tmp, "v.mp4")
            video.render_style(spec, out, os.path.join(tmp, "w"))
            report = common.validate_mp4(out, 320, 180, 8)
            self.assertTrue(report["ok"])
            self.assertIn("human", report["note"].lower())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
