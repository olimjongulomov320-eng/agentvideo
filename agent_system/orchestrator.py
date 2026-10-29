# -*- coding: utf-8 -*-
"""orchestrator.py — the single predefined workflow the Telegram bot may start.

The bot never executes user-supplied commands. It validates a small set of
parameters into a :class:`JobRequest` and calls :func:`run_job`, which performs
exactly these stages:

    research → story (concepts/script/storyboard/manifest)
             → [approval gate]
             → render (one of three backends)
             → ffprobe validation → delivery report

Every stage writes its artefacts into the job's own output directory, so two
jobs can never overwrite each other.
"""
import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

from . import story as story_mod
from . import video
from . import voice as voice_mod
from .config import PREVIEW_PROFILE, PRODUCTION_PROFILE
from .research import ledger_csv, report_markdown, research_firm
from .security import redact

STAGE_RESEARCH = "research"
STAGE_STORY = "story"
STAGE_APPROVAL = "approval"
STAGE_RENDER = "render"
STAGE_DONE = "done"

MIN_DURATION = 20
MAX_DURATION = 400
PREVIEW_SECONDS = 14.0


@dataclass
class JobRequest:
    firm_name: str = ""
    website: str = ""
    facebook: str = ""
    language: str = "en"
    style: str = "motion"
    duration_sec: int = 140
    event_date: str = ""
    new_office: str = ""
    audience: str = ""
    extra_urls: List[str] = field(default_factory=list)
    preview_only: bool = False
    auto_approve: bool = True
    # ---- staged (human-gated) workflow, see agent_system/pipeline.py ----
    # When set, the job stops after research for a human decision and never
    # writes a script or starts a render before each gate is approved. The
    # default keeps the original single-pass behaviour byte-for-byte.
    staged: bool = False
    # Transcript files the operator already holds. Only ever read locally; the
    # workflow never contacts an interviewee.
    transcripts: List[str] = field(default_factory=list)
    # The concept the operator approved, e.g. "A". Empty until approved.
    concept: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "JobRequest":
        known = set(cls.__dataclass_fields__.keys())
        return cls(**{k: v for k, v in (d or {}).items() if k in known})


def sanitize_request(raw: Dict[str, Any]) -> JobRequest:
    """Validate/normalise untrusted input from Telegram into a JobRequest."""
    req = JobRequest.from_dict(raw)
    req.firm_name = (req.firm_name or "Untitled firm").strip()[:120]
    lang = (req.language or "en").strip().lower()[:2]
    req.language = lang if lang in story_mod.LANGS else "en"
    style = (req.style or "motion").strip().lower()
    req.style = style if style in ("motion", "illustrated", "blender3d") else "motion"
    try:
        req.duration_sec = int(req.duration_sec)
    except (TypeError, ValueError):
        req.duration_sec = 140
    req.duration_sec = max(MIN_DURATION, min(MAX_DURATION, req.duration_sec))
    for attr in ("website", "facebook"):
        val = getattr(req, attr) or ""
        if val and not val.lower().startswith(("http://", "https://")):
            val = "https://" + val
        setattr(req, attr, val.strip()[:500])
    req.extra_urls = [u.strip()[:500] for u in (req.extra_urls or [])
                      if isinstance(u, str) and u.strip()][:5]
    req.new_office = (req.new_office or "").strip()[:200]
    req.event_date = (req.event_date or "").strip()[:60]
    # Transcripts are local file paths chosen by the operator. They are
    # normalised but never fetched from a URL.
    req.transcripts = [t.strip() for t in (req.transcripts or [])
                       if isinstance(t, str) and t.strip()][:24]
    req.concept = (req.concept or "").strip()[:40]
    req.staged = bool(req.staged)
    return req


class Cancelled(RuntimeError):
    """Raised inside the workflow when the user cancels their job."""


def _write(path: str, text: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def _preview_spec(spec) -> Any:
    """Build a short preview spec: the opening scenes at the preview profile.

    The preview is deliberately *not* the deliverable: it is shorter and its
    dimensions come from ``PREVIEW_PROFILE``. Frames are still rendered at
    this (smaller) size natively — nothing is upscaled or downscaled after the
    fact.
    """
    scenes: List[Dict[str, Any]] = []
    acc = 0.0
    for s in spec.scenes:
        scenes.append(dict(s))
        acc += float(s["dur"])
        if acc >= PREVIEW_SECONDS:
            break
    raw = spec.to_dict()
    raw["scenes"] = scenes
    raw["width"] = min(spec.width, int(PREVIEW_PROFILE["width"]))
    raw["height"] = min(spec.height, int(PREVIEW_PROFILE["height"]))
    raw["fps"] = min(spec.fps, int(PREVIEW_PROFILE["fps"]))
    raw["watermark"] = ""
    raw["output_name"] = "preview.mp4"
    preview, _errors = video.validate_render_spec(raw)
    return preview


def _run_job_impl(cfg, store, job_id: str, request: JobRequest,
                  progress: Optional[Callable[[str, int, str], None]] = None,
                  cancel: Optional[Callable[[], bool]] = None,
                  approve: Optional[Callable[[Dict[str, Any]], bool]] = None,
                  asset_dir: str = "",
                  fetcher: Optional[Callable[[str], Any]] = None,
                  overrides: Optional[Dict[str, Any]] = None,
                  enable_preview: bool = True,
                  enable_render: bool = True) -> Dict[str, Any]:
    """Execute the whole workflow for one job. Returns a result summary.

    ``fetcher`` and ``overrides`` exist for offline operation and fast previews:
    a fetcher lets the operator supply pre-downloaded pages, and overrides can
    set width/height/fps so a preview renders quickly.

    ``enable_render=False`` (CLI ``--no-render``, or the ``AGENT_NO_RENDER``
    environment variable set to a truthy value) runs research, evidence and the
    script/storyboard stages only: **no ffmpeg subprocess is started**, no
    preview and no final video are produced, and the delivery report says so
    explicitly instead of pretending a video exists.
    """
    job_dir = cfg.job_dir(job_id)
    work_dir = os.path.join(job_dir, "work")
    os.makedirs(work_dir, exist_ok=True)

    # Explicit no-render mode: the CLI flag passes enable_render=False directly;
    # the AGENT_NO_RENDER environment variable is honoured for any other caller.
    if os.environ.get("AGENT_NO_RENDER", "").strip().lower() in ("1", "true", "yes", "on"):
        enable_render = False
    if not enable_render:
        enable_preview = False

    def say(stage: str, pct: int, msg: str) -> None:
        store.update(job_id, progress=max(0, min(100, pct)), message=redact(msg)[:400])
        store.log_event(job_id, "progress", "%s %d%% %s" % (stage, pct, msg))
        if progress:
            try:
                progress(stage, pct, msg)
            except Exception:
                pass

    def guard() -> None:
        if cancel and cancel():
            raise Cancelled("cancelled by user")
        job = store.get(job_id)
        if job and job["status"] == "cancelled":
            raise Cancelled("cancelled by user")

    result: Dict[str, Any] = {
        "job_id": job_id, "output_dir": job_dir, "artifacts": [],
        "status": "running", "errors": [], "warnings": [],
        "delivery_state": "running",
    }

    def artifact(path: str) -> str:
        result["artifacts"].append(os.path.basename(path))
        return path

    # ---------------------------------------------------------------- research
    store.set_status(job_id, "researching", "reading public sources", 5)
    say(STAGE_RESEARCH, 5, "starting source discovery")
    guard()
    research = research_firm(
        request.firm_name, request.website, request.facebook,
        extra_urls=request.extra_urls,
        fetcher=fetcher, language=request.language,
        progress=lambda m: say(STAGE_RESEARCH, 15, m),
    )
    guard()
    store.update(job_id, params_json=request.to_dict())

    artifact(_write(os.path.join(job_dir, "research_report.md"),
                    report_markdown(research)))
    artifact(_write(os.path.join(job_dir, "evidence_ledger.csv"),
                    ledger_csv(research)))
    _write(os.path.join(job_dir, "research_raw.json"),
           json.dumps({"firm_name": research.firm_name,
                       "sources": [s.__dict__ for s in research.sources],
                       "claims": [c.__dict__ for c in research.claims],
                       "gaps": research.gaps, "notes": research.notes},
                      indent=2, ensure_ascii=False))
    from . import producer
    for p in producer.write_research_package(job_dir, request.firm_name, research):
        artifact(p)
    say(STAGE_RESEARCH, 35,
        "%d sources read, %d blocked, %d claims logged"
        % (sum(1 for s in research.sources if s.state == "INSPECTED"),
           len(research.inaccessible), len(research.claims)))

    if not research.claims:
        result["warnings"].append(
            "No readable public claims were found. The script will contain explicit "
            "gaps — nothing was invented to fill them.")

    # ---------------------------------------------------------------- story
    store.set_status(job_id, "researching", "drafting story", 40)
    guard()
    facts = story_mod.extract_facts(research, request.firm_name,
                                    request.event_date, request.new_office)
    story_paths = story_mod.build_story_assets(
        job_dir, request.firm_name, facts, research,
        request.language, request.style, float(request.duration_sec))
    for p in story_paths.values():
        artifact(p)
    say(STAGE_STORY, 55, "concepts, script, storyboard and scene manifest written")

    with open(story_paths["scene_manifest.json"], "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if overrides:
        # An explicit caller override wins (used by tests and by the CLI's
        # deliberately-non-deliverable fast mode).
        manifest.update(overrides)
        result["render_profile"] = "override"
    else:
        # A deliverable is produced at the Full-HD production profile unless the
        # manifest itself already declares dimensions (advanced/offline callers).
        for key, value in PRODUCTION_PROFILE.items():
            manifest.setdefault(key, value)
        result["render_profile"] = "production"
    spec, spec_errors = video.validate_render_spec(manifest)
    if spec_errors:
        for e in spec_errors:
            result["warnings"].append("spec: " + e)
            store.log_event(job_id, "warn", "spec: " + e)

    voice_note = voice_mod.attach(
        spec, os.path.join(work_dir, "voice"),
        min(spec.transition_sec, min(s["dur"] for s in spec.scenes) * 0.4))
    if voice_note:
        (result["warnings"] if not spec.audio.voiceover else result.setdefault("notes", [])
         ).append("voice: " + voice_note)

    # ------------------------------------------------------- preview clip first
    # Cheap sample rendered *before* the expensive pass so a human can look at
    # something real while deciding whether to approve the full render.
    info = video.backend_info(spec.style)
    if enable_preview and info["ready"]:
        guard()
        say(STAGE_RENDER, 58, "rendering a short preview clip")
        try:
            pspec = _preview_spec(spec)
            preview_out = os.path.join(job_dir, "preview.mp4")
            pres = video.render_style(pspec, preview_out,
                                      os.path.join(work_dir, "preview"),
                                      asset_dir=asset_dir, cancel=cancel,
                                      profile="preview")
            artifact(preview_out)
            result["preview"] = preview_out
            result["preview_validation"] = pres["validation"]
        except Cancelled:
            store.set_status(job_id, "cancelled", "cancelled during preview")
            result["status"] = "cancelled"
            result["delivery_state"] = "cancelled"
            return result
        except Exception as exc:      # a preview must never sink the job
            result["warnings"].append("preview clip failed: %s" % exc)
            store.log_event(job_id, "warn", "preview failed: %s" % exc)

    if request.preview_only:
        say(STAGE_RENDER, 62, "preview-only job: skipping the full render")
        store.set_status(job_id, "completed", "preview only", 100)
        result["status"] = "completed"
        result["delivery_state"] = "preview_only"
        artifact(_write(os.path.join(job_dir, "delivery_report.md"),
                        _delivery_report(job_id, request, research, facts, result,
                                         result.get("preview_validation"), info)))
        return result

    # ------------------------------------------------------------- no-render
    # Research, evidence and the script/storyboard are complete; nothing is
    # rendered. The report must say that plainly — no video is claimed.
    if not enable_render:
        say(STAGE_RENDER, 62,
            "no-render mode: research, evidence and script complete; rendering skipped")
        store.set_status(job_id, "completed",
                         "completed without video (no-render mode)", 100)
        result["status"] = "completed"
        result["no_render"] = True
        result["delivery_state"] = "no_render"
        result["warnings"].append(
            "no-render mode: no preview and no final video were rendered")
        artifact(_write(os.path.join(job_dir, "delivery_report.md"),
                        _delivery_report(job_id, request, research, facts, result,
                                         None, info)))
        return result

    # ---------------------------------------------------------------- approval
    store.set_status(job_id, "awaiting_approval",
                     "waiting for storyboard approval", 60)
    approved = True
    if approve is not None:
        approval_payload = {
            "job_id": job_id,
            "firm": request.firm_name,
            "style": request.style,
            "language": request.language,
            "duration_sec": request.duration_sec,
            "gaps": facts.missing(),
            "preview": result.get("preview"),
            "scenes": [{"id": s["id"], "key": s["key"], "dur": s["dur"],
                        "heading": s["heading"], "narration": s["narration"],
                        "placeholder": s["placeholder"]} for s in spec.scenes],
        }
        approved = bool(approve(approval_payload))
    if not approved:
        store.set_status(job_id, "cancelled", "storyboard rejected by user")
        result["status"] = "cancelled"
        result["delivery_state"] = "rejected"
        return result

    # ---------------------------------------------------------------- render
    store.set_status(job_id, "rendering", "rendering full video", 65)
    guard()
    if not info["ready"]:
        msg = ("backend %r is not ready: %s" % (spec.style, "; ".join(info["reasons"])))
        store.fail(job_id, msg)
        result["status"] = "failed"
        result["delivery_state"] = "failed"
        result["errors"].append(msg)
        _write(os.path.join(job_dir, "delivery_report.md"),
               _delivery_report(job_id, request, research, facts, result, None, info))
        return result

    def render_progress(text: str, pct: int) -> None:
        say(STAGE_RENDER, 65 + int(pct * 0.3), text)

    try:
        full_out = os.path.join(job_dir, "final.mp4")
        rendered = video.render_style(spec, full_out, work_dir, asset_dir=asset_dir,
                                      cancel=cancel, progress=render_progress,
                                      profile=cfg.encode_profile())
        artifact(full_out)
        result["output"] = full_out
        result["validation"] = rendered["validation"]
        _write(os.path.join(job_dir, "render_manifest.json"),
               json.dumps(rendered["manifest"], indent=2, ensure_ascii=False))
        artifact(os.path.join(job_dir, "render_manifest.json"))
    except Cancelled:
        store.set_status(job_id, "cancelled", "cancelled during render")
        result["status"] = "cancelled"
        result["delivery_state"] = "cancelled"
        return result
    except Exception as exc:
        msg = redact("%s: %s" % (type(exc).__name__, exc))[:1500]
        store.fail(job_id, msg)
        result["status"] = "failed"
        result["delivery_state"] = "failed"
        result["errors"].append(msg)
        _write(os.path.join(job_dir, "delivery_report.md"),
               _delivery_report(job_id, request, research, facts, result, None, info))
        return result

    # ---------------------------------------------------------------- report
    # Status is finalised *before* the report is written, so the document
    # records the real outcome rather than the state it was created in.
    result["status"] = "completed"
    result["final_qa"] = final_qa_checks(spec, result.get("validation"), job_dir, request)
    if result["final_qa"]["certified"]:
        result["delivery_state"] = "final_ready"
    else:
        result["delivery_state"] = "final_not_certified"
        for b in result["final_qa"]["blockers"]:
            result["warnings"].append("final QA: " + b)
    store.set_status(job_id, "completed", "finished", 100)
    artifacts = _write(os.path.join(job_dir, "delivery_report.md"),
                       _delivery_report(job_id, request, research, facts, result,
                                        result.get("validation"), info))
    artifact(artifacts)
    return result


def run_job(cfg, store, job_id: str, *args, **kwargs) -> Dict[str, Any]:
    """Public entry point for the one predefined workflow.

    Cancellation is part of normal operation, so it is converted into a clean
    terminal status here rather than being allowed to escape as an exception:
    callers (the bot, the CLI) only ever see a result dictionary.

    A job created with ``staged=True`` (see :mod:`agent_system.pipeline`) is
    handed to the staged workflow, which stops at explicit human gates. Every
    other caller keeps the original single-pass behaviour unchanged.
    """
    request = args[0] if args else kwargs.get("request")
    if isinstance(request, JobRequest) and request.staged:
        from . import pipeline          # imported lazily: pipeline imports this module
        return pipeline.advance_staged(cfg, store, job_id, *args, **kwargs)
    try:
        return _run_job_impl(cfg, store, job_id, *args, **kwargs)
    except Cancelled:
        try:
            store.set_status(job_id, "cancelled", "cancelled by user")
        except Exception:
            pass
        return {"job_id": job_id, "output_dir": cfg.job_dir(job_id),
                "artifacts": [], "status": "cancelled", "errors": [],
                "delivery_state": "cancelled",
                "warnings": ["cancelled by user"]}


def _delivery_report(job_id: str, request: JobRequest, research, facts,
                     result: Dict[str, Any], validation: Optional[Dict[str, Any]],
                     backend_info: Dict[str, Any]) -> str:
    lines = [
        "# Delivery report — job %s" % job_id,
        "",
        "_Generated: %s_" % time.strftime("%Y-%m-%d %H:%M:%S"),
        "",
        "## Request",
        "",
        "- Firm: **%s**" % request.firm_name,
        "- Style: `%s` — %s" % (request.style, backend_info.get("label", "")),
        "- Language: `%s`" % request.language.upper(),
        "- Target duration: %ss" % request.duration_sec,
        "- Website: %s" % (request.website or "—"),
        "- Facebook: %s" % (request.facebook or "—"),
        "",
        "## Status",
        "",
        "**%s**" % result.get("status", "unknown").upper(),
        "",
        "Delivery readiness: **%s**" % result.get("delivery_state", "unknown"),
        "",
    ]
    qa = result.get("final_qa")
    if qa:
        lines += ["## Final QA (fail-closed)", "",
                  "Certified as a publishable final: **%s**" % bool(qa.get("certified")), ""]
        for chk in qa.get("checks") or []:
            lines.append("- [%s] %s — %s"
                         % ("PASS" if chk.get("ok") else "FAIL",
                            chk.get("check"), chk.get("detail")))
        lines.append("")
        if qa.get("blockers"):
            lines += ["**Blocking issues (the file must not be presented as a "
                      "finished film):**", ""] + \
                     ["- %s" % b for b in qa["blockers"]] + [""]
    if result.get("no_render"):
        lines += ["**No video was rendered** — no-render mode was requested: "
                  "this delivery contains research, evidence, script and "
                  "storyboard only. No `preview.mp4` or `final.mp4` exists.", ""]
    if result.get("errors"):
        lines += ["### Errors", ""] + ["- %s" % e for e in result["errors"]] + [""]
    if result.get("warnings"):
        lines += ["### Warnings", ""] + ["- %s" % w for w in result["warnings"]] + [""]

    lines += ["## Sources actually accessed", ""]
    for s in research.sources:
        lines.append("- `%s` %s — **%s** (%s)" % (s.id, s.url, s.state, s.note or "-"))
    lines.append("")
    if research.gaps:
        lines += ["## Missing / blocked evidence", ""] + \
                 ["- %s" % g for g in research.gaps] + [""]

    ev_counts: Dict[str, int] = {}
    for c in research.claims:
        ev_counts[c.evidence_class] = ev_counts.get(c.evidence_class, 0) + 1
    lines += ["## Evidence ledger summary", ""]
    if ev_counts:
        for k in sorted(ev_counts):
            lines.append("- %s: %d" % (k, ev_counts[k]))
    else:
        lines.append("- no claims extracted")
    lines += ["", "Public-safe claims: %d of %d (unverified claims are never "
                  "imported into the film as fact)"
              % (len(research.public_claims()), len(research.claims)), ""]

    lines += ["## Gaps the script had to leave open", ""]
    missing = facts.missing()
    lines += ["- %s" % m for m in missing] if missing else ["- none"]
    lines += [""]

    lines += ["## Asset permissions", "",
              "- Real brand assets used only when supplied by the operator with permission.",
              "- Commissioned photos/illustrations: **not supplied** — placeholders are marked.",
              "- Music: synthesized pad unless a licensed file was supplied "
              "(`synthesized_temporary` is recorded in the render manifest).",
              "- Voice-over: synthetic voice (Microsoft Edge neural TTS) when `AGENT_TTS=edge` "
              "is set and the service was reachable; otherwise none. The render manifest "
              "(`audio_detail`) records which. A synthetic voice must be reviewed by a "
              "native speaker before any public use.",
              ""]

    if validation:
        lines += ["## Technical validation (ffprobe)", "",
                  "- OK: **%s**" % validation.get("ok"),
                  "- Duration: %ss" % validation.get("duration_sec"),
                  "- Size: %s bytes" % validation.get("size_bytes"),
                  "- Video: %s %sx%s @ %sfps" % (validation.get("video_codec"),
                                                 validation.get("width"),
                                                 validation.get("height"),
                                                 validation.get("fps")),
                  "- Audio: %s (%s ch)" % (validation.get("audio_codec"),
                                           validation.get("audio_channels")),
                  ""]
        for c in validation.get("checks", []):
            lines.append("- %s" % c)
        lines += ["", "> %s" % validation.get("note", ""), ""]

    lines += ["## Limitations", ""]
    for lim in backend_info.get("limitations", []):
        lines.append("- %s" % lim)
    lines += ["",
              "## Next steps for a human", "",
              "1. Watch the film end to end — ffprobe cannot judge visual or audio quality.",
              "2. Fill the gaps listed above from interviews and archives.",
              "3. License music and record narration in the target language.",
              "4. Obtain written permission for every real photo and quote used.",
              "5. Approve before any external publication.",
              ""]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- final QA gate
def final_qa_checks(spec, validation, job_dir: str,
                    request: JobRequest) -> Dict[str, Any]:
    """Fail-closed checks a *publishable final* must pass.

    The checks are deliberately data-driven — the render specification, the
    ffprobe validation and the files actually produced — so they are
    deterministic and introduce no new failure modes inside the render itself.
    Any failure marks the output ``final_not_certified``: the file still exists
    (so a human can review it), but it is never presented as a finished film.

    A certified final means: the file is technically valid, **no scene still
    shows an evidence-gap marker**, a synchronised subtitle file exists, and the
    file carries an audio track. Films are never watermarked; an uncertified
    file is flagged in the report and the bot message instead.
    """
    blockers: List[str] = []
    checks: List[Dict[str, Any]] = []

    def add(name: str, ok: bool, good: str, bad: str) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": good if ok else bad})
        if not ok:
            blockers.append(bad)

    v = validation or {}
    add("technical", bool(v.get("ok")),
        "the rendered file passed the technical (ffprobe) checks",
        "the rendered file did not pass the technical (ffprobe) checks")

    gap_scenes = [str(s.get("id") or "?") for s in (getattr(spec, "scenes", None) or [])
                  if s.get("placeholder") or s.get("needs")]
    add("no_gap_markers", not gap_scenes,
        "no scene shows an evidence-gap marker",
        "the film still shows evidence-gap markers on %d scene(s): %s"
        % (len(gap_scenes), ", ".join(gap_scenes)))

    srt = os.path.join(job_dir, "subtitles.srt")
    has_srt = os.path.isfile(srt) and os.path.getsize(srt) > 0
    add("subtitles", has_srt,
        "a synchronised subtitle file (subtitles.srt) is present",
        "no synchronised subtitle file (subtitles.srt) was produced")

    add("audio", bool(v.get("audio_codec")),
        "the file carries an audio track",
        "the file has no audio track")

    return {"certified": not blockers, "checks": checks, "blockers": blockers}
