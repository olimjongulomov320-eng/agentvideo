# -*- coding: utf-8 -*-
"""cli.py — command-line interface.

    python3 -m agent_system serve              # run the Telegram bot
    python3 -m agent_system health             # capabilities + backend readiness
    python3 -m agent_system styles             # list the three animation styles
    python3 -m agent_system run-job --firm "..." --website https://... --style motion
    python3 -m agent_system run-job --no-render        # research + story only
    python3 -m agent_system check-spec path/to/scene_manifest.json
    python3 -m agent_system selftest           # render a 6-second test clip per backend
"""
import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from . import video
from .config import Config
from .jobs import JobStore
from .orchestrator import JobRequest, run_job, sanitize_request
from .security import redact


def _cfg() -> Config:
    return Config.from_env()


def cmd_health(args) -> int:
    cfg = _cfg()
    cfg.ensure_dirs()
    print(json.dumps(cfg.summary(), indent=2))
    print("\nBackends:")
    for info in video.list_backends():
        print("  %-12s ready=%-5s %s" % (info["style"], info["ready"],
                                         "; ".join(info.get("reasons", [])) or "ok"))
    return 0


def cmd_styles(args) -> int:
    for info in video.list_backends():
        print("%-12s %-30s %s" % (info["style"], info["label"],
                                  "READY" if info["ready"] else "UNAVAILABLE"))
        for r in info.get("reasons", []):
            print("    ! %s" % r)
        for lim in info.get("limitations", []):
            print("    - %s" % lim)
    return 0


def cmd_serve(args) -> int:
    from .telegrambot.bot import main as bot_main
    return bot_main()


def cmd_run_job(args) -> int:
    cfg = _cfg()
    cfg.ensure_dirs()
    store = JobStore(cfg.db_path)
    raw = {
        "firm_name": args.firm, "website": args.website or "",
        "facebook": args.facebook or "", "language": args.language,
        "style": args.style, "duration_sec": args.duration,
        "new_office": args.new_office or "", "event_date": args.event_date or "",
        "extra_urls": args.extra or [], "preview_only": bool(args.preview_only),
    }
    req = sanitize_request(raw)
    job_id = store.create(0, req.style, req.language, req.firm_name,
                          req.duration_sec, None, params=req.to_dict())

    def progress(stage: str, pct: int, msg: str) -> None:
        print("[%3d%%] %-10s %s" % (pct, stage, redact(msg)))

    def approve(payload: Dict[str, Any]) -> bool:
        if args.auto_approve:
            print("[approval] auto-approved (%d scenes, gaps: %s)"
                  % (len(payload["scenes"]), ", ".join(payload["gaps"]) or "none"))
            return True
        print("[approval] storyboard written to %s" % cfg.job_dir(job_id))
        return False

    overrides = {}
    if args.fast:
        from .config import PREVIEW_PROFILE
        overrides = dict(PREVIEW_PROFILE)
        print("! --fast is a PREVIEW profile (%dx%d@%d) — the result is NOT a "
              "deliverable. Omit --fast for Full-HD production output."
              % (overrides["width"], overrides["height"], overrides["fps"]))
    if args.no_render:
        os.environ.setdefault("AGENT_NO_RENDER", "1")

    result = run_job(cfg, store, job_id, req, progress=progress, approve=approve,
                     overrides=overrides,
                     enable_preview=not args.no_preview,
                     enable_render=not args.no_render,
                     )
    print("\nJob %s → %s" % (job_id, result.get("status")))
    print("Output directory: %s" % cfg.job_dir(job_id))
    for a in result.get("artifacts", []):
        print("  • %s" % a)
    if result.get("output"):
        print("Video: %s" % result["output"])
    if result.get("errors"):
        for e in result["errors"]:
            print("  error: %s" % e)
    return 0 if result.get("status") == "completed" else 1


def cmd_check_spec(args) -> int:
    with open(args.path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    spec, errors = video.validate_render_spec(raw)
    print("valid: %s" % (not errors))
    for e in errors:
        print("  ! %s" % e)
    print("style=%s scenes=%d total=%.2fs %dx%d@%d"
          % (spec.style, len(spec.scenes), spec.total_duration,
             spec.width, spec.height, spec.fps))
    return 0 if not errors else 1


def cmd_selftest(args) -> int:
    """Render a very short clip with each available backend (real render, real probe)."""
    from .video import common
    cfg = _cfg()
    cfg.ensure_dirs()
    out_root = os.path.join(cfg.output_dir, "selftest")
    os.makedirs(out_root, exist_ok=True)

    scenes: List[Dict[str, Any]] = [
        {"id": "t1", "key": "hook", "kind": "statement", "dur": 2.0,
         "heading": "Selftest", "sub": "", "narration": "selftest", "placeholder": False},
        {"id": "t2", "key": "stat", "kind": "stat", "dur": 2.0,
         "heading": "2010", "sub": "selftest card", "narration": "selftest",
         "placeholder": False},
        {"id": "t3", "key": "closing", "kind": "endcard", "dur": 2.0,
         "heading": "Selftest", "sub": "DEMO", "narration": "selftest",
         "placeholder": False},
    ]
    raw = {"firm_name": "Selftest", "language": "en", "style": "motion",
           "width": 480, "height": 270, "fps": 12, "scenes": scenes,
           "audio": {"license": "synthesized_temporary"}, "watermark": "SELFTEST"}
    results = {}
    for style in ("motion", "illustrated", "blender3d"):
        raw["style"] = style
        spec, errors = video.validate_render_spec(raw)
        info = video.backend_info(style)
        entry: Dict[str, Any] = {"ready": info["ready"], "errors": errors}
        if not info["ready"]:
            entry["skipped"] = "; ".join(info["reasons"])
            results[style] = entry
            continue
        out = os.path.join(out_root, "selftest_%s.mp4" % style)
        try:
            r = video.render_style(spec, out, os.path.join(out_root, "work_" + style))
            entry.update({"ok": r["validation"]["ok"],
                          "duration": r["validation"]["duration_sec"],
                          "size": r["validation"]["size_bytes"],
                          "output": out})
        except Exception as exc:
            entry.update({"ok": False, "exception": "%s: %s" % (type(exc).__name__, exc)})
        results[style] = entry
    print(json.dumps(results, indent=2))
    with open(os.path.join(out_root, "selftest_report.json"), "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    return 0


def cmd_qa(args) -> int:
    """Run the visual QA pass on an existing MP4 (technical + heuristics + sheet)."""
    from .video import qa as qa_mod
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.video)), "qa")
    report = qa_mod.qa_video(
        args.video, out_dir,
        expect_width=args.width or None, expect_height=args.height or None,
        expect_fps=args.fps or None, require_audio=not args.no_audio,
        label=args.label or "")
    tech = report.get("technical", {}) or {}
    print("QA report: %s" % os.path.join(out_dir, "qa_report.md"))
    print("  file      : %s" % report.get("video"))
    print("  duration  : %ss" % tech.get("duration_sec"))
    print("  video     : %s %sx%s @ %sfps" % (tech.get("video_codec"), tech.get("width"),
                                              tech.get("height"), tech.get("fps")))
    print("  audio     : %s (%s ch)" % (tech.get("audio_codec"), tech.get("audio_channels")))
    print("  size      : %s bytes" % tech.get("size_bytes"))
    print("  contact   : %s" % report.get("contact_sheet"))
    for e in report.get("errors", []):
        print("  FAILURE   : %s" % e)
    for f in report.get("findings", []):
        print("  finding   : %s" % f)
    if not report.get("findings") and not report.get("errors"):
        print("  note      : no automated flag — human review still required")
    return 1 if report.get("errors") else 0


def cmd_render_qa(args) -> int:
    """Render the self-contained QA fixture (Full-HD by default) and QA it.

    The fixture is synthetic test content, never a client film; it exists to
    demonstrate and inspect the renderer and the QA pipeline.
    """
    from . import qa_fixture
    cfg = _cfg()
    cfg.ensure_dirs()
    out_dir = args.out or os.path.join(cfg.output_dir, "qa")
    os.makedirs(out_dir, exist_ok=True)

    def progress(text: str, pct: int) -> None:
        print("[%3d%%] %s" % (pct, text), flush=True)

    video_path, result, report = qa_fixture.run_qa(
        out_dir, style=args.style, width=args.width, height=args.height,
        fps=args.fps, profile=args.profile, progress=progress)
    tech = report.get("technical", {}) or {}
    print("\nQA fixture video : %s" % video_path)
    print("  validated    : %s" % (result.get("validation", {}).get("ok")))
    print("  duration     : %ss" % tech.get("duration_sec"))
    print("  video        : %s %sx%s @ %sfps" % (tech.get("video_codec"), tech.get("width"),
                                                tech.get("height"), tech.get("fps")))
    print("  audio        : %s (%s ch)" % (tech.get("audio_codec"), tech.get("audio_channels")))
    print("  size         : %s bytes" % tech.get("size_bytes"))
    print("  contact sheet: %s" % report.get("contact_sheet"))
    print("  report       : %s" % os.path.join(out_dir, "qa_%s" % args.style, "qa_report.md"))
    for f in report.get("findings", []):
        print("  finding      : %s" % f)
    for e in report.get("errors", []):
        print("  FAILURE      : %s" % e)
    print("\nNOTE: automated checks are heuristics; a human must watch the film.")
    return 0 if tech.get("width") else 1


def cmd_transcribe_info(args) -> int:
    """Report, honestly, which local speech-to-text engines exist on this machine."""
    from .transcripts import detect_speech_backends
    info = detect_speech_backends()
    print(json.dumps(info, indent=2, ensure_ascii=False))
    if not info["available"]:
        print("\nAudio cannot be transcribed here. Supply the interview as SRT / "
              "VTT / TXT / JSON and run 'analyse-interview' on it.")
    return 0 if info["available"] else 1


def cmd_analyse_interview(args) -> int:
    """Parse a supplied transcript, extract attributed statements, write findings."""
    from .transcripts import analyse_file, write_analysis
    out_dir = args.out or os.path.join(os.path.dirname(os.path.abspath(args.path)), "analysis")
    analysis = analyse_file(args.path, language=args.language or "")
    paths = write_analysis(out_dir, analysis)
    print("Transcript : %s (%s, produced by %s)" % (
        analysis.source_name, analysis.language or "language unspecified",
        analysis.produced_by))
    print("Speakers   : %s" % (", ".join(analysis.speakers) or "not labelled"))
    print("Statements : %d attributed (all SINGLE-SOURCE until corroborated)"
          % len(analysis.claims))
    print("Questions  : %d recorded as context" % len(analysis.questions))
    print("Inaudible  : %d segment(s) — recorded as gaps, not guessed" %
          len(analysis.inaudible_segments))
    print("Privacy    : %s" % (", ".join(analysis.privacy_flags) or "no markers found "
                               "(this does NOT mean the material is cleared)"))
    print("Flagged    : %s" % ", ".join(
        "%s=%d" % (k, len(v)) for k, v in sorted(analysis.flagged_terms.items())) or "none")
    for g in analysis.gaps:
        print("  gap      : %s" % g)
    print()
    for label, path in paths.items():
        print("  wrote    : %s" % path)
    print("\nNOTE: no statement is cleared for publication by this command.")
    return 0


def cmd_interview_plans(args) -> int:
    """Build per-role interview questionnaires, driven by the evidence gaps."""
    from .interviews import build_all, write_plans
    from .research import claims_from_ledger_csv, ResearchResult
    from .story import extract_facts

    missing: List[str] = []
    open_questions: List[str] = []
    if args.ledger:
        with open(args.ledger, "r", encoding="utf-8", errors="replace") as fh:
            claims = claims_from_ledger_csv(fh.read())
        res = ResearchResult(firm_name=args.firm)
        res.claims = claims
        facts = extract_facts(res, args.firm, event_date=args.event_date or "",
                              new_office=args.new_office or "")
        missing = facts.missing()
        open_questions = ["No claim in the ledger establishes '%s'" % m for m in missing]
        if not claims:
            open_questions.append("The ledger contained no claims at all.")
    else:
        missing = ["founding_year", "practice_areas", "new_office", "achievement"]
        open_questions = ["No evidence ledger supplied — every core fact is open."]

    plans = build_all(args.firm, missing_facts=missing, open_questions=open_questions,
                      interviewees={})
    out_dir = args.out or os.path.join(os.getcwd(), "interviews")
    written = write_plans(out_dir, plans, force=bool(args.force))
    print("Firm        : %s" % args.firm)
    print("Gaps driven : %s" % (", ".join(missing) or "none"))
    print("Output dir  : %s" % out_dir)
    for role, path in written.items():
        if path:
            print("  wrote     : %s" % path)
        else:
            print("  skipped   : %s (already exists — pass --force to overwrite)"
                  % role)
    print("\nNOTE: the agent does not contact or interview anyone. A human "
          "conducts the interview and supplies the recording or transcript.")
    return 0


def cmd_chronology(args) -> int:
    """Build a cited chronology from a saved evidence ledger."""
    from .chronology import build_timeline, write_timeline
    from .research import claims_from_ledger_csv

    ledger = args.ledger
    if os.path.isdir(ledger):
        ledger = os.path.join(ledger, "evidence_ledger.csv")
    if not os.path.exists(ledger):
        print("ledger not found: %s" % ledger)
        return 1
    with open(ledger, "r", encoding="utf-8", errors="replace") as fh:
        claims = claims_from_ledger_csv(fh.read())
    timeline = build_timeline(args.firm, claims)
    out_dir = args.out or os.path.dirname(os.path.abspath(ledger))
    paths = write_timeline(out_dir, timeline)
    print("Claims read    : %d" % len(claims))
    print("Dated entries  : %d (%d documented)" % (
        len(timeline.entries), sum(1 for e in timeline.entries if e.documented)))
    print("Undated claims : %d (kept, not dated by guesswork)" % len(timeline.undated))
    print("Contradictions : %d" % len(timeline.conflicts))
    for c in timeline.conflicts:
        print("  conflict     : %s" % c)
    for g in timeline.gaps:
        print("  gap          : %s" % g)
    print()
    for label, path in paths.items():
        print("  wrote        : %s" % path)
    return 0


def _read_json(path: str):
    """Read a JSON object, distinguishing absent from malformed.

    Returns ``("ok", dict)``, ``("missing", None)`` or ``("malformed", None)``.
    The distinction matters: an absent chronology can honestly be represented by
    the research-stage snapshot, but a *corrupt* one must not be silently
    replaced by a stale count.
    """
    if not os.path.isfile(path):
        return "missing", None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return "malformed", None
    if not isinstance(data, dict):
        return "malformed", None
    return "ok", data


def _print_job_plan(cfg, store, job_id: str) -> None:
    """Show where a staged job stands: completed steps and the next gate."""
    from . import pipeline

    job = store.get(job_id)
    if not job:
        print("no such job: %s" % job_id)
        return
    job_dir = cfg.job_dir(job_id)
    state = pipeline.read_state(job_dir)
    step = pipeline.current_step(state)
    print("Job %s" % job_id)
    print("  firm        : %s" % job.get("firm_name"))
    print("  status      : %s  (%s)" % (job.get("status"), job.get("message") or "-"))
    print("  progress    : %s%%" % job.get("progress"))
    print("  completed   : %s" % (", ".join(state.get("completed") or []) or "none"))
    print("  next step   : %s" % step)
    approvals = state.get("approvals") or {}
    if approvals:
        for gate in sorted(approvals):
            when = (approvals[gate] or {}).get("at", "?")
            extra = (approvals[gate] or {}).get("concept", "")
            print("  approved    : %s at %s%s"
                  % (gate, when, (" (concept %s)" % extra) if extra else ""))
    if state.get("transcripts"):
        print("  transcripts : %d supplied" % len(state["transcripts"]))
    transcript_status = state.get("transcripts_status") or {}
    if transcript_status:
        for path in sorted(transcript_status):
            record = transcript_status[path] or {}
            note = record.get("status") or "unknown"
            if record.get("reused"):
                note += ", unchanged since the last run"
            print("    - %s: %s" % (os.path.basename(path), note))

    # The chronology is the canonical persisted record. The research summary is
    # a snapshot written at the research step and goes stale the moment
    # transcript analysis adds or contradicts a statement, so it must never be
    # the last word on contradictions.
    summary_state, summary = _read_json(
        os.path.join(job_dir, "research_summary.json"))
    chrono_state, chrono = _read_json(
        os.path.join(job_dir, "chronology", "chronology.json"))

    if summary_state == "ok":
        print("  evidence    : %d sources read, %d blocked, %d claims (%d public-safe)"
              % (summary.get("sources_read", 0), summary.get("sources_blocked", 0),
                 summary.get("claims_total", 0), summary.get("claims_public_safe", 0)))

    if chrono_state == "ok":
        conflicts = sorted(set(chrono.get("conflicts") or []))
        print("  chronology  : %d dated, %d undated, %d conflict(s)"
              % (len(chrono.get("entries") or []), len(chrono.get("undated") or []),
                 len(conflicts)))
        for conflict in conflicts:
            print("    conflict  : %s" % conflict)
    elif chrono_state == "malformed":
        # The chronology exists but cannot be read. Reporting the stale snapshot
        # here would be a quiet lie about the current count, so say so instead.
        print("  chronology  : unknown (the stored chronology could not be read; "
              "no conflict count is shown rather than a stale one)")
    elif summary_state == "ok":
        # No chronology on disk yet: the research-stage snapshot is the only
        # record, and it is labelled as a snapshot so a stale "0" is never
        # mistaken for the current count.
        print("  chronology  : %d dated, %d undated, %d conflict(s) "
              "(research-stage snapshot — no chronology on disk yet)"
              % (summary.get("dated_events", 0), summary.get("undated_claims", 0),
                 len(set(summary.get("conflicts") or []))))
    else:
        print("  chronology  : unknown (neither the chronology nor a research "
              "summary could be read)")
    print("  output dir  : %s" % job_dir)
    if step != "done":
        gate = pipeline.gate_for_step(step)
        if gate and gate not in approvals:
            print("  waiting for : approval of %s  (status %s)"
                  % (gate, pipeline.gate_status(step)))
    else:
        print("  waiting for : nothing — every staged step has run")


def cmd_run_staged(args) -> int:
    """Run the staged workflow until it pauses at the first human gate."""
    from . import pipeline

    cfg = _cfg()
    cfg.ensure_dirs()
    store = JobStore(cfg.db_path)
    raw = {
        "firm_name": args.firm, "website": args.website or "",
        "facebook": args.facebook or "", "language": args.language,
        "style": args.style, "duration_sec": args.duration,
        "new_office": args.new_office or "", "event_date": args.event_date or "",
        "extra_urls": args.extra or [], "staged": True,
    }
    req = sanitize_request(raw)
    job_id = store.create(0, req.style, req.language, req.firm_name,
                          req.duration_sec, None, params=req.to_dict())
    print("staged job %s created for %s" % (job_id, req.firm_name))
    print("! the job stops after research; no script is written and no video is "
          "rendered until you approve each gate.")
    return _advance_and_report(cfg, store, job_id, args)


def cmd_review(args) -> int:
    """Record a human decision on a paused staged job and advance it."""
    from . import pipeline

    cfg = _cfg()
    store = JobStore(cfg.db_path)
    job_id = args.job
    if args.show:
        _print_job_plan(cfg, store, job_id)
        return 0
    job = store.get(job_id)
    if not job:
        print("no such job: %s" % job_id)
        return 1
    kwargs = {}
    if args.approve_research:
        kwargs["approve_research"] = True
    if args.concept:
        kwargs["approve_concept"] = args.concept
    if args.approve_storyboard:
        kwargs["approve_storyboard"] = True
    if args.transcript:
        kwargs["transcripts"] = list(args.transcript)
    if getattr(args, "allow_missing_transcripts", False):
        kwargs["allow_missing_transcripts"] = True
    if args.note:
        kwargs["note"] = args.note
    if args.force:
        kwargs["force"] = True
    if not kwargs:
        print("nothing to do: pass --approve-research, --concept, "
              "--approve-storyboard, --transcript or --show")
        return 1
    # A staged job may be resumed from the database alone: params are stored.
    return _advance_and_report(cfg, store, job_id, args, **kwargs)


def _advance_and_report(cfg, store, job_id: str, args, **kwargs) -> int:
    from . import pipeline

    request = None
    job = store.get(job_id) or {}
    raw = job.get("params_json") or "{}"
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            raw = {}
    if isinstance(raw, dict):
        request = sanitize_request(raw)

    def progress(stage: str, pct: int, msg: str) -> None:
        print("[%3d%%] %-10s %s" % (pct, stage, redact(msg)))

    overrides = {}
    if getattr(args, "fast", False):
        from .config import PREVIEW_PROFILE
        overrides = dict(PREVIEW_PROFILE)
        print("! --fast is a PREVIEW profile (%dx%d@%d) — NOT a deliverable."
              % (overrides["width"], overrides["height"], overrides["fps"]))
    no_render = bool(getattr(args, "no_render", False))
    if no_render:
        os.environ.setdefault("AGENT_NO_RENDER", "1")

    try:
        result = pipeline.advance_staged(
            cfg, store, job_id, request, progress=progress,
            overrides=overrides,
            enable_preview=not getattr(args, "no_preview", False),
            enable_render=not no_render, **kwargs)
    except pipeline.PipelineError as exc:
        print("cannot advance job %s: %s" % (job_id, exc))
        return 1

    print()
    print("Job %s → %s" % (job_id, result.get("status")))
    if result.get("gate"):
        print("Paused at the %s gate." % result["gate"])
    for a in result.get("artifacts", []):
        print("  artifact    : %s" % a)
    if result.get("output"):
        print("  video       : %s" % result["output"])
    for w in result.get("warnings", []):
        print("  warning     : %s" % w)
    for e in result.get("errors", []):
        print("  error       : %s" % e)
    if result.get("review"):
        print()
        print(pipeline.format_review(result["review"]))
    print("Run `python3 -m agent_system job-status %s` for the full picture."
          % job_id)
    return 0 if result.get("status") in ("completed",) or result.get("gate") else 1


def cmd_job_status(args) -> int:
    cfg = _cfg()
    store = JobStore(cfg.db_path)
    _print_job_plan(cfg, store, args.job)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="agent_system",
                                description="Law-firm research & video production system")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="run the Telegram bot").set_defaults(func=cmd_serve)
    sub.add_parser("health", help="capabilities and backend readiness").set_defaults(func=cmd_health)
    sub.add_parser("styles", help="list animation styles").set_defaults(func=cmd_styles)
    sub.add_parser("selftest", help="render a short clip per backend").set_defaults(func=cmd_selftest)

    rj = sub.add_parser("run-job", help="run a full job headlessly")
    rj.add_argument("--firm", required=True)
    rj.add_argument("--website", default="")
    rj.add_argument("--facebook", default="")
    rj.add_argument("--extra", action="append", default=[])
    rj.add_argument("--language", default="en")
    rj.add_argument("--style", default="motion",
                    choices=["motion", "illustrated", "blender3d"])
    rj.add_argument("--duration", type=int, default=140)
    rj.add_argument("--new-office", dest="new_office", default="")
    rj.add_argument("--event-date", dest="event_date", default="")
    rj.add_argument("--auto-approve", dest="auto_approve", action="store_true", default=True)
    rj.add_argument("--no-auto-approve", dest="auto_approve", action="store_false")
    rj.add_argument("--no-render", dest="no_render", action="store_true")
    rj.add_argument("--no-preview", dest="no_preview", action="store_true",
                    help="skip the short preview clip")
    rj.add_argument("--fast", action="store_true",
                    help="PREVIEW ONLY: render at the preview profile for quick checks "
                         "(never a deliverable)")
    rj.add_argument("--preview-only", dest="preview_only", action="store_true",
                    help="research + story + short preview only (no full render)")
    rj.set_defaults(func=cmd_run_job)

    cs = sub.add_parser("check-spec", help="validate a scene manifest")
    cs.add_argument("path")
    cs.set_defaults(func=cmd_check_spec)

    qa = sub.add_parser("qa", help="visual QA on an existing MP4 "
                                   "(technical + heuristics + contact sheet)")
    qa.add_argument("video")
    qa.add_argument("--out", default="", help="output directory for the QA report")
    qa.add_argument("--label", default="", help="human label for the artifact")
    qa.add_argument("--width", type=int, default=0, help="expected width")
    qa.add_argument("--height", type=int, default=0, help="expected height")
    qa.add_argument("--fps", type=int, default=0, help="expected fps")
    qa.add_argument("--no-audio", dest="no_audio", action="store_true",
                    help="do not require an audio stream")
    qa.set_defaults(func=cmd_qa)

    rqa = sub.add_parser("render-qa", help="render the synthetic QA fixture and QA it")
    rqa.add_argument("--style", default="motion",
                     choices=["motion", "illustrated", "blender3d"])
    rqa.add_argument("--width", type=int, default=1920)
    rqa.add_argument("--height", type=int, default=1080)
    rqa.add_argument("--fps", type=int, default=30)
    rqa.add_argument("--profile", default="production", choices=["production", "preview"])
    rqa.add_argument("--out", default="")
    rqa.set_defaults(func=cmd_render_qa)

    sub.add_parser("transcribe-info",
                   help="report which local speech-to-text engines exist "
                        "(no network, no paid API)").set_defaults(func=cmd_transcribe_info)

    ai = sub.add_parser("analyse-interview",
                        help="parse a supplied transcript (SRT/VTT/TXT/JSON) and "
                             "extract attributed, timestamped statements")
    ai.add_argument("path", help="the transcript file the user supplied")
    ai.add_argument("--language", default="", choices=["", "en", "ru", "uz"])
    ai.add_argument("--out", default="", help="output directory for the analysis")
    ai.set_defaults(func=cmd_analyse_interview)

    ip = sub.add_parser("interview-plans",
                        help="generate per-role interview questionnaires from the "
                             "evidence gaps (never overwrites a finished plan)")
    ip.add_argument("--firm", required=True)
    ip.add_argument("--ledger", default="", help="evidence_ledger.csv used to derive gaps")
    ip.add_argument("--event-date", dest="event_date", default="")
    ip.add_argument("--new-office", dest="new_office", default="")
    ip.add_argument("--out", default="", help="output directory (default ./interviews)")
    ip.add_argument("--force", action="store_true",
                    help="overwrite an existing questionnaire (do NOT use on a "
                         "reviewed plan)")
    ip.set_defaults(func=cmd_interview_plans)

    ch = sub.add_parser("chronology",
                        help="build a cited, confidence-labelled chronology from a "
                             "saved evidence ledger")
    ch.add_argument("ledger", help="evidence_ledger.csv, or a job directory containing it")
    ch.add_argument("--firm", required=True)
    ch.add_argument("--out", default="", help="output directory")
    ch.set_defaults(func=cmd_chronology)

    # ---- staged (human-gated) documentary workflow ----
    def _add_common(sp):
        sp.add_argument("--fast", action="store_true",
                        help="PREVIEW profile (not a deliverable); for smoke runs")
        sp.add_argument("--no-preview", dest="no_preview", action="store_true",
                        help="do not render the short preview clip")
        sp.add_argument("--no-render", dest="no_render", action="store_true",
                        help="research/script only: never start ffmpeg")

    rs = sub.add_parser("run-staged",
                        help="start the staged workflow; it pauses after research "
                             "and writes no script or video until you approve")
    rs.add_argument("--firm", required=True)
    rs.add_argument("--website", default="")
    rs.add_argument("--facebook", default="")
    rs.add_argument("--extra", action="append", default=[])
    rs.add_argument("--language", default="en")
    rs.add_argument("--style", default="motion",
                    choices=["motion", "illustrated", "blender3d"])
    rs.add_argument("--duration", type=int, default=140)
    rs.add_argument("--event-date", dest="event_date", default="")
    rs.add_argument("--new-office", dest="new_office", default="")
    _add_common(rs)
    rs.set_defaults(func=cmd_run_staged)

    rv = sub.add_parser("review",
                        help="record a human decision on a paused job and advance it")
    rv.add_argument("job", help="job id, e.g. J7F3K2Q9")
    rv.add_argument("--show", action="store_true",
                    help="only print the job's current state")
    rv.add_argument("--approve-research", dest="approve_research",
                    action="store_true",
                    help="the public evidence is sufficient to continue")
    rv.add_argument("--concept", default="",
                    help="approve a concept by id (e.g. A, B, C) before scripting")
    rv.add_argument("--approve-storyboard", dest="approve_storyboard",
                    action="store_true", help="approve rendering the full video")
    rv.add_argument("--transcript", action="append", default=[],
                    help="a transcript file you already hold (never fetched)")
    rv.add_argument("--allow-missing-transcripts", dest="allow_missing_transcripts",
                    action="store_true",
                    help="accept that a supplied transcript could not be read and "
                         "continue without it (records the gap as a human decision)")
    rv.add_argument("--note", default="", help="why the decision was taken")
    rv.add_argument("--force", action="store_true",
                    help="resume a job the service marked failed after a restart")
    _add_common(rv)
    rv.set_defaults(func=cmd_review)

    js = sub.add_parser("job-status", help="show a staged job's phase and gates")
    js.add_argument("job")
    js.set_defaults(func=cmd_job_status)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted")
        return 130


if __name__ == "__main__":
    sys.exit(main())
