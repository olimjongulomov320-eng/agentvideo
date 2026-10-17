# QA comparison — old pipeline vs new design system

All figures below are **measured**, not estimated. Reproduce with:

```bash
python3 -m agent_system qa output/jobs/JYDV8WGZQ/final.mp4 --out qa/baseline_qa \
    --label "BASELINE old pipeline" --width 1920 --height 1080 --fps 30
python3 -m agent_system render-qa --style motion   --width 1920 --height 1080 --fps 30 --out qa/fhd
python3 -m agent_system render-qa --style illustrated --width 1920 --height 1080 --fps 30 --out qa/fhd
```

## Technical

| | Baseline (old) | New — motion | New — illustrated |
|---|---|---|---|
| Resolution | 960 × 540 | **1920 × 1080** | **1920 × 1080** |
| Frame rate | 24 fps | **30 fps** | **30 fps** |
| Video codec | h264 (yuv420p) | h264 (yuv420p) | h264 (yuv420p) |
| Audio | aac, 2 ch, 48 kHz | aac, 2 ch, 48 kHz | aac, 2 ch, 48 kHz |
| Duration | 35.792 s | 23.700 s | 23.700 s |
| Frames | 859 | 711 | 711 |
| Size | 1 394 907 B | 3 729 014 B | 5 606 464 B |
| Bitrate | 311 783 bps | 1 211 408 bps | 1 810 000 bps |
| Meets HD expectation | ❌ fails 1920×1080@30 | ✅ | ✅ |

The baseline row is a genuine `ffprobe` reading of the previously delivered
`final.mp4`. Passing `--width 1920 --height 1080 --fps 30` to the QA command
makes those mismatches **failures** in the report rather than silent facts.

## Motion (is the film actually moving?)

Consecutive sampled frames are compared pixel-wise; the mean absolute luminance
difference is the motion signal.

| | Baseline (old) | New — motion | New — illustrated |
|---|---|---|---|
| Minimum Δluma | **0.0013** | 0.02001 | 0.01492 |
| Mean Δluma | 0.0883 | 0.1008 | 0.04597 |
| Maximum Δluma | 0.76001 | 0.47836 | 0.08527 |
| Static stretches (< 0.004) | **2 pairs** | 0 | 0 |

The baseline's minimum of 0.0013 means roughly **three seconds of screen time
where two sampled frames are effectively identical** — a static slide. The new
renders clear the threshold by more than 3×.

## Automated findings

| | Baseline (old) | New — motion | New — illustrated |
|---|---|---|---|
| Near-blank frames | **2 / 12** (t=22.37, 25.353) | 0 | 0 |
| Low-contrast frames | 0 | 0 | 0 |
| Safe-margin breaches | **3 / 12** | 0 | 0 |
| Static stretches | **2** | 0 | 0 |
| **Total automated flags** | **4 findings** | **0** | **0** |

## Contact sheets (for human review — the agent cannot see images)

| Artifact | Contact sheet | Frames |
|---|---|---|
| Baseline (old) | `qa/baseline_qa/contact_sheet.png` | `qa/baseline_qa/frames/` |
| New — motion 1080p | `qa/fhd/qa_motion/contact_sheet.png` | `qa/fhd/qa_motion/frames/` |
| New — illustrated 1080p | `qa/fhd/qa_illustrated/contact_sheet.png` | `qa/fhd/qa_illustrated/frames/` |

## Reproduce the renders

| Artifact | Files |
|---|---|
| New — motion | `qa/fhd/qa_fixture_motion_1080p.mp4`, report `qa/fhd/qa_motion/qa_report.md` |
| New — illustrated | `qa/fhd/qa_fixture_illustrated_1080p.mp4`, report `qa/fhd/qa_illustrated/qa_report.md` |
| Baseline (original, untouched) | `output/jobs/JYDV8WGZQ/final.mp4`, report `qa/baseline_qa/qa_report.md` |

> **Not a visual verdict.** These are automated heuristics. Nothing in this
> document proves the new films look professional — a human must open the contact
> sheets and watch the MP4s. What it does prove is that specific measurable
> defects present in the old file are absent from the new ones.
