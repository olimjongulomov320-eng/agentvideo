# Video Pipeline — Full-HD production system

Technical reference for the rendering subsystem in `agent_system/video/`.
Written after a ground-up audit of the existing pipeline.

---

## 1. Root-cause analysis (what was actually wrong)

Three separate defects, not one:

| # | Defect | Evidence | Cause |
|---|--------|----------|-------|
| 1 | **The "final" film was half-HD** | `ffprobe output/jobs/JYDV8WGZQ/final.mp4` → `h264 960x540 @ 24 fps`, 1.39 MB | `Config.render_overrides()` returned the *preview* dimensions whenever fast mode was on, and nothing distinguished a preview from a deliverable. A "final" render produced by fast mode was therefore a low-resolution file with no warning. |
| 2 | **Scenes were static slides, not animation** | QA on the old file: 2 of 11 sampled frame pairs differ by Δluma **0.0013–0.0036** — i.e. ~3 s on screen with essentially zero change | Compositions drew their elements once per scene with no timed motion budget; entrances were either instant or absent. |
| 3 | **There was no way to see any of this** | No QA step existed | `validate_mp4()` proves a file is *valid*, not that it is *good*. Nothing measured legibility, margins or motion. |

A fourth, non-visual problem: **speed**. Backgrounds (gradient + soft light +
vignette) were rebuilt for every single frame, and photographs were re-resized
with `cover()` per frame.

---

## 2. What was built

No new third-party dependencies. Everything uses Pillow + numpy + the existing
ffmpeg/ffprobe.

### New modules

| File | Purpose |
|------|---------|
| `agent_system/video/design.py` | The design system: palette, `Theme` (grid, safe margins, type scale), cached background grounds, and vector primitives (kicker, heading, body, rule, panel, badge, chip, lockup, scrim, soft shadow) plus a small hand-drawn icon set. |
| `agent_system/video/qa.py` | Automated visual QA: frame metrics, motion detection, safe-margin tests, contact sheet, `qa_report.json` + `qa_report.md`. |
| `agent_system/qa_fixture.py` | A self-contained synthetic QA film exercising every composition. Labelled `QA FIXTURE — NOT A CLIENT FILM`. |

### Rewritten / extended

- `draw.py` — low-level primitives rewritten (numpy-accelerated gradient, glow,
  vignette, grain, `cover`), API preserved; `FontBook` extended with
  `display/serif/label/sans` families and metrics.
- `motion.py` — compositions rewritten on the design system with a timed motion
  budget per composition, plus cached backgrounds and a pre-scaled photo cache.
- `illustrated.py` — sky built once and cached (was per frame); accepts a profile.
- `common.py` — `ENCODE_PROFILES` (production / preview) and
  `encode_frames_to_video(..., profile=)`. The legacy positional signature and
  its historical defaults (CRF 20 / veryfast) are unchanged.
- `spec.py` — new composition kinds (`quote`, `comparison`, `process`, `logo`);
  dimensions are snapped to **even** numbers, because libx264/yuv420p rejects odd
  width/height with a cryptic error.
- `config.py` — `PRODUCTION_PROFILE`, `PREVIEW_PROFILE`, `production_profile()`,
  `preview_profile()`, `encode_profile()`, `RENDER_QUALITY`.
- `orchestrator.py` — a deliverable render uses the production profile unless the
  caller passes explicit overrides; the encoder profile is passed through.
- `cli.py` — new `qa` and `render-qa` commands; `--fast` is now labelled
  PREVIEW ONLY.

---

## 3. Profiles: preview vs deliverable

| | Production (deliverable) | Preview |
|---|---|---|
| Resolution | **1920 × 1080** | 960 × 540 |
| Frame rate | **30 fps** | 24 fps |
| x264 | CRF 18, preset `medium`, tune `film` | CRF 23, preset `veryfast` |

Precedence for the *final* render dimensions:

1. explicit `overrides=` passed to the job (used by tests and `--fast`) — wins;
2. otherwise the **production profile** (1920×1080@30).

Selection:

- `RENDER_QUALITY=production` (default) → production encoder.
- `RENDER_QUALITY=preview`, or `FAST_RENDER=true`, or CLI `--fast` → preview
  encoder; the CLI prints a warning that the output is not a deliverable.

`render_overrides()` still exists and still returns the preview dimensions when
fast mode is on, but it is now documented as **preview-only** — this is the exact
function whose silent use produced the 960×540 "final".

---

## 4. Commands

```bash
# Deliverable film for a firm (Full HD by default)
python3 -m agent_system run-job --firm "Firm Name" --website https://example.uz --style motion

# Research + story only — never starts ffmpeg
python3 -m agent_system run-job --firm "..." --no-render

# Deliberately non-deliverable quick check (prints a warning)
python3 -m agent_system run-job --firm "..." --fast

# Visual QA of any existing MP4 (technical + heuristics + contact sheet)
python3 -m agent_system qa path/to/film.mp4 --label "..." --width 1920 --height 1080 --fps 30

# Render the self-contained synthetic QA fixture and QA it
python3 -m agent_system render-qa --style motion --width 1920 --height 1080 --fps 30

# Validate a scene manifest
python3 -m agent_system check-spec path/to/scene_manifest.json
```

---

## 5. What the QA pass measures — and what it cannot

`qa_video()` writes `qa_report.md` (human) and `qa_report.json` (machine).

**Technical** — real `ffprobe` numbers: dimensions, aspect, fps, frame count,
duration, bitrate, codecs, audio channels; optional expectations that *fail* the
report (a 960×540 file checked with `--width 1920` is reported as a failure).

**Per-frame heuristics** — brightness, tonal spread, edge (detail) density,
colourfulness, dark/light fractions, near-blank detection.

**Motion** — consecutive sampled frames are compared **pixel-wise** (mean
absolute luminance difference). This is the signal that distinguishes animation
from a static slide. A real well-animated frame pair scores ≈ 0.02–0.48; the old
pipeline contained stretches at 0.0013.

**Safe margins** — two complementary signals measured in the outer 2.5 % ring:

- *edge density* catches textured content (text, rules) at the edge;
- *mean step* catches a solid block flush with the edge (which has no internal
  edges to find).

### Threshold calibration (measured, not guessed)

| Signal | Legitimate frames | Breach | Threshold |
|--------|------------------|--------|-----------|
| edge density | 0.0000 – 0.0059 | 0.043 – 0.085 | 0.02 |
| mean step | 0.01 – 4.83 | 104 – 217 | 25.0 |
| consecutive Δluma | 0.0149 – 0.478 | 0.0013 (static) | 0.004 |

A third candidate signal (ring luminance dispersion) was **tried and rejected**:
it flagged the illustrated backend's legitimate sky gradient (dispersion 22–26)
and it *inverts* on solid fills. This is recorded in `qa.py` so it is not
re-attempted.

Two measurement bugs found and fixed during development, both of which produced
false positives:

1. `FIND_EDGES` treats out-of-bounds samples as black, so the image border always
   registered as an edge along the whole perimeter — an empty ground scored 0.038.
   Fixed by insetting the **edge map** (not the image) afterwards.
2. The first duplicate/motion check compared scalar *mean brightness*, which is
   nearly meaningless. Replaced with a per-pixel difference.

### Honest limitations

- These are **heuristics**. A clean report means "nothing suspicious was
  measured", not "this film is good".
- **The agent cannot view images in this environment.** Frames were verified
  programmatically only. A human must open the contact sheet and watch the film —
  this is stated in every generated report.
- The margin check is a coarse "content is jammed against the frame" alarm. The
  real safe-area guarantee is the `Theme` content box, which is unit-tested.
- Bitrate on these films is low (~1.2 Mbps for 1080p) because the content is flat
  graphics with large uniform areas; that is correct CRF behaviour, not a defect.

---

## 6. Performance

Caching the grounds and pre-scaling photographs removed the per-frame cost that
made high resolution impractical.

| Work | Before | After |
|------|--------|-------|
| Background build | per frame | once per (w, h, variant); ~0.18 s first call, ~0 s cached |
| Photo | `cover()` resize per frame | scaled once per (path, size) |
| Full HD fixture (711 frames + encode + QA) | not practical | **≈ 21 s** (motion), ≈ 29 s (illustrated) |

---

## 7. Environment capabilities (measured on this machine)

- Python 3.9.6, Pillow 11.2.1, numpy 2.0.2, ffmpeg / ffprobe 8.1.2
- **No Blender** — the `blender3d` style reports itself unavailable rather than
  pretending.
- **No SVG rasteriser** (no cairosvg / rsvg-convert / inkscape / resvg). Vector
  art is therefore drawn directly with Pillow primitives. `design.svg_available()`
  returns `(False, reason)` and `rasterize_svg()` returns the reason instead of
  silently failing.
- `raqm: False` — no complex text shaping (fine for Latin script).
- TTS (`say`) voices: `en: yes`, `ru: yes`, `uz: no`. Any synthesised narration is
  a DEMO placeholder and must be labelled.

---

## 8. Validation

```bash
# Everything
python3 -m unittest discover -s tests -t .

# The new video-specific suites
python3 -m unittest tests.test_video_design tests.test_video_qa tests.test_video_pipeline

# Prove an artifact's real properties
ffprobe -v error -show_entries format=duration,size,bit_rate \
        -show_entries stream=codec_name,width,height,r_frame_rate,nb_frames \
        -of default=noprint_wrappers=1 path/to/film.mp4
```

Note: `tests/test_config_security.py` requires `.env` to be **absent**. Move it
aside before running the full suite, then restore it.

---

## 9. Known limitations / remaining work

- **Quality is not certified.** No human has reviewed the QA contact sheets or
  watched the rendered films in this environment.
- The QA heuristic thresholds were calibrated against the compositions in the
  repository; a radically different visual style may need re-calibration.
- Music is not synthesised or licensed; audio in QA fixtures is a silent track.
- Real narration needs a human voice or a properly licensed TTS engine; `uz` is
  not available locally.

## Voice-over (optional) and captions
- Narration is always burned in as a caption; no watermark is ever drawn.
- `AGENT_TTS=edge` (plus `pip install edge-tts`) adds a synthetic voice, including Uzbek
  (`uz-UZ-MadinaNeural`). Narration text is sent to Microsoft's online speech service.
  If the package is missing or the service is unreachable, the film is rendered without a
  voice and the reason appears in the job warnings.
