# -*- coding: utf-8 -*-
"""Tests: the render pipeline — profiles, encoder selection, failure handling.

The central guarantee under test is that a *deliverable* render cannot silently
be produced at preview resolution. The old pipeline shipped a 960x540 file as a
"final" film because fast mode overrode the dimensions with nothing to stop it;
these tests pin the separation down.
"""
import os
import shutil
import subprocess
import tempfile
import types
import unittest
from unittest import mock

from PIL import Image

from agent_system import qa_fixture
from agent_system.config import (PREVIEW_PROFILE, PRODUCTION_PROFILE, QUALITY_NAMES,
                                 Config)
from agent_system.jobs import JobStore
from agent_system.orchestrator import run_job, sanitize_request
from agent_system.video import common, design, motion, spec as video_spec
from tests.fakes import html_pages

FIRM_HTML = """<html><head><title>Acme Legal LLP</title></head><body>
<h1>About</h1>
<p>Acme Legal LLP was founded in 2010 in Tashkent.</p>
</body></html>"""


class TestProfiles(unittest.TestCase):
    def setUp(self):
        self._env = {k: os.environ.get(k) for k in ("RENDER_QUALITY", "FAST_RENDER",
                                                    "OUTPUT_DIR", "PROJECT_ROOT")}
        for k in ("RENDER_QUALITY", "FAST_RENDER"):
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _cfg(self, **kw):
        tmp = tempfile.mkdtemp(prefix="prof-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        return Config.from_env(project_root=tmp, detect=False, **kw)

    def test_production_profile_is_full_hd(self):
        cfg = self._cfg()
        self.assertEqual(cfg.production_profile(), {"width": 1920, "height": 1080, "fps": 30})
        self.assertEqual(PRODUCTION_PROFILE, {"width": 1920, "height": 1080, "fps": 30})

    def test_preview_profile_is_smaller_than_production(self):
        self.assertLess(PREVIEW_PROFILE["width"], PRODUCTION_PROFILE["width"])
        self.assertLess(PREVIEW_PROFILE["height"], PRODUCTION_PROFILE["height"])
        self.assertLess(PREVIEW_PROFILE["fps"], PRODUCTION_PROFILE["fps"])

    def test_default_quality_is_production(self):
        cfg = self._cfg()
        self.assertEqual(cfg.render_quality, "production")
        self.assertEqual(cfg.encode_profile(), "production")
        self.assertEqual(cfg.render_overrides(), {},
                         "a production render must not override the manifest dimensions")

    def test_fast_render_switches_to_preview_and_is_non_deliverable(self):
        os.environ["FAST_RENDER"] = "true"
        cfg = self._cfg()
        self.assertEqual(cfg.encode_profile(), "preview")
        self.assertEqual(cfg.render_overrides(), PREVIEW_PROFILE)
        # Crucially the *production* profile is untouched — the difference between
        # the two is explicit rather than a mutated global.
        self.assertEqual(cfg.production_profile(), PRODUCTION_PROFILE)

    def test_render_quality_env_selects_the_preview_encoder(self):
        os.environ["RENDER_QUALITY"] = "preview"
        cfg = self._cfg()
        self.assertEqual(cfg.render_quality, "preview")
        self.assertEqual(cfg.encode_profile(), "preview")

    def test_unknown_render_quality_falls_back_to_production(self):
        os.environ["RENDER_QUALITY"] = "ultra-mega"
        cfg = self._cfg()
        self.assertEqual(cfg.render_quality, "production")
        self.assertIn(cfg.render_quality, QUALITY_NAMES)

    def test_preview_spec_caps_at_the_preview_profile(self):
        from agent_system.orchestrator import _preview_spec
        full = video_spec.validate_render_spec({
            "firm_name": "A", "width": 1920, "height": 1080, "fps": 30,
            "scenes": [{"id": "s%d" % i, "kind": "statement", "dur": 4.0,
                        "heading": "H", "narration": "n"} for i in range(6)]})[0]
        prev = _preview_spec(full)
        self.assertLessEqual(prev.width, PREVIEW_PROFILE["width"])
        self.assertLessEqual(prev.height, PREVIEW_PROFILE["height"])
        self.assertLessEqual(prev.fps, PREVIEW_PROFILE["fps"])
        self.assertIn("PREVIEW", prev.watermark.upper())
        self.assertLess(prev.total_duration, full.total_duration)

    def test_preview_spec_never_upscales_a_smaller_spec(self):
        from agent_system.orchestrator import _preview_spec
        small = video_spec.validate_render_spec({
            "firm_name": "A", "width": 320, "height": 180, "fps": 8,
            "scenes": [{"id": "s", "kind": "statement", "dur": 3.0,
                        "heading": "H", "narration": "n"}]})[0]
        prev = _preview_spec(small)
        self.assertEqual((prev.width, prev.height), (320, 180))


class TestEncoderProfiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="enc-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def _capture_cmd(self, **kw):
        """Run the encoder against a fake ffmpeg that records the argv."""
        captured = {}

        class FakeStdin(object):
            def write(self, data):
                return len(data)

            def close(self):
                pass

        class FakeProc(object):
            def __init__(self, cmd, **kwargs):
                captured["cmd"] = cmd
                self.stdin = FakeStdin()
                self.stderr = types.SimpleNamespace(read=lambda: b"")
                self.returncode = 0

            def wait(self, timeout=None):
                return 0

            def kill(self):
                pass

        frames = iter([Image.new("RGB", (64, 36), (10, 20, 30))])
        with mock.patch.object(common.subprocess, "Popen", FakeProc):
            common.encode_frames_to_video(frames, os.path.join(self.tmp, "o.mp4"),
                                          64, 36, 8, **kw)
        return captured["cmd"]

    def test_production_profile_uses_quality_settings(self):
        cmd = self._capture_cmd(profile="production")
        self.assertIn("-crf", cmd)
        self.assertEqual(cmd[cmd.index("-crf") + 1], "18")
        self.assertEqual(cmd[cmd.index("-preset") + 1], "medium")

    def test_preview_profile_uses_fast_settings(self):
        cmd = self._capture_cmd(profile="preview")
        self.assertEqual(cmd[cmd.index("-crf") + 1], "23")
        self.assertEqual(cmd[cmd.index("-preset") + 1], "veryfast")

    def test_legacy_defaults_are_unchanged_for_backward_compatibility(self):
        """No profile ⇒ the historical CRF 20 / veryfast behaviour."""
        cmd = self._capture_cmd()
        self.assertEqual(cmd[cmd.index("-crf") + 1], "20")
        self.assertEqual(cmd[cmd.index("-preset") + 1], "veryfast")

    def test_explicit_crf_and_preset_win_over_the_profile(self):
        cmd = self._capture_cmd(profile="production", crf=31, preset="ultrafast")
        self.assertEqual(cmd[cmd.index("-crf") + 1], "31")
        self.assertEqual(cmd[cmd.index("-preset") + 1], "ultrafast")

    def test_unknown_profile_falls_back_to_legacy_defaults(self):
        cmd = self._capture_cmd(profile="not-a-profile")
        self.assertEqual(cmd[cmd.index("-crf") + 1], "20")

    def test_encode_profiles_map_has_both_names(self):
        self.assertIn("production", common.ENCODE_PROFILES)
        self.assertIn("preview", common.ENCODE_PROFILES)
        for name, prof in common.ENCODE_PROFILES.items():
            self.assertIn("crf", prof)
            self.assertIn("preset", prof)


class TestRenderFailures(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fail-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_ffmpeg_non_zero_exit_raises_render_error(self):
        class FakeStdin(object):
            def write(self, data):
                return len(data)

            def close(self):
                pass

        class FailingProc(object):
            def __init__(self, cmd, **kwargs):
                self.stdin = FakeStdin()
                self.stderr = types.SimpleNamespace(read=lambda: b"encoder exploded")
                self.returncode = 1

            def wait(self, timeout=None):
                return 1

            def kill(self):
                pass

        frames = iter([Image.new("RGB", (32, 18), (0, 0, 0))])
        with mock.patch.object(common.subprocess, "Popen", FailingProc):
            with self.assertRaises(common.RenderError) as ctx:
                common.encode_frames_to_video(frames, os.path.join(self.tmp, "x.mp4"),
                                              32, 18, 8)
        self.assertIn("ffmpeg", str(ctx.exception).lower())

    def test_a_frame_generator_that_raises_fails_fast(self):
        def broken():
            yield Image.new("RGB", (32, 18), (0, 0, 0))
            raise RuntimeError("generator died")

        with self.assertRaises(common.RenderError):
            common.encode_frames_to_video(broken(), os.path.join(self.tmp, "y.mp4"),
                                          32, 18, 8)

    def test_generator_producing_no_frames_raises(self):
        def empty():
            return
            yield  # pragma: no cover
        with self.assertRaises(common.RenderError):
            common.encode_frames_to_video(empty(), os.path.join(self.tmp, "z.mp4"),
                                          32, 18, 8)

    def test_truncated_or_garbage_file_fails_validation(self):
        bad = os.path.join(self.tmp, "garbage.mp4")
        with open(bad, "wb") as fh:
            fh.write(b"this is definitely not an mp4 file")
        report = common.validate_mp4(bad)
        self.assertFalse(report["ok"])
        self.assertTrue(report["errors"])

    def test_missing_file_fails_validation_without_raising(self):
        report = common.validate_mp4(os.path.join(self.tmp, "absent.mp4"))
        self.assertFalse(report["ok"])
        self.assertTrue(report["errors"])

    def test_validate_mp4_rejects_a_wrong_resolution(self):
        """A 320x180 clip must not pass a 1920x1080 expectation."""
        clip = os.path.join(self.tmp, "small.mp4")
        common.encode_frames_to_video(
            (Image.new("RGB", (320, 180), (10, 20, 30)) for _ in range(4)),
            clip, 320, 180, 8, profile="preview")
        ok = common.validate_mp4(clip, expect_width=1920, expect_height=1080,
                                 expect_fps=30, require_audio=False)
        self.assertFalse(ok["ok"])


@unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
class TestTinyRenderIntegrity(unittest.TestCase):
    """One small real render, checked for timing/frame-count/size correctness."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="render-")
        scenes = [{"id": "a", "key": "hook", "kind": "title", "dur": 1.2,
                   "heading": "Alpha", "sub": "first", "narration": ""},
                  {"id": "b", "key": "origin", "kind": "statement", "dur": 1.2,
                   "heading": "Bravo", "sub": "second", "narration": ""},
                  {"id": "c", "key": "closing", "kind": "endcard", "dur": 1.2,
                   "heading": "Charlie", "sub": "third", "narration": ""}]
        cls.spec = video_spec.validate_render_spec({
            "firm_name": "Tiny Test", "width": 256, "height": 144, "fps": 10,
            "scenes": scenes})[0]
        cls.out = os.path.join(cls.tmp, "tiny.mp4")
        video_spec  # keep the import obviously used
        from agent_system import video as video_pkg
        cls.result = video_pkg.render_style(cls.spec, cls.out,
                                            os.path.join(cls.tmp, "work"),
                                            profile="preview")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_frame_count_matches_duration_times_fps(self):
        overlap = min(self.spec.transition_sec,
                      min(s["dur"] for s in self.spec.scenes) * 0.4)
        starts = motion._scene_starts(self.spec.scenes, overlap)
        total = starts[-1] + float(self.spec.scenes[-1]["dur"])
        expected = int(round(total * self.spec.fps))
        info = common.probe(self.out)
        vstream = next(s for s in info["streams"] if s["codec_type"] == "video")
        self.assertEqual(int(vstream["nb_frames"]), expected,
                         "rendered frame count must equal round(total_seconds * fps)")

    def test_scene_starts_overlap_by_the_transition(self):
        starts = motion._scene_starts(
            [{"dur": 2.0}, {"dur": 2.0}, {"dur": 2.0}], 0.5)
        self.assertEqual(starts, [0.0, 1.5, 3.0])

    def test_single_scene_starts_at_zero(self):
        self.assertEqual(motion._scene_starts([{"dur": 3.0}], 0.6), [0.0])

    def test_render_reports_validation_and_manifest(self):
        self.assertTrue(self.result["validation"]["ok"])
        self.assertEqual(self.result["validation"]["width"], 256)
        self.assertIn("manifest", self.result)
        manifest = self.result["manifest"]
        # The manifest must record which design system and encoder profile were
        # actually used, so a delivered file can always be audited afterwards.
        self.assertEqual(manifest["design_system"], design.DESIGN_VERSION)
        self.assertEqual(manifest["profile"], "preview")

    def test_audio_stream_is_present_by_default(self):
        report = common.validate_mp4(self.out, require_audio=True)
        self.assertTrue(report["ok"], report.get("errors"))
        self.assertTrue(report["audio_codec"])

    def test_aspect_ratio_is_preserved_end_to_end(self):
        report = common.validate_mp4(self.out)
        self.assertAlmostEqual(report["width"] / float(report["height"]),
                               256 / 144.0, places=3)


class TestDeliverableRenderProfile(unittest.TestCase):
    """The end-to-end guarantee: a job with no overrides renders Full HD.

    The renderer itself is mocked so this test is fast and deterministic; what it
    proves is the *wiring* — that the orchestrator hands the backend a 1920x1080
    @30 spec and asks for the production encoder profile. Without this, the old
    failure mode (a "final" film quietly produced at 960x540) could return.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="deliver-")
        self._env = {k: os.environ.get(k) for k in ("OUTPUT_DIR", "PROJECT_ROOT",
                                                    "FAST_RENDER", "RENDER_QUALITY")}
        for k in ("FAST_RENDER", "RENDER_QUALITY"):
            os.environ.pop(k, None)
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

    def _fake_render(self, captured):
        def fake_render(spec, out_path, work_dir, asset_dir="", cancel=None,
                        progress=None, profile="production"):
            captured["spec"] = spec
            captured["profile"] = profile
            os.makedirs(os.path.dirname(out_path), exist_ok=True)
            with open(out_path, "wb") as fh:
                fh.write(b"\x00" * 4096)
            validation = {
                "path": out_path, "ok": True, "checks": [], "warnings": [], "errors": [],
                "width": spec.width, "height": spec.height, "fps": spec.fps,
                "duration_sec": spec.total_duration, "size_bytes": 4096,
                "video_codec": "h264", "audio_codec": "aac", "audio_channels": 2,
            }
            return {"output": out_path, "validation": validation,
                    "manifest": {"design_system": design.DESIGN_VERSION,
                                 "profile": profile, "backend": spec.style}}
        return fake_render

    def _run(self, overrides=None, **kw):
        from agent_system import video as video_pkg
        captured = {}
        req = sanitize_request(dict({"firm_name": "Acme Legal LLP",
                                     "website": "https://acme.uz",
                                     "language": "uz", "style": "motion",
                                     "duration_sec": 21}, **kw))
        jid = self.store.create(1, req.style, req.language, req.firm_name,
                                req.duration_sec, 1, params=req.to_dict())
        with mock.patch.object(video_pkg, "render_style", self._fake_render(captured)):
            result = run_job(self.cfg, self.store, jid, req, fetcher=self.fetcher,
                             approve=lambda payload: True, enable_preview=False,
                             overrides=overrides)
        return jid, result, captured

    def test_job_without_overrides_renders_at_full_hd_with_production_profile(self):
        _jid, result, captured = self._run()
        self.assertEqual(result["status"], "completed", result.get("errors"))
        spec = captured["spec"]
        self.assertEqual((spec.width, spec.height, spec.fps), (1920, 1080, 30))
        self.assertEqual(captured["profile"], "production")
        self.assertEqual(result["render_profile"], "production")

    def test_fast_render_config_downgrades_to_a_preview_encoder(self):
        os.environ["FAST_RENDER"] = "true"
        self.cfg = Config.from_env(project_root=self.tmp, detect=False)
        _jid, _result, captured = self._run()
        # fast mode still overrides dimensions, but the encoder profile must be
        # the preview one so a fast file can never be mistaken for a deliverable.
        self.assertEqual(captured["profile"], "preview")

    def test_explicit_overrides_still_win(self):
        _jid, result, captured = self._run(overrides={"width": 320, "height": 180,
                                                      "fps": 8})
        spec = captured["spec"]
        self.assertEqual((spec.width, spec.height, spec.fps), (320, 180, 8))
        self.assertEqual(result["render_profile"], "override")


class TestMissingAssetFallback(unittest.TestCase):
    @unittest.skipUnless(common.ffmpeg_available(), "ffmpeg not installed")
    def test_photo_scene_with_missing_asset_still_renders(self):
        tmp = tempfile.mkdtemp(prefix="noasset-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        s = video_spec.validate_render_spec({
            "firm_name": "A", "width": 320, "height": 180, "fps": 8,
            "scenes": [{"id": "p", "key": "office", "kind": "photo", "dur": 1.0,
                        "heading": "Office", "narration": "",
                        "asset": "definitely-not-there.jpg"}]})[0]
        out = os.path.join(tmp, "photo.mp4")
        result = video_pkg_render(s, out, tmp)
        self.assertTrue(result["validation"]["ok"])
        self.assertTrue(os.path.getsize(out) > 0)

    def test_motion_context_asset_returns_none_for_a_missing_file(self):
        ctx = motion.MotionContext(self.spec_like(), asset_dir="/nonexistent-dir")
        self.assertIsNone(ctx.asset("nope.jpg"))

    def test_motion_context_asset_finds_a_real_file(self):
        tmp = tempfile.mkdtemp(prefix="asset-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        Image.new("RGB", (40, 20), (200, 100, 50)).save(os.path.join(tmp, "p.jpg"))
        ctx = motion.MotionContext(self.spec_like(), asset_dir=tmp)
        self.assertIsNotNone(ctx.asset("p.jpg"))

    def spec_like(self):
        return video_spec.validate_render_spec({
            "firm_name": "A", "width": 160, "height": 90, "fps": 8,
            "scenes": [{"id": "s", "kind": "statement", "dur": 1.0,
                        "heading": "H", "narration": "n"}]})[0]


def video_pkg_render(spec, out, tmp):
    from agent_system import video as video_pkg
    return video_pkg.render_style(spec, out, os.path.join(tmp, "work"),
                                  profile="preview")


class TestEvenDimensions(unittest.TestCase):
    """libx264/yuv420p needs even width and height; the spec must guarantee it."""

    def _spec(self, w, h):
        return video_spec.validate_render_spec({
            "firm_name": "A", "width": w, "height": h, "fps": 10,
            "scenes": [{"id": "s", "kind": "statement", "dur": 1.0,
                        "heading": "H", "narration": "n"}]})

    def test_odd_dimensions_are_snapped_to_even(self):
        s, errors = self._spec(241, 135)
        self.assertEqual(errors, [])
        self.assertEqual(s.width % 2, 0)
        self.assertEqual(s.height % 2, 0)
        self.assertEqual((s.width, s.height), (242, 136))

    def test_even_dimensions_are_left_alone(self):
        s, _ = self._spec(256, 144)
        self.assertEqual((s.width, s.height), (256, 144))

    def test_all_aspects_are_even(self):
        for name, (w, h) in video_spec.ASPECTS.items():
            self.assertEqual((w % 2, h % 2), (0, 0), "aspect %s is odd" % name)


class TestGapBannerNamesTheMissingEvidence(unittest.TestCase):
    """Regression: the GAP banner must name the *specific* unsupplied fact.

    Bug history — ``validate_render_spec`` rebuilt each scene from a fixed set of
    keys and silently dropped ``needs``. Both render paths normalise through that
    function (the full render directly, the preview via ``_preview_spec``), so
    ``scene.get("needs")`` was always None at paint time and every gap scene
    printed the generic fallback "GAP: unverified content". The film stopped
    saying which fact a human had to supply — a data-loss bug in normalisation,
    not a research gap and not a strict validator.

    The pre-existing test only asserted that the render succeeded, so it could
    not detect a wrong caption. These tests assert the caption itself.
    """

    def _raw(self, **scene_over):
        scene = {"id": "sc1", "key": "origin", "kind": "timeline", "dur": 4.0,
                 "heading": "H", "sub": "", "narration": "n"}
        scene.update(scene_over)
        return {"firm_name": "Acme", "width": 320, "height": 180, "fps": 10,
                "scenes": [scene]}

    # ---------------------------------------------------------- normalisation
    def test_needs_survives_normalisation_as_a_list(self):
        spec, errors = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["founding_year"]))
        self.assertEqual(errors, [])
        self.assertEqual(spec.scenes[0]["needs"], ["founding_year"])

    def test_needs_accepts_the_comma_joined_string_story_py_emits(self):
        """story.scene_text returns ", ".join(needs); that shape must work too."""
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs="founding_year,new_office"))
        self.assertEqual(spec.scenes[0]["needs"], ["founding_year", "new_office"])

    def test_needs_defaults_to_an_empty_list_when_absent(self):
        spec, _ = video_spec.validate_render_spec(self._raw())
        self.assertEqual(spec.scenes[0]["needs"], [])
        self.assertFalse(spec.scenes[0]["placeholder"])

    def test_needs_is_trimmed_and_empties_dropped(self):
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["  founding_year  ", "", "   "]))
        self.assertEqual(spec.scenes[0]["needs"], ["founding_year"])

    def test_a_named_gap_is_bounded_in_length_and_count(self):
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True,
                      needs=["x" * 500] + ["g%d" % i for i in range(20)]))
        needs = spec.scenes[0]["needs"]
        self.assertEqual(len(needs), video_spec.MAX_NEEDS)
        self.assertTrue(all(len(n) <= video_spec.NEED_MAX for n in needs))

    def test_survives_the_preview_second_normalisation_pass(self):
        """_preview_spec re-runs validate_render_spec; needs must not be lost."""
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["founding_year"]))
        raw = spec.to_dict()
        raw["width"], raw["height"], raw["fps"] = 320, 180, 10
        again, _ = video_spec.validate_render_spec(raw)
        self.assertEqual(again.scenes[0]["needs"], ["founding_year"])

    # ------------------------------------------------------------- the caption
    def test_banner_names_the_specific_gap_not_the_generic_fallback(self):
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["founding_year"]))
        text = video_spec.gap_banner_text(spec.scenes[0])
        self.assertEqual(text, "founding_year")
        self.assertNotIn("unverified content", text)

    def test_banner_lists_every_named_gap(self):
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["founding_year", "new_office"]))
        self.assertEqual(video_spec.gap_banner_text(spec.scenes[0]),
                         "founding_year, new_office")

    def test_banner_falls_back_only_when_no_gap_is_named(self):
        """A placeholder with no named need still warns - never silently passes."""
        spec, _ = video_spec.validate_render_spec(self._raw(placeholder=True))
        self.assertEqual(video_spec.gap_banner_text(spec.scenes[0]),
                         "unverified content")

    def test_verified_scene_gets_no_banner(self):
        spec, _ = video_spec.validate_render_spec(self._raw())
        self.assertEqual(video_spec.gap_banner_text(spec.scenes[0]), "")

    def test_banner_never_claims_verification(self):
        """Guard the evidence rule: the caption must not assert facts."""
        spec, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["founding_year"]))
        text = video_spec.gap_banner_text(spec.scenes[0]).lower()
        for forbidden in ("verified", "confirmed", "proven"):
            self.assertNotIn(forbidden, text)

    # --------------------------------------------------- don't hide a real gap
    def test_naming_a_gap_without_the_flag_still_flags_it(self):
        """A manifest that lists needs but forgets placeholder=True is still a gap."""
        spec, _ = video_spec.validate_render_spec(
            self._raw(needs=["founding_year"]))       # no placeholder key at all
        self.assertTrue(spec.scenes[0]["placeholder"])
        self.assertEqual(video_spec.gap_banner_text(spec.scenes[0]), "founding_year")

    # ------------------------------------------------------ end-to-end wiring
    def test_both_renderers_use_the_shared_caption_helper(self):
        """Neither renderer may re-implement the caption logic inline."""
        from agent_system.video import illustrated
        import inspect
        for mod in (motion, illustrated):
            src = inspect.getsource(mod)
            self.assertIn("gap_banner_text(scene)", src,
                          "%s must use the shared helper" % mod.__name__)
            self.assertNotIn('or "unverified content"', src,
                             "%s re-implements the fallback inline" % mod.__name__)

    def test_banner_is_actually_drawn_at_render_time(self):
        """Paint a real frame: the placeholder scene must differ from a clean one."""
        import tempfile
        tmp = tempfile.mkdtemp(prefix="gapbanner-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        flagged, _ = video_spec.validate_render_spec(
            self._raw(placeholder=True, needs=["founding_year"]))
        clean, _ = video_spec.validate_render_spec(self._raw())
        ctx_f = motion.MotionContext(flagged, asset_dir="")
        ctx_c = motion.MotionContext(clean, asset_dir="")
        img_f = motion.render_scene_frame(ctx_f, flagged.scenes[0], 3.0)
        img_c = motion.render_scene_frame(ctx_c, clean.scenes[0], 3.0)
        self.assertIsNotNone(img_f)
        self.assertNotEqual(img_f.tobytes(), img_c.tobytes(),
                            "the GAP banner must change the frame")

    def test_different_gap_names_paint_different_frames(self):
        """Proves the *named fact* reaches the canvas, not just 'a banner'.

        Regressing to the generic fallback would make every gap scene paint
        identically; distinct captions must yield distinct pixels.
        """
        frames = {}
        for need in ("founding_year", "new_office"):
            spec, _ = video_spec.validate_render_spec(
                self._raw(placeholder=True, needs=[need]))
            ctx = motion.MotionContext(spec, asset_dir="")
            frames[need] = motion.render_scene_frame(ctx, spec.scenes[0], 3.0).tobytes()
        self.assertNotEqual(frames["founding_year"], frames["new_office"],
                            "different gap names must not paint identical frames")

    # ------------------------------------------------------ orchestrator wiring
    def test_specific_gap_survives_the_whole_orchestrator_run(self):
        """End-to-end: a real job must hand the renderer the named gap.

        This is the path the bug actually travelled: run_job -> manifest ->
        validate_render_spec -> _preview_spec -> render_style. An unreadable site
        must yield a caption naming the missing fact, never the generic phrase.
        """
        tmp = tempfile.mkdtemp(prefix="gapflow-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        cfg = Config.from_env(project_root=tmp, detect=False)
        cfg.ensure_dirs()
        store = JobStore(cfg.db_path)

        captured = []
        real_render_style = motion_render_style()

        def spy(spec, out_path, work_dir, **kw):
            captured.append(spec)
            return real_render_style(spec, out_path, work_dir, **kw)

        req = sanitize_request({"firm_name": "Ghost LLP", "website": "https://ghost.uz",
                                "style": "motion", "duration_sec": 21})
        jid = store.create(1, "motion", "en", "Ghost", 21, 1)
        with mock.patch("agent_system.orchestrator.video.render_style", spy):
            result = run_job(cfg, store, jid, req,
                             fetcher=html_pages({}),      # everything 404 -> gaps
                             approve=lambda p: True,
                             overrides={"width": 320, "height": 180, "fps": 8},
                             enable_preview=True)
        self.assertEqual(result["status"], "completed")
        self.assertTrue(captured, "render_style should have been called (preview/final)")

        # Both the preview spec and the final spec must name the specific gap.
        checked = 0
        seen_captions = set()
        for spec in captured:
            for s in spec.scenes:
                if not s.get("placeholder"):
                    continue
                checked += 1
                self.assertTrue(s.get("needs"),
                                "scene %s lost its named gap in normalisation" % s["id"])
                caption = video_spec.gap_banner_text(s)
                # The caption must be exactly the scene's named gaps, never the
                # generic fallback that the bug produced.
                self.assertEqual(caption, ", ".join(s["needs"]))
                self.assertNotEqual(caption, "unverified content",
                                    "scene %s fell back to the generic caption" % s["id"])
                seen_captions.add(caption)
        self.assertGreater(checked, 0, "no placeholder scene reached the renderer")
        # An unreadable site must name the founding year as a gap somewhere.
        self.assertIn("founding_year", seen_captions)


def motion_render_style():
    """The real render_style, resolved late so the spy can wrap it."""
    from agent_system import video as video_pkg
    return video_pkg.render_style


class TestBackwardCompatibility(unittest.TestCase):
    def test_render_style_accepts_a_call_without_profile(self):
        import inspect
        from agent_system import video as video_pkg
        sig = inspect.signature(video_pkg.render_style)
        self.assertIn("profile", sig.parameters)
        self.assertEqual(sig.parameters["profile"].default, "production")

    def test_motion_backend_render_accepts_profile(self):
        import inspect
        sig = inspect.signature(motion.MotionBackend.render)
        self.assertIn("profile", sig.parameters)

    def test_illustrated_backend_render_accepts_profile(self):
        import inspect
        from agent_system.video import illustrated
        sig = inspect.signature(illustrated.IllustratedBackend.render)
        self.assertIn("profile", sig.parameters)

    def test_encode_frames_positional_signature_is_unchanged(self):
        import inspect
        params = list(inspect.signature(common.encode_frames_to_video).parameters)
        self.assertEqual(params[:5], ["frames", "out_path", "width", "height", "fps"])

    def test_qa_fixture_is_synthetic_and_labelled(self):
        self.assertIn("QA FIXTURE", qa_fixture.WATERMARK.upper())
        self.assertIn("NOT A CLIENT FILM", qa_fixture.WATERMARK.upper())
        s = qa_fixture.fixture_spec(width=320, height=180, fps=8)
        self.assertIn("QA FIXTURE", s.watermark.upper())
        kinds = [sc["kind"] for sc in s.scenes]
        # Composition coverage: the fixture must exercise distinct layouts.
        for kind in ("title", "statement", "timeline", "list", "stat",
                     "comparison", "process", "quote", "photo", "endcard"):
            self.assertIn(kind, kinds, "fixture does not exercise %r" % kind)


if __name__ == "__main__":
    unittest.main()
