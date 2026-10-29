# -*- coding: utf-8 -*-
"""video/motion.py — Motion Graphics backend (2D corporate/legal).

Each scene is a *composition* built on the shared design system
(:mod:`agent_system.video.design`): a real grid, a typographic hierarchy, gold
accents used sparingly, and a small library of line icons drawn as vectors.

The backends expose the same contract to the rest of the system:

* :func:`render_scene_frame` paints one scene at a given time;
* :func:`iter_frames` yields the whole film as RGB frames for ffmpeg.

Two things make this pipeline different from the earlier "text on a gradient"
version:

1. **Backgrounds are built once and cached** (gradient + soft light + vignette),
   instead of being re-derived for every frame — the single biggest reason the
   old renderer was slow at 1080p.
2. **Composition, not decoration**: every scene uses one of a handful of
   purposeful structures (title sequence, editorial statement, timeline,
   numbered list, statistic, comparison, process, quote, branded end card)
   chosen to fit the storyboard kind, rather than the same centred block.
"""
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from . import common, design, draw
from .design import Theme, col
from .spec import RenderSpec, gap_banner_text

LIMITATIONS = [
    "Transitions between scenes are crossfades computed in the frame renderer.",
    "Depth is suggested by layered parallax; there are no true 3D depth maps.",
    "Icons are drawn as vector primitives with Pillow, not imported SVG glyphs "
    "(no SVG rasteriser is installed on this machine).",
    "No licensed music is bundled; audio defaults to a synthesized pad (labelled).",
    "The DEMO / CONCEPT PREVIEW watermark is stamped on every preview frame.",
]

_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")

# On-screen "kicker" labels, one set per language, so a localised film never
# shows a stray English word burned into the picture.
_KICKERS = {
    "en": {"hook": "A law firm in Tashkent", "origin": "Origin",
           "practice": "Practice", "achievements": "Record", "people": "People",
           "office": "Office", "closing": ""},
    "ru": {"hook": "Юридическая фирма в Ташкенте", "origin": "Истоки",
           "practice": "Практика", "achievements": "Результаты", "people": "Люди",
           "office": "Офис", "closing": ""},
    "uz": {"hook": "Toshkentdagi yuridik firma", "origin": "Tarix",
           "practice": "Faoliyat", "achievements": "Natijalar", "people": "Odamlar",
           "office": "Ofis", "closing": ""},
}

# Prefix drawn on an evidence-gap banner, per language.
_GAP_PREFIX = {"en": "GAP", "ru": "ПРОБЕЛ", "uz": "BO'SHLIQ"}


def _lang_of(ctx: "MotionContext") -> str:
    lang = (getattr(getattr(ctx, "spec", None), "language", "en") or "en")
    lang = lang[:2].lower()
    return lang if lang in _KICKERS else "en"


class MotionContext(object):
    def __init__(self, spec: RenderSpec, asset_dir: str = ""):
        self.spec = spec
        self.w, self.h = spec.width, spec.height
        self.fb = draw.FontBook(self.h)
        self.theme = Theme(self.w, self.h, self.fb)
        self.asset_dir = asset_dir
        self.logo = self._find_logo()
        self._photo_cache: Dict[str, Image.Image] = {}

    def _find_logo(self) -> Optional[str]:
        for cand in ("logo-full.png", "logo.png", "logo-wide.png", "logo-shield.png"):
            p = os.path.join(self.asset_dir, cand) if self.asset_dir else ""
            if p and os.path.isfile(p):
                return p
        return None

    def asset(self, name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        if os.path.isabs(name) and os.path.isfile(name):
            return name
        if self.asset_dir:
            p = os.path.join(self.asset_dir, name)
            if os.path.isfile(p):
                return p
        return None

    def photo(self, path: str) -> Optional[Image.Image]:
        """Load and pre-scale a photo once (max zoom frame), for cheap push-ins."""
        if path in self._photo_cache:
            return self._photo_cache[path]
        try:
            src = Image.open(path).convert("RGB")
            z = 1.06
            tw, th = int(self.w * z), int(self.h * z)
            big = draw.cover(src, (tw, th))
            self._photo_cache[path] = big
            return big
        except Exception:
            self._photo_cache[path] = None  # type: ignore[assignment]
            return None


# ---------------------------------------------------------------- helpers
def _base(ctx: MotionContext, variant: str = "navy") -> Image.Image:
    """A cached ground; returned as a fresh copy the painter can draw on."""
    return design.build_background(ctx.w, ctx.h, variant).copy()


def _placeholder_mark(img: Image.Image, fb: draw.FontBook, text: str,
                      lang: str = "en") -> None:
    """Draw an unmistakable gap marker on scenes with missing evidence."""
    if not text:
        return
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    a = col("alert")
    y = int(h * 0.865)
    d.rounded_rectangle([int(w * 0.06), y, int(w * 0.94), y + int(h * 0.062)],
                        radius=int(h * 0.008), fill=a + (235,))
    prefix = _GAP_PREFIX.get(lang, "GAP")
    d.text((int(w * 0.072), y + int(h * 0.014)), "%s: %s" % (prefix, text[:110]),
           font=fb.label(22), fill=(255, 250, 246, 255))


# ---------------------------------------------------------------- compositions
def _title(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """A strong opening/title sequence: kicker, headline, rule, sub, mark."""
    th = ctx.theme
    img = _base(ctx, "deep")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content
    cx = ctx.w / 2

    # slow push-in on the type block (cheap: no full-frame resample)
    zoom = 1.0 + 0.012 * draw.ease_in_out(min(1.0, t / max(0.001, dur)))
    kick_p = design.enter(t, 0.15, 0.6)
    head_p = design.enter(t, 0.35, 0.9)
    rule_p = design.enter(t, 0.85, 0.8)
    sub_p = design.enter(t, 1.05, 0.8)

    # top mark
    design.logo_lockup(img, th, x0, y0, ctx.spec.firm_name, ctx.logo,
                       color=col("cream"), alpha=kick_p)

    kicker = _kicker_text(scene, ctx)
    if kicker:
        design.kicker(d, th, x0, y0 + th.sp(19), kicker, col("gold_500"), 26)

    head = (scene["heading"] or ctx.spec.firm_name or "").strip()
    hsize = int((96 if len(head) <= 26 else 78) * zoom)
    hy = ctx.h * 0.42 - (1 - head_p) * th.sp(3)
    hh = design.heading(d, th, cx, hy, head, th.content_w * 0.86,
                        size=hsize, color=col("cream"), align="center",
                        alpha=head_p)
    design.rule(d, th, cx - th.content_w * 0.06, hy + hh + th.sp(3),
                th.content_w * 0.12, col("gold_500"), progress=rule_p)
    if scene["sub"]:
        design.body_text(d, th, cx, hy + hh + th.sp(6), scene["sub"],
                         th.content_w * 0.72, size=32, color=col("gold_100"),
                         align="center", alpha=sub_p)
    return img


def _kicker_text(scene: Dict[str, Any], ctx: MotionContext) -> str:
    table = _KICKERS[_lang_of(ctx)]
    key = (scene.get("key") or "").strip()
    return table[key] if key in table else key.replace("_", " ").title()


def _statement(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """Editorial statement: a left-aligned block on a real grid, not centred text."""
    th = ctx.theme
    img = _base(ctx, "navy")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content

    text = (scene["heading"] or scene["narration"] or "").strip()
    long_form = len(text) > 64 or ":" in text
    # Two-zone layout: text on the left, a framed icon motif on the right.
    text_w = th.content_w * (0.58 if long_form else 0.62)
    ix0 = x0 + th.content_w * 0.66

    accent_p = design.enter(t, 0.2, 0.7)
    design.accent_bar(d, th, x0, y0 + th.sp(12), th.sp(9), col("gold_500"),
                      w=th.sp(1.0))
    # scale the accent bar in vertically
    d.rectangle([x0, y0 + th.sp(12), x0 + th.sp(1.0),
                 y0 + th.sp(12) + th.sp(9) * accent_p], fill=col("gold_500") + (255,))

    kicker = _kicker_text(scene, ctx)
    if kicker:
        design.kicker(d, th, x0 + th.sp(3), y0 + th.sp(12), kicker, col("gold_500"), 25)

    head_p = design.enter(t, 0.4, 0.9)
    hsize = 84 if not long_form else 62
    hy = y0 + th.sp(17)
    hh = design.heading(d, th, x0 + th.sp(3), hy, text, text_w,
                        size=hsize, color=col("cream"), alpha=head_p)
    rule_p = design.enter(t, 1.0, 0.8)
    design.rule(d, th, x0 + th.sp(3), hy + hh + th.sp(3), th.content_w * 0.10,
                col("gold_500"), progress=rule_p)
    if scene["sub"] and scene["sub"] != text and not (
            scene.get("key") == "people" and "," in scene["sub"]):
        design.body_text(d, th, x0 + th.sp(3), hy + hh + th.sp(6), scene["sub"],
                         text_w, size=30, color=col("gold_100"),
                         alpha=design.enter(t, 1.15, 0.8))

    names = [n.strip() for n in (scene.get("sub") or "").split(",") if n.strip()]
    if scene.get("key") == "people" and len(names) >= 2:
        # Real names beat an empty icon frame: stack them on the right zone.
        for i, n in enumerate(names[:4]):
            ip = design.enter(t, 0.7 + 0.25 * i, 0.7)
            ny = ctx.h * 0.30 + i * th.sp(11)
            d.rectangle([ix0, ny, ix0 + th.sp(1.0), ny + th.sp(8)],
                        fill=col("gold_500") + (int(255 * ip),))
            design.body_text(d, th, ix0 + th.sp(3), ny + th.sp(1), n, th.content_w * 0.30,
                             size=34, color=col("cream"), alpha=ip)
        return img

    # right-hand motif: a thin frame with a line icon, drawn on
    if not long_form:
        fp = design.enter(t, 0.6, 1.0, ease="in_out")
        box = (ix0, ctx.h * 0.30, ix0 + th.content_w * 0.26, ctx.h * 0.66)
        d.rounded_rectangle(box, radius=th.sp(2),
                            outline=col("gold_500") + (int(200 * fp),),
                            width=max(2, int(2 * th._s)))
        iw = box[2] - box[0]
        design.icon(d, th, design.icon_for_key(scene.get("key", "")),
                    (box[0] + iw * 0.25, box[1] + iw * 0.25,
                     box[2] - iw * 0.25, box[3] - iw * 0.25),
                    col("gold_400"), width=max(3, int(4 * th._s)))
    return img


def _stat(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """A statistic/milestone card with an honest count-up numeral and a rule."""
    th = ctx.theme
    img = _base(ctx, "slate")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content
    cx = (x0 + x1) / 2.0

    label = scene["heading"] or "—"
    p = draw.ease_out(draw.ramp(t, 0.25, 0.9))
    # count up only when the label is a bare number/year; never invent one.
    shown = label
    m = re.fullmatch(r"\s*(\d{2,5})\s*", label)
    if m:
        target = int(m.group(1))
        cur = int(round(target * draw.ease_out(draw.ramp(t, 0.35, 1.2))))
        shown = str(cur)

    kicker = _kicker_text(scene, ctx)
    if kicker:
        design.kicker(d, th, cx, y0 + th.sp(14), kicker, col("gold_500"), 26,
                      align="center")
    size = 190 if len(shown) <= 5 else 120
    yy = ctx.h * 0.40 - (1 - p) * th.sp(2)
    design.heading(d, th, cx, yy, shown, th.content_w * 0.8, size=size,
                   color=col("gold_300"), align="center", alpha=p,
                   font=th.stat(size))
    rule_p = design.enter(t, 0.8, 0.7)
    design.rule(d, th, cx - th.content_w * 0.05, ctx.h * 0.60,
                th.content_w * 0.10, col("gold_500"), progress=rule_p)
    if scene["sub"]:
        design.body_text(d, th, cx, ctx.h * 0.64, scene["sub"], th.content_w * 0.74,
                         size=32, color=col("cream"), align="center",
                         alpha=design.enter(t, 0.95, 0.8))
    return img


def _years_in(scene: Dict[str, Any]) -> List[str]:
    """All 4-digit years literally present in the scene's own text."""
    blob = " ".join(str(scene.get(k) or "") for k in ("heading", "sub", "narration"))
    seen: List[str] = []
    for y in _YEAR.findall(blob):
        if y not in seen:
            seen.append(y)
    return seen


def _timeline(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """A real timeline: track draws on, milestones appear where the data exists."""
    th = ctx.theme
    img = _base(ctx, "deep")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content
    y = ctx.h * 0.60
    xa, xb = x0 + th.content_w * 0.04, x1 - th.content_w * 0.04

    kicker = _kicker_text(scene, ctx)
    if kicker:
        design.kicker(d, th, x0, y0 + th.sp(12), kicker, col("gold_500"), 26)

    head = (scene["heading"] or "").strip()
    years = _years_in(scene)
    # A heading that is only a placeholder is not a fact: show the caption, not a date.
    show_head = head if (head and not _is_placeholder(head)) else ""

    track_p = draw.ease_in_out(draw.ramp(t, 0.18, 1.2))
    d.rectangle([xa, y, xa + (xb - xa) * track_p, y + max(2, int(3 * th._s))],
                fill=col("gold_500") + (235,))

    # milestone positions: real years if present, else one anchor for the caption
    if years:
        pts = []
        n = len(years)
        for i, yr in enumerate(years):
            fx = 0.12 + (0.76 * i / max(1, n - 1)) if n > 1 else 0.5
            pts.append((yr, fx))
    else:
        pts = [("", 0.5 if re.fullmatch(r"\s*\d{1,5}\+?\s*", head or "") else 0.42)]

    for i, (yr, fx) in enumerate(pts):
        mp = design.enter(t, 0.5 + i * 0.28, 0.6, ease="out")
        if mp <= 0:
            continue
        mx = xa + (xb - xa) * fx
        r = th.sp(2.0) * mp
        d.ellipse([mx - r * 1.9, y - r * 1.9 + 2, mx + r * 1.9, y + r * 1.9 + 2],
                  outline=col("gold_500") + (int(190 * mp),), width=max(2, int(2 * th._s)))
        d.ellipse([mx - r, y - r + 2, mx + r, y + r + 2],
                  fill=col("cream") + (int(255 * mp),))
        if yr:
            design.heading(d, th, mx, y - th.sp(9), yr, th.content_w * 0.3,
                           size=46, color=col("gold_300"), align="center", alpha=mp,
                           font=th.h2(46))

    hero = re.fullmatch(r"\s*\d{1,5}\+?\s*", head or "") if not years else None
    if hero:
        # A bare figure ("16+") is the point of the scene: show it large and put
        # the sentence it belongs to under the track.
        hp = design.enter(t, 0.5, 0.9)
        design.heading(d, th, (xa + xb) / 2, y - th.sp(26), head.strip(), th.content_w * 0.5,
                       size=150, color=col("gold_300"), align="center", alpha=hp,
                       font=th.h2(150))
        if scene["sub"]:
            design.body_text(d, th, (xa + xb) / 2, y + th.sp(7), scene["sub"],
                             th.content_w * 0.7, size=34, color=col("cream"),
                             align="center", alpha=design.enter(t, 1.1, 0.8))
        return img
    cap = show_head or (scene["sub"] or "")
    if cap:
        cy = y - th.sp(9) if not years else y + th.sp(6)
        design.body_text(d, th, (xa + xb) / 2, cy, cap, th.content_w * 0.78,
                         size=30, color=col("cream"), align="center",
                         alpha=design.enter(t, 1.1, 0.8))
    if scene["sub"] and years:
        design.body_text(d, th, (xa + xb) / 2, y + th.sp(11), scene["sub"],
                         th.content_w * 0.74, size=27, color=col("gold_100"),
                         align="center", alpha=design.enter(t, 1.3, 0.8))
    return img


def _list(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """Numbered practice/feature list on a real grid with badges and icons."""
    th = ctx.theme
    img = _base(ctx, "navy")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content

    title = (scene["heading"] or "Practice").strip()
    design.kicker(d, th, x0, y0 + th.sp(10), title, col("gold_500"), 27)
    head_p = design.enter(t, 0.25, 0.7)
    design.rule(d, th, x0, y0 + th.sp(16), th.content_w * 0.16, col("gold_500"),
                progress=head_p)

    raw = (scene["sub"] or scene["narration"] or "")
    items = [s.strip(" .;") for s in re.split(r"[;,]", raw)]
    items = [i for i in items if len(i) > 1][:5]

    top = y0 + th.sp(22)
    row_h = th.sp(12.5)
    col_w = th.content_w
    for i, it in enumerate(items):
        p = design.stagger(t, i, first=0.28, step=0.16, dur=0.55)
        if p <= 0:
            continue
        yy = top + i * row_h
        ax, aw = x0, col_w
        # row panel
        design.panel(d, th, (ax, yy, ax + aw, yy + row_h - th.sp(2.5)),
                     fill=col("navy_900"), outline=None, alpha=int(150 * p),
                     radius=th.sp(1.5))
        design.accent_bar(d, th, ax, yy, (row_h - th.sp(2.5)), col("gold_500"),
                          w=th.sp(0.6))
        # badge + number
        bx = ax + th.sp(5)
        by = yy + (row_h - th.sp(2.5)) / 2.0
        design.badge(d, th, bx, by, th.sp(3.0), "%02d" % (i + 1),
                     fill=col("gold_500"), text_color=col("navy_900"),
                     font=th.ui_bold(24))
        # text (multi-line aware)
        tx = bx + th.sp(5)
        tw = aw - (tx - ax) - th.sp(4)
        design.body_text(d, th, tx, yy + th.sp(2.6), it, tw, size=34,
                         color=col("cream"), alpha=p)
    return img


def _comparison(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """Two-column comparison (e.g. risk vs recommendation)."""
    th = ctx.theme
    img = _base(ctx, "navy")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content
    kicker = _kicker_text(scene, ctx) or "Comparison"
    design.kicker(d, th, x0, y0 + th.sp(10), kicker, col("gold_500"), 26)

    top = y0 + th.sp(18)
    head = (scene["heading"] or "").strip()
    if head:
        hh = design.heading(d, th, x0, top, head, th.content_w * 0.72, size=54,
                            color=col("cream"), alpha=design.enter(t, 0.15, 0.7),
                            font=th.h2(54))
        design.rule(d, th, x0, top + hh + th.sp(2), th.content_w * 0.12,
                    col("gold_500"), progress=design.enter(t, 0.4, 0.6))
        top += hh + th.sp(8)

    cols = th.columns(2)
    pairs = _split_pairs(scene)
    bot = y1 - th.sp(8)
    for i, (x, cw) in enumerate(cols):
        p = design.enter(t, 0.30 + i * 0.22, 0.7)
        head2, items = pairs[i] if i < len(pairs) else ("", [])
        box = (x, top, x + cw, bot)
        design.soft_shadow(img, box, radius=th.sp(2), spread=th.sp(1), alpha=110)
        d = ImageDraw.Draw(img, "RGBA")
        design.panel(d, th, box, fill=col("navy_900") if i == 0 else col("paper"),
                     alpha=int(220 * p), radius=th.sp(2))
        accent = col("alert") if i == 0 else col("ok")
        d.rectangle([x, top, x + th.sp(1), bot], fill=accent + (int(255 * p),))
        hy = top + th.sp(4)
        design.heading(d, th, x + th.sp(4), hy, head2, cw - th.sp(8), size=40,
                       color=col("cream") if i == 0 else col("ink_700"),
                       alpha=p, font=th.h2(40))
        iy = hy + th.sp(10)
        for k, it in enumerate(items[:4]):
            design.icon(d, th, "dot", (x + th.sp(4), iy + th.sp(1),
                                       x + th.sp(8), iy + th.sp(5)),
                        accent, width=max(2, int(2 * th._s)))
            h = design.body_text(d, th, x + th.sp(9), iy, it, cw - th.sp(13), size=28,
                                 color=col("cream") if i == 0 else col("ink_500"),
                                 alpha=design.stagger(t, k, first=0.45, step=0.11))
            iy += max(h, th.sp(5)) + th.sp(1.6)
    return img


def _process(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """A numbered process/steps strip joined by a line, under a real heading."""
    th = ctx.theme
    img = _base(ctx, "deep")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content
    kicker = _kicker_text(scene, ctx) or "Process"
    design.kicker(d, th, x0, y0 + th.sp(10), kicker, col("gold_500"), 26)

    head = (scene["heading"] or "").strip()
    hy = y0 + th.sp(18)
    hh = 0
    if head:
        hh = design.heading(d, th, x0, hy, head, th.content_w * 0.7, size=54,
                            color=col("cream"), alpha=design.enter(t, 0.12, 0.7),
                            font=th.h2(54))
        design.rule(d, th, x0, hy + hh + th.sp(2), th.content_w * 0.12,
                    col("gold_500"), progress=design.enter(t, 0.3, 0.6))

    steps = [s.strip(" .;") for s in re.split(r"[;,]", scene["sub"] or scene["narration"] or "")]
    steps = [s for s in steps if len(s) > 1][:4] or ["Step"]

    n = len(steps)
    y = ctx.h * 0.64 if head else ctx.h * 0.58
    xs = [x0 + th.content_w * (0.12 + 0.76 * i / max(1, n - 1)) if n > 1
          else x0 + th.content_w * 0.5 for i in range(n)]
    # connecting line draws on promptly so the scene is never empty
    lp = draw.ease_in_out(draw.ramp(t, 0.12, 1.1))
    if n > 1:
        d.line([(xs[0], y), (xs[0] + (xs[-1] - xs[0]) * lp, y)],
               fill=col("gold_500") + (200,), width=max(2, int(3 * th._s)))
    for i, st in enumerate(steps):
        p = design.stagger(t, i, first=0.18, step=0.16, dur=0.5)
        if p <= 0:
            continue
        design.badge(d, th, xs[i], y, th.sp(3.6) * p, str(i + 1),
                     fill=col("gold_500"), text_color=col("navy_900"), font=th.ui_bold(28))
        design.body_text(d, th, xs[i], y + th.sp(6), st, th.content_w / max(2, n) * 0.9,
                         size=28, color=col("cream"), align="center", alpha=p)
    return img


def _quote(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """A pull-quote with a large quotation mark and optional attribution."""
    th = ctx.theme
    img = _base(ctx, "gold")
    d = ImageDraw.Draw(img, "RGBA")
    x0, y0, x1, y1 = th.content
    cx = (x0 + x1) / 2.0
    p = design.enter(t, 0.25, 0.9)
    mark = th.display(160)
    draw.draw_tracked(d, (x0, y0 + th.sp(4)), "\u201C", mark,
                      col("gold_500") + (int(180 * p),), tracking=0)
    hh = design.heading(d, th, cx, ctx.h * 0.36, scene["heading"] or scene["narration"],
                        th.content_w * 0.82, size=60, color=col("cream"),
                        align="center", alpha=p, font=th.h2(60))
    design.rule(d, th, cx - th.content_w * 0.05, ctx.h * 0.36 + hh + th.sp(3),
                th.content_w * 0.10, col("gold_500"),
                progress=design.enter(t, 0.9, 0.7))
    if scene["sub"]:
        design.body_text(d, th, cx, ctx.h * 0.36 + hh + th.sp(6), scene["sub"],
                         th.content_w * 0.7, size=28, color=col("gold_100"),
                         align="center", alpha=design.enter(t, 1.05, 0.8))
    return img


def _endcard(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    """A branded ending on paper white."""
    th = ctx.theme
    card = _base(ctx, "paper")
    d = ImageDraw.Draw(card, "RGBA")
    x0, y0, x1, y1 = th.content
    cx = (x0 + x1) / 2.0
    p = design.enter(t, 0.2, 1.0)

    design.centered_lockup(card, th, cx, ctx.h * 0.30, ctx.spec.firm_name,
                           ctx.logo, max_h=th.sp(20), color=col("navy_900"), alpha=p)
    design.rule(d, th, cx - th.content_w * 0.06, ctx.h * 0.53, th.content_w * 0.12,
                col("gold_500"), progress=design.enter(t, 0.7, 0.8))
    if scene["sub"]:
        design.body_text(d, th, cx, ctx.h * 0.58, scene["sub"], th.content_w * 0.7,
                         size=30, color=col("ink_500"), align="center",
                         alpha=design.enter(t, 0.85, 0.8))
    head = (scene["heading"] or ctx.spec.firm_name or "").strip()
    design.heading(d, th, cx, ctx.h * 0.68, head, th.content_w * 0.8, size=44,
                   color=col("navy_900"), align="center",
                   alpha=design.enter(t, 0.95, 0.8), font=th.h2(44))
    return card
    if scene["sub"]:
        design.body_text(d, th, cx, ctx.h * 0.58, scene["sub"], th.content_w * 0.7,
                         size=30, color=col("ink_500"), align="center",
                         alpha=design.enter(t, 0.85, 0.8))
    head = (scene["heading"] or ctx.spec.firm_name or "").strip()
    design.heading(d, th, cx, ctx.h * 0.68, head, th.content_w * 0.8, size=44,
                   color=col("navy_900"), align="center",
                   alpha=design.enter(t, 0.95, 0.8), font=th.h2(44))
    return card


def _photo(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    path = ctx.asset(scene.get("asset"))
    big = ctx.photo(path) if path else None
    if big is None:
        img = _base(ctx, "slate")
        _placeholder_mark(img, ctx.fb, "photo asset '%s' not supplied"
                          % (scene.get("asset") or "?"), _lang_of(ctx))
    else:
        z = 1.0 + 0.06 * draw.ease_in_out(min(1.0, t / max(0.001, dur)))
        sw, sh = int(ctx.w * z), int(ctx.h * z)
        frame = big.resize((sw, sh), Image.LANCZOS) if (sw, sh) != big.size else big
        left = (sw - ctx.w) // 2
        top = int((sh - ctx.h) * 0.45)
        img = frame.crop((left, top, left + ctx.w, top + ctx.h))
        img = design.scrim(img, (0, int(ctx.h * 0.58), ctx.w, ctx.h),
                           (5, 20, 30), 165, feather=int(ctx.h * 0.05))
    draw.lower_third(img, ctx.fb, scene["heading"] or "", scene["sub"] or "",
                     draw.ease_out(draw.ramp(t, 0.5, 0.8)))
    return img


def _is_placeholder(text: str) -> bool:
    t = (text or "").strip()
    return t.startswith("[") and t.endswith("]")


def _split_pairs(scene: Dict[str, Any]) -> List[Tuple[str, List[str]]]:
    """Split sub/narration into a left/right pair of label+bullets, honestly."""
    raw = (scene["sub"] or scene["narration"] or "").strip()
    halves = re.split(r"\s+(?:vs\.?|versus|—|-{1,2}|/)\s+", raw, maxsplit=1, flags=re.I)
    out: List[Tuple[str, List[str]]] = []
    labels = ("Risk", "Recommendation")
    for i, half in enumerate(halves[:2]):
        items = [s.strip(" .;") for s in re.split(r"[;,]", half) if s.strip(" .;")]
        head = labels[i]
        out.append((head, items or [half.strip()]))
    while len(out) < 2:
        out.append((labels[len(out)], [""]))
    return out


PAINTERS = {
    "statement": _statement, "timeline": _timeline, "list": _list, "stat": _stat,
    "title": _title, "endcard": _endcard, "photo": _photo,
    "illustration": _statement, "quote": _quote, "comparison": _comparison,
    "process": _process, "logo": _endcard,
}


def render_scene_frame(ctx: MotionContext, scene: Dict[str, Any], t: float) -> Image.Image:
    painter = PAINTERS.get(scene["kind"], _statement)
    img = painter(ctx, scene, t, float(scene["dur"]))
    _placeholder_mark(img, ctx.fb, gap_banner_text(scene), _lang_of(ctx))
    if not ctx.spec.audio.voiceover and draw.narration_needs_caption(scene):
        dur = float(scene["dur"])
        draw.caption(img, ctx.fb, scene["narration"],
                     draw.ramp(t, 0.9, 0.6) * draw.ramp(dur - t, 0.0, 0.5))
    draw.watermark(img, ctx.fb, ctx.spec.watermark)
    return img


# ---------------------------------------------------------------- frame stream
def _scene_starts(scenes: List[Dict[str, Any]], overlap: float) -> List[float]:
    starts: List[float] = []
    acc = 0.0
    for s in scenes:
        starts.append(acc)
        acc += float(s["dur"]) - overlap
    return starts


def iter_frames(ctx: MotionContext, scenes: List[Dict[str, Any]],
                cancel: Optional[Callable[[], bool]] = None,
                progress: Optional[Callable[[int, int], None]] = None):
    """Yield every frame of the film, crossfading scene boundaries."""
    spec = ctx.spec
    fps = spec.fps
    overlap = min(spec.transition_sec, min(s["dur"] for s in scenes) * 0.4)
    starts = _scene_starts(scenes, overlap)
    total = starts[-1] + float(scenes[-1]["dur"])
    n_frames = max(1, int(round(total * fps)))
    for n in range(n_frames):
        if cancel and cancel():
            return
        tg = n / float(fps)
        active = [(i, st) for i, st in enumerate(starts)
                  if st <= tg < st + float(scenes[i]["dur"])]
        if not active:
            active = [(len(scenes) - 1, starts[-1])]
        i, st = active[-1]
        frame = render_scene_frame(ctx, scenes[i], tg - st)
        if len(active) > 1 and overlap > 0:
            prev_i, prev_st = active[-2]
            w = max(0.0, min(1.0, (tg - prev_st - float(scenes[prev_i]["dur"]) + overlap) / overlap))
            prev = render_scene_frame(ctx, scenes[prev_i], tg - prev_st)
            frame = Image.blend(prev, frame, w)
        if progress and n % 15 == 0:
            progress(n, n_frames)
        yield frame


class MotionBackend(object):
    style = "motion"
    label = "Motion Graphics"

    def render(self, spec: RenderSpec, out_path: str, work_dir: str,
               asset_dir: str = "", cancel: Optional[Callable[[], bool]] = None,
               progress: Optional[Callable[[str, int], None]] = None,
               profile: str = "production") -> Dict[str, Any]:
        if not common.ffmpeg_available():
            raise common.RenderError("ffmpeg is not available — cannot render motion graphics")
        os.makedirs(work_dir, exist_ok=True)
        design.clear_background_cache()
        ctx = MotionContext(spec, asset_dir)

        def _prog(n: int, total: int) -> None:
            if progress:
                progress("rendering frame %d/%d" % (n, total), int(100 * n / max(1, total)))

        if progress:
            progress("rendering %d scenes at %dx%d@%d (%s)"
                     % (len(spec.scenes), spec.width, spec.height, spec.fps, profile), 1)
        video_only = os.path.join(work_dir, "_video_only.mp4")
        common.encode_frames_to_video(iter_frames(ctx, spec.scenes, cancel, _prog),
                                      video_only, spec.width, spec.height, spec.fps,
                                      profile=profile)
        audio_path, audio_meta = common.build_audio_track(
            os.path.join(work_dir, "_audio.wav"), spec.total_duration, spec.audio, work_dir)
        common.mux(video_only, audio_path, out_path)
        validation = common.validate_mp4(out_path, spec.width, spec.height, spec.fps,
                                         require_audio=True)
        manifest = common.write_render_manifest(
            os.path.join(work_dir, "render_manifest.json"), spec, self.style,
            common.engine_info("motion-pillow-ffmpeg"),
            sources=[s.get("asset") for s in spec.scenes if s.get("asset")],
            limitations=LIMITATIONS + ([] if common.ffmpeg_available() else ["ffmpeg missing"]),
            validation=validation,
            extra={"audio_detail": audio_meta, "profile": profile,
                   "design_system": design.DESIGN_VERSION})
        return {"output": out_path, "manifest": manifest, "validation": validation}


def render(spec: RenderSpec, out_path: str, work_dir: str, asset_dir: str = "",
           cancel: Optional[Callable[[], bool]] = None,
           progress: Optional[Callable[[str, int], None]] = None,
           profile: str = "production") -> Dict[str, Any]:
    return MotionBackend().render(spec, out_path, work_dir, asset_dir, cancel, progress,
                                  profile)
