# -*- coding: utf-8 -*-
"""interviews.py — interview preparation (workflow stage C).

The agent never contacts anybody. It prepares questions for a human
interviewer, and analyses the recording or transcript that comes back.

Every question produced here carries two extra fields, because a question that
does not know *why* it is being asked tends to produce unusable answers:

* ``addresses``     — the specific historical uncertainty the answer would close.
* ``corroboration`` — the evidence that would settle it independently. An
  answer alone is a recollection; the document is the proof.

Gap-driven questions are generated from the facts the research could not
establish, so the interview spends its time on real holes rather than on
material already in hand.

**Do not overwrite finished work.** :func:`write_plans` refuses to replace an
existing questionnaire unless ``force=True``. For the GSP run the canonical
questionnaires already exist (``research/06_…``, ``research/07_…``) and must be
left alone.
"""
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

ROLE_MANAGING = "managing_partner"
ROLE_FOUNDING = "founding_partners"
ROLE_PARTNERS = "partners"
ROLES = (ROLE_MANAGING, ROLE_FOUNDING, ROLE_PARTNERS)

ROLE_TITLES = {
    ROLE_MANAGING: "Managing Partner",
    ROLE_FOUNDING: "Founding / Name Partners",
    ROLE_PARTNERS: "Current Partners",
}
ROLE_FILENAMES = {
    ROLE_MANAGING: "questionnaireManagingPartner.md",
    ROLE_FOUNDING: "questionnaireFoundingPartners.md",
    ROLE_PARTNERS: "questionnairePartners.md",
}

# The eight enquiry areas the brief requires, in the order they should be asked.
TIER_1 = "the origin"
TIER_2 = "change and turning points"
TIER_3 = "work, values and what comes next"

# What would independently settle a missing fact. Without this a question just
# produces another unverifiable anecdote.
CORROBORATION: Dict[str, str] = {
    "founding_year": "the founding/registration document with a date, dated "
                     "correspondence, a dated photo, or a dated press item — "
                     "not recollection alone",
    "practice_areas": "practice pages archived over time, a dated mandate, a "
                      "dated publication or directory entry",
    "achievement": "the awarding/ranking body itself (certificate, ranking page, "
                   "press release with a date) — a firm's own marketing line is "
                   "not evidence of an award",
    "new_office": "the lease, the opening announcement, an invitation with a "
                  "date, or a dated photograph of the premises",
    "team_size": "a dated staff list, or a dated filing/registration record",
    "name_history": "the registration record showing the name at each stage",
}

# Follow-up generators for the four failure modes the brief names.
FOLLOWUP_VAGUE_DATE = [
    "Which year was that, exactly? If you are not sure, say so — we will mark it as unconfirmed.",
    "What dated document would show it? A contract, a registration paper, a letter, a photo, a news item?",
    "Who else was there who could confirm the date?",
]
FOLLOWUP_CONFLICT = [
    "Written sources disagree here. Which version do you believe is right, and why?",
    "What would settle the disagreement — a document, a record, or another person's account?",
    "Could both be right because they refer to different things (a practice vs the firm)?",
]
FOLLOWUP_UNSUPPORTED = [
    "Where could that be checked independently? Do you have the document or a link?",
    "Was that reported anywhere at the time — a publication, a directory, an award page?",
    "If we cannot verify it, would you prefer we leave it out of the film?",
]
FOLLOWUP_CONFIDENTIAL = [
    "If this involves a client or privileged matter, say so now and we will exclude it from the film.",
    "Could it be told in anonymised form — no client name, no identifying detail?",
    "Is there a version of this story that is safe to publish?"]


@dataclass
class Question:
    """One question, with the uncertainty it closes and its corroboration path."""
    id: str
    text: str
    tier: str
    addresses: str = ""
    corroboration: str = ""
    followups: List[str] = field(default_factory=list)
    # Set when the answer might touch privilege or client confidentiality.
    confidentiality: str = ""
    # Which missing fact, if any, this question was generated to close.
    closes_gap: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterviewPlan:
    role: str
    title: str
    firm: str
    interviewee: str = ""
    purpose: str = ""
    before_you_start: List[str] = field(default_factory=list)
    questions: List[Question] = field(default_factory=list)
    unresolved: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "title": self.title,
            "firm": self.firm,
            "interviewee": self.interviewee,
            "purpose": self.purpose,
            "before_you_start": list(self.before_you_start),
            "unresolved": list(self.unresolved),
            "notes": list(self.notes),
            "questions": [q.as_dict() for q in self.questions],
        }


# ---------------------------------------------------------------- builders
def _q(qid: str, text: str, tier: str, addresses: str, corroboration: str,
       followups: Optional[Sequence[str]] = None,
       confidentiality: str = "", closes_gap: str = "") -> Question:
    return Question(id=qid, text=text, tier=tier, addresses=addresses,
                    corroboration=corroboration,
                    followups=list(followups or []),
                    confidentiality=confidentiality, closes_gap=closes_gap)


def _before_you_start(firm: str) -> List[str]:
    return [
        "Explain the film plainly: about two to two and a half minutes, made for "
        "the new-office opening, intended for public use.",
        "Ask for permission to record, and separately for permission to quote.",
        "State the boundary up front: no privileged client details, no "
        "confidential case facts, nothing under an NDA.",
        "Agree how they will be named and described on screen.",
        "Ask them to flag anything mid-answer that should be off the record — "
        "and honour it when they do.",
    ]


def _closing_notes(firm: str) -> List[str]:
    return [
        "Record the date, place and who was present for every session.",
        "Ask for the documents mentioned while they are still being discussed.",
        "Note which answers were confident and which were hedged — the hedges "
        "are where the unverified history is.",
        "Nothing said here is treated as established fact until it is "
        "corroborated or clearly marked as one person's recollection.",
    ]


def _founding_questions(interviewee: str) -> List[Question]:
    who = interviewee or "you"
    return [
        _q("T1.1", "Take me back to the year the firm began. Where were %s "
                   "working, who was there with %s, and what made you start a "
                   "firm of your own?" % (who, who), TIER_1,
           "the founding motive and the founding date/circumstances",
           CORROBORATION["founding_year"],
           FOLLOWUP_VAGUE_DATE, closes_gap="founding_year"),
        _q("T1.2", "What was the first office like, and what was the first "
                   "real piece of work the firm was trusted with?", TIER_1,
           "the early scale of the practice and its first mandates",
           "a dated document from the first year of practice",
           FOLLOWUP_VAGUE_DATE),
        _q("T1.3", "What was the hardest moment in those early years — the one "
                   "that nearly stopped it?", TIER_1,
           "the firm's first real turning point and how it survived",
           "a dated record of the event, or a second account of it",
           FOLLOWUP_CONFLICT),
        _q("T1.4", "Has the firm's name changed since it began? Why that name?",
           TIER_1, "the name history, which sources currently disagree about",
           CORROBORATION["name_history"], FOLLOWUP_CONFLICT,
           closes_gap="name_history"),
    ]


def _turning_point_questions(interviewee: str) -> List[Question]:
    who = interviewee or "you"
    return [
        _q("T2.1", "Can you recall the specific moment when the firm crossed "
                   "into a different stage? What happened, and who was involved?",
           TIER_2, "the documented turning points, currently undated",
           "a dated record of the change (a new partnership, a move, a hire)",
           FOLLOWUP_VAGUE_DATE),
        _q("T2.2", "How did the way %s work change over the years — the kind of "
                   "matters, the clients, the size of the team?" % who, TIER_2,
           "how the practice areas evolved, and the team size over time",
           CORROBORATION["team_size"] + "; " + CORROBORATION["practice_areas"],
           FOLLOWUP_VAGUE_DATE + FOLLOWUP_CONFLICT, closes_gap="team_size"),
        _q("T2.3", "Which case — one we can discuss publicly, or in anonymised "
                   "form — shows what this firm is really for?", TIER_2,
           "a concrete, publishable example of the firm's work",
           "the outcome on a public record, or an anonymised account",
           FOLLOWUP_CONFIDENTIAL,
           confidentiality="Exclude client names and privileged detail unless "
                           "explicitly authorised in writing."),
        _q("T2.4", "Who shaped how this firm works most, and through what "
                   "*specific action* rather than what they said?", TIER_2,
           "the firm's culture and the people who formed it",
           "a second account from another partner", FOLLOWUP_CONFLICT),
    ]


def _values_questions(interviewee: str) -> List[Question]:
    who = interviewee or "you"
    return [
        _q("T3.1", "What principle have %s never abandoned, even when it cost "
                   "something? Tell me about a time it cost." % who, TIER_3,
           "the firm's stated values, grounded in an actual event",
           "a second account, or a dated record of the decision", []),
        _q("T3.2", "What has changed about the legal market here that most "
                   "people outside the profession would not notice?", TIER_3,
           "the wider context the film can use without overclaiming",
           "a dated publication or market report", []),
        _q("T3.3", "Where is the firm going next, and what should it be known "
                   "for in ten years?", TIER_3,
           "the forward-looking close of the film",
           "the firm's own plans, to be labelled as intention, not fact", []),
        _q("T3.4", "Is there anything I should have asked and did not?",
           TIER_3, "material the plan itself missed", "",
           ["What would you want people to remember about this place?"], []),
    ]


def _gap_question(gap: str, index: int, interviewee: str) -> Question:
    """A question written specifically to close one missing fact."""
    who = interviewee or "you"
    prompts = {
        "founding_year": ("What year exactly did the firm begin, and what dated "
                          "document shows it?"),
        "practice_areas": ("What work did the firm actually do in its first "
                           "years — and which of those areas is still core?"),
        "new_office": ("Tell me about the move to the new office — when did it "
                       "happen and what does it change?"),
        "achievement": ("Which recognition is the firm genuinely proud of, and "
                        "who granted it?"),
        "team_size": "How many lawyers were there at each stage you remember?",
        "name_history": "When, if ever, did the firm's name change, and why?",
    }
    text = prompts.get(gap, "Can you help with this open question: %s?" % gap)
    corroboration = CORROBORATION.get(gap, "an independent, preferably dated, record")
    extra = [FOLLOWUP_UNSUPPORTED[0], FOLLOWUP_UNSUPPORTED[1]]
    if gap in ("founding_year", "new_office", "name_history"):
        extra = FOLLOWUP_VAGUE_DATE + extra[:1]
    if gap == "achievement":
        extra = ["Which body granted it, in which year, and is there a page or "
                 "certificate we could see?"] + extra[:1]
    return _q("G%d" % index, text, TIER_2 if gap != "founding_year" else TIER_1,
              "the missing fact '%s'" % gap, corroboration, extra,
              confidentiality="Refuse nothing, but mark anything client-specific "
                              "for exclusion.",
              closes_gap=gap)


def build_plan(role: str, firm: str,
               missing_facts: Iterable[str] = (),
               open_questions: Iterable[str] = (),
               interviewee: str = "") -> InterviewPlan:
    """Build one role's questionnaire, driven by what the research could not prove."""
    if role not in ROLES:
        raise ValueError("unknown role %r (expected one of %s)" % (role, ", ".join(ROLES)))

    plan = InterviewPlan(
        role=role, title=ROLE_TITLES[role], firm=firm, interviewee=interviewee,
        before_you_start=_before_you_start(firm))

    plan.purpose = {
        ROLE_MANAGING: "Recover the authentic account of why the firm exists, how "
                       "it grew, and the decisions that shaped it — concrete, "
                       "dated and situated memories, not corporate statements.",
        ROLE_FOUNDING: "Establish what was actually true at the beginning: who "
                       "founded the firm, when, under what name, and with what "
                       "resources. Founding accounts often disagree; this is where "
                       "those disagreements are surfaced rather than smoothed over.",
        ROLE_PARTNERS: "Establish how the practice changed from the inside — the "
                       "work, the team, the turning points — and gather independent "
                       "accounts that can corroborate or contradict the founders'.",
    }[role]

    if role in (ROLE_MANAGING, ROLE_FOUNDING):
        plan.questions += _founding_questions(interviewee)
    plan.questions += _turning_point_questions(interviewee)
    plan.questions += _values_questions(interviewee)

    # Gap-driven questions come last so the core narrative is always covered
    # first, even if the session is cut short. A gap already closed by a
    # narrative question is not asked a second time: repeating the same question
    # in one interview wastes the session and looks careless.
    already_covered = {q.closes_gap for q in plan.questions if q.closes_gap}
    index = 0
    for gap in missing_facts:
        gap = str(gap)
        if gap in already_covered:
            continue
        index += 1
        plan.questions.append(_gap_question(gap, index, interviewee))
        already_covered.add(gap)

    plan.unresolved = [str(g) for g in missing_facts]
    plan.notes = _closing_notes(firm)
    for i, q in enumerate(open_questions, start=1):
        plan.notes.append("Open question from research (%d): %s" % (i, q))
    if not interviewee:
        plan.notes.append(
            "No interviewee name recorded yet: the plan is written for the role. "
            "Fill in the name before the session so it can be cited.")
    return plan


def plan_markdown(plan: InterviewPlan, generated_at: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append("# Interview plan — %s" % plan.title)
    lines.append("")
    lines.append("**Firm:** %s  " % plan.firm)
    lines.append("**Role:** %s  " % plan.title)
    if plan.interviewee:
        lines.append("**Interviewee:** %s  " % plan.interviewee)
    lines.append("**Generated:** %s  " % (generated_at or time.strftime("%Y-%m-%d %H:%M")))
    lines.append("**Status:** DRAFT — prepared for a human interviewer. "
                 "The agent does not contact or interview anyone.")
    lines.append("")

    lines.append("## Purpose")
    lines.append("")
    lines.append(plan.purpose)
    lines.append("")

    lines.append("## Before you start")
    lines.append("")
    for b in plan.before_you_start:
        lines.append("- %s" % b)
    lines.append("")

    def render(q: Question) -> None:
        lines.append("**%s.** %s" % (q.id, q.text))
        lines.append("")
        if q.addresses:
            lines.append("- *What this closes:* %s" % q.addresses)
        if q.corroboration:
            lines.append("- *What would corroborate it:* %s" % q.corroboration)
        if q.closes_gap:
            lines.append("- *Missing fact:* `%s`" % q.closes_gap)
        if q.confidentiality:
            lines.append("- *Confidentiality:* %s" % q.confidentiality)
        for f in q.followups:
            lines.append("- *Follow-up:* %s" % f)
        lines.append("")

    narrative = [q for q in plan.questions if not q.closes_gap]
    gapdriven = [q for q in plan.questions if q.closes_gap]

    lines.append("## Questions")
    lines.append("")
    for tier in (TIER_1, TIER_2, TIER_3):
        tier_qs = [q for q in narrative if q.tier == tier]
        if not tier_qs:
            continue
        lines.append("### %s" % tier.capitalize())
        lines.append("")
        for q in tier_qs:
            render(q)

    if gapdriven:
        lines.append("## Questions targeting the missing evidence")
        lines.append("")
        lines.append("_Asked after the narrative questions, so the story is covered "
                     "even if the session is cut short. Each one names the fact it "
                     "must close and the record that would settle it._")
        lines.append("")
        for q in gapdriven:
            render(q)

    if plan.unresolved:
        lines.append("## Gaps this session must close")
        lines.append("")
        for u in plan.unresolved:
            lines.append("- `%s` — %s" % (u, CORROBORATION.get(u, "needs an independent record")))
        lines.append("")

    if plan.notes:
        lines.append("## Notes")
        lines.append("")
        for n in plan.notes:
            lines.append("- %s" % n)
        lines.append("")

    lines.append("> **Permission.** Ask for consent to record, and separately for "
                 "consent to quote. Nothing from this interview may be used "
                 "publicly until the subject grants it and any historical claim is "
                 "corroborated. Client-identifying and privileged matter is "
                 "excluded unless separately authorised in writing.")
    return "\n".join(lines) + "\n"


def write_plans(out_dir: str, plans: Sequence[InterviewPlan],
                stamp: Optional[str] = None, force: bool = False) -> Dict[str, str]:
    """Write each plan as markdown + one machine-readable JSON bundle.

    Refuses to overwrite an existing questionnaire unless ``force`` is set: a
    finished, reviewed plan must never be silently replaced by a generated one.
    """
    os.makedirs(out_dir, exist_ok=True)
    written: Dict[str, str] = {}
    for plan in plans:
        name = ROLE_FILENAMES[plan.role]
        path = os.path.join(out_dir, name)
        if os.path.exists(path) and not force:
            written[plan.role] = ""
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(plan_markdown(plan, generated_at=stamp))
        written[plan.role] = path

    bundle = os.path.join(out_dir, "interview_plans.json")
    if not os.path.exists(bundle) or force:
        payload = {
            "generated_at": stamp or time.strftime("%Y-%m-%dT%H:%M:%S"),
            "plans": [p.as_dict() for p in plans],
        }
        with open(bundle, "w", encoding="utf-8") as fh:
            import json
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        written["bundle"] = bundle
    return written


def build_all(firm: str, missing_facts: Iterable[str] = (),
              open_questions: Iterable[str] = (),
              interviewees: Optional[Dict[str, str]] = None) -> List[InterviewPlan]:
    interviewees = interviewees or {}
    return [build_plan(role, firm, missing_facts=missing_facts,
                       open_questions=open_questions,
                       interviewee=interviewees.get(role, ""))
            for role in ROLES]
