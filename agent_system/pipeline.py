# -*- coding: utf-8 -*-
"""pipeline.py — the staged, human-gated documentary workflow.

Why this module exists
----------------------
:func:`agent_system.orchestrator._run_job_impl` is the original single-pass
workflow::

    research -> story (concepts+script+storyboard) -> [approve] -> render

That path is left exactly as it was, because delivered jobs and the existing
test suite depend on it. This module adds the *staged* workflow that serious
history reconstruction needs: research must first produce an evidence-based
chronology, an explicit gap list and per-role interview plans; the job then
stops and reports, and **no final script is written and no video is rendered
until a person has approved the research and chosen a concept**.

Phases and gates
----------------
::

    step "evidence"     research + chronology + gap list + interview plans
      -> GATE research    (status: awaiting_research_review)
    step "transcripts"  analyse supplied interviews, update the chronology
    step "concepts"     generate/regenerate the three concepts
      -> GATE concept     (status: awaiting_concept_review)
    step "script"       script + storyboard + scene manifest + preview
      -> GATE storyboard  (status: awaiting_approval)  [pre-existing gate]
    step "render"       full render -> ffprobe validation -> delivery report

The ``transcripts`` step only exists when transcript files were supplied.

Resumability
------------
The phase, the approvals and the transcript list live in
``<job_dir>/pipeline_state.json``, and the evidence lives in the job directory.
A job paused today can therefore be resumed days later — and after a service
restart, which is why the marker file, not the database row, is the authority on
*how far the work got*. The database row is the authority on *whether a phase
may run at all* (it is the duplicate-execution guard).

Honesty rules enforced here
---------------------------
* Nothing is fabricated: a gap stays a gap and is reported as a gap.
* An interview statement is evidence of what was *said*, never that it is true.
  Every interview claim enters as ``SINGLE-SOURCE``.
* Client-identifying or privileged statements are quarantined from the film,
  never merged into the citation set.
* A finished deliverable is never overwritten: every re-run writes into
  ``revisions/rN/``.
* No render starts without an explicit approval for that gate.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from . import chronology as chronology_mod
from . import interviews as interviews_mod
from . import story as story_mod
from . import transcripts as transcripts_mod
from . import video
from . import voice as voice_mod
from .config import PRODUCTION_PROFILE
from .jobs import RESUMABLE_STATES
from .orchestrator import (
    Cancelled, JobRequest, _delivery_report, _preview_spec, _write,
    final_qa_checks,
)
from .research import ledger_csv, load_raw, report_markdown, research_firm
from .security import redact

# ----------------------------------------------------------------- step names
STEP_EVIDENCE = "evidence"
STEP_TRANSCRIPTS = "transcripts"
STEP_CONCEPTS = "concepts"
STEP_SCRIPT = "script"
STEP_RENDER = "render"
STEP_ORDER = (STEP_EVIDENCE, STEP_TRANSCRIPTS, STEP_CONCEPTS, STEP_SCRIPT,
              STEP_RENDER)

STATUS_EVIDENCE_GATE = "awaiting_research_review"
STATUS_CONCEPT_GATE = "awaiting_concept_review"
STATUS_STORY_GATE = "awaiting_approval"
PAUSED_STATUSES = (STATUS_EVIDENCE_GATE, STATUS_CONCEPT_GATE, STATUS_STORY_GATE)

# The artefacts a storyboard approval covers. The approval's stored hash is
# computed over exactly these files; if any of them changes, the sign-off is
# stale and must be re-obtained before a render is allowed to start.
RESEARCH_ARTIFACTS = (
    "research_report.md", "evidence_ledger.csv",
    "research_raw.json", "research_summary.json",
)
CONCEPT_ARTIFACTS = RESEARCH_ARTIFACTS + ("concepts.md",)
STORYBOARD_ARTIFACTS = CONCEPT_ARTIFACTS + (
    "script.md", "storyboard.md", "scene_manifest.json",
)  # production_brief.md rides along but is not a gate input

STATE_FILENAME = "pipeline_state.json"
CHRONOLOGY_DIRNAME = "chronology"
INTERVIEWS_DIRNAME = "interviews"
ANALYSIS_DIRNAME = "analysis"
REVISIONS_DIRNAME = "revisions"


class PipelineError(RuntimeError):
    """A staged job cannot be advanced; the reason is user-facing and specific."""


# ----------------------------------------------------------------- marker file
def state_path(job_dir: str) -> str:
    return os.path.join(job_dir, STATE_FILENAME)


def read_state(job_dir: str) -> Dict[str, Any]:
    """Read the phase marker. A missing/corrupt marker is empty, never assumed."""
    path = state_path(job_dir)
    if not os.path.isfile(path):
        return {"completed": [], "approvals": {}, "revision": 0}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {"completed": [], "approvals": {}, "revision": 0}
    if not isinstance(data, dict):
        return {"completed": [], "approvals": {}, "revision": 0}
    data.setdefault("completed", [])
    data.setdefault("approvals", {})
    data.setdefault("revision", 0)
    return data


def write_state(job_dir: str, **updates: Any) -> Dict[str, Any]:
    state = read_state(job_dir)
    state.update(updates)
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    os.makedirs(job_dir, exist_ok=True)
    with open(state_path(job_dir), "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
    return state


def next_revision_dir(job_dir: str) -> Tuple[str, int]:
    """Return ``(path, number)`` for a fresh revision directory.

    Re-runs never touch an earlier round's files, so an approved concept or a
    reviewed chronology cannot be silently replaced.
    """
    base = os.path.join(job_dir, REVISIONS_DIRNAME)
    n = 1
    while os.path.exists(os.path.join(base, "r%d" % n)):
        n += 1
    path = os.path.join(base, "r%d" % n)
    os.makedirs(path, exist_ok=True)
    return path, n


# ------------------------------------------------------------------ gate text
def _gate_line(ok: bool, text: str) -> str:
    return "%s %s" % ("PASS" if ok else "STOP", text)


def review_summary(job_id: str, request: JobRequest, research,
                   timeline, written: Dict[str, Any]) -> Dict[str, Any]:
    """Everything a human needs to decide whether the research is sufficient."""
    ev_counts: Dict[str, int] = {}
    for c in research.claims:
        ev_counts[c.evidence_class] = ev_counts.get(c.evidence_class, 0) + 1
    return {
        "job_id": job_id,
        "firm": request.firm_name,
        "sources_read": sum(1 for s in research.sources
                            if s.state == "INSPECTED"),
        "sources_blocked": len(research.inaccessible),
        "claims_total": len(research.claims),
        "claims_public_safe": len(research.public_claims()),
        "evidence_classes": ev_counts,
        "dated_events": len(timeline.entries),
        "undated_claims": len(timeline.undated),
        "conflicts": list(timeline.conflicts),
        "gaps": list(research.gaps) + list(timeline.gaps),
        "interview_plans": sorted(k for k in written.get("plans", {})
                                  if k in interviews_mod.ROLES),
        "question": ("Is the public evidence sufficient to draft the film, or "
                     "must interviews close the gaps first? Nothing has been "
                     "scripted and nothing will be rendered until you approve."),
    }


def format_review(summary: Dict[str, Any]) -> str:
    """Plain-text rendering of :func:`review_summary` for a terminal."""
    lines = [
        "Job %s — research review for %s" % (summary["job_id"], summary["firm"]),
        "",
        "Sources read: %d   blocked/error: %d" % (summary["sources_read"],
                                                  summary["sources_blocked"]),
        "Claims: %d total, %d cleared for public use"
        % (summary["claims_total"], summary["claims_public_safe"]),
        "Dated events on the chronology: %d (undated: %d)"
        % (summary["dated_events"], summary["undated_claims"]),
    ]
    if summary["evidence_classes"]:
        lines.append("Evidence classes:")
        for k in sorted(summary["evidence_classes"]):
            lines.append("  - %s: %d" % (k, summary["evidence_classes"][k]))
    if summary["interview_plans"]:
        lines.append("Interview plans written: %s"
                     % ", ".join(sorted(summary["interview_plans"])))
    if summary["conflicts"]:
        lines.append("Conflicts to resolve:")
        lines += ["  ! %s" % c for c in summary["conflicts"]]
    if summary["gaps"]:
        lines.append("Open gaps:")
        lines += ["  ? %s" % g for g in summary["gaps"]]
    lines += ["", "Read next: source_access_plan.md (what to hand over and how), "
              "archive_register.md (achievements, stories, media, quotes, permissions), "
              "chronology/chronology.md, and the interview questionnaires.",
              "", summary["question"], ""]
    return "\n".join(lines)


# --------------------------------------------------------------- evidence step
def evidence_stage(job_dir: str, request: JobRequest, research,
                   timeline=None) -> Dict[str, Any]:
    """Write the chronology and the per-role interview plans.

    Pure file work: no network. Idempotent, and it refuses to overwrite an
    existing questionnaire (a reviewed plan must never be replaced by a
    generated one).
    """
    written: Dict[str, Any] = {"artifacts": [], "plans": {}}

    if timeline is None:
        timeline = chronology_mod.build_timeline(request.firm_name, research.claims)

    chrono_dir = os.path.join(job_dir, CHRONOLOGY_DIRNAME)
    paths = chronology_mod.write_timeline(chrono_dir, timeline)
    written["artifacts"] += [paths["markdown"], paths["json"]]
    written["chronology"] = paths

    facts = story_mod.extract_facts(research, request.firm_name,
                                    request.event_date, request.new_office)
    plans = interviews_mod.build_all(
        request.firm_name,
        missing_facts=facts.missing(),
        open_questions=list(research.gaps),
    )
    plan_paths = interviews_mod.write_plans(
        os.path.join(job_dir, INTERVIEWS_DIRNAME), plans)
    for role, path in plan_paths.items():
        if path:
            written["artifacts"].append(path)
            written["plans"][role] = os.path.basename(path)
    written["timeline"] = timeline
    from . import producer
    written["artifacts"] += producer.write_research_package(
        job_dir, request.firm_name, research, facts)
    return written


# ------------------------------------------------------------ transcript step
def _file_digest(path: str) -> str:
    """SHA-256 of a file, so a retry can tell "unchanged" from "edited"."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def transcript_stage(job_dir: str, job_id: str, request: JobRequest,
                     transcript_paths: Sequence[str],
                     language: str = "",
                     known_status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Analyse supplied transcripts; never contact the interviewee.

    Only files the operator already holds are read. A missing or unreadable
    transcript is recorded as exactly that and is **never** marked as
    successfully analysed; the remaining files are still processed, so one bad
    path does not discard the rest.

    The stage is idempotent, which is what makes a retry safe:

    * a transcript whose bytes are unchanged since its last successful analysis
      is reused rather than analysed and re-written, so a retry after a
      *different* file appears cannot duplicate findings already on disk;
    * a transcript whose bytes have changed is re-analysed, so an old analysis is
      never presented as if it were current.

    Returns per-path ``status`` so the caller can decide whether the step may be
    called complete.
    """
    out_dir = os.path.join(job_dir, INTERVIEWS_DIRNAME, ANALYSIS_DIRNAME)
    known = dict(known_status or {})
    written: Dict[str, Any] = {"artifacts": [], "analyses": [], "failures": [],
                               "claims": [], "status": {}}
    for path in transcript_paths:
        key = os.path.abspath(path)
        record: Dict[str, Any] = {"status": "", "sha256": "", "reused": False,
                                  "at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        if not os.path.isfile(path):
            written["failures"].append("%s (file not found)" % path)
            record["status"] = "missing"
            written["status"][key] = record
            continue
        try:
            digest = _file_digest(path)
        except OSError as exc:
            written["failures"].append("%s (unreadable: %s)" % (path, exc))
            record["status"] = "unreadable"
            written["status"][key] = record
            continue

        previous = known.get(key) or {}
        prior_artifacts = list(previous.get("artifacts") or [])
        if (previous.get("status") == "analysed"
                and previous.get("sha256") == digest
                and prior_artifacts
                and all(os.path.isfile(p) for p in prior_artifacts)):
            # Same bytes, previous output still on disk: reuse instead of
            # re-writing identical files a second time.
            record["status"] = "analysed"
            record["sha256"] = digest
            record["reused"] = True
            record["artifacts"] = prior_artifacts
            written["artifacts"] += prior_artifacts
            written["status"][key] = record
            continue

        try:
            analysis = transcripts_mod.analyse_file(
                path, language=language or request.language)
        except Exception as exc:                 # one bad file never sinks the job
            written["failures"].append("%s (%s: %s)"
                                       % (path, type(exc).__name__, exc))
            record["status"] = "failed"
            written["status"][key] = record
            continue
        paths = transcripts_mod.write_analysis(out_dir, analysis)
        produced = [p for p in paths.values() if p]
        written["artifacts"] += produced
        written["analyses"].append(analysis)
        record["status"] = "analysed"
        record["sha256"] = digest
        record["artifacts"] = produced
        written["status"][key] = record
        # Quarantine: a statement flagged as client-identifying or privileged is
        # never merged into the citation set used to build the film.
        for claim in analysis.claims:
            if claim.privacy_flags:
                claim.safe_for_public = False
            written["claims"].append(claim)
    written["unresolved"] = [k for k, v in written["status"].items()
                             if v.get("status") != "analysed"]
    return written


def merge_chronology(job_dir: str, request: JobRequest, research,
                     interview_claims: Sequence[Any],
                     revision_dir: str) -> Any:
    """Rebuild the chronology from public claims **plus** interview statements.

    The interview claims are ``SINGLE-SOURCE`` by construction, so they cannot
    inflate corroboration of a documented event: the corroboration rule counts
    only independent documented sources (see
    :func:`agent_system.chronology.build_timeline`).
    """
    combined = list(research.claims) + list(interview_claims)
    timeline = chronology_mod.build_timeline(request.firm_name, combined)
    current = chronology_mod.write_timeline(
        os.path.join(job_dir, CHRONOLOGY_DIRNAME), timeline)
    snapshot = chronology_mod.write_timeline(revision_dir, timeline)
    return {"timeline": timeline, "current": current, "snapshot": snapshot}


# ------------------------------------------------------------- concepts step
def concepts_markdown(firm: str, concepts: List[Dict[str, Any]],
                      heading: str = "") -> str:
    lines = ["# Concepts — %s" % firm, ""]
    if heading:
        lines += ["_%s_" % heading, ""]
    for c in concepts:
        lines.append("## %s — %s%s" % (c["id"], c["title"],
                                       " (recommended)" if c.get("recommended")
                                       else ""))
        lines.append("")
        lines.append("_%s_" % c["central_idea"])
        lines.append("")
        lines.append("- Evidence fit: %s" % c["evidence_fit"])
        lines.append("- Strengths: %s" % "; ".join(c["strengths"]))
        lines.append("- Weaknesses: %s" % "; ".join(c["weaknesses"]))
        # The four buckets are kept apart on purpose: what the ledger documents,
        # what is only attributed speech, what is a creative choice, and what is
        # still unresolved must never be read as one pile of facts.
        basis = c.get("evidence_basis") or {}
        for label, key in (("Documented facts", "documented_facts"),
                           ("Attributed statements", "attributed_statements"),
                           ("Creative framing", "creative_framing"),
                           ("Unresolved claims", "unresolved_claims")):
            vals = basis.get(key) or []
            lines.append("- %s: %s" % (
                label, "; ".join(str(v) for v in vals) if vals else "none recorded"))
        lines.append("")
    return "\n".join(lines)


def concepts_stage(job_dir: str, request: JobRequest, research, revision_dir: str,
                   interview_claims: Sequence[Any] = ()) -> Dict[str, Any]:
    """Generate the concepts. Deliberately does **not** write the script."""
    facts = story_mod.extract_facts(research, request.firm_name,
                                    request.event_date, request.new_office)
    # Interview recollections are passed in so a concept can be described as
    # available *and* labelled single-source — never promoted to documented fact.
    concepts = story_mod.build_concepts(request.firm_name, facts, research,
                                        interview_claims)
    heading = ("Round generated from public evidence and %d interview "
               "statement(s). Each concept states its own evidence fit; none "
               "is a claim of quality." % len(interview_claims)
               if interview_claims else
               "Round generated from public evidence only. No interview "
               "material was supplied, so every gap below is still open.")
    body = concepts_markdown(request.firm_name, concepts, heading)

    written: Dict[str, Any] = {"artifacts": [], "concepts": concepts,
                               "concepts_json": concepts}
    # The round-scoped copy is always written; the job-root file is treated as
    # the approved artefact and is only created when absent.
    rev_path = _write(os.path.join(revision_dir, "concepts.md"), body)
    written["artifacts"].append(rev_path)
    root_path = os.path.join(job_dir, "concepts.md")
    if not os.path.exists(root_path):
        written["artifacts"].append(_write(root_path, body))
        written["approved_copy"] = root_path
    _write(os.path.join(revision_dir, "concepts.json"),
           json.dumps({"firm": request.firm_name, "concepts": concepts},
                      indent=2, ensure_ascii=False))
    written["facts"] = facts
    try:
        from . import producer
        producer.write_concepts_docx(os.path.join(job_dir, "concepts.docx"),
                                     request.firm_name, concepts)
    except Exception:  # the .md copies remain; the docx is a convenience
        pass
    return written


# --------------------------------------------------------------- script step
def script_stage(job_dir: str, request: JobRequest, research, revision_dir: str,
                 concept_id: str = "") -> Dict[str, Any]:
    """Write script, storyboard and scene manifest — after concept approval.

    ``story.build_story_assets`` writes ``concepts.md`` too. That file is an
    approved artefact by this point, so the bundle is built in the revision
    directory and only the script/storyboard/manifest are lifted to the job
    root. The concepts file the human approved is never rewritten.
    """
    facts = story_mod.extract_facts(research, request.firm_name,
                                   request.event_date, request.new_office)
    # If ``concept_id`` names a concept that does not exist for this job,
    # ``build_story_assets`` raises ConceptSelectionError *before* writing
    # anything. A script is never produced from a different concept than the one
    # the operator approved.
    bundle = story_mod.build_story_assets(
        revision_dir, request.firm_name, facts, research,
        request.language, request.style, float(request.duration_sec),
        concept_id)

    written: Dict[str, Any] = {"artifacts": [], "facts": facts,
                               "bundle": bundle, "concept_id": concept_id}
    for name in ("script.md", "storyboard.md", "scene_manifest.json",
                 "subtitles.srt", "production_brief.md"):
        src = bundle.get(name)
        if not src:
            continue
        dst = os.path.join(job_dir, name)
        with open(dst, "w", encoding="utf-8") as fh:
            with open(src, "r", encoding="utf-8") as fh2:
                fh.write(fh2.read())
        written["artifacts"].append(dst)
    written["manifest_path"] = os.path.join(job_dir, "scene_manifest.json")

    # The manifest records the concept the script was actually built from. Read
    # it back and use *that* for chosen_concept.md, so the decision note, the
    # script header and the manifest can never name different concepts.
    selected = {}
    try:
        with open(bundle["scene_manifest.json"], "r", encoding="utf-8") as fh:
            selected = (json.load(fh) or {}).get("concept") or {}
    except (KeyError, OSError, ValueError):
        selected = {}
    selected_id = str(selected.get("id") or concept_id or "")
    written["selected_concept"] = selected
    if concept_id and selected_id and \
            not story_mod.concept_ids_match(selected_id, concept_id):
        # Defensive: the guard in build_story_assets should make this unreachable.
        raise story_mod.ConceptSelectionError(
            "refusing to script: approved concept %r but the script was built "
            "from %r" % (concept_id, selected_id))

    if concept_id:
        chosen_path = os.path.join(job_dir, "chosen_concept.md")
        written["artifacts"].append(_write(
            chosen_path, _concept_choice_note(request, selected_id or concept_id,
                                              selected.get("title", ""))))
    return written


def _concept_choice_note(request: JobRequest, concept_id: str,
                         title: str = "") -> str:
    label = ("%s — %s" % (concept_id, title)) if title else concept_id
    return ("# Chosen concept — %s\n\n"
            "_Recorded: %s_\n\n"
            "The operator approved concept `%s` for this job. The full concept "
            "text and its evidence fit are in `concepts.md`; this file records "
            "only the decision and when it was taken.\n"
            % (request.firm_name, time.strftime("%Y-%m-%d %H:%M:%S"), label))


# ------------------------------------------------------------------ the driver
def _steps_for(state: Dict[str, Any]) -> List[str]:
    steps = [STEP_EVIDENCE]
    if state.get("transcripts"):
        steps.append(STEP_TRANSCRIPTS)
    steps += [STEP_CONCEPTS, STEP_SCRIPT, STEP_RENDER]
    return steps


def current_step(state: Dict[str, Any]) -> str:
    """The first step that has not completed, or ``done``."""
    for step in _steps_for(state):
        if step not in (state.get("completed") or []):
            return step
    return "done"


def gate_for_step(step: str) -> Optional[str]:
    """The approval that must exist *before* this step may run."""
    if step in (STEP_TRANSCRIPTS, STEP_CONCEPTS):
        return "research"
    if step == STEP_SCRIPT:
        return "concept"
    if step == STEP_RENDER:
        return "storyboard"
    return None


def gate_status(step: str) -> str:
    gate = gate_for_step(step)
    if gate == "research":
        return STATUS_EVIDENCE_GATE
    if gate == "concept":
        return STATUS_CONCEPT_GATE
    return STATUS_STORY_GATE


def advance_staged(cfg, store, job_id: str,
                   request: Optional[JobRequest] = None, *,
                   progress: Optional[Callable[[str, int, str], None]] = None,
                   cancel: Optional[Callable[[], bool]] = None,
                   asset_dir: str = "",
                   fetcher: Optional[Callable[[str], Any]] = None,
                   overrides: Optional[Dict[str, Any]] = None,
                   enable_preview: bool = True,
                   enable_render: bool = True,
                   approve: Optional[Callable[[Dict[str, Any]], bool]] = None,
                   transcripts: Optional[Sequence[str]] = None,
                   approve_research: bool = False,
                   approve_concept: Optional[str] = None,
                   approve_storyboard: bool = False,
                   allow_missing_transcripts: bool = False,
                   note: str = "",
                   force: bool = False) -> Dict[str, Any]:
    """Run the staged workflow forward until it completes or hits a gate.

    Safe to call repeatedly: a second concurrent call for the same job loses
    the atomic claim and returns ``status="busy"`` without doing any work.
    """
    job = store.get(job_id)
    if not job:
        raise PipelineError("no such job: %s" % job_id)

    if request is None:
        # The database column is a JSON string; tolerate an already-decoded dict
        # so this works from the CLI, the bot and tests alike.
        raw = job.get("params_json") or "{}"
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except ValueError:
                raw = {}
        if not isinstance(raw, dict):
            raw = {}
        request = JobRequest.from_dict(raw)

    job_dir = cfg.job_dir(job_id)
    os.makedirs(job_dir, exist_ok=True)
    work_dir = os.path.join(job_dir, "work")
    os.makedirs(work_dir, exist_ok=True)

    if os.environ.get("AGENT_NO_RENDER", "").strip().lower() in ("1", "true", "yes", "on"):
        enable_render = False
    if not enable_render:
        enable_preview = False

    result: Dict[str, Any] = {
        "job_id": job_id, "output_dir": job_dir, "artifacts": [],
        "status": job["status"], "errors": [], "warnings": [],
        "delivery_state": "unknown",
    }

    def say(stage: str, pct: int, msg: str) -> None:
        store.update(job_id, progress=max(0, min(100, pct)),
                     message=redact(msg)[:400])
        store.log_event(job_id, "progress", "%s %d%% %s" % (stage, pct, msg))
        if progress:
            try:
                progress(stage, pct, msg)
            except Exception:
                pass

    def guard() -> None:
        if cancel and cancel():
            raise Cancelled("cancelled by user")
        fresh = store.get(job_id)
        if fresh and fresh["status"] == "cancelled":
            raise Cancelled("cancelled by user")

    state = read_state(job_dir)

    # -------- record the decisions this call carries (before choosing a step)
    approvals = dict(state.get("approvals") or {})
    if approve_research:
        research_hash = _artifact_hash(job_dir, RESEARCH_ARTIFACTS)
        approvals["research"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                 "note": note, "artifact_hash": research_hash}
        store.log_event(job_id, "approval", "research approved: %s" % (note or "-"))
        store.record_approval(job_id, "research", 1,
                              actor_ref=str(store.get(job_id).get("user_id", 0)),
                              artifact_hash=research_hash,
                              idempotency_key="")
    if approve_concept:
        concept_hash = _artifact_hash(job_dir, CONCEPT_ARTIFACTS)
        approvals["concept"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                "concept": approve_concept, "note": note,
                                "artifact_hash": concept_hash}
        store.log_event(job_id, "approval",
                        "concept approved: %s" % approve_concept)
        store.record_approval(job_id, "concept", 1,
                              actor_ref=str(store.get(job_id).get("user_id", 0)),
                              artifact_hash=concept_hash,
                              idempotency_key="")
    if approve_storyboard:
        storyboard_hash = _artifact_hash(job_dir, STORYBOARD_ARTIFACTS)
        approvals["storyboard"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                   "note": note, "artifact_hash": storyboard_hash}
        store.log_event(job_id, "approval", "storyboard approved: %s" % (note or "-"))
        store.record_approval(job_id, "storyboard", 1,
                              actor_ref=str(store.get(job_id).get("user_id", 0)),
                              artifact_hash=storyboard_hash,
                              idempotency_key="")

    new_transcripts = [os.path.abspath(p) for p in (transcripts or [])]
    known = list(state.get("transcripts") or [])
    for p in new_transcripts:
        if p not in known:
            known.append(p)

    # An explicit acceptance of a missing transcript is a human decision, so it
    # is persisted: without it the interviews step stays open and cannot be
    # passed, which is what stops the film being built as if an interview had
    # been reviewed when the file was never available.
    accepted = list(state.get("transcripts_accepted") or [])
    if allow_missing_transcripts:
        for p in known:
            if p not in accepted:
                accepted.append(p)
        if known:
            store.log_event(job_id, "approval",
                            "missing transcript(s) accepted as a gap: %d"
                            % len(known))
    state = write_state(job_dir, approvals=approvals, transcripts=known,
                        transcripts_accepted=accepted)

    # A transcript supplied in this call that has never been analysed must reopen
    # the interviews step and everything derived from it. Without this, a file
    # added *after* the step already ran would be silently skipped, and the film
    # could be built as though that interview had never been read.
    if new_transcripts:
        status_now = dict(state.get("transcripts_status") or {})
        unread = [p for p in known
                  if (status_now.get(p) or {}).get("status") != "analysed"]
        if unread:
            completed_now = [s for s in (state.get("completed") or [])
                             if s not in (STEP_TRANSCRIPTS, STEP_CONCEPTS,
                                          STEP_SCRIPT, STEP_RENDER)]
            if completed_now != list(state.get("completed") or []):
                store.log_event(job_id, "progress",
                                "transcript supplied for re-analysis: reopening the "
                                "interviews step")
            state = write_state(job_dir, completed=completed_now)

    # -------- what is next, and may it run?
    step = current_step(state)

    # The final gate may be answered by a live callback (the bot's
    # approve/reject buttons). The research and concept gates have no callback:
    # they exist precisely so a person reads the findings before continuing.

    # ---- fail-closed approval check (storyboard gate).
    # A render may only start when a *persisted* storyboard approval exists and
    # the artefacts it covered are byte-for-byte unchanged since sign-off. A
    # hash mismatch (or a state-file approval with no matching persisted record)
    # means the sign-off is stale: it is withdrawn and the job pauses at the
    # gate instead of rendering evidence nobody approved.
    if step == STEP_RENDER:
        current_hash = _artifact_hash(job_dir, STORYBOARD_ARTIFACTS)
        stored_hash = store.get_approval_hash(job_id, "storyboard")
        if "storyboard" in approvals and stored_hash != current_hash:
            store.delete_approval(job_id, "storyboard")
            approvals.pop("storyboard", None)
            state = write_state(job_dir, approvals=approvals)
            store.log_event(job_id, "approval",
                            "storyboard approval withdrawn: the signed-off "
                            "artefacts changed or were never persisted")
            result["warnings"].append(
                "the storyboard approval was withdrawn because the evidence "
                "behind it changed; it must be approved again before rendering")

    if (step == STEP_RENDER and approve is not None
            and "storyboard" not in approvals):
        payload = {"job_id": job_id, "firm": request.firm_name,
                   "style": request.style, "language": request.language,
                   "duration_sec": request.duration_sec,
                   "gaps": _spec_gaps(job_dir),
                   "preview": result.get("preview"), "scenes": _spec_scenes(job_dir)}
        if bool(approve(payload)):
            storyboard_hash = _artifact_hash(job_dir, STORYBOARD_ARTIFACTS)
            approvals["storyboard"] = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                       "note": "approved via callback",
                                       "artifact_hash": storyboard_hash}
            state = write_state(job_dir, approvals=approvals)
            store.record_approval(job_id, "storyboard", 1,
                                  actor_ref=str(store.get(job_id).get("user_id", 0)),
                                  artifact_hash=storyboard_hash,
                                  idempotency_key="")
            store.log_event(job_id, "approval",
                            "storyboard approved via callback (hash %s)"
                            % storyboard_hash[:12])
        else:
            store.set_status(job_id, "cancelled", "storyboard rejected by user")
            result["status"] = "cancelled"
            result["delivery_state"] = "rejected"
            return result

    if step == "done":
        result["status"] = job["status"]
        result["delivery_state"] = "already_complete"
        result["warnings"].append("this job has already run the whole staged "
                                  "workflow; nothing to do")
        return result

    gate = gate_for_step(step)
    if gate and gate not in approvals:
        return _pause(store, job_id, step, gate_status(step), result)

    # -------- duplicate-execution guard: one worker per job
    claim_to = "rendering" if step == STEP_RENDER else "researching"
    allowed = list(RESUMABLE_STATES)
    if force:
        allowed.append("failed")
    if not store.claim_transition(job_id, tuple(allowed), claim_to,
                                  "staged workflow: %s" % step):
        fresh = store.get(job_id) or {}
        if fresh.get("status") in ("completed", "cancelled", "failed") and not force:
            result["status"] = fresh.get("status", "unknown")
            result["delivery_state"] = "refused"
            result["errors"].append(
                "job is %s; refusing to advance it (pass force=True to resume a "
                "failed job)" % fresh.get("status"))
            return result
        result["status"] = "busy"
        result["delivery_state"] = "busy"
        result["warnings"].append(
            "another worker holds this job (status=%s); no work was done"
            % fresh.get("status"))
        return result

    # -------- run steps until a gate blocks or everything is done
    try:
        while step != "done":
            gate = gate_for_step(step)
            if gate and gate not in approvals:
                return _pause(store, job_id, step, gate_status(step), result)
            guard()
            runner = _RUNNERS[step]
            outcome = runner(cfg=cfg, store=store, job_id=job_id,
                             request=request, research=None, job_dir=job_dir,
                             work_dir=work_dir, revision_dir=None,
                             result=result, state=state, say=say,
                             asset_dir=asset_dir, fetcher=fetcher,
                             overrides=overrides, enable_preview=enable_preview,
                             enable_render=enable_render, cancel=cancel,
                             step=step)
            if outcome.get("terminal"):
                # A terminal step (render / no-render / preview-only) ends the
                # job; record it as complete only when it actually succeeded,
                # so a failed render is never shown as a finished step.
                if outcome.get("done"):
                    completed = list(state.get("completed") or [])
                    if step not in completed:
                        completed.append(step)
                    state = write_state(job_dir, completed=completed, phase=step)
                return outcome["result"]

            completed = list(state.get("completed") or [])
            if outcome.get("invalidate_downstream"):
                # The interviews step found *changed* evidence (a transcript was
                # re-analysed, not reused). Anything derived from the previous
                # evidence — the merged chronology in the concepts step, and the
                # script and render built on top of it — is now stale and must be
                # rebuilt rather than presented as current.
                stale = [s for s in completed
                         if s in (STEP_CONCEPTS, STEP_SCRIPT, STEP_RENDER)]
                if stale:
                    completed = [s for s in completed if s not in stale]
                    store.log_event(job_id, "progress",
                                    "transcript evidence changed: reopening %s"
                                    % ", ".join(stale))
                    result["warnings"].append(
                        "transcript evidence changed; %s will be rebuilt from the "
                        "current findings" % ", ".join(stale))
                # Regardless of which downstream steps were still marked done (a
                # transcript added later may already have reopened them), the
                # storyboard a human approved was drawn from the *previous*
                # evidence and cannot cover what will now be rendered. The
                # concept *choice* survives — it is a decision about approach,
                # not about these statements — but the storyboard must be
                # approved again on the new facts.
                approvals_now = dict(read_state(job_dir).get("approvals") or {})
                if "storyboard" in approvals_now:
                    approvals_now.pop("storyboard")
                    write_state(job_dir, approvals=approvals_now)
                    store.delete_approval(job_id, "storyboard")
                    approvals = approvals_now
                    store.log_event(job_id, "approval",
                                    "storyboard approval withdrawn: the "
                                    "evidence behind it changed")
                    result["warnings"].append(
                        "the storyboard approval was withdrawn because the "
                        "evidence behind it changed; it must be approved again "
                        "before rendering")
            if step not in completed:
                completed.append(step)
            state = write_state(job_dir, completed=completed,
                                phase=step, revision=outcome.get("revision",
                                                                 state.get("revision", 0)))
            step = current_step(state)

        result["status"] = "completed"
        return result
    except Cancelled:
        store.set_status(job_id, "cancelled", "cancelled during %s" % step)
        result["status"] = "cancelled"
        result["delivery_state"] = "cancelled"
        result["warnings"].append("cancelled by user")
        return result


def _artifact_hash(job_dir: str, files: Sequence[str]) -> str:
    """Compute SHA-256 of the concatenated contents of ``files`` relative to ``job_dir``.

    Returns hex digest.  An empty ``files`` list yields a constant sentinel so that
    an un-approved gate can always be detected as "missing" rather than "hash-equal".
    """
    h = hashlib.sha256()
    any_file = False
    for f in files:
        path = os.path.join(job_dir, f)
        if os.path.isfile(path):
            any_file = True
            with open(path, "rb") as ph:
                h.update(ph.read())
    return h.hexdigest() if any_file else ""


def _pause(store, job_id: str, step: str, status: str,
           result: Dict[str, Any]) -> Dict[str, Any]:
    """Stop at a gate. The message names the *decision* being asked for, not the
    internal step that happens to come next."""
    asked = {"research": "the research findings",
             "concept": "the chosen concept",
             "storyboard": "the storyboard before rendering"}
    gate = gate_for_step(step)
    store.set_status(job_id, status,
                     "paused: waiting for a human to approve %s"
                     % asked.get(gate, step), None)
    result["status"] = status
    result["gate"] = gate
    result["awaiting"] = status
    result["next_step"] = step
    # Delivery readiness is tracked separately from ``status`` (which keeps the
    # historical "awaiting_*" value the existing callers/tests expect). A paused
    # job has delivered *nothing* watchable yet.
    result["delivery_state"] = "paused"
    return result


# ------------------------------------------------------------------- runners
def _run_evidence(**kw: Any) -> Dict[str, Any]:
    cfg, store, job_id = kw["cfg"], kw["store"], kw["job_id"]
    request, job_dir = kw["request"], kw["job_dir"]
    result, say = kw["result"], kw["say"]
    fetcher = kw["fetcher"]

    say("research", 5, "starting source discovery")
    research = research_firm(
        request.firm_name, request.website, request.facebook,
        extra_urls=request.extra_urls, fetcher=fetcher,
        language=request.language,
        progress=lambda m: say("research", 15, m))
    store.update(job_id, params_json=request.to_dict())

    result["artifacts"].append(os.path.basename(_write(
        os.path.join(job_dir, "research_report.md"), report_markdown(research))))
    result["artifacts"].append(os.path.basename(_write(
        os.path.join(job_dir, "evidence_ledger.csv"), ledger_csv(research))))
    from .research import result_to_dict
    _write(os.path.join(job_dir, "research_raw.json"),
           json.dumps(result_to_dict(research), indent=2, ensure_ascii=False))
    say("research", 30, "%d sources read, %d blocked, %d claims logged"
        % (sum(1 for s in research.sources if s.state == "INSPECTED"),
           len(research.inaccessible), len(research.claims)))
    if not research.claims:
        result["warnings"].append(
            "No readable public claims were found. Nothing was invented to fill "
            "the gap; the film cannot be scripted until this is resolved.")

    say("evidence", 35, "building chronology and interview plans")
    written = evidence_stage(job_dir, request, research)
    for path in written["artifacts"]:
        result["artifacts"].append(os.path.basename(path))
    timeline = written["timeline"]
    payload = review_summary(job_id, request, research, timeline, written)
    _write(os.path.join(job_dir, "research_review.md"), format_review(payload))
    result["review"] = payload
    _write(os.path.join(job_dir, "research_summary.json"),
           json.dumps(payload, indent=2, ensure_ascii=False))
    say("evidence", 40, "chronology: %d dated event(s), %d undated; interview "
        "plans: %s" % (len(timeline.entries), len(timeline.undated),
                       ", ".join(sorted(k for k in written["plans"]
                                        if k in interviews_mod.ROLES)) or "none"))
    return {"revision": 0}


def _run_transcripts(**kw: Any) -> Dict[str, Any]:
    request, job_dir, result, say = kw["request"], kw["job_dir"], kw["result"], kw["say"]
    store, job_id = kw["store"], kw["job_id"]
    state = read_state(job_dir)
    paths = list(state.get("transcripts") or [])
    known = dict(state.get("transcripts_status") or {})
    say("interviews", 45, "analysing %d supplied transcript(s)" % len(paths))
    outcome = transcript_stage(job_dir, job_id, request, paths,
                               known_status=known)
    for path in outcome["artifacts"]:
        result["artifacts"].append(os.path.relpath(path, job_dir))
    for failure in outcome["failures"]:
        result["warnings"].append("transcript not analysed: %s" % failure)
    if outcome["claims"]:
        say("interviews", 48, "%d statement(s) extracted; none is treated as "
            "established fact" % len(outcome["claims"]))

    # Persist what actually happened, per transcript. This record is what
    # decides whether the step may be called complete.
    merged = dict(known)
    merged.update(outcome["status"])
    write_state(job_dir, transcripts_status=merged)

    accepted = set(state.get("transcripts_accepted") or [])
    unresolved = [k for k in merged
                  if merged[k].get("status") != "analysed" and k not in accepted]
    if unresolved:
        # A transcript the operator supplied was not analysed. The step must not
        # be marked done: if it were, adding the file later would be silently
        # ignored and the film could be built as though the interview had been
        # reviewed. The job stays resumable so the same job can retry.
        msg = redact(
            "%d supplied transcript(s) could not be analysed (%s). Add the "
            "file(s) and re-run this job to analyse them; the interviews step "
            "stays open until then, and nothing downstream will run. To proceed "
            "without them, accept the gap explicitly."
            % (len(unresolved),
               ", ".join(os.path.basename(p) for p in unresolved)))[:400]
        store.set_status(job_id, STATUS_EVIDENCE_GATE, msg, None)
        store.log_event(job_id, "gate", "transcripts incomplete: %s" % msg)
        result["status"] = STATUS_EVIDENCE_GATE
        result["warnings"].append(msg)
        return {"terminal": True, "result": result, "done": False}

    # A transcript that was freshly analysed (rather than reused unchanged) means
    # the evidence set moved: the caller must rebuild anything derived from it.
    changed = any(record.get("status") == "analysed" and not record.get("reused")
                  for record in outcome["status"].values())
    return {"revision": state.get("revision", 0),
            "invalidate_downstream": changed}


def _run_concepts(**kw: Any) -> Dict[str, Any]:
    request, job_dir, result, say = kw["request"], kw["job_dir"], kw["result"], kw["say"]
    research = _load_research(job_dir)
    revision_dir, number = next_revision_dir(job_dir)
    # Statements are re-read from the analysis files, so the chronology is
    # rebuilt identically whether this runs in the same call as the transcript
    # step or in a later resumed one.
    claims = _interview_claims(job_dir)
    if claims:
        merged = merge_chronology(job_dir, request, research, claims, revision_dir)
        for path in merged["snapshot"].values():
            result["artifacts"].append(os.path.relpath(path, job_dir))
        result["warnings"].append(
            "%d interview statement(s) were added to the chronology as "
            "SINGLE-SOURCE; they are not treated as established fact."
            % len(claims))
    written = concepts_stage(job_dir, request, research, revision_dir, claims)
    for path in written["artifacts"]:
        result["artifacts"].append(os.path.relpath(path, job_dir))
    say("concepts", 52, "round %d: %d concepts written for review"
        % (number, len(written["concepts"])))
    return {"revision": number}


def _run_script(**kw: Any) -> Dict[str, Any]:
    request, job_dir, result, say = kw["request"], kw["job_dir"], kw["result"], kw["say"]
    store, job_id = kw["store"], kw["job_id"]
    research = _load_research(job_dir)
    revision_dir, number = next_revision_dir(job_dir)
    concept_id = (read_state(job_dir).get("approvals") or {}).get(
        "concept", {}).get("concept", "")
    try:
        written = script_stage(job_dir, request, research, revision_dir, concept_id)
    except story_mod.ConceptSelectionError as exc:
        # Never script a concept the operator did not approve. Stop the job at
        # the concept gate with an explicit request for a valid selection; no
        # script, storyboard or manifest is written, so nothing downstream can
        # render from a wrong concept.
        msg = redact("%s No script was generated. Re-approve one of the "
                     "concepts listed in concepts.md and re-run this job."
                     % exc)[:600]
        store.set_status(job_id, "awaiting_concept_review", msg, None)
        store.log_event(job_id, "gate", "script blocked: %s" % msg)
        result["status"] = "awaiting_concept_review"
        result["gate"] = "concept"
        result["errors"].append(msg)
        return {"terminal": True, "result": result, "done": False}
    for path in written["artifacts"]:
        result["artifacts"].append(os.path.relpath(path, job_dir))
    say("script", 58, "script, storyboard and scene manifest written")

    overrides = kw["overrides"]
    with open(written["manifest_path"], "r", encoding="utf-8") as fh:
        manifest = json.load(fh)
    if overrides:
        manifest.update(overrides)
        result["render_profile"] = "override"
    else:
        for key, value in PRODUCTION_PROFILE.items():
            manifest.setdefault(key, value)
        result["render_profile"] = "production"
    spec, spec_errors = video.validate_render_spec(manifest)
    for e in spec_errors:
        result["warnings"].append("spec: " + e)
        say("script", 58, "spec: " + e)
    voice_note = voice_mod.attach(
        spec, os.path.join(kw["work_dir"], "voice"),
        min(spec.transition_sec, min(s["dur"] for s in spec.scenes) * 0.4))
    if voice_note and not spec.audio.voiceover:
        result["warnings"].append("voice: " + voice_note)
    result["_spec"] = spec
    result["_facts"] = written["facts"]
    # Persist the *effective* render spec (including any caller override) so a
    # job resumed in a later process renders exactly what this step decided.
    # It lives in work/ because it is a working file, not a deliverable.
    _write(os.path.join(kw["work_dir"], "render_spec.json"),
           json.dumps(spec.to_dict(), indent=2, ensure_ascii=False))

    if kw["enable_preview"] and video.backend_info(spec.style)["ready"]:
        say("render", 60, "rendering a short preview clip (labelled as a preview)")
        try:
            pspec = _preview_spec(spec)
            preview_out = os.path.join(job_dir, "preview.mp4")
            pres = video.render_style(pspec, preview_out,
                                      os.path.join(kw["work_dir"], "preview"),
                                      asset_dir=kw["asset_dir"],
                                      cancel=kw["cancel"], profile="preview")
            result["artifacts"].append(os.path.basename(preview_out))
            result["preview"] = preview_out
            result["preview_validation"] = pres["validation"]
        except Cancelled:
            raise
        except Exception as exc:
            result["warnings"].append("preview clip failed: %s" % exc)
    return {"revision": number}


def _run_render(**kw: Any) -> Dict[str, Any]:
    cfg, store, job_id = kw["cfg"], kw["store"], kw["job_id"]
    request, job_dir, result = kw["request"], kw["job_dir"], kw["result"]
    say = kw["say"]
    research = _load_research(job_dir)
    facts = result.get("_facts") or story_mod.extract_facts(
        research, request.firm_name, request.event_date, request.new_office)
    spec = result.get("_spec")
    if spec is None:
        # Resumed in a later process: prefer the persisted effective spec so the
        # caller's overrides survive; otherwise fall back to the scene manifest.
        persisted = os.path.join(kw["work_dir"], "render_spec.json")
        if os.path.isfile(persisted):
            try:
                with open(persisted, "r", encoding="utf-8") as fh:
                    spec, errors = video.validate_render_spec(json.load(fh))
                for e in errors:
                    result["warnings"].append("spec: " + e)
                result["render_profile"] = "override"
            except (OSError, ValueError):
                spec = None
        if spec is None:
            with open(os.path.join(job_dir, "scene_manifest.json"), "r",
                      encoding="utf-8") as fh:
                raw = json.load(fh)
            spec, errors = video.validate_render_spec(raw)
            for e in errors:
                result["warnings"].append("spec: " + e)

    info = video.backend_info(spec.style)

    if request.preview_only:
        say("render", 62, "preview-only job: skipping the full render")
        store.set_status(job_id, "completed", "preview only", 100)
        result["artifacts"].append(os.path.basename(_write(
            os.path.join(job_dir, "delivery_report.md"),
            _delivery_report(job_id, request, research, facts, result,
                             result.get("preview_validation"), info))))
        result["status"] = "completed"
        result["delivery_state"] = "preview_only"
        return {"terminal": True, "result": result, "done": True}

    if not kw["enable_render"]:
        say("render", 62, "no-render mode: script complete, rendering skipped")
        result["no_render"] = True
        result["warnings"].append(
            "no-render mode: no preview and no final video were rendered")
        store.set_status(job_id, "completed",
                         "completed without video (no-render mode)", 100)
        result["artifacts"].append(os.path.basename(_write(
            os.path.join(job_dir, "delivery_report.md"),
            _delivery_report(job_id, request, research, facts, result, None, info))))
        result["status"] = "completed"
        result["delivery_state"] = "no_render"
        return {"terminal": True, "result": result, "done": True}

    if not info["ready"]:
        msg = "backend %r is not ready: %s" % (spec.style, "; ".join(info["reasons"]))
        store.fail(job_id, msg)
        result["status"] = "failed"
        result["delivery_state"] = "failed"
        result["errors"].append(msg)
        _write(os.path.join(job_dir, "delivery_report.md"),
               _delivery_report(job_id, request, research, facts, result, None, info))
        return {"terminal": True, "result": result, "done": False}

    def render_progress(text: str, pct: int) -> None:
        say("render", 65 + int(pct * 0.3), text)

    try:
        full_out = os.path.join(job_dir, "final.mp4")
        rendered = video.render_style(spec, full_out, kw["work_dir"],
                                      asset_dir=kw["asset_dir"],
                                      cancel=kw["cancel"],
                                      progress=render_progress,
                                      profile=cfg.encode_profile())
        result["artifacts"].append(os.path.basename(full_out))
        result["output"] = full_out
        result["validation"] = rendered["validation"]
        manifest_path = os.path.join(job_dir, "render_manifest.json")
        _write(manifest_path, json.dumps(rendered["manifest"], indent=2,
                                        ensure_ascii=False))
        result["artifacts"].append(os.path.basename(manifest_path))
    except Cancelled:
        raise
    except Exception as exc:
        msg = redact("%s: %s" % (type(exc).__name__, exc))[:1500]
        store.fail(job_id, msg)
        result["status"] = "failed"
        result["delivery_state"] = "failed"
        result["errors"].append(msg)
        _write(os.path.join(job_dir, "delivery_report.md"),
               _delivery_report(job_id, request, research, facts, result, None, info))
        return {"terminal": True, "result": result, "done": False}

    result["status"] = "completed"
    # Fail-closed: only a render that passes every final check is certified as a
    # publishable final. Otherwise the file exists for review but is honestly
    # reported as not certified (no watermark is ever drawn on the picture).
    result["final_qa"] = final_qa_checks(spec, result.get("validation"), job_dir, request)
    if result["final_qa"]["certified"]:
        result["delivery_state"] = "final_ready"
    else:
        result["delivery_state"] = "final_not_certified"
        for b in result["final_qa"]["blockers"]:
            result["warnings"].append("final QA: " + b)
    store.set_status(job_id, "completed", "finished", 100)
    result["artifacts"].append(os.path.basename(_write(
        os.path.join(job_dir, "delivery_report.md"),
        _delivery_report(job_id, request, research, facts, result,
                         result.get("validation"), info))))
    return {"terminal": True, "result": result, "done": True}


_RUNNERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    STEP_EVIDENCE: _run_evidence,
    STEP_TRANSCRIPTS: _run_transcripts,
    STEP_CONCEPTS: _run_concepts,
    STEP_SCRIPT: _run_script,
    STEP_RENDER: _run_render,
}


# ------------------------------------------------------------------- helpers
def _manifest(job_dir: str) -> Dict[str, Any]:
    path = os.path.join(job_dir, "scene_manifest.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def _spec_gaps(job_dir: str) -> List[str]:
    return list(_manifest(job_dir).get("gaps") or [])


def _spec_scenes(job_dir: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for s in (_manifest(job_dir).get("scenes") or []):
        if not isinstance(s, dict):
            continue
        out.append({"id": s.get("id"), "key": s.get("key"), "dur": s.get("dur"),
                    "heading": s.get("heading"), "narration": s.get("narration"),
                    "placeholder": s.get("placeholder")})
    return out


def _load_research(job_dir: str):
    """Reload the research written by the evidence step (never re-fetches)."""
    research = load_raw(os.path.join(job_dir, "research_raw.json"))
    if not research.firm_name and not research.claims and not research.sources:
        raise PipelineError(
            "research_raw.json is missing or empty in %s — the evidence step "
            "has not produced evidence for this job" % job_dir)
    return research


def _interview_claims(job_dir: str) -> List[Any]:
    """Re-read interview statements from a previous run's analysis JSON files."""
    out: List[Any] = []
    analysis_dir = os.path.join(job_dir, INTERVIEWS_DIRNAME, ANALYSIS_DIRNAME)
    if not os.path.isdir(analysis_dir):
        return out
    for name in sorted(os.listdir(analysis_dir)):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(analysis_dir, name), "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except (OSError, ValueError):
            continue
        fields = set(transcripts_mod.InterviewClaim.__dataclass_fields__)
        for raw in (payload.get("claims") or []):
            if isinstance(raw, dict):
                out.append(transcripts_mod.InterviewClaim(
                    **{k: v for k, v in raw.items() if k in fields}))
    return out


def resume_staged(cfg, store, job_id: str, **kwargs: Any) -> Dict[str, Any]:
    """Alias for :func:`advance_staged`, for readability at call sites."""
    return advance_staged(cfg, store, job_id, **kwargs)
