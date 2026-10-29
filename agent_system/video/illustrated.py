# -*- coding: utf-8 -*-
"""video/illustrated.py — Illustrated 2D Animation backend.

A genuinely different pipeline from motion graphics: each scene is built from
**layers** (sky, far skyline, mid buildings, foreground props, figures) that move
with independent keyframed parallax under a slow camera drift, drawn as flat
vector-style raster art with Pillow and piped to ffmpeg.

Characters/objects are drawn procedurally from primitives. Bespoke illustration
assets (commissioned artwork) can replace any layer via ``scene["asset"]``.
"""
import math
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from . import common, design, draw
from .spec import RenderSpec, gap_banner_text

LIMITATIONS = [
    "Illustrations are procedurally drawn flat art (no commissioned artwork supplied).",
    "Character animation is limited to procedural figures; bespoke rigged characters "
    "require authored SVG/Lottie/PNG assets, which were not supplied.",
    "Camera moves are 2D pans/zooms; there is no 3D depth.",
    "Scene changes use crossfades.",
    "No licensed music is bundled; audio defaults to a synthesized pad (labelled).",
]

PAPER = (245, 240, 230)
INK2 = (26, 35, 46)
SKY_TOP = (26, 60, 86)
SKY_BOT = (78, 116, 138)
HILL = (18, 48, 66)
HILL2 = (24, 62, 84)
ACCENT = (201, 169, 110)
ACCENT2 = (232, 201, 138)


class IllusContext(object):
    def __init__(self, spec: RenderSpec, asset_dir: str = ""):
        self.spec = spec
        self.w, self.h = spec.width, spec.height
        self.fb = draw.FontBook(self.h)
        self.theme = design.Theme(self.w, self.h, self.fb)
        self.asset_dir = asset_dir
        self._sky_cache = None

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


def _sky(ctx: "IllusContext") -> Image.Image:
    """The static sky (gradient + sun) — built once, reused for every frame.

    The previous version re-derived the gradient and, worse, a large Gaussian
    glow for *every* frame. Caching it is what makes 1080p illustrated renders
    practical.
    """
    if ctx._sky_cache is None:
        img = draw.gradient((ctx.w, ctx.h), SKY_TOP, SKY_BOT, vertical=True)
        img = _sun(img, ctx.w * 0.72, ctx.h * 0.27, ctx.w * 0.16, 0.9)
        ctx._sky_cache = img
    return ctx._sky_cache


# ---------------------------------------------------------------- primitives
def _figure(d: ImageDraw.ImageDraw, x: float, ground: float, s: float, color) -> None:
    """A simple flat figure: head + shoulders + body."""
    head_r = 0.16 * s
    d.ellipse([x - head_r, ground - 1.16 * s, x + head_r, ground - 1.16 * s + 2 * head_r], fill=color)
    d.polygon([(x - 0.30 * s, ground), (x + 0.30 * s, ground),
               (x + 0.22 * s, ground - 0.86 * s), (x - 0.22 * s, ground - 0.86 * s)], fill=color)
    d.rectangle([x - 0.06 * s, ground - 0.62 * s, x + 0.06 * s, ground - 0.12 * s],
                fill=(max(0, color[0] - 26), max(0, color[1] - 26), max(0, color[2] - 26)))


def _building(d: ImageDraw.ImageDraw, x: float, base: float, w: float, h: float,
              color, lit: float = 0.0, seed: int = 0) -> None:
    d.rectangle([x, base - h, x + w, base], fill=color)
    cols = max(2, int(w / 26))
    rows = max(2, int(h / 34))
    for r in range(rows):
        for c in range(cols):
            if (r * 7 + c * 3 + seed) % 5 == 0:
                continue
            on = ((r + c + seed) % 3 == 0) and lit > 0.35
            wx = x + 8 + c * (w - 16) / cols + 2
            wy = base - h + 12 + r * (h - 20) / rows
            win_col = ACCENT2 if on else (12, 32, 46)
            d.rectangle([wx, wy, wx + 8, wy + 12], fill=win_col)


def _sun(img: Image.Image, cx: float, cy: float, r: float, p: float) -> Image.Image:
    return draw.glow(img, (cx, cy), r, ACCENT, int(60 + 90 * p))


def _graph(d: ImageDraw.ImageDraw, x: float, base: float, w: float, h: float,
           p: float, bars: int = 5) -> None:
    bw = w / (bars * 1.7)
    for i in range(bars):
        frac = (i + 1) / bars
        bp = max(0.0, min(1.0, (p - i * 0.12) / 0.5))
        bh = h * frac * bp
        bx = x + i * w / bars
        d.rectangle([bx, base - bh, bx + bw, base], fill=ACCENT)
        d.rectangle([bx, base - bh, bx + bw, base - bh + 3], fill=ACCENT2)


def _scales(d: ImageDraw.ImageDraw, cx: float, cy: float, s: float, color) -> None:
    d.rectangle([cx - s * 0.03, cy - s * 0.5, cx + s * 0.03, cy + s * 0.5], fill=color)
    d.line([cx - s * 0.45, cy - s * 0.42, cx + s * 0.45, cy - s * 0.42], fill=color, width=max(2, int(s * 0.03)))
    for side in (-1, 1):
        px = cx + side * s * 0.45
        d.line([(cx, cy - s * 0.42), (px, cy - s * 0.20)], fill=color, width=max(2, int(s * 0.025)))
        d.polygon([(px - s * 0.13, cy - s * 0.20), (px + s * 0.13, cy - s * 0.20),
                   (px, cy - s * 0.02)], fill=color)
    d.rectangle([cx - s * 0.22, cy + s * 0.5, cx + s * 0.22, cy + s * 0.56], fill=color)


def _books(d: ImageDraw.ImageDraw, x: float, base: float, s: float) -> None:
    cols = [ACCENT, (222, 216, 200), (140, 170, 190), ACCENT2]
    for i, c in enumerate(cols):
        d.rectangle([x + i * s * 0.16, base - s * (0.5 + 0.07 * i),
                     x + i * s * 0.16 + s * 0.13, base], fill=c)


def _room(d: ImageDraw.ImageDraw, ctx: "IllusContext", off: float) -> None:
    w, h = ctx.w, ctx.h
    floor = h * 0.78
    d.rectangle([0, floor, w, h], fill=(30, 44, 56))
    back = (22, 52, 72)
    d.rectangle([w * 0.10 + off * 0.4, h * 0.24, w * 0.90 + off * 0.4, floor], fill=back)
    d.rectangle([w * 0.62 + off * 0.4, h * 0.34, w * 0.80 + off * 0.4, h * 0.52],
                fill=(96, 132, 152))
    d.rectangle([w * 0.28 + off * 0.55, floor - h * 0.02, w * 0.72 + off * 0.55, floor + h * 0.10],
                fill=(38, 58, 72))


def _skyline(d: ImageDraw.ImageDraw, ctx: "IllusContext", off: float, base: float,
             color, seed: int, scale: float = 1.0, lit: float = 0.0) -> None:
    w, h = ctx.w, ctx.h
    x = -w * 0.1 + off
    rnd = (seed * 2654435761) % 4294967296
    while x < w * 1.1:
        rnd = (rnd * 1103515245 + 12345) % 2147483648
        bw = 60 + (rnd % 90) * scale
        rnd = (rnd * 1103515245 + 12345) % 2147483648
        bh = 120 + (rnd % 260) * scale
        _building(d, x, base, bw, bh, color, lit=lit, seed=seed)
        x += bw * 0.92


def _hills(d: ImageDraw.ImageDraw, ctx: "IllusContext", off: float, base: float,
           color, amp: float, seed: int) -> None:
    w = ctx.w
    pts = [(0, ctx.h)]
    steps = 24
    for i in range(steps + 1):
        x = w * i / steps
        y = base - amp * (0.5 + 0.5 * math.sin(i * 0.7 + seed + off / (w * 0.5)))
        pts.append((x, y))
    pts.append((w, ctx.h))
    d.polygon(pts, fill=color)


CREAM_TEXT = (248, 246, 241)

# Prefix drawn on an evidence-gap banner, per language (kept out of the
# localised picture's target language only when the film is in English).
_GAP_PREFIX = {"en": "GAP", "ru": "ПРОБЕЛ", "uz": "BO'SHLIQ"}


def _placeholder_mark(img: Image.Image, ctx: "IllusContext", text: str) -> None:
    if not text:
        return
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    d.rectangle([int(w * 0.05), int(h * 0.055), int(w * 0.95), int(h * 0.105)],
                outline=(220, 120, 80, 200), width=2)
    lang = (getattr(getattr(ctx, "spec", None), "language", "en") or "en")[:2].lower()
    prefix = _GAP_PREFIX.get(lang, "GAP")
    d.text((int(w * 0.062), int(h * 0.065)), "%s: %s" % (prefix, text[:110]),
           font=ctx.fb.label(22), fill=(240, 170, 120, 235))


# ---------------------------------------------------------------- icons
# Flat pictograms drawn from primitives; one per practice area keyword.
_ICON_RULES = [
    (r"kiber|cyber|киберп|\bit\b|\bit |it-|it va|ит-", "lock"),
    (r"m&a|korporativ|corporate|корпоратив", "building"),
    (r"soliq|tax|налог", "coin"),
    (r"bank|банк|finans|финанс", "columns"),
    (r"nizo|dispute|спор|arbitra|арбитр", "scales"),
    (r"bojxona|customs|таможен|jinoiy|criminal|уголов", "shield"),
    (r"mehnat|labou?r|труд|shartnoma|contract|контракт|договор", "doc"),
    (r"mulk|property|estate|недвижим|intellekt|intellectual|интеллект", "globe"),
]
_ICON_ORDER = ["scales", "building", "lock", "coin", "columns", "doc", "shield", "globe"]


def _icon_for(label: str, index: int) -> str:
    low = (label or "").lower()
    for pattern, name in _ICON_RULES:
        if re.search(pattern, low):
            return name
    return _ICON_ORDER[index % len(_ICON_ORDER)]


def _draw_icon(d: ImageDraw.ImageDraw, name: str, cx: float, cy: float, s: float) -> None:
    c, c2 = ACCENT2, (240, 244, 247)
    lw = max(2, int(s * 0.045))
    if name == "scales":
        _scales(d, cx, cy, s, c)
    elif name == "building":
        d.rectangle([cx - s * 0.28, cy - s * 0.46, cx + s * 0.28, cy + s * 0.46], fill=c)
        for r in range(4):
            for k in range(3):
                d.rectangle([cx - s * 0.20 + k * s * 0.15, cy - s * 0.36 + r * s * 0.2,
                             cx - s * 0.12 + k * s * 0.15, cy - s * 0.26 + r * s * 0.2], fill=(14, 36, 50))
    elif name == "lock":
        d.pieslice([cx - s * 0.22, cy - s * 0.52, cx + s * 0.22, cy - s * 0.08], 180, 360, outline=c, width=lw * 2)
        d.rounded_rectangle([cx - s * 0.32, cy - s * 0.18, cx + s * 0.32, cy + s * 0.46], radius=s * 0.06, fill=c)
        d.ellipse([cx - s * 0.06, cy + s * 0.04, cx + s * 0.06, cy + s * 0.16], fill=(14, 36, 50))
        d.rectangle([cx - s * 0.025, cy + s * 0.12, cx + s * 0.025, cy + s * 0.28], fill=(14, 36, 50))
    elif name == "coin":
        for k in range(3):
            y = cy + s * (0.25 - 0.2 * k)
            d.ellipse([cx - s * 0.34, y - s * 0.12, cx + s * 0.34, y + s * 0.12], fill=c, outline=(14, 36, 50), width=lw)
    elif name == "columns":
        d.polygon([(cx - s * 0.42, cy - s * 0.22), (cx, cy - s * 0.5), (cx + s * 0.42, cy - s * 0.22)], fill=c)
        for k in range(4):
            x = cx - s * 0.32 + k * s * 0.21
            d.rectangle([x, cy - s * 0.16, x + s * 0.11, cy + s * 0.32], fill=c)
        d.rectangle([cx - s * 0.44, cy + s * 0.36, cx + s * 0.44, cy + s * 0.46], fill=c)
    elif name == "doc":
        d.rounded_rectangle([cx - s * 0.3, cy - s * 0.46, cx + s * 0.3, cy + s * 0.46], radius=s * 0.05, fill=c2)
        for k in range(5):
            d.rectangle([cx - s * 0.2, cy - s * 0.3 + k * s * 0.15, cx + s * (0.2 - 0.08 * (k == 4)), cy - s * 0.26 + k * s * 0.15], fill=(120, 140, 155))
        d.ellipse([cx + s * 0.06, cy + s * 0.18, cx + s * 0.32, cy + s * 0.44], fill=c)
    elif name == "shield":
        d.polygon([(cx - s * 0.36, cy - s * 0.4), (cx, cy - s * 0.52), (cx + s * 0.36, cy - s * 0.4),
                   (cx + s * 0.32, cy + s * 0.12), (cx, cy + s * 0.5), (cx - s * 0.32, cy + s * 0.12)], fill=c)
        d.line([(cx - s * 0.14, cy), (cx - s * 0.03, cy + s * 0.13), (cx + s * 0.18, cy - s * 0.14)],
               fill=(14, 36, 50), width=lw * 2)
    else:   # globe
        d.ellipse([cx - s * 0.42, cy - s * 0.42, cx + s * 0.42, cy + s * 0.42], outline=c, width=lw * 2)
        d.ellipse([cx - s * 0.18, cy - s * 0.42, cx + s * 0.18, cy + s * 0.42], outline=c, width=lw)
        d.line([cx - s * 0.42, cy, cx + s * 0.42, cy], fill=c, width=lw)
        d.arc([cx - s * 0.42, cy - s * 0.2, cx + s * 0.42, cy + s * 0.2], 0, 180, fill=c, width=lw)


# ---------------------------------------------------------------- skies
# The film moves from night to morning, so the palette follows the story arc.
_PALETTES = {
    "hook": ((10, 22, 40), (30, 62, 92), 0.0),
    "origin": ((22, 46, 76), (96, 98, 120), 0.35),
    "practice": ((30, 60, 92), (150, 120, 118), 0.55),
    "achievements": ((34, 74, 106), (196, 150, 118), 0.7),
    "people": ((44, 88, 120), (214, 176, 128), 0.8),
    "office": ((54, 100, 132), (226, 196, 146), 0.9),
    "closing": ((70, 118, 148), (244, 214, 160), 1.0),
}


def _sky_for(ctx: "IllusContext", key: str) -> Image.Image:
    cache = ctx.__dict__.setdefault("_skies", {})
    key = key if key in _PALETTES else "origin"
    if key not in cache:
        top, bot, sun = _PALETTES[key]
        img = draw.gradient((ctx.w, ctx.h), top, bot, vertical=True)
        cy = ctx.h * (0.52 - 0.27 * sun)
        img = _sun(img, ctx.w * 0.74, cy, ctx.w * (0.12 + 0.06 * sun), 0.4 + 0.6 * sun)
        cache[key] = img
    return cache[key]


def _stars(d: ImageDraw.ImageDraw, ctx: "IllusContext", t: float, amount: float) -> None:
    rnd = 12345
    for i in range(70):
        rnd = (rnd * 1103515245 + 12345) % 2147483648
        x = (rnd % 1000) / 1000.0 * ctx.w
        rnd = (rnd * 1103515245 + 12345) % 2147483648
        y = (rnd % 1000) / 1000.0 * ctx.h * 0.55
        tw = 0.5 + 0.5 * math.sin(t * 2.0 + i)
        a = int(200 * amount * tw)
        r = 1 + (i % 3)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 244, 214, a))


def _cloud(d: ImageDraw.ImageDraw, x: float, y: float, s: float, a: int) -> None:
    for dx, dy, r in ((0, 0, 0.5), (0.45, -0.12, 0.6), (0.95, 0, 0.45), (0.5, 0.1, 0.55)):
        d.ellipse([x + dx * s - r * s * 0.5, y + dy * s - r * s * 0.35,
                   x + dx * s + r * s * 0.5, y + dy * s + r * s * 0.35], fill=(255, 255, 255, a))


def _backdrop(ctx: "IllusContext", key: str, t: float, dur: float, grow: float = 1.0) -> Image.Image:
    """Sky, drifting clouds and three parallax skyline layers."""
    w, h = ctx.w, ctx.h
    cam = t / dur
    img = _sky_for(ctx, key).copy()
    d = ImageDraw.Draw(img, "RGBA")
    night = 1.0 if key == "hook" else (0.4 if key == "origin" else 0.0)
    if night:
        _stars(d, ctx, t, night)
    for i in range(3):
        _cloud(d, (w * (0.15 + 0.38 * i) + t * (9 + 4 * i)) % (w * 1.3) - w * 0.15,
               h * (0.14 + 0.07 * i), h * 0.20, 44 if night else 70)
    sunrise = _PALETTES.get(key, _PALETTES["origin"])[2]
    far = (int(24 + 14 * sunrise), int(54 + 16 * sunrise), int(76 + 12 * sunrise))
    mid = (int(16 + 8 * sunrise), int(42 + 10 * sunrise), int(62 + 8 * sunrise))
    _hills(d, ctx, -w * 0.04 * cam, h * 0.72, far, h * 0.05, 1.3)
    _skyline(d, ctx, -w * 0.07 * cam, h * 0.74, far, 7, 0.8, lit=0.0)
    _skyline_grow(d, ctx, -w * 0.12 * cam, h * 0.80, mid, 3, grow, lit=0.6 if night else 0.0, t=t)
    _hills(d, ctx, -w * 0.18 * cam, h * 0.90, (11, 30, 44), h * 0.04, 2.6)
    return img


def _skyline_grow(d, ctx, off, base, color, seed, grow, lit, t) -> None:
    """Skyline whose towers rise one after another (grow 0 → 1)."""
    w = ctx.w
    x = -w * 0.1 + off
    rnd = (seed * 2654435761) % 4294967296
    i = 0
    n_total = 22.0
    while x < w * 1.1:
        rnd = (rnd * 1103515245 + 12345) % 2147483648
        bw = 60 + (rnd % 90) * 0.9
        rnd = (rnd * 1103515245 + 12345) % 2147483648
        bh = 120 + (rnd % 260) * 0.9
        rise = max(0.0, min(1.0, grow * 1.6 - i / n_total))
        if rise > 0:
            # windows flicker on gradually in the night scenes
            _building(d, x, base, bw, bh * draw.ease_out(rise), color,
                      lit=lit * (0.5 + 0.5 * math.sin(t + i)), seed=seed)
        x += bw * 0.92
        i += 1


# ---------------------------------------------------------------- text helpers
def _txt(img: Image.Image, ctx: "IllusContext", x: float, y: float, text: str, font,
         color, alpha: float, max_w: Optional[float] = None, line_h: float = 1.25,
         align: str = "left", max_lines: int = 3) -> float:
    """Wrapped text with alpha; returns the height used."""
    if not text or alpha <= 0:
        return 0.0
    d = ImageDraw.Draw(img, "RGBA")
    lines = draw.wrap(d, text, font, max_w or ctx.w * 0.8)[:max_lines]
    lh = font.size * line_h
    a = int(255 * min(1.0, alpha))
    for i, ln in enumerate(lines):
        lx = x if align == "left" else x - draw.text_width(d, ln, font) / (1 if align == "right" else 2)
        d.text((lx, y + i * lh), ln, font=font, fill=tuple(color) + (a,))
    return lh * len(lines)


def _panel(img: Image.Image, box, alpha: float, radius: float = 18) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    d.rounded_rectangle(box, radius=radius, fill=(8, 24, 36, int(200 * alpha)),
                        outline=ACCENT + (int(170 * alpha),), width=2)


def _title_block(img, ctx, scene, t) -> float:
    """Heading + sub at the top-left; returns the y where content may start."""
    p = draw.ease_out(draw.ramp(t, 0.3, 0.8))
    y = ctx.h * 0.075 + (1 - p) * ctx.h * 0.02
    used = 0.0
    if scene.get("heading"):
        used += _txt(img, ctx, ctx.w * 0.06, y, scene["heading"][:60], ctx.fb.display(58),
                     CREAM_TEXT, p, ctx.w * 0.7, max_lines=1)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([ctx.w * 0.06, y + used + ctx.h * 0.012,
                 ctx.w * 0.06 + ctx.w * 0.09 * p, y + used + ctx.h * 0.018], fill=ACCENT + (255,))
    return y + used + ctx.h * 0.04


def _count(label: str, t: float, delay: float = 0.4, dur: float = 1.6) -> str:
    """'1000+' counts up from 0; anything that is not a bare figure is unchanged."""
    m = re.fullmatch(r"\s*(\d{1,6})(\+?)\s*", label or "")
    if not m:
        return label
    v = int(round(int(m.group(1)) * draw.ease_out(draw.ramp(t, delay, dur))))
    return "%d%s" % (v, m.group(2))


# ---------------------------------------------------------------- scene painters
def _scene_hook(ctx, scene, t, dur):
    img = _backdrop(ctx, "hook", t, dur, grow=min(1.0, 0.35 + t / 3.0))
    p = draw.ease_out(draw.ramp(t, 0.5, 1.0))
    _txt(img, ctx, ctx.w * 0.06, ctx.h * 0.14 + (1 - p) * ctx.h * 0.03, scene["narration"],
         ctx.fb.display(64), CREAM_TEXT, p, ctx.w * 0.62, line_h=1.2, max_lines=4)
    return img


def _scene_origin(ctx, scene, t, dur):
    img = _backdrop(ctx, "origin", t, dur, grow=draw.ramp(t, 0.2, 2.6))
    _title_block(img, ctx, dict(scene, heading=""), t)
    label = (scene.get("heading") or "").strip()
    big = _count(label, t)
    p = draw.ease_out(draw.ramp(t, 0.4, 0.9))
    if re.fullmatch(r"\s*\d{1,6}\+?\s*", label):
        _panel(img, (ctx.w * 0.05, ctx.h * 0.12, ctx.w * 0.47, ctx.h * 0.50), p)
        _txt(img, ctx, ctx.w * 0.07, ctx.h * 0.14, big, ctx.fb.display(190), ACCENT2, p, max_lines=1)
        _txt(img, ctx, ctx.w * 0.07, ctx.h * 0.37, scene.get("sub") or "", ctx.fb.serif_regular(40),
             CREAM_TEXT, draw.ramp(t, 1.0, 0.7), ctx.w * 0.38, max_lines=2)
    else:
        _title_block(img, ctx, scene, t)
    return img


def _split_items(scene) -> List[str]:
    raw = scene.get("sub") or scene.get("heading") or ""
    return [i.strip() for i in raw.split(",") if i.strip()][:5]


def _scene_practice(ctx, scene, t, dur):
    img = _backdrop(ctx, "practice", t, dur)
    top = _title_block(img, ctx, scene, t)
    items = _split_items(scene)
    n = max(1, len(items))
    cw, ch = ctx.w * 0.165, ctx.h * 0.40
    gap = (ctx.w * 0.88 - cw * n) / max(1, n - 1) if n > 1 else 0
    x0 = ctx.w * 0.06 if n > 1 else (ctx.w - cw) / 2
    for i, label in enumerate(items):
        p = draw.ease_out_back(draw.ramp(t, 0.5 + 0.28 * i, 0.8))
        if p <= 0:
            continue
        x = x0 + i * (cw + gap)
        y = max(top + ctx.h * 0.03, ctx.h * 0.27) + (1 - min(1.0, p)) * ctx.h * 0.08
        a = min(1.0, p)
        _panel(img, (x, y, x + cw, y + ch), a)
        d = ImageDraw.Draw(img, "RGBA")
        bob = math.sin(t * 2.2 + i) * ctx.h * 0.008
        _draw_icon(d, _icon_for(label, i), x + cw / 2, y + ch * 0.36 + bob, ch * 0.34)
        _txt(img, ctx, x + cw / 2, y + ch * 0.66, label, ctx.fb.serif_regular(36), CREAM_TEXT, a,
             cw * 0.90, align="center", max_lines=3)
    return img


def _scene_stat(ctx, scene, t, dur):
    img = _backdrop(ctx, "achievements", t, dur)
    label = (scene.get("heading") or "").strip()
    p = draw.ease_out(draw.ramp(t, 0.3, 0.8))
    _panel(img, (ctx.w * 0.05, ctx.h * 0.12, ctx.w * 0.50, ctx.h * 0.52), p)
    _txt(img, ctx, ctx.w * 0.07, ctx.h * 0.14, _count(label, t), ctx.fb.display(170), ACCENT2, p,
         ctx.w * 0.42, max_lines=1)
    _txt(img, ctx, ctx.w * 0.07, ctx.h * 0.36, scene.get("sub") or "", ctx.fb.serif_regular(38),
         CREAM_TEXT, draw.ramp(t, 1.0, 0.7), ctx.w * 0.4, max_lines=2)
    d = ImageDraw.Draw(img, "RGBA")
    _graph(d, ctx.w * 0.56, ctx.h * 0.66, ctx.w * 0.36, ctx.h * 0.46,
           draw.ease_out(draw.ramp(t, 0.5, 1.8)), bars=6)
    # a figure per bar-top: the firm's people, rising with the results
    for i in range(3):
        _figure(d, ctx.w * (0.60 + 0.12 * i), ctx.h * 0.93, ctx.h * 0.16, (10, 28, 40))
    return img


def _circle_portrait(ctx, path: str, size: int) -> Optional[Image.Image]:
    cache = ctx.__dict__.setdefault("_portraits", {})
    if path not in cache:
        try:
            src = Image.open(path).convert("RGB")
            sq = draw.cover(src, (size, size), anchor_y=0.25)
            mask = Image.new("L", (size * 3, size * 3), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, size * 3 - 1, size * 3 - 1], fill=255)
            mask = mask.resize((size, size), Image.LANCZOS)
            out = sq.convert("RGBA")
            out.putalpha(mask)
            cache[path] = out
        except Exception:
            cache[path] = None
    return cache[path]


def _scene_people(ctx, scene, t, dur):
    img = _backdrop(ctx, "people", t, dur)
    _title_block(img, ctx, scene, t)
    people = [p for p in (scene.get("portraits") or []) if os.path.isfile(p["file"])]
    d = ImageDraw.Draw(img, "RGBA")
    if people:
        n = len(people)
        size = int(ctx.h * 0.27)
        gap = (ctx.w * 0.88 - size * n) / max(1, n + 1)
        for i, person in enumerate(people):
            p = draw.ease_out_back(draw.ramp(t, 0.5 + 0.3 * i, 0.8))
            if p <= 0:
                continue
            pic = _circle_portrait(ctx, person["file"], size)
            if pic is None:
                continue
            x = int(ctx.w * 0.06 + gap + i * (size + gap))
            y = int(ctx.h * 0.30 + (1 - min(1.0, p)) * ctx.h * 0.08)
            a = min(1.0, p)
            d.ellipse([x - 8, y - 8, x + size + 8, y + size + 8], fill=ACCENT + (int(255 * a),))
            img.paste(pic, (x, y), pic)
            _txt(img, ctx, x + size / 2, y + size + ctx.h * 0.025, person["name"],
                 ctx.fb.serif_regular(28), CREAM_TEXT, a, size * 1.12, align="center", max_lines=3)
    else:
        names = _split_items(scene)
        for i, nm in enumerate(names[:4]):
            p = draw.ease_out(draw.ramp(t, 0.5 + 0.3 * i, 0.8))
            x = ctx.w * (0.18 + 0.2 * i)
            _figure(d, x, ctx.h * 0.62, ctx.h * 0.28, (10, 28, 40))
            _txt(img, ctx, x, ctx.h * 0.65, nm, ctx.fb.serif_regular(30), CREAM_TEXT, p,
                 ctx.w * 0.18, align="center", max_lines=2)
    return img


def _scene_partner(ctx, scene, t, dur):
    img = _backdrop(ctx, "people", t, dur)
    d = ImageDraw.Draw(img, "RGBA")
    people = [p for p in (scene.get("portraits") or []) if os.path.isfile(p["file"])]
    tx = ctx.w * 0.08
    if people:
        size = int(ctx.h * 0.46)
        pic = _circle_portrait(ctx, people[0]["file"], size)
        p = draw.ease_out_back(draw.ramp(t, 0.3, 0.9))
        if pic is not None and p > 0:
            x, y = int(ctx.w * 0.07), int(ctx.h * 0.2 + (1 - min(1.0, p)) * ctx.h * 0.1)
            d.ellipse([x - 10, y - 10, x + size + 10, y + size + 10], fill=ACCENT + (int(255 * min(1.0, p)),))
            img.paste(pic, (x, y), pic)
        tx = ctx.w * 0.07 + size + ctx.w * 0.06
    ph = draw.ease_out(draw.ramp(t, 0.5, 0.8))
    used = _txt(img, ctx, tx, ctx.h * 0.22, scene.get("heading") or "", ctx.fb.display(60),
                CREAM_TEXT, ph, ctx.w - tx - ctx.w * 0.05, max_lines=2)
    role, _sep, specs = (scene.get("sub") or "").partition(" · ")
    y = ctx.h * 0.22 + used + ctx.h * 0.02
    d.rectangle([tx, y, tx + ctx.w * 0.09 * ph, y + ctx.h * 0.006], fill=ACCENT + (255,))
    y += ctx.h * 0.03
    y += _txt(img, ctx, tx, y, role, ctx.fb.serif_regular(40), ACCENT2, draw.ramp(t, 1.0, 0.7),
              ctx.w - tx - ctx.w * 0.05, max_lines=2) + ctx.h * 0.02
    for i, item in enumerate([s.strip() for s in specs.split(",") if s.strip()][:4]):
        a = draw.ramp(t, 1.4 + 0.2 * i, 0.6)
        d.ellipse([tx, y + ctx.h * 0.012, tx + ctx.h * 0.016, y + ctx.h * 0.028], fill=ACCENT + (int(255 * a),))
        y += _txt(img, ctx, tx + ctx.h * 0.04, y, item, ctx.fb.serif_regular(34), CREAM_TEXT, a,
                  ctx.w - tx - ctx.w * 0.08, max_lines=2) + ctx.h * 0.012
    return img


def _pin(d, x: float, y: float, s: float, a: int = 255) -> None:
    d.polygon([(x - s * 0.5, y - s * 1.3), (x + s * 0.5, y - s * 1.3), (x, y)],
              fill=(214, 74, 60, a))
    d.ellipse([x - s * 0.62, y - s * 2.0, x + s * 0.62, y - s * 0.76], fill=(214, 74, 60, a))
    d.ellipse([x - s * 0.24, y - s * 1.62, x + s * 0.24, y - s * 1.14], fill=(255, 244, 230, a))


def _scene_office(ctx, scene, t, dur):
    w, h = ctx.w, ctx.h
    img = _sky_for(ctx, "office").copy()
    d = ImageDraw.Draw(img, "RGBA")
    # stylised city map: blocks, avenues, a river
    d.rectangle([0, h * 0.18, w, h], fill=(32, 62, 82))
    rnd = 99
    for gx in range(14):
        for gy in range(8):
            rnd = (rnd * 1103515245 + 12345) % 2147483648
            if rnd % 5 == 0:
                continue
            bx, by = w * 0.04 + gx * w * 0.07, h * 0.22 + gy * h * 0.1
            d.rounded_rectangle([bx, by, bx + w * 0.058, by + h * 0.082], radius=6,
                                fill=(44, 78, 100) if rnd % 3 else (52, 92, 108))
    d.line([(0, h * 0.5), (w * 0.35, h * 0.44), (w * 0.7, h * 0.58), (w, h * 0.5)],
           fill=(92, 160, 196, 235), width=int(h * 0.05))
    d.line([(w * 0.62, h * 0.18), (w * 0.5, h)], fill=(226, 196, 146, 200), width=int(h * 0.016))
    pin_x, pin_y = w * 0.62, h * 0.60
    drop = draw.ramp(t, 0.6, 0.7)
    land = draw.ease_out(drop)
    bounce = math.sin(max(0.0, t - 1.3) * 9) * math.exp(-max(0.0, t - 1.3) * 3) * h * 0.04
    y = pin_y - (1 - land) * h * 0.5 - bounce
    for k in range(3):                                  # ripples after landing
        rp = draw.ramp(t, 1.3 + 0.35 * k, 1.4) % 1.0 if t > 1.3 else 0
        if rp > 0:
            r = h * 0.03 + rp * h * 0.14
            d.ellipse([pin_x - r, pin_y - r * 0.4, pin_x + r, pin_y + r * 0.4],
                      outline=(255, 244, 214, int(180 * (1 - rp))), width=3)
    d.ellipse([pin_x - h * 0.03, pin_y - h * 0.01, pin_x + h * 0.03, pin_y + h * 0.012], fill=(0, 0, 0, 90))
    _pin(d, pin_x, y, h * 0.045)
    _title_block(img, ctx, dict(scene, heading=scene.get("heading") if scene.get("sub") else ""), t)
    p = draw.ease_out(draw.ramp(t, 1.0, 0.8))
    _panel(img, (w * 0.05, h * 0.30, w * 0.46, h * 0.52), p)
    _txt(img, ctx, w * 0.07, h * 0.325, scene.get("sub") or scene.get("heading") or "",
         ctx.fb.serif_regular(40), CREAM_TEXT, p, w * 0.37, max_lines=3)
    return img


def _scene_closing(ctx, scene, t, dur):
    img = _backdrop(ctx, "closing", t, dur, grow=1.0)
    p = draw.ease_out(draw.ramp(t, 0.5, 1.0))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, ctx.h * 0.18, ctx.w, ctx.h * 0.62], fill=(8, 24, 36, int(120 * p)))
    _txt(img, ctx, ctx.w / 2, ctx.h * 0.29, ctx.spec.firm_name, ctx.fb.display(104),
         CREAM_TEXT, p, ctx.w * 0.86, align="center", max_lines=2)
    d.rectangle([ctx.w * 0.44, ctx.h * 0.50, ctx.w * (0.44 + 0.12 * p), ctx.h * 0.506],
                fill=ACCENT + (255,))
    return img


_PAINTERS = {"hook": _scene_hook, "origin": _scene_origin, "practice": _scene_practice,
             "achievements": _scene_stat, "people": _scene_people, "office": _scene_office,
             "closing": _scene_closing}


def _painter_for(key: str):
    if key.startswith("partner") and key[7:].isdigit():
        return _scene_partner
    return _PAINTERS.get(key, _generic)


def _generic(ctx, scene, t, dur):
    """Any other scene key: backdrop plus heading and sub."""
    img = _backdrop(ctx, "origin", t, dur)
    _title_block(img, ctx, scene, t)
    _txt(img, ctx, ctx.w * 0.06, ctx.h * 0.24, scene.get("sub") or scene.get("narration") or "",
         ctx.fb.serif_regular(40), CREAM_TEXT, draw.ramp(t, 0.8, 0.7), ctx.w * 0.6)
    return img


def render_illustration(ctx: IllusContext, scene: Dict[str, Any], t: float) -> Image.Image:
    dur = max(0.001, float(scene["dur"]))
    painter = _painter_for((scene.get("key") or "").strip())
    return painter(ctx, scene, t, dur)


def render_scene_frame(ctx: IllusContext, scene: Dict[str, Any], t: float) -> Image.Image:
    img = render_illustration(ctx, scene, t)
    dur = max(0.001, float(scene["dur"]))
    img = draw.apply_alpha(img, draw.scene_alpha(t, dur, fade_in=0.4, fade_out=0.4))
    _placeholder_mark(img, ctx, gap_banner_text(scene))
    if draw.narration_needs_caption(scene) and scene.get("key") != "hook":
        draw.caption(img, ctx.fb, scene["narration"],
                     draw.ramp(t, 0.9, 0.6) * draw.ramp(dur - t, 0.0, 0.5), max_lines=2)
    draw.watermark(img, ctx.fb, ctx.spec.watermark)
    return img


def iter_frames(ctx: IllusContext, scenes: List[Dict[str, Any]],
                cancel: Optional[Callable[[], bool]] = None,
                progress: Optional[Callable[[int, int], None]] = None):
    """Sequential frames with crossfades between illustrated scenes."""
    fps = ctx.spec.fps
    overlap = min(ctx.spec.transition_sec, min(s["dur"] for s in scenes) * 0.4)
    starts: List[float] = []
    acc = 0.0
    for s in scenes:
        starts.append(acc)
        acc += float(s["dur"]) - overlap
    total = acc + overlap
    n_frames = max(1, int(round(total * fps)))
    for n in range(n_frames):
        if cancel and cancel():
            return
        tg = n / float(fps)
        active = [(i, st) for i, st in enumerate(starts)
                  if st <= tg < st + float(scenes[i]["dur"])] or [(len(scenes) - 1, starts[-1])]
        i, st = active[-1]
        frame = render_scene_frame(ctx, scenes[i], tg - st)
        if len(active) > 1 and overlap > 0:
            j = active[-2][0]
            stj = starts[j]
            wgt = max(0.0, min(1.0, (tg - stj - float(scenes[j]["dur"]) + overlap) / overlap))
            frame = Image.blend(render_scene_frame(ctx, scenes[j], tg - stj), frame, wgt)
        if progress and n % 15 == 0:
            progress(n, n_frames)
        yield frame


class IllustratedBackend(object):
    style = "illustrated"
    label = "Illustrated 2D Animation"

    def render(self, spec: RenderSpec, out_path: str, work_dir: str,
               asset_dir: str = "", cancel: Optional[Callable[[], bool]] = None,
               progress: Optional[Callable[[str, int], None]] = None,
               profile: str = "production") -> Dict[str, Any]:
        if not common.ffmpeg_available():
            raise common.RenderError("ffmpeg is not available — cannot render illustrated 2D")
        os.makedirs(work_dir, exist_ok=True)
        ctx = IllusContext(spec, asset_dir)

        def _prog(n: int, total: int) -> None:
            if progress:
                progress("illustrating frame %d/%d" % (n, total),
                         int(100 * n / max(1, total)))

        if progress:
            progress("illustrated 2D pass: %d scenes at %dx%d@%d (%s)" %
                     (len(spec.scenes), spec.width, spec.height, spec.fps, profile), 1)
        video_only = os.path.join(work_dir, "_video_only.mp4")
        common.encode_frames_to_video(iter_frames(ctx, spec.scenes, cancel, _prog),
                                      video_only, spec.width, spec.height, spec.fps,
                                      profile=profile)
        audio_path, audio_meta = common.build_audio_track(
            os.path.join(work_dir, "_audio.wav"), spec.total_duration, spec.audio, work_dir)
        common.mux(video_only, audio_path, out_path)
        validation = common.validate_mp4(out_path, spec.width, spec.height, spec.fps)
        manifest = common.write_render_manifest(
            os.path.join(work_dir, "render_manifest.json"), spec, self.style,
            common.engine_info("illustrated-pillow-ffmpeg"),
            sources=[s.get("asset") for s in spec.scenes if s.get("asset")],
            limitations=LIMITATIONS, validation=validation,
            extra={"audio_detail": audio_meta, "profile": profile,
                   "design_system": design.DESIGN_VERSION})
        return {"output": out_path, "manifest": manifest, "validation": validation}


def render(spec: RenderSpec, out_path: str, work_dir: str, asset_dir: str = "",
           cancel: Optional[Callable[[], bool]] = None,
           progress: Optional[Callable[[str, int], None]] = None,
           profile: str = "production") -> Dict[str, Any]:
    return IllustratedBackend().render(spec, out_path, work_dir, asset_dir, cancel,
                                       progress, profile)
