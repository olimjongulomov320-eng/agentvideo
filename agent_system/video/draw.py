# -*- coding: utf-8 -*-
"""video/draw.py — resolution-independent drawing helpers (Pillow).

Used by the *motion* and *illustrated* backends. No text is ever rendered by
ffmpeg (this ffmpeg build has no drawtext/libfreetype), so all typography is
drawn here — which also keeps the look identical across resolutions.

Everything is expressed in "1080-space": a :class:`FontBook` built for a given
canvas height scales every size, so a 1920x1080 final and a 960x540 preview
share one design language instead of being two different looks.

The visual design *system* (palette, grid, compositions) lives in
``design.py``; this module only provides the low-level drawing primitives.
"""
import math
import os
from typing import List, Optional, Sequence, Tuple

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

# ---------------------------------------------------------------- brand palette
# Kept for backward compatibility; ``design.PALETTE`` is the canonical source.
DARK = (14, 45, 62)        # #0e2d3e
DARKER = (8, 27, 38)
NAVY = (23, 67, 90)        # #17435a
GOLD = (201, 169, 110)     # #c9a96e
GOLD_L = (232, 201, 138)   # #e8c98a
CREAM = (248, 246, 241)    # #f8f6f1
INK = (31, 41, 55)

_SERIF_DIRS = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts",
               "/Library/Fonts", "/usr/share/fonts", "/usr/local/share/fonts"]
_SERIF = ["Georgia.ttf", "Times New Roman.ttf", "DejaVuSerif.ttf"]
_SERIF_B = ["Georgia Bold.ttf", "Times New Roman Bold.ttf", "DejaVuSerif-Bold.ttf"]
_SANS = ["HelveticaNeue.ttc", "Helvetica.ttc", "SFNS.ttf", "Arial.ttf",
         "DejaVuSans.ttf"]
_SANS_B = ["HelveticaNeue.ttc", "Helvetica.ttc", "Arial Bold.ttf",
           "DejaVuSans-Bold.ttf"]


def _first_existing(candidates: Sequence[str]) -> Optional[str]:
    for d in _SERIF_DIRS:
        for n in candidates:
            p = os.path.join(d, n)
            if os.path.isfile(p):
                return p
    return None


class FontBook(object):
    """Caches fonts at a requested pixel size, scaled for the render height.

    Sizes are always given in 1080-space; the book multiplies by
    ``base_height / 1080`` so the same call produces the same *relative* size at
    any output resolution.
    """

    def __init__(self, base_height: int = 1080):
        self.base_height = base_height
        self.scale = max(0.15, base_height / 1080.0)
        self.serif = _first_existing(_SERIF)
        self.serif_bold = _first_existing(_SERIF_B) or self.serif
        self.sans = _first_existing(_SANS)
        self.sans_bold = _first_existing(_SANS_B) or self.sans
        self._cache = {}

    # -- internals ----------------------------------------------------------
    def _load(self, path: Optional[str], size: int, index: int = 0):
        px = max(6, int(round(size * self.scale)))
        key = (path, px, index)
        if key in self._cache:
            return self._cache[key]
        font = None
        if path:
            for idx in (index, 0):
                try:
                    font = ImageFont.truetype(path, px, index=idx)
                    break
                except Exception:
                    font = None
        if font is None:
            try:
                font = ImageFont.load_default()
            except Exception:
                font = None
        self._cache[key] = font
        return font

    def metrics(self, font) -> Tuple[int, int]:
        """(ascent, descent) in pixels for a loaded font."""
        try:
            a, d = font.getmetrics()
            return int(a), int(d)
        except Exception:
            size = getattr(font, "size", 20) or 20
            return int(size * 0.8), int(size * 0.25)

    # -- typed accessors (1080-space sizes) ---------------------------------
    def display(self, size: int = 96, weight: str = "bold"):
        if weight == "regular":
            return self._load(self.serif, size)
        if weight == "semibold":
            return self._load(self.sans_bold or self.serif_bold, size, index=1)
        return self._load(self.serif_bold or self.serif, size)

    def serif_regular(self, size: int = 48):
        return self._load(self.serif, size)

    def serif_medium(self, size: int = 40):
        return self._load(self.serif_bold or self.serif, size)

    def label(self, size: int = 26):
        return self._load(self.sans, size)

    def label_bold(self, size: int = 26):
        return self._load(self.sans_bold or self.sans, size, index=1)

    # Optional _load-miss: keep a stable fallback name for callers.
    def sans_regular(self, size: int = 26):
        return self._load(self.sans, size)


# ---------------------------------------------------------------- backgrounds
def gradient(size: Tuple[int, int], c1=(8, 27, 38), c2=(23, 67, 90),
             vertical: bool = True) -> Image.Image:
    """Linear gradient. numpy-accelerated when available, else scanline loop."""
    w, h = size
    try:
        import numpy as np
        n = h if vertical else w
        t = np.linspace(0.0, 1.0, n, dtype="float32")
        a = np.array(c1, dtype="float32")
        b = np.array(c2, dtype="float32")
        ramp = (a[None, :] + (b - a)[None, :] * t[:, None]).astype("uint8")
        if vertical:
            arr = np.repeat(ramp[:, None, :], w, axis=1)
        else:
            arr = np.repeat(ramp[None, :, :], h, axis=0)
        return Image.fromarray(arr, "RGB")
    except Exception:
        base = Image.new("RGB", (w, h), c1)
        top = Image.new("RGB", (w, h), c2)
        mask = Image.new("L", (w, h))
        md = ImageDraw.Draw(mask)
        if vertical:
            for y in range(h):
                md.line([(0, y), (w, y)], fill=int(255 * (y / max(1, h - 1))))
        else:
            for x in range(w):
                md.line([(x, 0), (x, h)], fill=int(255 * (x / max(1, w - 1))))
        return Image.composite(top, base, mask)


def glow(img: Image.Image, center: Tuple[float, float], radius: float,
         color=GOLD, alpha: int = 40) -> Image.Image:
    w, h = img.size
    layer = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(layer)
    cx, cy = center
    d.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=alpha)
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.55))
    tint = Image.new("RGB", (w, h), color)
    return Image.composite(tint, img, layer)


def vignette(img: Image.Image, strength: float = 0.34) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([-w * 0.32, -h * 0.5, w * 1.32, h * 1.5], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(40, w * 0.18)))
    dark = ImageEnhance.Brightness(img).enhance(1.0 - strength)
    return Image.composite(img, dark, mask)


def grain(img: Image.Image, amount: float = 4.0) -> Image.Image:
    w, h = img.size
    noise = Image.effect_noise((w, h), 90).convert("L")
    noise = noise.point(lambda v: 128 + (v - 128) * (amount / 100.0))
    return Image.blend(img, noise.convert("RGB"), 0.045)


def cover(img: Image.Image, size: Tuple[int, int], anchor_y: float = 0.4) -> Image.Image:
    """Scale-to-cover without distortion (LANCZOS), then centre-crop."""
    tw, th = size
    w, h = img.size
    if w == 0 or h == 0:
        return Image.new("RGB", size, DARK)
    s = max(tw / float(w), th / float(h))
    nw, nh = max(1, int(math.ceil(w * s))), max(1, int(math.ceil(h * s)))
    img = img.resize((nw, nh), Image.LANCZOS)
    left = max(0, (nw - tw) // 2)
    top = max(0, min(int((nh - th) * anchor_y), nh - th))
    return img.crop((left, top, left + tw, top + th))


# ---------------------------------------------------------------- text
def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: float) -> List[str]:
    words = (text or "").split()
    lines, cur = [], ""
    for wd in words:
        trial = (cur + " " + wd).strip()
        try:
            wpx = draw.textlength(trial, font=font)
        except Exception:
            wpx = len(trial) * (font.size * 0.5 if hasattr(font, "size") else 8)
        if wpx <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def text_width(draw: ImageDraw.ImageDraw, text: str, font, tracking: float = 0.0) -> float:
    if not text:
        return 0.0
    w = 0.0
    for ch in text:
        try:
            w += draw.textlength(ch, font=font)
        except Exception:
            w += 10
        w += tracking
    return w - tracking


def _vertical_offset(draw: ImageDraw.ImageDraw, text: str, font, anchor: str) -> float:
    """Extra y shift so ``anchor`` can be 'lm'/'mm'/'rm' (vertical middle)."""
    if not anchor or anchor[-1] != "m":
        return 0.0
    try:
        a, dsc = font.getmetrics()
        return -(a + dsc / 2.0)
    except Exception:
        size = getattr(font, "size", 20) or 20
        return -(size * 0.6)


def draw_tracked(draw: ImageDraw.ImageDraw, xy: Tuple[float, float], text: str, font,
                 fill, tracking: float = 0.0, anchor: str = "la") -> None:
    """Draw letter-spaced text. Supports horizontal l/c/m/r and vertical m."""
    if not text:
        return
    x, y = xy
    y += _vertical_offset(draw, text, font, anchor)
    total = text_width(draw, text, font, tracking)
    ha = anchor[0] if anchor else "l"
    if ha in ("c", "m"):
        x = x - total / 2.0
    elif ha == "r":
        x = x - total
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        try:
            x += draw.textlength(ch, font=font)
        except Exception:
            x += 10
        x += tracking


# ---------------------------------------------------------------- animation
def ease_in(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return t * t * t


def ease_in_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 4 * t * t * t if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2.0


def ease_out(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1 - pow(1 - t, 3)


def ease_out_back(t: float, overshoot: float = 1.2) -> float:
    """Slight overshoot for confident, intentional entrances."""
    t = max(0.0, min(1.0, t))
    c = overshoot
    return 1 + (c + 1) * pow(t - 1, 3) + c * pow(t - 1, 2)


def ramp(t: float, start: float, dur: float) -> float:
    """0→1 progress of an element that starts at *start* and takes *dur* seconds."""
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return max(0.0, min(1.0, (t - start) / dur))


def scene_alpha(t: float, dur: float, fade_in: float = 0.45,
                fade_out: float = 0.45) -> float:
    """Alpha ramp used to build transitions inside the frame renderer."""
    a = 1.0
    if t < fade_in:
        a = min(a, t / fade_in if fade_in > 0 else 1.0)
    if dur - t < fade_out:
        a = min(a, (dur - t) / fade_out if fade_out > 0 else 1.0)
    return max(0.0, min(1.0, a))


# ---------------------------------------------------------------- components
def lower_third(img: Image.Image, fb: FontBook, title: str, subtitle: str = "",
                progress: float = 1.0, accent=GOLD) -> None:
    """Draw a lower-third bar that slides in with *progress* 0→1."""
    if progress <= 0:
        return
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    bar_h = int(h * 0.135)
    y = int(h * 0.70)
    slide = (1.0 - ease_out(progress))
    x0 = int(-w * 0.42 * slide)
    d.rectangle([x0, y, w, y + bar_h], fill=(8, 27, 38, 205))
    d.rectangle([w - 8, y, w, y + bar_h], fill=accent + (255,))
    draw_tracked(d, (w * 0.06 + x0, y + int(bar_h * 0.18)), title.upper(),
                 fb.label(30), CREAM, tracking=2.0)
    if subtitle:
        d.text((w * 0.06 + x0, y + int(bar_h * 0.56)), subtitle, font=fb.serif_regular(30),
               fill=GOLD_L)


def watermark(img: Image.Image, fb: FontBook, text: str = "DEMO / CONCEPT PREVIEW") -> None:
    """Stamp the demo label so previews can never be mistaken for finals."""
    if not text:
        return
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    font = fb.label(22)
    tw = text_width(d, text, font, 1.5)
    x = w - tw - int(w * 0.03)
    y = int(h * 0.032)
    d.rectangle([x - 14, y - 8, x + tw + 14, y + 34], fill=(0, 0, 0, 110))
    draw_tracked(d, (x, y), text, font, (255, 235, 205, 235), tracking=1.5)


def end_card(img: Image.Image, fb: FontBook, firm: str, line: str = "",
             logo_path: Optional[str] = None) -> None:
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 0, w, h], fill=CREAM + (255,))
    if logo_path and os.path.isfile(logo_path):
        try:
            logo = Image.open(logo_path).convert("RGBA")
            scale = min(w * 0.34 / logo.width, h * 0.3 / logo.height)
            logo = logo.resize((max(1, int(logo.width * scale)),
                                max(1, int(logo.height * scale))), Image.LANCZOS)
            img.paste(logo, ((w - logo.width) // 2, int(h * 0.30)), logo)
        except Exception:
            pass
    else:
        draw_tracked(d, (w / 2, h * 0.34), firm, fb.display(78), DARK,
                     tracking=1.0, anchor="ca")
    if line:
        draw_tracked(d, (w / 2, h * 0.62), line, fb.label(30), NAVY, tracking=2.0, anchor="ca")
    d.rectangle([w * 0.44, h * 0.585, w * 0.56, h * 0.585 + 2], fill=GOLD + (255,))


def apply_alpha(img: Image.Image, alpha: float) -> Image.Image:
    """Fade a frame toward black (used for scene transitions)."""
    if alpha >= 0.999:
        return img
    if alpha <= 0.001:
        return Image.new("RGB", img.size, (0, 0, 0))
    return ImageEnhance.Brightness(img).enhance(max(0.0, alpha))
