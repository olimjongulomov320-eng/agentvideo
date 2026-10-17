# -*- coding: utf-8 -*-
"""chronology.py — chronology and story selection (workflow stage E).

Turns the evidence ledger into a dated timeline. Three rules keep it honest:

1.  **A year only appears if a source states it.** The year is taken from the
    claim text verbatim; it is never inferred from context, from a copyright
    line, or from the order of a page. Every entry records the claim ids and
    URLs it came from, so the reader can check it.
2.  **Undated material is not dropped.** Claims with no year are listed in their
    own section. Hiding them would quietly shrink the evidence.
3.  **Documented history and proposed interpretation are separate sections.**
    Only ``VERIFIED`` / ``CORROBORATED`` claims are presented as documented. A
    "significance" line is a *proposal for the film*, never a fact, and is
    labelled as such.

Where several claims disagree about a year, the disagreement is reported rather
than averaged, rounded, or silently resolved.
"""
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from .research import CORROBORATED, VERIFIED, source_key

DOCUMENTED = (VERIFIED, CORROBORATED)
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")


@dataclass
class TimelineEntry:
    year: int
    date_label: str
    event: str
    claim_ids: List[str] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    evidence_class: str = ""
    confidence: str = ""
    documented: bool = False
    # A proposal for the film, not a fact.
    significance: str = ""
    # Set when the claim itself mentions more than one year.
    ambiguity: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Timeline:
    firm_name: str
    entries: List[TimelineEntry] = field(default_factory=list)
    undated: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    narrative_notes: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "firm_name": self.firm_name,
            "entries": [e.as_dict() for e in self.entries],
            "undated": list(self.undated),
            "conflicts": list(self.conflicts),
            "narrative_notes": list(self.narrative_notes),
            "gaps": list(self.gaps),
        }


def _years_in(text: str) -> List[int]:
    return [int(y) for y in _YEAR.findall(text or "")]


def _significance(event: str, documented: bool) -> str:
    """A deliberately hedged proposal for the film — never a fact."""
    low = (event or "").lower()
    if re.search(r"\b(found|founded|establish|since|began|opened)\b", low):
        if documented:
            return ("Proposed opening anchor: a dated founding claim is the "
                    "strongest available way to open the film.")
        return ("Candidate opening anchor, but only single-source: needs a second "
                "source before it can carry the opening.")
    if re.search(r"\b(award|ranked|recognised|recognized|winner)\b", low):
        return ("Candidate milestone. Confirm the granting body and year before "
                "using it as an achievement.")
    if re.search(r"\b(office|moved|move|relocat)\b", low):
        return ("Candidate milestone for the new-office story. Confirm the date "
                "and the address.")
    return ""


def build_timeline(firm_name: str, claims: Iterable[Any]) -> Timeline:
    """Group dated claims into a sorted timeline; park the rest in ``undated``.

    ``claims`` may be :class:`agent_system.research.Claim` objects or the
    attributed statements from :mod:`agent_system.transcripts` — only the
    attributes ``text``, ``id``, ``source_url`` and ``evidence_class`` (or
    ``evidence_class``/``attributed_to``) are read.
    """
    timeline = Timeline(firm_name=firm_name)
    seen_years: Dict[int, List[str]] = {}

    for claim in claims:
        text = (getattr(claim, "text", "") or "").strip()
        if not text:
            continue
        cid = getattr(claim, "id", "") or ""
        source = (getattr(claim, "source_url", "")
                  or getattr(claim, "attributed_to", "") or "")
        evc = (getattr(claim, "evidence_class", "") or "").upper()
        conf = getattr(claim, "confidence", "") or ""

        years = _years_in(text)
        if not years:
            timeline.undated.append({"id": cid, "event": text[:300],
                                     "source": source, "evidence_class": evc})
            continue

        year = min(years)
        ambiguity = ""
        if len(set(years)) > 1:
            ambiguity = ("Claim mentions several years (%s); the earliest is used "
                         "as the sort key. A human must decide which year the "
                         "event belongs to." % ", ".join(str(y) for y in
                                                          sorted(set(years))))

        documented = evc in DOCUMENTED
        timeline.entries.append(TimelineEntry(
            year=year,
            # The wording says exactly where the date comes from.
            date_label=str(year),
            event=text[:300],
            claim_ids=[cid] if cid else [],
            sources=[source] if source else [],
            evidence_class=evc,
            confidence=conf or ("documented" if documented
                                else "single-source or unverified"),
            documented=documented,
            significance=_significance(text, documented),
            ambiguity=ambiguity))
        seen_years.setdefault(year, []).append(evc)

    # Which years are backed by more than one *independent documented source*?
    # Counting claims instead of sources would inflate corroboration: an
    # unverified claim must never be treated as corroborating a verified one.
    per_year_all: Dict[int, int] = {}
    per_year_sources: Dict[int, set] = {}
    for e in timeline.entries:
        per_year_all[e.year] = per_year_all.get(e.year, 0) + 1
        if e.documented:
            bucket = per_year_sources.setdefault(e.year, set())
            for s in e.sources:
                key = source_key(s)
                if key:
                    bucket.add(key)

    for e in timeline.entries:
        sources_for_year = per_year_sources.get(e.year, set())
        if len(sources_for_year) >= 2:
            e.documented = True
            e.confidence = (e.confidence + "; corroborated by %d independent "
                            "source(s)" % len(sources_for_year)).strip("; ")
        elif per_year_all.get(e.year, 0) > 1:
            others = per_year_all[e.year] - 1
            e.confidence = (e.confidence + "; %d other claim(s) mention this year "
                            "but are not counted as corroboration"
                            % others).strip("; ")

    timeline.entries.sort(key=lambda e: (e.year, e.event))
    _detect_conflicts(timeline)

    if not timeline.entries:
        timeline.gaps.append(
            "No dated claims were found, so no chronology can be established "
            "from the accessible sources.")
    if timeline.undated:
        timeline.gaps.append(
            "%d claim(s) carry no year and are therefore not on the timeline. "
            "They are listed separately rather than dated by guesswork."
            % len(timeline.undated))

    timeline.narrative_notes.append(
        "Sections 1–2 are evidence. Section 3 is interpretation and must be "
        "approved by a human before it reaches a script.")
    timeline.narrative_notes.append(
        "A \"significance\" line proposes why an event could matter to the film. "
        "It is a suggestion, not a finding, and it never upgrades an evidence class.")
    return timeline


def _detect_conflicts(timeline: Timeline) -> None:
    """Report claims that state *different* years for what looks like one event.

    Synonyms are grouped, because a disagreement is easy to miss when the two
    sources use different verbs for the same event: "was founded in 2010" and
    "was established in 2011" is exactly the conflict a human must resolve, and
    keying on the literal word stem would never compare them.
    """
    groups = (
        ("founding", ("found", "established", "establish", "formed", "incorporated",
                      "founded")),
        ("office opening", ("open", "opened", "opening", "moved", "relocat")),
        ("recognition", ("award", "awarded", "ranked", "rank", "recognised",
                         "recognized", "winner")),
    )
    buckets: Dict[str, Dict[int, List[str]]] = {}
    for entry in timeline.entries:
        low = entry.event.lower()
        for label, keys in groups:
            if any(re.search(r"\b%s" % re.escape(k), low) for k in keys):
                buckets.setdefault(label, {}).setdefault(entry.year, []).append(
                    entry.claim_ids[0] if entry.claim_ids else entry.event[:40])
    for label, years in sorted(buckets.items()):
        if len(years) > 1:
            detail = "; ".join("%d: %s" % (y, ", ".join(ids))
                               for y, ids in sorted(years.items()))
            timeline.conflicts.append(
                "Possible disagreement about '%s' across years — %s. Resolve with "
                "a dated document before the film claims either date."
                % (label, detail))


def timeline_markdown(timeline: Timeline,
                      generated_at: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append("# Chronology — %s" % timeline.firm_name)
    lines.append("")
    lines.append("_Generated: %s_" % (generated_at or time.strftime("%Y-%m-%d %H:%M")))
    lines.append("")
    lines.append("> A year appears here only because a cited source states it. "
                 "Nothing is dated by inference.")
    lines.append("")

    documented = [e for e in timeline.entries if e.documented]
    single = [e for e in timeline.entries if not e.documented]

    lines.append("## 1. Documented history (verified or corroborated)")
    lines.append("")
    if not documented:
        lines.append("_Nothing on the accessible sources reaches verified or "
                     "corroborated status yet._")
    else:
        for e in documented:
            lines.append("### %s — %s" % (e.date_label, e.event[:120]))
            lines.append("")
            lines.append("- Evidence class: **%s** — %s" % (e.evidence_class, e.confidence))
            if e.sources:
                lines.append("- Source(s): %s" % ", ".join(e.sources))
            if e.claim_ids:
                lines.append("- Claim ids: %s" % ", ".join(e.claim_ids))
            if e.ambiguity:
                lines.append("- **Ambiguity:** %s" % e.ambiguity)
            lines.append("")
    lines.append("")

    lines.append("## 2. Dated but not yet corroborated")
    lines.append("")
    if not single:
        lines.append("_None._")
    else:
        for e in single:
            lines.append("- **%s** — %s _(%s)_" % (
                e.date_label, e.event[:180], e.evidence_class or "unclassified"))
            if e.sources:
                lines.append("  - Source: %s" % ", ".join(e.sources))
            if e.ambiguity:
                lines.append("  - Ambiguity: %s" % e.ambiguity)
    lines.append("")

    lines.append("## 3. Proposed interpretation (NOT evidence)")
    lines.append("")
    proposals = [e for e in timeline.entries if e.significance]
    if not proposals:
        lines.append("_No significance proposals were generated._")
    else:
        for e in proposals:
            lines.append("- **%s** — %s" % (e.date_label, e.significance))
    lines.append("")
    for n in timeline.narrative_notes:
        lines.append("> %s" % n)
    lines.append("")

    lines.append("## 4. Undated evidence (kept, not guessed)")
    lines.append("")
    if not timeline.undated:
        lines.append("_None._")
    else:
        for u in timeline.undated:
            lines.append("- %s _(%s)_ — %s" % (
                u.get("event", "")[:160], u.get("evidence_class") or "unclassified",
                u.get("source") or "no source recorded"))
    lines.append("")

    if timeline.conflicts:
        lines.append("## 5. Contradictions to resolve")
        lines.append("")
        for c in timeline.conflicts:
            lines.append("- %s" % c)
        lines.append("")

    if timeline.gaps:
        lines.append("## 6. Gaps")
        lines.append("")
        for g in timeline.gaps:
            lines.append("- %s" % g)
        lines.append("")

    lines.append("> **Anti-fabrication:** undated material was not dated by guesswork, "
                 "disagreements were not averaged, and no interpretation was promoted "
                 "to a finding.")
    return "\n".join(lines) + "\n"


def write_timeline(out_dir: str, timeline: Timeline,
                   stamp: Optional[str] = None) -> Dict[str, str]:
    import json
    import os
    os.makedirs(out_dir, exist_ok=True)
    md_path = os.path.join(out_dir, "chronology.md")
    js_path = os.path.join(out_dir, "chronology.json")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(timeline_markdown(timeline, generated_at=stamp))
    payload = timeline.as_dict()
    payload["generated_at"] = stamp or time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(js_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return {"markdown": md_path, "json": js_path}
