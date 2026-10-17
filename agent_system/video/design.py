# -*- coding: utf-8 -*-
"""video/design.py — the reusable visual design system.

This module is the single source of truth for how the film *looks*: palette,
typography hierarchy, spacing/alignment grid, safe margins, reusable
compositions (kicker, heading, rule, panel, card, stat, timeline, list row,
quote, comparison, process, logo lockup, call-to-action) and a small set of
line-icon glyphs drawn as vector primitives.

Everything is resolution-independent: a :class:`Theme` is built for a concrete
``(width, height)`` and converts the design language's "1080-space" units into
pixels, so a 1920x1080 final and a 960x540 preview share one identity instead of
being two different looks.

Deliberate constraints (a professional corporate/legal identity, not a template):

* no emoji, no random decorative circles, no oversized gradient meshes;
* one accent colour (gold) used sparingly, never as a wash;
* text is set on a real grid with generous margins and a clear hierarchy;
* motion is expressed through the ``enter``/``stagger`` primitives so scenes
  move *intentionally* rather than everything animating at once.
"""
import math
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFilter

from . import draw

# --------------------------------------------------------------------- palette
# A restrained legal/corporate palette: deep navy ground, warm gold accent,
# paper-white for light cards. Tonal steps are named so no scene hardcodes RGB.
PALETTE: Dict[str, Tuple[int, int, int]] = {
    "ink_900":   (11, 31, 42),     # near-black navy (grounds)
    "navy_900":  (14, 45, 62),     # brand dark
    "navy_800":  (18, 59, 80),
    "navy_700":  (23, 67, 90),     # brand navy
    "navy_600":  (30, 86, 112),
    "navy_500":  (44, 108, 136),
    "slate_500": (107, 122, 136),  # muted body on light grounds
    "gold_500":  (201, 169, 110),  # brand gold (accent only)
    "gold_400":  (216, 186, 132),
    "gold_300":  (232, 201, 138),
    "gold_100":  (243, 227, 192),
    "cream":     (248, 246, 241),  # paper
    "paper":     (252, 251, 248),
    "ink_700":   (31, 41, 55),     # body ink on light
    "ink_500":   (74, 86, 100),
    "alert":     (198, 92, 66),    # reserved for risk/gap markers only
    "ok":        (86, 140, 110),
}

# Background variants, from darkest to lightest. ``solid`` marks the light card.
VARIANTS = ("deep", "navy", "slate", "gold", "paper")

# Bumped when the design system changes in a way that alters rendered output.
DESIGN_VERSION = "design-system/1.0"


def col(name: str, alpha: Optional[int] = None):
    """Return an RGB or RGBA tuple for a palette name."""
    rgb = PALETTE[name]
    return rgb if alpha is None else (rgb[0], rgb[1], rgb[2], alpha)


def mix(a: Sequence[int], b: Sequence[int], t: float) -> Tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return (int(round(a[0] + (b[0] - a[0]) * t)),
            int(round(a[1] + (b[1] - a[1]) * t)),
            int(round(a[2] + (b[2] - a[2]) * t)))


# ---------------------------------------------------------------- theme / grid
@dataclass
class Theme:
    """A concrete design instance for one output resolution."""

    width: int
    height: int
    fb: draw.FontBook
    margin: int = 0                 # safe area inset for all content
    gutter: int = 0                 # horizontal space between columns
    unit: int = 0                   # base spacing unit (8-pt scale, scaled)

    def __post_init__(self) -> None:
        h = self.height
        # 8-pt spacing scale expressed relative to a 1080-high canvas.
        self._s = h / 1080.0
        self.unit = max(2, int(round(8 * self._s)))
        self.margin = int(round(self.width * 0.062))
        self.gutter = int(round(32 * self._s))

    # -- spacing ------------------------------------------------------------
    def sp(self, steps: float) -> int:
        """Spacing in pixels: ``steps`` units of the 8-pt scale."""
        return int(round(self.unit * steps))

    # -- typography (sizes given in 1080-space, scaled by the FontBook) ------
    def display(self, size: int = 96):
        return self.fb.display(size)

    def title(self, size: int = 72):
        return self.fb.display(size)

    def h2(self, size: int = 46):
        return self.fb.display(size, weight="semibold")

    def h3(self, size: int = 34):
        return self.fb.serif_bold(size)

    def body(self, size: int = 30):
        return self.fb.serif_regular(size)

    def ui(self, size: int = 26):
        return self.fb.label(size)

    def ui_bold(self, size: int = 26):
        return self.fb.label_bold(size)

    def stat(self, size: int = 190):
        return self.fb.display(size)

    # -- content box --------------------------------------------------------
    @property
    def content(self) -> Tuple[int, int, int, int]:
        """(x0, y0, x1, y1) of the safe content area."""
        m = self.margin
        return (m, m, self.width - m, self.height - m)

    @property
    def content_w(self) -> int:
        return self.width - 2 * self.margin

    def columns(self, n: int, span: int = 12) -> List[Tuple[int, int]]:
        """Return (x, width) for a column span across the content width."""
        x0, _, x1, _ = self.content
        total = x1 - x0
        col_w = (total - self.gutter * (span - 1)) / span
        out = []
        x = x0
        for _ in range(n):
            out.append((int(round(x)), int(round(col_w))))
            x += col_w + self.gutter
        return out


# ------------------------------------------------------------------ backgrounds
_BG_CACHE: Dict[Any, Image.Image] = {}


def _vertical_gradient(w: int, h: int, c1, c2) -> Image.Image:
    """Fast vertical gradient. Uses numpy when present, else a scanline loop."""
    try:
        import numpy as np
        t = np.linspace(0.0, 1.0, h, dtype="float32")[:, None]
        a = np.array(c1, dtype="float32")[None, :]
        b = np.array(c2, dtype="float32")[None, :]
        row = a + (b - a) * t                      # (h, 3)
        arr = np.repeat(row[:, None, :], w, axis=1).astype("uint8")
        return Image.fromarray(arr, "RGB")
    except Exception:
        return draw.gradient((w, h), c1, c2, vertical=True)


def _radial_light(base: Image.Image, cx: float, cy: float, r: float,
                  color, strength: int) -> Image.Image:
    """A soft off-centre light, computed once per background (not per frame)."""
    w, h = base.size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=strength)
    layer = layer.filter(ImageFilter.GaussianBlur(max(8, r * 0.45)))
    tint = Image.new("RGB", (w, h), color)
    return Image.composite(tint, base, layer)


def _fine_grid(img: Image.Image, step: int, color, alpha: int) -> Image.Image:
    """A barely-visible engineering grid — structure, not decoration."""
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x in range(step, w, step):
        d.line([(x, 0), (x, h)], fill=color + (alpha,), width=1)
    for y in range(step, h, step):
        d.line([(0, y), (w, y)], fill=color + (alpha,), width=1)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


def build_background(width: int, height: int, variant: str = "navy") -> Image.Image:
    """Create (and cache) the static ground for one variant.

    Backgrounds are expensive (gradient + soft light + vignette) and identical
    for every frame of a scene, so they are built once and reused. This is the
    main reason the previous pipeline was slow: it rebuilt them per frame.
    """
    key = (width, height, variant)
    if key in _BG_CACHE:
        return _BG_CACHE[key]

    v = variant if variant in VARIANTS else "navy"
    if v == "deep":
        img = _vertical_gradient(width, height, PALETTE["ink_900"], PALETTE["navy_800"])
        img = _radial_light(img, width * 0.62, -height * 0.10, width * 0.55,
                            PALETTE["navy_600"], 60)
    elif v == "slate":
        img = _vertical_gradient(width, height, PALETTE["ink_900"], PALETTE["navy_600"])
        img = _radial_light(img, width * 0.18, height * 0.92, width * 0.60,
                            PALETTE["navy_700"], 54)
    elif v == "gold":
        img = _vertical_gradient(width, height, PALETTE["navy_900"], PALETTE["navy_700"])
        img = _radial_light(img, width * 0.80, height * 0.16, width * 0.42,
                            PALETTE["gold_500"], 26)
    elif v == "paper":
        img = Image.new("RGB", (width, height), PALETTE["paper"])
        img = _radial_light(img, width * 0.5, height * 1.05, width * 0.7,
                            PALETTE["gold_100"], 40)
    else:  # navy
        img = _vertical_gradient(width, height, PALETTE["navy_900"], PALETTE["navy_700"])
        img = _radial_light(img, width * 0.5, -height * 0.12, width * 0.50,
                            PALETTE["navy_500"], 46)

    if v != "paper":
        step = max(40, int(round(width / 26.0)))
        img = _fine_grid(img, step, (255, 255, 255), 6)
        img = draw.vignette(img, 0.30)
    else:
        img = draw.vignette(img, 0.10)

    _BG_CACHE[key] = img
    return img


def clear_background_cache() -> None:
    _BG_CACHE.clear()


# ------------------------------------------------------------------ effects
def soft_shadow(img: Image.Image, box: Tuple[int, int, int, int], radius: int = 18,
                spread: int = 10, alpha: int = 90) -> Image.Image:
    """Drop a soft shadow under a rectangular panel (drawn onto ``img``)."""
    x0, y0, x1, y1 = box
    w, h = img.size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle([x0 - spread, y0 - spread + radius // 2,
                         x1 + spread, y1 + spread + radius // 2],
                        radius=radius + spread, fill=alpha)
    layer = layer.filter(ImageFilter.GaussianBlur(max(4, radius * 0.7)))
    shade = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(shade, img, layer)


def scrim(img: Image.Image, box: Tuple[int, int, int, int],
          color=(0, 0, 0), alpha: int = 150, feather: int = 24) -> Image.Image:
    """Darken a region (for text over imagery) with a feathered edge."""
    w, h = img.size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    d.rectangle(box, fill=alpha)
    if feather:
        layer = layer.filter(ImageFilter.GaussianBlur(feather))
    tint = Image.new("RGB", (w, h), color)
    return Image.composite(tint, img, layer)


# ------------------------------------------------------------------ animation
def enter(t: float, delay: float = 0.0, dur: float = 0.6, ease: str = "out") -> float:
    """Eased 0→1 progress of an element that starts at ``delay`` seconds."""
    p = draw.ramp(t, delay, dur)
    if ease == "in_out":
        return draw.ease_in_out(p)
    if ease == "in":
        return draw.ease_in(p) if hasattr(draw, "ease_in") else p * p
    return draw.ease_out(p)


def stagger(t: float, i: int, first: float = 0.25, step: float = 0.12,
            dur: float = 0.55) -> float:
    return enter(t, first + i * step, dur)


def slide(px: float, py: float, p: float, dx: float = 0.0, dy: float = 0.0) -> Tuple[float, float]:
    """Offset a position by (1-p) of (dx, dy) — an eased slide-in."""
    return (px + (1.0 - p) * dx, py + (1.0 - p) * dy)


def with_alpha(color: Sequence[int], p: float) -> Tuple[int, int, int, int]:
    return (color[0], color[1], color[2], int(round(255 * max(0.0, min(1.0, p)))))


# ------------------------------------------------------------------ primitives
def kicker(d: ImageDraw.ImageDraw, th: Theme, x: float, y: float, text: str,
           color=None, size: int = 25, align: str = "left") -> None:
    """A small tracked-out eyebrow label with a leading accent tick."""
    if not text:
        return
    c = color or col("gold_500")
    f = th.ui_bold(size)
    tick = th.sp(3)
    text_w = draw.text_width(d, text.upper(), f, tracking=th.sp(0.45))
    total = tick * 2.2 + text_w
    if align in ("center", "c", "m"):
        x = x - total / 2.0
    elif align in ("right", "r"):
        x = x - total
    yy = y + th.sp(0.5)
    d.rectangle([x, yy + tick, x + tick, yy + tick + 2], fill=c + (255,))
    draw.draw_tracked(d, (x + tick * 2.2, y), text.upper(), f, c + (255,),
                      tracking=th.sp(0.45))


def heading(d: ImageDraw.ImageDraw, th: Theme, x: float, y: float, text: str,
            max_w: float, size: int = 78, color=None, align: str = "left",
            line_gap: float = 1.16, alpha: float = 1.0,
            font=None) -> float:
    """Draw a wrapped display heading. Returns the height consumed (px)."""
    if not text:
        return 0.0
    c = color or col("cream")
    f = font or th.title(size)
    lines = draw.wrap(d, text, f, max_w)
    lh = int(round(size * line_gap * th._s))
    for i, ln in enumerate(lines):
        yy = y + i * lh
        if align == "center":
            draw.draw_tracked(d, (x, yy), ln, f, with_alpha(c, alpha),
                              tracking=0.4, anchor="ma")
        else:
            draw.draw_tracked(d, (x, yy), ln, f, with_alpha(c, alpha), tracking=0.3)
    return len(lines) * lh


def body_text(d: ImageDraw.ImageDraw, th: Theme, x: float, y: float, text: str,
              max_w: float, size: int = 30, color=None, align: str = "left",
              line_gap: float = 1.42, alpha: float = 1.0) -> float:
    if not text:
        return 0.0
    c = color or col("cream")
    f = th.body(size)
    lines = draw.wrap(d, text, f, max_w)
    lh = int(round(size * line_gap * th._s))
    for i, ln in enumerate(lines):
        p = (x, y + i * lh)
        if align == "center":
            draw.draw_tracked(d, p, ln, f, with_alpha(c, alpha), tracking=0.3, anchor="ma")
        else:
            draw.draw_tracked(d, p, ln, f, with_alpha(c, alpha), tracking=0.2)
    return len(lines) * lh


def rule(d: ImageDraw.ImageDraw, th: Theme, x: float, y: float, w: float,
         color=None, thickness: Optional[int] = None, progress: float = 1.0) -> None:
    """A gold rule that can draw itself on (progress 0→1)."""
    if progress <= 0:
        return
    c = color or col("gold_500")
    t = thickness or max(2, int(round(2.5 * th._s)))
    wid = w * max(0.0, min(1.0, progress))
    d.rectangle([x, y, x + wid, y + t], fill=c + (255,))


def panel(d: ImageDraw.ImageDraw, th: Theme, box: Tuple[float, float, float, float],
          fill=None, outline=None, alpha: int = 210, radius: Optional[int] = None,
          width: int = 1) -> None:
    x0, y0, x1, y1 = box
    r = radius if radius is not None else th.sp(2)
    if fill is not None:
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill + (alpha,))
    if outline is not None:
        d.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=outline + (255,),
                            width=width)


def accent_bar(d: ImageDraw.ImageDraw, th: Theme, x: float, y: float, h: float,
               color=None, w: Optional[int] = None) -> None:
    c = color or col("gold_500")
    d.rectangle([x, y, x + (w or th.sp(0.7)), y + h], fill=c + (255,))


def badge(d: ImageDraw.ImageDraw, th: Theme, cx: float, cy: float, r: float,
          label: str, fill=None, text_color=None, font=None) -> None:
    """A circular numbered/lettered badge used by lists and processes."""
    c = fill or col("gold_500")
    tc = text_color or col("navy_900")
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (255,))
    f = font or th.ui_bold(26)
    draw.draw_tracked(d, (cx, cy), label, f, tc + (255,), tracking=0.0, anchor="mm")


def chip(d: ImageDraw.ImageDraw, th: Theme, x: float, y: float, text: str,
         fill=None, text_color=None, pad: Optional[int] = None) -> Tuple[float, float]:
    """A small pill label (e.g. evidence class, risk tag). Returns (w, h)."""
    f = th.ui_bold(21)
    pad = pad if pad is not None else th.sp(2)
    tw = draw.text_width(d, text.upper(), f, tracking=1.0)
    h = th.sp(4.6)
    w = tw + pad * 2
    d.rounded_rectangle([x, y, x + w, y + h], radius=h / 2.0,
                        fill=(fill or col("gold_500")) + (235,))
    draw.draw_tracked(d, (x + pad, y + h * 0.26), text.upper(), f,
                      (text_color or col("navy_900")) + (255,), tracking=1.0)
    return (w, h)


def logo_lockup(img: Image.Image, th: Theme, x: float, y: float,
                firm: str, logo_path: Optional[str] = None,
                max_h: Optional[int] = None, color=None,
                alpha: float = 1.0) -> Tuple[float, float]:
    """Draw the firm mark (real logo if supplied, else a type lockup).

    Returns the (width, height) consumed so callers can place other elements.
    """
    mh = max_h or th.sp(14)
    c = color or col("cream")
    if logo_path and os.path.isfile(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            scale = mh / float(logo.height)
            logo = logo.resize((max(1, int(logo.width * scale)), mh), Image.LANCZOS)
            if alpha < 0.999:
                a = logo.split()[3].point(lambda v: int(v * alpha))
                logo.putalpha(a)
            img.paste(logo, (int(x), int(y)), logo)
            return (logo.width, logo.height)
        except Exception:
            pass
    # Typographic lockup: a gold square mark + firm name.
    m = int(mh * 0.78)
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([x, y + (mh - m) / 2, x + m, y + (mh + m) / 2],
                outline=col("gold_500") + (255,), width=max(2, int(2 * th._s)))
    d.rectangle([x + m * 0.44, y + (mh - m) / 2 + m * 0.44, x + m, y + (mh + m) / 2],
                fill=col("gold_500") + (255,))
    f = th.ui_bold(int(round(mh * 0.46 / max(0.2, th._s))))
    tw = draw.text_width(d, firm, f, tracking=th.sp(0.3))
    draw.draw_tracked(d, (x + m + th.sp(2), y + mh / 2.0), firm, f,
                      with_alpha(c, alpha), tracking=th.sp(0.3), anchor="lm")
    return (m + th.sp(2) + tw, mh)


def centered_lockup(img: Image.Image, th: Theme, cx: float, y: float, firm: str,
                    logo_path: Optional[str] = None, max_h: Optional[int] = None,
                    color=None, alpha: float = 1.0) -> Tuple[float, float]:
    """Draw a logo/type lockup horizontally centred on ``cx``.

    The lockup is rendered onto a transparent layer first so it can be measured,
    then composited once — no double drawing.
    """
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    w, h = logo_lockup(layer, th, 0, 0, firm, logo_path, max_h=max_h,
                       color=color, alpha=alpha)
    if w <= 0:
        return (0.0, 0.0)
    crop = layer.crop((0, 0, max(1, int(w) + th.sp(1)), max(1, int(h) + th.sp(1))))
    x = int(round(cx - crop.width / 2.0))
    img.paste(crop, (x, int(round(y))), crop)
    return (float(crop.width), float(crop.height))


# ------------------------------------------------------------------ icon set
def _stroke(d, pts, color, width, joint="curve"):
    d.line(pts, fill=color, width=width, joint=joint)


def icon(d: ImageDraw.ImageDraw, th: Theme, name: str, box: Tuple[float, float, float, float],
         color=None, width: Optional[int] = None) -> None:
    """Draw a stroke line-icon into ``box`` (x0, y0, x1, y1).

    These are drawn with vector primitives rather than emoji or raster art, so
    they stay crisp at 1920x1080 and inherit the palette.
    """
    c = (color or col("gold_500")) + (255,)
    x0, y0, x1, y1 = box
    s = min(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lw = width or max(2, int(round(s * 0.055)))
    fn = _ICONS.get(name, _icon_dot)
    fn(d, cx, cy, s, c, lw)


def _icon_dot(d, cx, cy, s, c, lw):
    r = s * 0.10
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)


def _icon_scales(d, cx, cy, s, c, lw):
    d.line([cx, cy - s * 0.42, cx, cy + s * 0.40], fill=c, width=lw)
    d.line([cx - s * 0.34, cy - s * 0.30, cx + s * 0.34, cy - s * 0.30], fill=c, width=lw)
    for side in (-1, 1):
        px = cx + side * s * 0.30
        d.line([cx, cy - s * 0.30, px, cy - s * 0.12], fill=c, width=lw)
        d.polygon([(px - s * 0.10, cy - s * 0.12), (px + s * 0.10, cy - s * 0.12),
                   (px, cy + s * 0.08)], outline=c, fill=None)
        d.line([(px - s * 0.10, cy - s * 0.12), (px + s * 0.10, cy - s * 0.12),
                (px, cy + s * 0.08), (px - s * 0.10, cy - s * 0.12)], fill=c, width=lw)
    d.line([cx - s * 0.16, cy + s * 0.40, cx + s * 0.16, cy + s * 0.40], fill=c, width=lw)


def _icon_document(d, cx, cy, s, c, lw):
    w, h = s * 0.46, s * 0.60
    d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2],
                        radius=s * 0.05, outline=c, width=lw)
    for i in range(3):
        yy = cy - h * 0.18 + i * h * 0.20
        d.line([cx - w * 0.28, yy, cx + w * (0.28 if i != 2 else 0.02), yy], fill=c, width=lw)


def _icon_shield(d, cx, cy, s, c, lw):
    pts = [(cx, cy - s * 0.42), (cx + s * 0.32, cy - s * 0.26),
           (cx + s * 0.32, cy + s * 0.10), (cx, cy + s * 0.44),
           (cx - s * 0.32, cy + s * 0.10), (cx - s * 0.32, cy - s * 0.26),
           (cx, cy - s * 0.42)]
    d.line(pts, fill=c, width=lw, joint="curve")


def _icon_briefcase(d, cx, cy, s, c, lw):
    w, h = s * 0.62, s * 0.40
    d.rounded_rectangle([cx - w / 2, cy - h * 0.2, cx + w / 2, cy + h * 0.7],
                        radius=s * 0.05, outline=c, width=lw)
    d.line([cx - s * 0.14, cy - h * 0.2, cx - s * 0.14, cy - h * 0.36,
            cx + s * 0.14, cy - h * 0.36, cx + s * 0.14, cy - h * 0.2], fill=c, width=lw)
    d.line([cx - w / 2, cy + h * 0.16, cx + w / 2, cy + h * 0.16], fill=c, width=lw)


def _icon_building(d, cx, cy, s, c, lw):
    w, h = s * 0.46, s * 0.62
    d.rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], outline=c, width=lw)
    for r in range(3):
        for k in range(2):
            wx = cx - w * 0.26 + k * w * 0.30
            wy = cy - h * 0.30 + r * h * 0.24
            d.rectangle([wx, wy, wx + w * 0.16, wy + h * 0.12], fill=c)


def _icon_clock(d, cx, cy, s, c, lw):
    r = s * 0.36
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=c, width=lw)
    d.line([cx, cy - r * 0.55, cx, cy, cx + r * 0.42, cy + r * 0.18], fill=c, width=lw)


def _icon_check(d, cx, cy, s, c, lw):
    d.line([cx - s * 0.30, cy + s * 0.02, cx - s * 0.08, cy + s * 0.24,
            cx + s * 0.32, cy - s * 0.24], fill=c, width=lw)


def _icon_arrow(d, cx, cy, s, c, lw):
    d.line([cx - s * 0.36, cy, cx + s * 0.30, cy], fill=c, width=lw)
    d.line([cx + s * 0.12, cy - s * 0.18, cx + s * 0.30, cy, cx + s * 0.12, cy + s * 0.18],
           fill=c, width=lw)


def _icon_growth(d, cx, cy, s, c, lw):
    d.line([cx - s * 0.36, cy + s * 0.30, cx + s * 0.36, cy + s * 0.30], fill=c, width=lw)
    base = cy + s * 0.30
    for i, hf in enumerate((0.30, 0.52, 0.78)):
        bx = cx - s * 0.30 + i * s * 0.22
        bh = s * hf
        d.rectangle([bx, base - bh, bx + s * 0.14, base], fill=c)


def _icon_network(d, cx, cy, s, c, lw):
    r = s * 0.07
    for ang in range(0, 360, 60):
        px = cx + math.cos(math.radians(ang)) * s * 0.30
        py = cy + math.sin(math.radians(ang)) * s * 0.30
        d.line([cx, cy, px, py], fill=c, width=lw)
        d.ellipse([px - r, py - r, px + r, py + r], fill=c)
    d.ellipse([cx - r * 1.3, cy - r * 1.3, cx + r * 1.3, cy + r * 1.3], fill=c)


def _icon_lock(d, cx, cy, s, c, lw):
    w, h = s * 0.48, s * 0.36
    d.rounded_rectangle([cx - w / 2, cy - h * 0.1, cx + w / 2, cy + h * 0.8],
                        radius=s * 0.05, outline=c, width=lw)
    d.arc([cx - w * 0.32, cy - h * 0.72, cx + w * 0.32, cy + h * 0.24],
          180, 360, fill=c, width=lw)


def _icon_handshake(d, cx, cy, s, c, lw):
    d.line([cx - s * 0.38, cy - s * 0.06, cx - s * 0.10, cy - s * 0.06,
            cx + s * 0.06, cy + s * 0.08], fill=c, width=lw, joint="curve")
    d.line([cx + s * 0.38, cy - s * 0.06, cx + s * 0.10, cy - s * 0.06,
            cx - s * 0.06, cy + s * 0.08], fill=c, width=lw, joint="curve")


def _icon_megaphone(d, cx, cy, s, c, lw):
    d.polygon([(cx - s * 0.10, cy - s * 0.10), (cx + s * 0.30, cy - s * 0.30),
               (cx + s * 0.30, cy + s * 0.30), (cx - s * 0.10, cy + s * 0.10)],
              outline=c, fill=None)
    d.line([(cx - s * 0.10, cy - s * 0.10), (cx - s * 0.10, cy + s * 0.10),
            (cx + s * 0.30, cy + s * 0.30)], fill=c, width=lw)
    d.line([cx - s * 0.30, cy - s * 0.06, cx - s * 0.30, cy + s * 0.06], fill=c, width=lw)


_ICONS = {
    "scales": _icon_scales, "document": _icon_document, "shield": _icon_shield,
    "briefcase": _icon_briefcase, "building": _icon_building, "clock": _icon_clock,
    "check": _icon_check, "arrow": _icon_arrow, "growth": _icon_growth,
    "network": _icon_network, "lock": _icon_lock, "handshake": _icon_handshake,
    "megaphone": _icon_megaphone, "dot": _icon_dot,
}


def icon_for_key(key: str) -> str:
    """Map a storyboard scene key to a meaningful icon name."""
    return {
        "hook": "megaphone", "origin": "clock", "practice": "briefcase",
        "achievements": "growth", "people": "handshake", "office": "building",
        "closing": "scales",
    }.get((key or "").lower(), "document")


# ------------------------------------------------------------------ svg path
def svg_available() -> Tuple[bool, str]:
    """Report whether a true SVG rasteriser exists on this machine.

    Pillow cannot parse SVG. We therefore *report honestly* rather than pretend:
    the built-in vector art is drawn with Pillow primitives (crisp at any
    resolution), and a real SVG file is only used when a rasteriser is present.
    """
    try:
        import cairosvg  # noqa: F401
        return True, "cairosvg"
    except Exception:
        pass
    import shutil
    for binname in ("rsvg-convert", "inkscape", "resvg"):
        if shutil.which(binname):
            return True, binname
    return False, "no SVG rasteriser (cairosvg / rsvg-convert / inkscape / resvg) found"


def rasterize_svg(path: str, width: int, height: int) -> Tuple[Optional[Image.Image], str]:
    """Rasterise an SVG to RGBA at the target size, or return (None, reason)."""
    ok, engine = svg_available()
    if not ok:
        return None, engine
    try:
        if engine == "cairosvg":
            import io
            import cairosvg
            png = cairosvg.svg2png(url=path, output_width=width, output_height=height)
            return Image.open(io.BytesIO(png)).convert("RGBA"), "cairosvg"
        import subprocess
        if engine == "rsvg-convert":
            out = subprocess.run(["rsvg-convert", "-w", str(width), "-h", str(height), path],
                                 capture_output=True, timeout=60)
        elif engine == "resvg":
            out = subprocess.run(["resvg", "--width", str(width), "--height", str(height),
                                  path, "-"], capture_output=True, timeout=60)
        else:  # inkscape
            out = subprocess.run(["inkscape", path, "-w", str(width), "-h", str(height),
                                  "--export-type=png", "-"], capture_output=True, timeout=120)
        if out.returncode == 0 and out.stdout:
            import io
            return Image.open(io.BytesIO(out.stdout)).convert("RGBA"), engine
        return None, "%s failed: %s" % (engine, out.stderr.decode("utf-8", "ignore")[:200])
    except Exception as exc:  # pragma: no cover - environment dependent
        return None, "%s error: %s" % (engine, exc)
