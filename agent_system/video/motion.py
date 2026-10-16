# -*- coding: utf-8 -*-
"""video/motion.py — Motion Graphics backend (2D corporate/legal).

Implements: animated typography, date/timeline elements, logo reveal, slow
push-in, progressive line/shape drawing, photo documentary scenes with a
lower third, captions and an end card. Transitions are real crossfades computed
in the frame renderer.

All typography is drawn with Pillow (this ffmpeg has no drawtext), then the
frame stream is piped to ffmpeg as rawvideo.
"""
import os
from typing import Any, Callable, Dict, List, Optional

from PIL import Image, ImageDraw

from . import common, draw
from .spec import RenderSpec

LIMITATIONS = [
    "Transitions between scenes are crossfades computed in the frame renderer.",
    "Parallax is simulated by counter-moving layers, not by true depth maps.",
    "No licensed music is bundled; audio defaults to a synthesized pad (labelled).",
    "The DEMO / CONCEPT PREVIEW watermark is stamped on every preview frame.",
]


class MotionContext(object):
    def __init__(self, spec: RenderSpec, asset_dir: str = ""):
        self.spec = spec
        self.w, self.h = spec.width, spec.height
        self.fb = draw.FontBook(self.h)
        self.asset_dir = asset_dir
        self.logo = self._find_logo()

    def _find_logo(self) -> Optional[str]:
        for cand in ("logo-full.png", "logo.png", "logo-shield.png"):
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


# ---------------------------------------------------------------- scene painters
def _base(ctx: MotionContext, variant: int = 0) -> Image.Image:
    c1, c2 = (draw.DARKER, draw.NAVY) if variant % 2 == 0 else ((6, 22, 32), (17, 52, 71))
    img = draw.gradient((ctx.w, ctx.h), c1, c2, vertical=True)
    img = draw.glow(img, (ctx.w * 0.5, -ctx.h * 0.15), ctx.w * 0.42, draw.GOLD, 34)
    return img


def _placeholder_mark(img: Image.Image, fb: draw.FontBook, text: str) -> None:
    """Draw an unmistakable gap marker on scenes with missing evidence."""
    if not text:
        return
    w, h = img.size
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([int(w * 0.06), int(h * 0.80), int(w * 0.94), int(h * 0.88)],
                outline=(220, 120, 80, 200), width=2)
    d.text((int(w * 0.075), int(h * 0.815)), "GAP: " + text[:110],
           font=fb.label(24), fill=(240, 170, 120, 235))


def _statement(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    img = _base(ctx, 0)
    d = ImageDraw.Draw(img, "RGBA")
    fb = ctx.fb
    p = draw.ease_out(draw.ramp(t, 0.35, 1.1))
    big = fb.display(84)
    lines = draw.wrap(d, scene["heading"] or scene["narration"], big, ctx.w * 0.78)
    total_h = len(lines) * int(ctx.h * 0.115)
    y = (ctx.h - total_h) / 2 - ctx.h * 0.02 + (1 - p) * ctx.h * 0.03
    for i, ln in enumerate(lines):
        a = int(255 * draw.ease_out(draw.ramp(t, 0.35 + i * 0.18, 0.9)))
        draw.draw_tracked(d, (ctx.w / 2, y + i * ctx.h * 0.115), ln, big,
                          draw.CREAM + (a,), tracking=0.5, anchor="ca")
    rp = draw.ease_out(draw.ramp(t, 0.9, 0.8))
    if rp > 0:
        wpx = ctx.w * 0.12 * rp
        d.rectangle([ctx.w / 2 - wpx / 2, y + total_h + 24,
                     ctx.w / 2 + wpx / 2, y + total_h + 27], fill=draw.GOLD + (int(255 * rp),))
    return img


def _stat(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    img = _base(ctx, 1)
    d = ImageDraw.Draw(img, "RGBA")
    fb = ctx.fb
    p = draw.ease_out(draw.ramp(t, 0.3, 1.0))
    label = scene["heading"] or "—"
    size = fb.display(140 if len(label) <= 6 else 84)
    alpha = int(255 * p)
    draw.draw_tracked(d, (ctx.w / 2, ctx.h * 0.36 - (1 - p) * 20), label, size,
                      draw.GOLD_L + (alpha,), tracking=1.0, anchor="ca")
    if scene["sub"]:
        for i, ln in enumerate(draw.wrap(d, scene["sub"], fb.serif_regular(38), ctx.w * 0.74)):
            a = int(255 * draw.ease_out(draw.ramp(t, 0.7 + i * 0.15, 0.8)))
            draw.draw_tracked(d, (ctx.w / 2, ctx.h * 0.60 + i * 56), ln,
                              fb.serif_regular(38), draw.CREAM + (a,), tracking=0.5, anchor="ca")
    return img


def _timeline(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    img = _base(ctx, 0)
    d = ImageDraw.Draw(img, "RGBA")
    fb = ctx.fb
    y = ctx.h * 0.62
    x0, x1 = ctx.w * 0.12, ctx.w * 0.88
    p = draw.ease_in_out(draw.ramp(t, 0.4, 1.4))
    d.rectangle([x0, y, x0 + (x1 - x0) * p, y + 3], fill=draw.GOLD + (235,))
    marker_p = draw.ease_out(draw.ramp(t, 0.9, 0.7))
    mx = x0 + (x1 - x0) * p * 0.42
    if marker_p > 0:
        r = 16 * marker_p
        d.ellipse([mx - r, y + 1.5 - r, mx + r, y + 1.5 + r],
                  fill=draw.CREAM + (int(255 * marker_p),))
        d.ellipse([mx - r * 1.9, y + 1.5 - r * 1.9, mx + r * 1.9, y + 1.5 + r * 1.9],
                  outline=draw.GOLD + (int(200 * marker_p),), width=2)
        draw.draw_tracked(d, (mx, y - 92), scene["heading"] or "", fb.display(72),
                          draw.CREAM + (int(255 * marker_p),), tracking=0.5, anchor="ca")
    if scene["sub"]:
        a = int(255 * draw.ease_out(draw.ramp(t, 1.2, 1.0)))
        for i, ln in enumerate(draw.wrap(d, scene["sub"], fb.serif_regular(34), ctx.w * 0.7)):
            draw.draw_tracked(d, (ctx.w / 2, y + 78 + i * 48), ln,
                              fb.serif_regular(34), draw.CREAM + (a,), tracking=0.4, anchor="ca")
    return img


def _list(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    img = _base(ctx, 1)
    d = ImageDraw.Draw(img, "RGBA")
    fb = ctx.fb
    title = scene["heading"] or "Practice"
    draw.draw_tracked(d, (ctx.w * 0.12, ctx.h * 0.20), title.upper(), fb.label(34),
                      draw.GOLD + (255,), tracking=5.0)
    d.rectangle([ctx.w * 0.12, ctx.h * 0.27, ctx.w * 0.12 + ctx.w * 0.10, ctx.h * 0.27 + 2],
                fill=draw.GOLD + (200,))
    items = [s.strip(" .;") for s in (scene["sub"] or scene["narration"]).replace(";", ",").split(",")]
    items = [i for i in items if i][:6]
    for i, it in enumerate(items):
        p = draw.ease_out(draw.ramp(t, 0.6 + i * 0.34, 0.7))
        if p <= 0:
            continue
        y = ctx.h * 0.36 + i * ctx.h * 0.095
        x = ctx.w * 0.12 + (1 - p) * 40
        a = int(255 * p)
        draw.draw_tracked(d, (x, y), "%02d" % (i + 1), fb.label(26), draw.GOLD + (a,), tracking=1.0)
        lines = draw.wrap(d, it, fb.serif_regular(40), ctx.w * 0.62)
        draw.draw_tracked(d, (x + 74, y - 6), lines[0] if lines else it,
                          fb.serif_regular(40), draw.CREAM + (a,), tracking=0.4)
    return img


def _title(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    img = _base(ctx, 0)
    d = ImageDraw.Draw(img, "RGBA")
    fb = ctx.fb
    p = draw.ease_out(draw.ramp(t, 0.3, 1.2))
    zoom = 1.0 + 0.03 * draw.ease_in_out(min(1.0, t / max(0.001, dur)))
    size = fb.display(int(70 * zoom))
    draw.draw_tracked(d, (ctx.w / 2, ctx.h * 0.34), (scene["heading"] or "")[:46], size,
                      draw.CREAM + (int(255 * p),), tracking=0.5, anchor="ca")
    if scene["sub"]:
        for i, ln in enumerate(draw.wrap(d, scene["sub"], fb.serif_regular(36), ctx.w * 0.72)):
            a = int(255 * draw.ease_out(draw.ramp(t, 0.8 + i * 0.16, 0.8)))
            draw.draw_tracked(d, (ctx.w / 2, ctx.h * 0.56 + i * 50), ln,
                              fb.serif_regular(36), draw.GOLD_L + (a,), tracking=0.5, anchor="ca")
    return img


def _endcard(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    img = Image.new("RGB", (ctx.w, ctx.h), draw.CREAM)
    p = draw.ease_out(draw.ramp(t, 0.2, 1.0))
    overlay = Image.new("RGB", (ctx.w, ctx.h), (0, 0, 0))
    card = Image.new("RGB", (ctx.w, ctx.h), draw.CREAM)
    draw.end_card(card, ctx.fb, scene["heading"] or "", scene["sub"] or "", ctx.logo)
    return Image.blend(overlay, card, p)


def _photo(ctx: MotionContext, scene: Dict[str, Any], t: float, dur: float) -> Image.Image:
    path = ctx.asset(scene.get("asset"))
    if not path:
        img = _base(ctx, 1)
        _placeholder_mark(img, ctx.fb, "photo asset '%s' not supplied" % (scene.get("asset") or "?"))
    else:
        try:
            src = Image.open(path).convert("RGB")
            z = 1.0 + 0.06 * draw.ease_in_out(min(1.0, t / max(0.001, dur)))
            big = draw.cover(src, (int(ctx.w * z), int(ctx.h * z)))
            left = (big.width - ctx.w) // 2
            top = int((big.height - ctx.h) * 0.45)
            img = big.crop((left, top, left + ctx.w, top + ctx.h))
        except Exception:
            img = _base(ctx, 1)
            _placeholder_mark(img, ctx.fb, "photo could not be opened: %s" % scene.get("asset"))
    draw.lower_third(img, ctx.fb, scene["heading"] or "", scene["sub"] or "",
                     draw.ease_out(draw.ramp(t, 0.5, 0.8)))
    return img


PAINTERS = {
    "statement": _statement, "timeline": _timeline, "list": _list, "stat": _stat,
    "title": _title, "endcard": _endcard, "photo": _photo,
    "illustration": _statement,
}


def render_scene_frame(ctx: MotionContext, scene: Dict[str, Any], t: float) -> Image.Image:
    painter = PAINTERS.get(scene["kind"], _statement)
    img = painter(ctx, scene, t, float(scene["dur"]))
    if scene.get("placeholder"):
        _placeholder_mark(img, ctx.fb, ", ".join(scene.get("needs") or []) or "unverified content")
    draw.watermark(img, ctx.fb, ctx.spec.watermark)
    return img


# ---------------------------------------------------------------- frame stream
def iter_frames(ctx: MotionContext, scenes: List[Dict[str, Any]],
                cancel: Optional[Callable[[], bool]] = None,
                progress: Optional[Callable[[int, int], None]] = None):
    """Yield every frame of the film, crossfading scene boundaries."""
    spec = ctx.spec
    fps = spec.fps
    overlap = min(spec.transition_sec, min(s["dur"] for s in scenes) * 0.4)
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
               progress: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
        if not common.ffmpeg_available():
            raise common.RenderError("ffmpeg is not available — cannot render motion graphics")
        os.makedirs(work_dir, exist_ok=True)
        ctx = MotionContext(spec, asset_dir)

        def _prog(n: int, total: int) -> None:
            if progress:
                progress("rendering frame %d/%d" % (n, total), int(100 * n / max(1, total)))

        if progress:
            progress("rendering %d scenes at %dx%d@%d" %
                     (len(spec.scenes), spec.width, spec.height, spec.fps), 1)
        video_only = os.path.join(work_dir, "_video_only.mp4")
        common.encode_frames_to_video(iter_frames(ctx, spec.scenes, cancel, _prog),
                                      video_only, spec.width, spec.height, spec.fps)
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
            validation=validation, extra={"audio_detail": audio_meta})
        return {"output": out_path, "manifest": manifest, "validation": validation}


def render(spec: RenderSpec, out_path: str, work_dir: str, asset_dir: str = "",
           cancel: Optional[Callable[[], bool]] = None,
           progress: Optional[Callable[[str, int], None]] = None) -> Dict[str, Any]:
    return MotionBackend().render(spec, out_path, work_dir, asset_dir, cancel, progress)
