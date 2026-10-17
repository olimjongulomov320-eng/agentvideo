# -*- coding: utf-8 -*-
"""qa_fixture.py — a self-contained render fixture for visual QA.

This exists so the *renderer* can be exercised and inspected **without any real
firm data**. Every string below is obviously synthetic test content, and the
film carries a ``QA FIXTURE — NOT A CLIENT FILM`` watermark. Nothing here is a
research claim, a client name, an award or a statistic about anybody.

Its purpose is to show several *visually distinct* compositions in one short
film — title sequence, editorial statement, timeline, numbered list, statistic,
comparison, process, pull quote, missing-asset fallback, branded end card — with
deliberate motion and real crossfades, so both the automated QA heuristics and a
human reviewer have something meaningful to look at.
"""
from typing import Any, Dict, List, Optional, Tuple

from . import video

WATERMARK = "QA FIXTURE — NOT A CLIENT FILM"

#: Synthetic scenes. ``kind`` picks the composition; durations are in seconds.
SCENES: List[Dict[str, Any]] = [
    {"id": "q1", "key": "hook", "kind": "title", "dur": 3.4,
     "heading": "Fixture Legal", "sub": "A test film exercising every composition",
     "narration": "", "placeholder": False, "transition": "fade"},
    {"id": "q2", "key": "origin", "kind": "statement", "dur": 3.0,
     "heading": "One clear idea per scene.",
     "sub": "Editorial statement layout on a real grid.",
     "narration": "", "placeholder": False, "transition": "dissolve"},
    {"id": "q3", "key": "achievements", "kind": "timeline", "dur": 3.4,
     "heading": "A short timeline of synthetic milestones",
     "sub": "Years shown only because they appear in this fixture text.",
     "narration": "Milestones: 2010, 2016, 2024.", "placeholder": False,
     "transition": "fade"},
    {"id": "q4", "key": "practice", "kind": "list", "dur": 3.0,
     "heading": "Practice areas (synthetic)",
     "sub": "Corporate, disputes, IT and data, employment.",
     "narration": "", "placeholder": False, "transition": "dissolve"},
    {"id": "q5", "key": "achievements", "kind": "stat", "dur": 2.6,
     "heading": "2010", "sub": "A numeral that counts up — fixture value only.",
     "narration": "", "placeholder": False, "transition": "fade"},
    {"id": "q6", "key": "people", "kind": "comparison", "dur": 3.0,
     "heading": "Risk vs recommendation",
     "sub": "Unclear scope; late evidence; missed notice vs Scoped retainer; early "
            "evidence review; notice calendar.",
     "narration": "", "placeholder": False, "transition": "slide"},
    {"id": "q7", "key": "origin", "kind": "process", "dur": 3.0,
     "heading": "How a matter runs (synthetic)",
     "sub": "Intake; Conflict check; Strategy; Execution; Review.",
     "narration": "", "placeholder": False, "transition": "dissolve"},
    {"id": "q8", "key": "people", "kind": "quote", "dur": 2.8,
     "heading": "Testimonial text is synthetic and never a real quotation.",
     "sub": "— QA fixture", "narration": "", "placeholder": False,
     "transition": "fade"},
    {"id": "q9", "key": "office", "kind": "photo", "dur": 2.6,
     "heading": "Missing-asset fallback", "sub": "No photo supplied in the fixture.",
     "narration": "", "placeholder": False, "asset": "does-not-exist.jpg",
     "transition": "dissolve"},
    {"id": "q10", "key": "closing", "kind": "endcard", "dur": 3.2,
     "heading": "Fixture Legal", "sub": "Synthetic end card — not a real firm.",
     "narration": "", "placeholder": False, "transition": "fade"},
]


def fixture_spec(style: str = "motion", width: int = 1920, height: int = 1080,
                 fps: int = 30,
                 scenes: Optional[List[Dict[str, Any]]] = None):
    """Validate and return a render spec for the QA fixture."""
    raw = {
        "firm_name": "Fixture Legal",
        "language": "en",
        "style": style,
        "width": width, "height": height, "fps": fps,
        "scenes": scenes if scenes is not None else SCENES,
        "watermark": WATERMARK,
        "audio": {"music": None, "voiceover": None, "license": "synthesized_temporary",
                  "voice": "none"},
    }
    spec, errors = video.validate_render_spec(raw)
    if errors:
        raise RuntimeError("QA fixture spec invalid: %s" % "; ".join(errors))
    return spec


def render_fixture(out_path: str, work_dir: str, style: str = "motion",
                   width: int = 1920, height: int = 1080, fps: int = 30,
                   profile: str = "production",
                   progress=None) -> Dict[str, Any]:
    """Render the QA fixture with the requested backend and profile."""
    spec = fixture_spec(style=style, width=width, height=height, fps=fps)
    return video.render_style(spec, out_path, work_dir, profile=profile,
                              progress=progress)


def run_qa(out_dir: str, style: str = "motion", width: int = 1920,
           height: int = 1080, fps: int = 30, profile: str = "production",
           keep: bool = True, progress=None) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    """Render the fixture and run the visual QA pass on the result.

    Returns ``(video_path, render_result, qa_report)``.
    """
    import os
    import shutil
    from .video import qa as qa_mod
    os.makedirs(out_dir, exist_ok=True)
    video_path = os.path.join(out_dir, "qa_fixture_%s_%dp.mp4" % (style, height))
    work_dir = os.path.join(out_dir, "work_%s" % style)

    result = render_fixture(video_path, work_dir, style=style, width=width,
                            height=height, fps=fps, profile=profile,
                            progress=progress)
    report = qa_mod.qa_video(
        video_path, os.path.join(out_dir, "qa_%s" % style),
        expect_width=width, expect_height=height, expect_fps=fps,
        require_audio=True, label="QA FIXTURE (%s, %s profile)" % (style, profile))
    if not keep:
        shutil.rmtree(work_dir, ignore_errors=True)
    return video_path, result, report
