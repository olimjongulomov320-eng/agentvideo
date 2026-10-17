# -*- coding: utf-8 -*-
"""video/qa.py — visual quality assurance for rendered films.

A successful ffmpeg exit code proves the file is *valid*; it says nothing about
whether the picture is legible, well-composed or actually moving. This module
adds a *measurable* QA pass on top of ffprobe:

* **technical** — dimensions, aspect, frame count, duration, codecs, audio;
* **frame metrics** — brightness/contrast, colourfulness, edge (detail) density,
  near-blank detection, and a safe-margin edge test;
* **motion check** — consecutive sampled frames are compared *pixel-wise* to
  catch "static slide" stretches where a scene is on screen but nothing moves;
* **contact sheet** — one image of representative frames (opening → ending) for
  rapid human inspection;
* a machine-readable ``qa_report.json`` and a human ``qa_report.md``.

Honest limitation, repeated in the report itself: these are *heuristics*. They
can flag a frame that is unlikely to be legible, but they cannot certify that a
film looks professional — a human must watch it.
"""
import json
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageStat

from . import common, draw

# ------------------------------------------------------------------ thresholds
# Deliberately conservative: we would rather miss a subtle issue than cry wolf.
NEAR_BLANK_STDDEV = 6.0        # per-frame luminance stddev below this ⇒ flat
NEAR_BLANK_EDGE = 0.004        # edge-detail fraction below this ⇒ no content
LOW_CONTRAST_STDDEV = 12.0     # luminance spread below this ⇒ little tonal range
MARGIN_RING_FRAC = 0.025       # outer 2.5% of the frame is the "too tight" zone
# Calibrated empirically on real FHD renders: empty grounds and correctly-composed
# frames measure 0.0000-0.0048 in the ring, while content genuinely jammed against
# the frame edge measures 0.043-0.085. 0.02 sits in the gap with ~4x headroom both
# ways. This is a coarse "content is pressed against the frame" alarm, not a
# fine-grained safe-area checker (the real safe area is the Theme content box).
MARGIN_EDGE_MAX = 0.02
MARGIN_TOP_EXCLUDE = 0.09      # ignore the top 9% (DEMO/source watermark lives there)
STATIC_FRAME_DIFF = 0.004      # mean |Δluma| (0..1) below this ⇒ frames look static
# Second margin signal: the mean-luminance step across the ring's inner boundary.
# Calibrated on real renders — legitimate frames peak at 4.8 (the illustrated
# sky gradient reaches 3.7), while a solid block flush with the edge steps by
# 104-217. 25 sits in the gap with ~5x headroom either way.
MARGIN_STEP_MAX = 25.0
SAMPLE_COUNT = 12              # representative frames sampled for motion analysis


def sample_times(duration: float, n: int = SAMPLE_COUNT) -> List[float]:
    """Evenly spaced sample times, clipped just inside the runtime."""
    n = max(2, n)
    out: List[float] = []
    for i in range(n):
        t = duration * (i + 0.5) / n
        out.append(round(min(max(0.0, t), max(0.0, duration - 0.05)), 3))
    return out


# ----------------------------------------------------------------- frame probing
def extract_frame(video: str, t: float, out_path: str,
                  scale: Optional[int] = None) -> Optional[str]:
    """Extract a single frame at ``t`` seconds. Returns the path or None."""
    args = [common.FFMPEG, "-v", "error", "-ss", "%.3f" % max(0.0, t), "-i", video,
            "-frames:v", "1", "-y"]
    if scale:
        args += ["-vf", "scale=%d:-1" % scale]
    args += [out_path]
    proc = common.run(args, timeout=180)
    if proc.returncode != 0 or not os.path.isfile(out_path):
        return None
    return out_path


def extract_frames(video: str, out_dir: str, duration: float,
                   times: Optional[Sequence[float]] = None,
                   scale: Optional[int] = 960) -> List[Tuple[float, str]]:
    os.makedirs(out_dir, exist_ok=True)
    if times is None:
        times = sample_times(duration)
    frames: List[Tuple[float, str]] = []
    for i, t in enumerate(times):
        p = os.path.join(out_dir, "frame_%02d_%.2fs.png" % (i, t))
        got = extract_frame(video, t, p, scale=scale)
        if got:
            frames.append((float(t), got))
    return frames


# ------------------------------------------------------------- frame metrics
def _inset(img: Image.Image, px: Optional[int] = None) -> Image.Image:
    """Trim the outermost pixels before edge detection.

    Pillow's ``FIND_EDGES`` treats out-of-bounds samples as black, so the 1-pixel
    frame border always registers as a strong edge along the whole perimeter.
    That artifact dominates any measurement near the frame edge, so we inset
    first.
    """
    w, h = img.size
    if px is None:
        px = max(1, int(round(min(w, h) * 0.004)))
    if w - 2 * px < 8 or h - 2 * px < 8:
        return img
    return img.crop((px, px, w - px, h - px))


def _edge_map(img: Image.Image) -> Image.Image:
    """Raw gradient-magnitude map (has an artificial response on the frame border)."""
    return img.convert("L").filter(ImageFilter.FIND_EDGES)


def _edge_field(img: Image.Image) -> Image.Image:
    """Edge map with the artificial frame-border response removed.

    ``FIND_EDGES`` treats out-of-bounds samples as black, so the outermost pixel
    row/column always lights up along the whole perimeter. The inset must be
    applied *after* the filter — cropping the image first just moves the artifact
    to the new border.
    """
    return _inset(_edge_map(img))


def _edge_density(img: Image.Image, region: Optional[Tuple[int, int, int, int]] = None) -> float:
    """Fraction of pixels carrying edge detail (a cheap 'is there content?')."""
    e = _edge_field(img)
    if region:
        e = e.crop(region)
    hist = e.histogram()
    strong = sum(hist[40:])                 # ignore low-level noise
    total = max(1, e.width * e.height)
    return strong / float(total)


def _colorfulness(img: Image.Image) -> float:
    """Hasler-Süsstrunk colourfulness — a rough 'is it grey/flat?' signal."""
    small = img.convert("RGB").resize((max(1, img.width // 4), max(1, img.height // 4)))
    stat = ImageStat.Stat(small)
    r, g, b = (list(stat.mean) + [0, 0, 0])[:3]
    rg = abs(r - g)
    yb = abs(0.5 * (r + g) - b)
    std = sum(stat.stddev) / 3.0
    return math.sqrt(rg * rg + yb * yb) + 0.3 * std


def _mean_abs_diff(a: Image.Image, b: Image.Image) -> float:
    """Mean per-pixel absolute luminance difference, normalised to 0..1.

    This is the *motion* signal: comparing whole pixel fields (not just mean
    brightness) is what makes it possible to tell a genuinely animating scene
    from a static slide.
    """
    ga, gb = a.convert("L"), b.convert("L")
    if ga.size != gb.size:
        gb = gb.resize(ga.size)
    diff = ImageChops.difference(ga, gb)
    return ImageStat.Stat(diff).mean[0] / 255.0


def margin_metrics(img: Image.Image) -> Tuple[float, float]:
    """Measure the outer "too tight" ring two ways: (edge density, mean step).

    Two complementary signals are needed because neither alone is sufficient:

    * **edge density** catches *textured* content (text, rules, icons) pressed
      against the frame edge. It is blind to a solid fill, whose interior has no
      internal edges.
    * **mean step** compares the mean luminance of the ring with a band of the
      same thickness immediately inside it. A smooth background gradient
      continues (step ≈ 0) whereas a solid bar or block flush with the edge
      steps sharply (step > 100).

    Thresholds were calibrated on real renders — see ``MARGIN_EDGE_MAX`` and
    ``MARGIN_STEP_MAX``.

    A third signal was tried and rejected: the ring's own luminance dispersion.
    It flagged the illustrated backend's legitimate sky gradient (its ring
    dispersion reaches 22-26) and it *inverts* on solid fills, where the ring is
    uniform and the inner band is mixed.
    """
    inset_img = _inset(img)
    iw, ih = inset_img.size
    ring = max(2, int(round(min(iw, ih) * MARGIN_RING_FRAC)))
    top = int(round(ih * MARGIN_TOP_EXCLUDE))
    lum = inset_img.convert("L")
    efield = _edge_field(img)

    regions = [
        # (ring box, inner reference band shifted inward)
        ((0, ih - ring, iw, ih), (0, max(0, ih - 2 * ring), iw, max(1, ih - ring))),
        ((0, top, ring, ih), (min(iw - 1, ring), top, min(iw, 2 * ring), ih)),
        ((iw - ring, top, iw, ih), (max(0, iw - 2 * ring), top, max(1, iw - ring), ih)),
    ]
    strong = 0
    total = 0
    step = 0.0
    for ring_box, inner_box in regions:
        hist = efield.crop(ring_box).histogram()
        strong += sum(hist[40:])
        total += (ring_box[2] - ring_box[0]) * (ring_box[3] - ring_box[1])
        if inner_box[2] <= inner_box[0] or inner_box[3] <= inner_box[1]:
            continue
        m_ring = ImageStat.Stat(lum.crop(ring_box)).mean[0]
        m_in = ImageStat.Stat(lum.crop(inner_box)).mean[0]
        step = max(step, abs(m_ring - m_in))
    return strong / float(max(1, total)), step


def margin_edge_density(img: Image.Image) -> float:
    """Edge density in the outer ring (see :func:`margin_metrics`)."""
    return margin_metrics(img)[0]


def analyze_frame(path: str) -> Dict[str, Any]:
    """Measure one frame. All numbers are heuristics, not verdicts."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    stat = ImageStat.Stat(img)
    stddev = sum(stat.stddev) / 3.0
    brightness = sum(stat.mean) / 3.0
    edge = _edge_density(img)
    lum = img.convert("L")
    hist = lum.histogram()
    total = max(1, w * h)
    dark = sum(hist[:48]) / float(total)
    light = sum(hist[200:]) / float(total)
    info: Dict[str, Any] = {
        "path": os.path.basename(path),
        "width": w, "height": h,
        "aspect": round(w / float(h), 4),
        "brightness": round(brightness, 2),
        "stddev": round(stddev, 2),
        "edge_density": round(edge, 5),
        "colorfulness": round(_colorfulness(img), 2),
        "dark_fraction": round(dark, 4),
        "light_fraction": round(light, 4),
        "near_blank": bool(stddev < NEAR_BLANK_STDDEV or edge < NEAR_BLANK_EDGE),
        "low_contrast": bool(stddev < LOW_CONTRAST_STDDEV),
    }
    m_edge, m_step = margin_metrics(img)
    info["margin_edge_density"] = round(m_edge, 5)
    info["margin_step"] = round(m_step, 2)
    info["margin_ok"] = bool(m_edge <= MARGIN_EDGE_MAX and m_step <= MARGIN_STEP_MAX)
    return info


# ---------------------------------------------------------------- contact sheet
def contact_sheet(frames: Sequence[Tuple[float, str]], out_path: str,
                  cols: int = 4, cell_w: int = 460,
                  title: str = "") -> Optional[str]:
    """Assemble representative frames into one labelled sheet for human review."""
    if not frames:
        return None
    from PIL import ImageFont
    sample = Image.open(frames[0][1])
    cell_h = int(cell_w * sample.height / max(1, sample.width))
    rows = int(math.ceil(len(frames) / float(cols)))
    pad, label_h = 16, 34
    head_h = 64 if title else 0
    W = cols * cell_w + (cols + 1) * pad
    H = head_h + rows * (cell_h + label_h) + (rows + 1) * pad
    sheet = Image.new("RGB", (W, H), (18, 22, 28))
    d = ImageDraw.Draw(sheet)
    font_path = draw._first_existing(["Helvetica.ttc", "HelveticaNeue.ttc"])
    try:
        f_label = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
        f_title = ImageFont.truetype(font_path, 30) if font_path else ImageFont.load_default()
    except Exception:
        f_label = f_title = ImageFont.load_default()

    if title:
        d.text((pad, pad + 12), title, font=f_title, fill=(238, 231, 214))
    for i, (t, p) in enumerate(frames):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = head_h + pad + r * (cell_h + label_h + pad)
        try:
            img = Image.open(p).convert("RGB").resize((cell_w, cell_h), Image.LANCZOS)
        except Exception:
            continue
        sheet.paste(img, (x, y))
        d.rectangle([x, y, x + cell_w - 1, y + cell_h - 1], outline=(70, 78, 88), width=1)
        d.text((x + 4, y + cell_h + 6), "t=%ss" % t, font=f_label, fill=(200, 196, 186))
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    sheet.save(out_path)
    return out_path


# ---------------------------------------------------------------- video QA
def qa_video(video: str, out_dir: str, expect_width: Optional[int] = None,
             expect_height: Optional[int] = None, expect_fps: Optional[int] = None,
             require_audio: bool = True, frames_dir: Optional[str] = None,
             label: str = "", contact_path: Optional[str] = None,
             samples: int = SAMPLE_COUNT) -> Dict[str, Any]:
    """Run the full QA pass and write ``qa_report.json`` + ``qa_report.md``.

    Never raises for a merely *ugly* video: it records findings so a human can
    judge. Returns the report dict.
    """
    os.makedirs(out_dir, exist_ok=True)
    frames_dir = frames_dir or os.path.join(out_dir, "frames")
    report: Dict[str, Any] = {
        "video": os.path.abspath(video),
        "label": label,
        "heuristics_only": True,
        "thresholds": {
            "low_contrast_stddev": LOW_CONTRAST_STDDEV,
            "static_frame_diff": STATIC_FRAME_DIFF,
            "margin_edge_max": MARGIN_EDGE_MAX,
            "margin_step_max": MARGIN_STEP_MAX,
            "near_blank_stddev": NEAR_BLANK_STDDEV,
            "near_blank_edge": NEAR_BLANK_EDGE,
        },
        "note": ("Automated checks are heuristics. Blank/contrast/margin/static "
                 "checks can flag suspicion; only a human can confirm visual quality."),
        "findings": [], "warnings": [], "errors": [],
    }
    if not os.path.isfile(video):
        report["errors"].append("file not found: %s" % video)
        _write_reports(report, out_dir)
        return report

    validation = common.validate_mp4(video, expect_width, expect_height, expect_fps,
                                     require_audio=require_audio)
    report["technical"] = validation
    if not validation.get("ok"):
        report["errors"] += validation.get("errors", [])

    duration = float(validation.get("duration_sec") or 0.0)
    if duration <= 0:
        report["errors"].append("duration could not be determined")
        _write_reports(report, out_dir)
        return report

    frames = extract_frames(video, frames_dir, duration, times=sample_times(duration, samples))
    report["frames_sampled"] = len(frames)
    if not frames:
        report["errors"].append("no frames could be extracted")
        _write_reports(report, out_dir)
        return report

    analyses: List[Dict[str, Any]] = []
    for t, p in frames:
        a = analyze_frame(p)
        a["t"] = t
        analyses.append(a)
    report["frames"] = analyses

    # -- near-blank frames
    blanks = [a for a in analyses if a.get("near_blank")]
    if blanks:
        report["findings"].append(
            "%d/%d sampled frames look near-blank (stddev<%.0f or edge<%.4f): %s"
            % (len(blanks), len(analyses), NEAR_BLANK_STDDEV, NEAR_BLANK_EDGE,
               ", ".join("t=%s" % b["t"] for b in blanks)))

    # -- low contrast / legibility risk
    low = [a for a in analyses if a.get("low_contrast")]
    if low:
        report["findings"].append(
            "%d/%d sampled frames have a low luminance spread (<%.0f) — text may be "
            "low-contrast: %s" % (len(low), len(analyses), LOW_CONTRAST_STDDEV,
                                  ", ".join("t=%s" % b["t"] for b in low)))

    # -- safe margins (content pressed against the frame edge)
    tight = [a for a in analyses if not a.get("margin_ok")]
    if tight:
        report["findings"].append(
            "%d/%d sampled frames have detail or a solid block in the outer %.1f%% "
            "ring (possible safe-margin breach; top %.0f%% excluded as watermark "
            "band): %s"
            % (len(tight), len(analyses), MARGIN_RING_FRAC * 100,
               MARGIN_TOP_EXCLUDE * 100,
               ", ".join("t=%s (edge %.4f, step %.1f)"
                         % (b["t"], b["margin_edge_density"], b["margin_step"])
                         for b in tight)))

    # -- motion: pixel-wise diff between consecutive samples
    diffs: List[Dict[str, Any]] = []
    prev = None
    prev_t = None
    for t, p in frames:
        img = Image.open(p).convert("RGB")
        if prev is not None:
            diffs.append({"from": prev_t, "to": t, "diff": round(_mean_abs_diff(prev, img), 5)})
        prev, prev_t = img, t
    report["consecutive_diffs"] = diffs
    static = [d for d in diffs if d["diff"] < STATIC_FRAME_DIFF]
    report["static_stretches"] = static
    if static:
        report["findings"].append(
            "%d/%d consecutive sampled frame pair(s) barely differ (mean |Δluma| < "
            "%.3f) — the film may contain static stretches: %s"
            % (len(static), len(diffs), STATIC_FRAME_DIFF,
               ", ".join("%s→%s (%.4f)" % (d["from"], d["to"], d["diff"]) for d in static)))
    if diffs:
        report["motion_summary"] = {
            "min_diff": min(d["diff"] for d in diffs),
            "max_diff": max(d["diff"] for d in diffs),
            "mean_diff": round(sum(d["diff"] for d in diffs) / len(diffs), 5),
        }

    # -- audio sanity
    tech = report["technical"]
    if require_audio and not tech.get("audio_codec"):
        report["errors"].append("audio required but no audio stream found")

    # -- contact sheet
    cs = contact_sheet(frames, contact_path or os.path.join(out_dir, "contact_sheet.png"),
                       title=label or "Rendered film — representative frames (human review)")
    report["contact_sheet"] = cs

    _write_reports(report, out_dir)
    return report


def _write_reports(report: Dict[str, Any], out_dir: str) -> None:
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "qa_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)
    with open(os.path.join(out_dir, "qa_report.md"), "w", encoding="utf-8") as fh:
        fh.write(_report_markdown(report))


def _report_markdown(r: Dict[str, Any]) -> str:
    tech = r.get("technical", {}) or {}
    lines = ["# Visual QA report", ""]
    if r.get("label"):
        lines += ["**Artifact:** %s" % r["label"], ""]
    lines += ["- File: `%s`" % r.get("video", "?"),
              "- Duration: %ss" % tech.get("duration_sec"),
              "- Size: %s bytes" % tech.get("size_bytes"),
              "- Video: %s %sx%s @ %sfps" % (tech.get("video_codec"), tech.get("width"),
                                             tech.get("height"), tech.get("fps")),
              "- Audio: %s (%s ch)" % (tech.get("audio_codec"), tech.get("audio_channels")),
              "- Frames sampled: %s of %s frames"
              % (r.get("frames_sampled"), tech.get("nb_frames")),
              ""]
    lines += ["> %s" % r.get("note", ""), ""]
    ms = r.get("motion_summary")
    if ms:
        lines += ["## Motion summary", "",
                  "- min consecutive Δluma: %s" % ms["min_diff"],
                  "- mean consecutive Δluma: %s" % ms["mean_diff"],
                  "- max consecutive Δluma: %s" % ms["max_diff"], ""]
    if r.get("errors"):
        lines += ["## Automated failures", ""] + ["- %s" % e for e in r["errors"]] + [""]
    if r.get("findings"):
        lines += ["## Findings (heuristics — review visually)", ""] + \
                 ["- %s" % f for f in r["findings"]] + [""]
    else:
        lines += ["## Findings", "", "- no automated flag raised", ""]
    if r.get("contact_sheet"):
        lines += ["## Contact sheet", "", "`%s`" % r["contact_sheet"], ""]
    if r.get("frames"):
        lines += ["## Sampled frames", "",
                  "| t (s) | brightness | stddev | edge | colourfulness | margin-edge | margin-step | near-blank |",
                  "|-------|-----------|--------|------|---------------|-------------|-------------|-----------|"]
        for a in r["frames"]:
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                a.get("t"), a.get("brightness"), a.get("stddev"), a.get("edge_density"),
                a.get("colorfulness"), a.get("margin_edge_density"),
                a.get("margin_step"), a.get("near_blank")))
        lines.append("")
    lines += ["## Required human review", "",
              "1. Open the contact sheet and watch the full film.",
              "2. Confirm text legibility at 100% zoom on a 1080p display.",
              "3. Confirm no scene feels static or accidentally empty.",
              "4. Confirm audio (if present) is not clipped and stays in sync.", ""]
    return "\n".join(lines)
