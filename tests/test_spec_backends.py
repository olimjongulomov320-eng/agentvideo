# -*- coding: utf-8 -*-
"""Tests: scene-specification validation and backend discovery."""
import unittest

from agent_system import video
from agent_system.video import blender3d
from agent_system.video.spec import SpecError


def scene(**kw):
    base = {"id": "s1", "kind": "statement", "dur": 3.0, "heading": "H",
            "sub": "", "narration": "n"}
    base.update(kw)
    return base


class TestSpecValidation(unittest.TestCase):
    def test_valid_spec(self):
        spec, errors = video.validate_render_spec(
            {"firm_name": "A", "style": "motion", "scenes": [scene()]})
        self.assertEqual(errors, [])
        self.assertEqual(spec.style, "motion")
        self.assertEqual(spec.total_duration, 3.0)

    def test_fps_defaults_to_30_not_8(self):
        spec, _ = video.validate_render_spec({"firm_name": "A", "scenes": [scene()]})
        self.assertEqual(spec.fps, 30)
        self.assertEqual(spec.width, 1920)
        self.assertEqual(spec.height, 1080)

    def test_aspect_ratio_sets_default_dimensions(self):
        spec, _ = video.validate_render_spec(
            {"firm_name": "A", "aspect": "9:16", "scenes": [scene()]})
        self.assertEqual((spec.width, spec.height), (1080, 1920))

    def test_unknown_style_reported_and_defaulted(self):
        spec, errors = video.validate_render_spec(
            {"firm_name": "A", "style": "claymation", "scenes": [scene()]})
        self.assertEqual(spec.style, "motion")
        self.assertTrue(any("unknown style" in e for e in errors))

    def test_unknown_kind_reported(self):
        _spec, errors = video.validate_render_spec(
            {"firm_name": "A", "scenes": [scene(kind="hologram")]})
        self.assertTrue(any("unknown kind" in e for e in errors))

    def test_scene_duration_bounds(self):
        _spec, errors = video.validate_render_spec(
            {"firm_name": "A", "scenes": [scene(dur=0.2)]})
        self.assertTrue(any("outside" in e for e in errors))

    def test_empty_scenes_is_hard_error(self):
        with self.assertRaises(SpecError):
            video.validate_render_spec({"firm_name": "A", "scenes": []})

    def test_too_many_scenes_is_hard_error(self):
        with self.assertRaises(SpecError):
            video.validate_render_spec({"firm_name": "A",
                                        "scenes": [scene(id="s%d" % i) for i in range(60)]})

    def test_narration_length_capped(self):
        _spec, errors = video.validate_render_spec(
            {"firm_name": "A", "scenes": [scene(narration="x" * 5000)]})
        self.assertTrue(any("narration" in e for e in errors))

    def test_resolution_limits(self):
        _spec, errors = video.validate_render_spec(
            {"firm_name": "A", "width": 10, "height": 10, "scenes": [scene()]})
        self.assertTrue(any("width" in e for e in errors))

    def test_spec_round_trips_to_dict(self):
        spec, _ = video.validate_render_spec({"firm_name": "A", "scenes": [scene()]})
        d = spec.to_dict()
        self.assertEqual(d["total_duration_sec"], 3.0)
        self.assertIn("audio", d)


class TestBackendDiscovery(unittest.TestCase):
    def test_three_styles_exposed(self):
        styles = [b["style"] for b in video.list_backends()]
        self.assertEqual(styles, ["motion", "illustrated", "blender3d"])

    def test_motion_and_illustrated_ready_when_ffmpeg_present(self):
        from agent_system.video import common
        expects = common.ffmpeg_available()
        self.assertEqual(video.backend_info("motion")["ready"], expects)
        self.assertEqual(video.backend_info("illustrated")["ready"], expects)

    def test_blender_readiness_matches_binary_presence(self):
        info = video.backend_info("blender3d")
        self.assertEqual(info["ready"], blender3d.blender_available())
        if not blender3d.blender_available():
            self.assertTrue(any("Blender is not installed" in r for r in info["reasons"]))
            self.assertTrue(info["limitations"])

    def test_unknown_backend_raises(self):
        with self.assertRaises(SpecError):
            video.get_backend("holodeck")


if __name__ == "__main__":
    unittest.main()
