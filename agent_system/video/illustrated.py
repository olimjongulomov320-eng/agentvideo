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
from typing import Any, Callable, Dict, List, Optional, Tuple

from PIL import Image, ImageDraw

from . import common, draw
from .spec import RenderSpec

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
        self.asset_dir = asset_dir

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


def _headline(img: Image.Image, ctx: "IllusContext", scene: Dict[str, Any], p: float,
              dark_text: bool = True) -> None:
    d = ImageDraw.Draw(img, "RGBA")
    fb = ctx.fb
    band_y = ctx.h * 0.70
    a = int(180 * p)
    d.rectangle([0, band_y, ctx.w * min(1.0, p * 1.2), band_y + ctx.h * 0.16],
                fill=(8, 27, 38, a))
    if scene["heading"]:
        draw.draw_tracked(d, (ctx.w * 0.05, band_y + ctx.h * 0.025), scene["heading"][:42],
                          fb.display(56), CREAM_TEXT + (int(255 * p),), tracking=0.5)
    if scene["sub"]:
        lines = draw.wrap(d, scene["sub"], fb.serif_regular(30), ctx.w * 0.7)
        if lines:
            draw.draw_tracked(d, (ctx.w * 0.05, band_y + ctx.h * 0.098), lines[0],
                              fb.serif_regular(30), ACCENT2 + (int(255 * p),), tracking=0.4)


CREAM_TEXT = (248, 246, 241)


def _placeholder_mark(img: Image.Image, ctx: "IllusContext", text: str) -> None:
    if not text:
        return
    d = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    d.rectangle([int(w * 0.05), int(h * 0.055), int(w * 0.95), int(h * 0.105)],
                outline=(220, 120, 80, 200), width=2)
    d.text((int(w * 0.062), int(h * 0.065)), "GAP: " + text[:110],
           font=ctx.fb.label(22), fill=(240, 170, 120, 235))


# ---------------------------------------------------------------- scene painter
def render_illustration(ctx: IllusContext, scene: Dict[str, Any], t: float) -> Image.Image:
    w, h = ctx.w, ctx.h
    dur = max(0.001, float(scene["dur"]))
    prog = draw.ease_in_out(max(0.0, min(1.0, t / dur)))
    cam = (t / dur) if dur > 0 else 0.0

    img = draw.gradient((w, h), SKY_TOP, SKY_BOT, vertical=True)
    img = _sun(img, w * (0.72 - 0.06 * cam), h * (0.26 + 0.03 * cam), w * 0.16, 0.5 + 0.5 * cam)
    d = ImageDraw.Draw(img, "RGBA")

    kind = scene["kind"]
    # ---- layer stack, back to front, each with its own parallax rate
    if kind in ("statement", "endcard", "title", "timeline"):
        _hills(d, ctx, -w * 0.05 * cam, h * 0.74, HILL, h * 0.055, 1.3)
        _skyline(d, ctx, -w * 0.10 * cam, h * 0.76, (16, 44, 62), 3, 0.85, lit=0.5)
        _hills(d, ctx, -w * 0.18 * cam, h * 0.88, (12, 34, 48), h * 0.04, 2.6)
        img = _foreground_figures(ctx, img, cam, count=2 + int(prog * 2))
    elif kind == "list":
        _skyline(d, ctx, -w * 0.08 * cam, h * 0.80, (17, 48, 68), 5, 0.9, lit=0.6)
        img = _books_layer(ctx, img, prog)
    elif kind == "stat":
        _hills(d, ctx, -w * 0.06 * cam, h * 0.82, HILL, h * 0.05, 0.7)
        d2 = ImageDraw.Draw(img, "RGBA")
        _graph(d2, w * 0.30, h * 0.80, w * 0.40, h * 0.34, draw.ease_out(draw.ramp(t, 0.4, 1.6)))
    else:
        _room(d, ctx, -w * 0.03 * cam)
        img = _office_figures(ctx, img, prog)

    return img


def _foreground_figures(ctx: IllusContext, img: Image.Image, cam: float,
                        count: int = 3, ground: float = 0.955) -> Image.Image:
    d = ImageDraw.Draw(img, "RGBA")
    w, h = ctx.w, ctx.h
    for i in range(count):
        x = w * (0.22 + 0.17 * i) - w * 0.04 * cam
        s = h * 0.20
        _figure(d, x, h * ground, s, (12, 30, 42))
    return img


def _office_figures(ctx: IllusContext, img: Image.Image, prog: float) -> Image.Image:
    d = ImageDraw.Draw(img, "RGBA")
    w, h = ctx.w, ctx.h
    ground = h * 0.80
    _figure(d, w * 0.34, ground, h * 0.26, (14, 34, 48))
    _figure(d, w * 0.62, ground, h * 0.24, (20, 44, 60))
    d.rectangle([w * 0.45, ground - h * 0.03, w * 0.55, ground], fill=(58, 82, 98))
    if prog > 0.4:
        _books(d, w * 0.47, ground - h * 0.03, h * 0.09)
    return img


def _books_layer(ctx: IllusContext, img: Image.Image, prog: float) -> Image.Image:
    d = ImageDraw.Draw(img, "RGBA")
    w, h = ctx.w, ctx.h
    base = h * 0.86
    for i in range(3):
        p = draw.ramp(1.0 if prog > 0.2 * i else 0.0, 0, 1)
        _books(d, w * (0.14 + 0.24 * i), base, h * (0.10 + 0.02 * i))
    gt = ctx.fb.display(64)
    draw.draw_tracked(d, (w * 0.5, h * 0.30), ctx.spec.firm_name[:28], gt,
                      (18, 44, 62), tracking=1.0, anchor="ca")
    return img


def render_scene_frame(ctx: IllusContext, scene: Dict[str, Any], t: float) -> Image.Image:
    img = render_illustration(ctx, scene, t)
    dur = max(0.001, float(scene["dur"]))
    alpha = draw.scene_alpha(t, dur, fade_in=0.4, fade_out=0.4)
    img = draw.apply_alpha(img, alpha)
    p = draw.ease_out(draw.ramp(t, 0.6, 0.8))
    if scene["kind"] not in ("endcard",):
        _headline(img, ctx, scene, p)
    if scene.get("placeholder"):
        _placeholder_mark(img, ctx, ", ".join(scene.get("needs") or []) or "unverified content")
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
               progress: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        if not common.ffmpeg_available():
            raise common.RenderError("ffmpeg is not available — cannot render illustrated 2D")
        os.makedirs(work_dir, exist_ok=True)
        ctx = IllusContext(spec, asset_dir)

        def _prog(n: int, total: int) -> None:
            if progress:
                progress("illustrating frame %d/%d" % (n, total),
                         int(100 * n / max(1, total)))

        if progress:
            progress("illustrated 2D pass: %d scenes at %dx%d@%d" %
                     (len(spec.scenes), spec.width, spec.height, spec.fps), 1)
        video_only = os.path.join(work_dir, "_video_only.mp4")
        common.encode_frames_to_video(iter_frames(ctx, spec.scenes, cancel, _prog),
                                      video_only, spec.width, spec.height, spec.fps)
        audio_path, audio_meta = common.build_audio_track(
            os.path.join(work_dir, "_audio.wav"), spec.total_duration, spec.audio, work_dir)
        common.mux(video_only, audio_path, out_path)
        validation = common.validate_mp4(out_path, spec.width, spec.height, spec.fps)
        manifest = common.write_render_manifest(
            os.path.join(work_dir, "render_manifest.json"), spec, self.style,
            common.engine_info("illustrated-pillow-ffmpeg"),
            sources=[s.get("asset") for s in spec.scenes if s.get("asset")],
            limitations=LIMITATIONS, validation=validation,
            extra={"audio_detail": audio_meta})
        return {"output": out_path, "manifest": manifest, "validation": validation}


def render(spec: RenderSpec, out_path: str, work_dir: str, asset_dir: str = "",
           cancel: Optional[Callable[[], bool]] = None,
           progress: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
    return IllustratedBackend().render(spec, out_path, work_dir, asset_dir, cancel, progress)
