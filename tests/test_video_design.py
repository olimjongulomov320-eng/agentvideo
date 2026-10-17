# -*- coding: utf-8 -*-
"""Tests: the visual design system (palette, grid, typography, primitives).

These are unit tests on the design language itself — no ffmpeg, no rendering of
a film, just the layout maths and the vector primitives. They guard against the
regressions that make a design system silently stop being consistent: margins
that drift, type that stops scaling with resolution, text that overflows its
column, and backgrounds that get rebuilt per frame.
"""
import os
import tempfile
import unittest

from PIL import Image, ImageChops, ImageDraw

from agent_system.video import design, draw, spec


class TestThemeAndGrid(unittest.TestCase):
    def test_margins_scale_with_resolution(self):
        hd = design.Theme(1920, 1080, draw.FontBook(1080))
        sd = design.Theme(960, 540, draw.FontBook(540))
        self.assertAlmostEqual(hd.margin / float(sd.margin), 2.0, delta=0.02)
        # Margin is a sane fraction of the frame (roughly 5-7%).
        self.assertTrue(0.05 * 1920 <= hd.margin <= 0.07 * 1920,
                        "margin %d is not in the intended band" % hd.margin)

    def test_content_box_is_inside_the_frame(self):
        th = design.Theme(1920, 1080, draw.FontBook(1080))
        x0, y0, x1, y1 = th.content
        self.assertGreater(x0, 0)
        self.assertGreater(y0, 0)
        self.assertLess(x1, th.width)
        self.assertLess(y1, th.height)
        self.assertEqual(x1 - x0, th.content_w)

    def test_font_scales_with_height(self):
        a = draw.FontBook(1080)
        b = draw.FontBook(540)
        self.assertAlmostEqual(a.scale, 1.0, places=6)
        self.assertAlmostEqual(b.scale, 0.5, places=6)
        self.assertAlmostEqual(a.scale / b.scale, 2.0, places=6)

    def test_columns_fit_the_content_width(self):
        th = design.Theme(1920, 1080, draw.FontBook(1080))
        cols = th.columns(2)
        self.assertEqual(len(cols), 2)
        x0, cw0 = cols[0]
        x1, cw1 = cols[1]
        self.assertEqual(x0, th.content[0])
        # Second column ends at the right content edge.
        self.assertLessEqual(x1 + cw1, th.content[2] + 1)

    def test_spacing_scale_is_monotonic(self):
        th = design.Theme(1920, 1080, draw.FontBook(1080))
        self.assertLess(th.sp(1), th.sp(4))
        self.assertLess(th.sp(4), th.sp(12))


class TestTypography(unittest.TestCase):
    def _canvas(self):
        img = Image.new("RGB", (1920, 1080), (11, 31, 42))
        return img, ImageDraw.Draw(img, "RGBA")

    def test_heading_wraps_within_its_column(self):
        th = design.Theme(1920, 1080, draw.FontBook(1080))
        img, d = self._canvas()
        text = ("A deliberately long headline used to prove that the design "
                "system wraps text inside its column instead of overflowing it")
        max_w = th.content_w * 0.6
        font = th.title(78)
        lines = draw.wrap(d, text, font, max_w)
        self.assertGreater(len(lines), 1, "long text should wrap")
        for ln in lines:
            self.assertLessEqual(draw.text_width(d, ln, font, 0.3), max_w + 1.0,
                                 "a wrapped line exceeded the column width")

    def test_heading_height_grows_with_line_count(self):
        th = design.Theme(1920, 1080, draw.FontBook(1080))
        img, d = self._canvas()
        h1 = design.heading(d, th, th.margin, th.margin, "Short", th.content_w * 0.8, 78)
        h2 = design.heading(d, th, th.margin, th.margin,
                            "A much longer headline that certainly wraps over "
                            "several lines in this column", th.content_w * 0.8, 78)
        self.assertGreater(h2, h1)

    def test_text_stays_inside_the_safe_margin(self):
        th = design.Theme(1920, 1080, draw.FontBook(1080))
        base = Image.new("RGB", (1920, 1080), (11, 31, 42))
        img = base.copy()
        d = ImageDraw.Draw(img, "RGBA")
        design.heading(d, th, th.margin, 400, "Safe margin check",
                       th.content_w * 0.8, 78)
        diff = ImageChops.difference(img, base).convert("L")
        bbox = diff.getbbox()
        self.assertIsNotNone(bbox, "nothing was drawn")
        self.assertGreaterEqual(bbox[0], th.margin - 3,
                                "text was drawn left of the safe margin")
        self.assertLessEqual(bbox[2], th.width - th.margin + 3,
                             "text was drawn right of the safe margin")

    def test_vertical_anchor_centres_text_on_the_given_y(self):
        img = Image.new("RGB", (600, 200), (0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")
        fb = draw.FontBook(200)
        draw.draw_tracked(d, (300, 100), "CENTERED", fb.label(60), (255, 255, 255, 255),
                          tracking=0.0, anchor="mm")
        diff = img.convert("L")
        bbox = diff.getbbox()
        self.assertIsNotNone(bbox)
        centre = (bbox[1] + bbox[3]) / 2.0
        self.assertLess(abs(centre - 100), 12,
                        "vertically anchored text was not centred (centre=%.1f)" % centre)


class TestBackgrounds(unittest.TestCase):
    def setUp(self):
        design.clear_background_cache()

    def tearDown(self):
        design.clear_background_cache()

    def test_background_is_cached(self):
        a = design.build_background(320, 180, "navy")
        b = design.build_background(320, 180, "navy")
        self.assertIs(a, b, "background should be cached, not rebuilt per frame")
        self.assertEqual(a.size, (320, 180))

    def test_cache_clears(self):
        a = design.build_background(320, 180, "navy")
        design.clear_background_cache()
        b = design.build_background(320, 180, "navy")
        self.assertIsNot(a, b)

    def test_every_variant_renders_at_the_requested_size(self):
        for variant in design.VARIANTS:
            img = design.build_background(200, 112, variant)
            self.assertEqual(img.size, (200, 112))
            self.assertEqual(img.mode, "RGB")

    def test_unknown_variant_falls_back_instead_of_failing(self):
        img = design.build_background(120, 68, "not-a-variant")
        self.assertEqual(img.size, (120, 68))

    def test_paper_variant_is_light(self):
        img = design.build_background(160, 90, "paper")
        px = img.convert("L").getpixel((80, 45))
        self.assertGreater(px, 180, "the 'paper' ground should be light")

    def test_deep_variant_is_dark(self):
        img = design.build_background(160, 90, "deep")
        px = img.convert("L").getpixel((80, 45))
        self.assertLess(px, 140, "the 'deep' ground should be dark")


class TestPrimitives(unittest.TestCase):
    def _canvas(self, w=1920, h=1080):
        img = Image.new("RGB", (w, h), (11, 31, 42))
        return img, ImageDraw.Draw(img, "RGBA"), design.Theme(w, h, draw.FontBook(h))

    def test_enter_is_eased_and_bounded(self):
        self.assertEqual(design.enter(0.0, 0.5, 0.5), 0.0)
        self.assertEqual(design.enter(2.0, 0.5, 0.5), 1.0)
        mid = design.enter(0.75, 0.5, 0.5)
        self.assertTrue(0.0 < mid < 1.0)
        # Ease-out should already be past the linear midpoint.
        self.assertGreater(mid, 0.5)

    def test_stagger_orders_entrances_without_overlap_violations(self):
        first = design.stagger(0.6, 0, first=0.2, step=0.2)
        second = design.stagger(0.6, 1, first=0.2, step=0.2)
        self.assertGreater(first, second, "earlier items should appear first")
        self.assertGreaterEqual(second, 0.0)

    def test_with_alpha_clamps(self):
        self.assertEqual(design.with_alpha((1, 2, 3), -1.0)[3], 0)
        self.assertEqual(design.with_alpha((1, 2, 3), 5.0)[3], 255)

    def test_col_and_mix(self):
        self.assertEqual(design.col("gold_500"), design.PALETTE["gold_500"])
        self.assertEqual(len(design.col("gold_500", 128)), 4)
        self.assertEqual(design.mix((0, 0, 0), (255, 255, 255), 0.5), (128, 128, 128))
        self.assertEqual(design.mix((0, 0, 0), (10, 20, 30), 2.0), (10, 20, 30))

    def test_kicker_draws_accent_and_label(self):
        img, d, th = self._canvas()
        base = img.copy()
        design.kicker(d, th, th.margin, th.margin, "since 2010")
        self.assertIsNotNone(ImageChops.difference(img, base).convert("L").getbbox())

    def test_kicker_center_align_centres_on_x(self):
        img, d, th = self._canvas()
        base = img.copy()
        design.kicker(d, th, 960, th.margin, "centred", align="center")
        bbox = ImageChops.difference(img, base).convert("L").getbbox()
        centre = (bbox[0] + bbox[2]) / 2.0
        self.assertLess(abs(centre - 960), 20)

    def test_rule_progress_zero_draws_nothing(self):
        img, d, th = self._canvas()
        base = img.copy()
        design.rule(d, th, 100, 100, 400, progress=0.0)
        self.assertIsNone(ImageChops.difference(img, base).convert("L").getbbox())

    def test_panel_and_badge_and_chip_draw(self):
        img, d, th = self._canvas()
        base = img.copy()
        design.panel(d, th, (100, 100, 400, 300), fill=design.col("navy_900"),
                     outline=design.col("gold_500"))
        design.badge(d, th, 300, 300, 40, "1")
        design.chip(d, th, 100, 500, "verified")
        self.assertIsNotNone(ImageChops.difference(img, base).convert("L").getbbox())

    def test_panel_with_no_style_draws_nothing(self):
        img, d, th = self._canvas()
        base = img.copy()
        design.panel(d, th, (100, 100, 400, 300))
        self.assertIsNone(ImageChops.difference(img, base).convert("L").getbbox())

    def test_every_named_icon_draws_without_error(self):
        names = ["scales", "document", "shield", "briefcase", "building", "clock",
                 "check", "arrow", "growth", "network", "lock", "handshake",
                 "megaphone", "dot"]
        for name in names:
            img, d, th = self._canvas(400, 400)
            base = img.copy()
            design.icon(ImageDraw.Draw(img, "RGBA"), th, name, (100, 100, 300, 300))
            self.assertIsNotNone(ImageChops.difference(img, base).convert("L").getbbox(),
                                 "icon %r drew nothing" % name)

    def test_icon_for_key_is_stable(self):
        self.assertEqual(design.icon_for_key("hook"), "megaphone")
        self.assertEqual(design.icon_for_key("office"), "building")
        self.assertEqual(design.icon_for_key("unknown-key"), "document")
        self.assertEqual(design.icon_for_key(""), "document")

    def test_centered_lockup_returns_positive_size_and_is_centred(self):
        img, d, th = self._canvas()
        base = img.copy()
        w, h = design.centered_lockup(img, th, 960, 400, "Fixture Legal")
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)
        bbox = ImageChops.difference(img, base).convert("L").getbbox()
        centre = (bbox[0] + bbox[2]) / 2.0
        self.assertLess(abs(centre - 960), 14)

    def test_logo_lockup_uses_a_real_logo_when_supplied(self):
        tmp = tempfile.mkdtemp(prefix="logo-")
        self.addCleanup(lambda: __import__("shutil").rmtree(tmp, ignore_errors=True))
        logo_path = os.path.join(tmp, "logo.png")
        Image.new("RGBA", (240, 80), (255, 0, 0, 255)).save(logo_path)
        img, d, th = self._canvas()
        w, h = design.logo_lockup(img, th, 50, 50, "Fixture Legal", logo_path, max_h=80)
        self.assertAlmostEqual(w / float(h), 3.0, delta=0.05)

    def test_scrim_darkens_the_region(self):
        img, d, th = self._canvas()
        before = img.convert("L").getpixel((960, 900))
        out = design.scrim(img, (0, 700, 1920, 1080), (0, 0, 0), 200, feather=4)
        after = out.convert("L").getpixel((960, 900))
        self.assertLess(after, before)


class TestSvgHonesty(unittest.TestCase):
    def test_svg_availability_is_reported_as_a_bool_and_a_reason(self):
        ok, engine = design.svg_available()
        self.assertIsInstance(ok, bool)
        self.assertIsInstance(engine, str)
        self.assertTrue(engine)

    def test_rasterize_returns_a_reason_when_no_rasterizer_exists(self):
        ok, _ = design.svg_available()
        img, reason = design.rasterize_svg("/nonexistent/file.svg", 100, 100)
        if not ok:
            self.assertIsNone(img)
            self.assertTrue(reason)
        else:
            self.assertIsNone(img)  # file genuinely does not exist


class TestAspectRatio(unittest.TestCase):
    def test_spec_aspects_have_expected_dimensions(self):
        for name, dims in spec.ASPECTS.items():
            s, errors = spec.validate_render_spec(
                {"firm_name": "A", "aspect": name,
                 "scenes": [{"id": "s", "kind": "statement", "dur": 2.0,
                             "heading": "H", "narration": "n"}]})
            self.assertEqual(errors, [], "aspect %s should validate" % name)
            self.assertEqual((s.width, s.height), dims)

    def test_cover_preserves_aspect_without_distortion(self):
        # A square marker in a 4:3 source must stay square after a 16:9 cover crop.
        src = Image.new("RGB", (400, 300), (0, 0, 0))
        ImageDraw.Draw(src).rectangle([150, 100, 250, 200], fill=(255, 0, 0))
        out = draw.cover(src, (400, 225))
        self.assertEqual(out.size, (400, 225))
        r, g, b = out.split()
        red = ImageChops.subtract(r, g)
        bbox = red.point(lambda v: 255 if v > 40 else 0).getbbox()
        self.assertIsNotNone(bbox)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        self.assertLessEqual(abs(w - h), 2, "cover distorted the square (w=%d h=%d)" % (w, h))


if __name__ == "__main__":
    unittest.main()
