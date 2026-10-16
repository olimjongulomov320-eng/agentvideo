# -*- coding: utf-8 -*-
"""story.py — concepts, script, storyboard and the scene manifest.

The story builder is **template-driven, not generative**: it only writes
sentences that the evidence ledger can support. When a fact is missing it emits
an explicit placeholder like ``[founding year — not found in accessible
sources]`` so a human sees the gap rather than a confident invention.
"""
import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .research import CORROBORATED, Claim, ResearchResult, VERIFIED

PLACEHOLDER = "[{} — not found in accessible sources]"

# Scene arc: (key, weight, kind)
ARC = [
    ("hook",   1.0, "statement"),
    ("origin", 2.0, "timeline"),
    ("practice", 1.5, "list"),
    ("achievements", 1.5, "stat"),
    ("people", 1.3, "statement"),
    ("office", 1.5, "title"),
    ("closing", 1.0, "endcard"),
]

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

# Which single fact each historical scene depends on ("" = no external fact).
SCENE_FACT = {
    "origin": "founding_year",
    "practice": "practice_areas",
    "achievements": "achievement",
    "office": "new_office",
}
PRACTICE_HINTS = [
    "corporate", "m&a", "it", "cyber", "tax", "banking", "labour", "labor",
    "ip", "intellectual property", "customs", "arbitration", "dispute",
    "economic disputes", "islamic finance", "исламск", "корпоратив", "кибер",
    "налог", "iqtisodiy", "korporativ", "soliq",
]
ADDRESS_RE = re.compile(
    r"(?i)(\d+[a-zа-я]?[-\s]?(?:uy|house|дом|street|ko['’]?chasi|улица|tumani|district|rayon)[^.,;]{0,40})")

# Word-boundary matcher for the hints above: the short ones ("it", "ip") would
# otherwise match inside unrelated words such as "politics".
PRACTICE_RE = re.compile(
    r"(?i)(?<![0-9a-z])(?:%s)(?![0-9a-z])"
    % "|".join(re.escape(h) for h in sorted(PRACTICE_HINTS, key=len, reverse=True)))


# ----------------------------------------------------------------- facts layer
@dataclass
class Fact:
    key: str
    value: str
    source_id: str
    source_url: str
    confidence: str
    note: str = ""


@dataclass
class Facts:
    firm_name: str
    items: Dict[str, Fact] = field(default_factory=dict)

    def has(self, key: str) -> bool:
        return key in self.items

    def get(self, key: str) -> Optional[str]:
        f = self.items.get(key)
        return f.value if f else None

    def note(self, key: str) -> str:
        f = self.items.get(key)
        return f"{f.value} [{f.source_id} · {f.confidence}]" if f else ""

    def source(self, key: str) -> str:
        """URL (or id) of the single claim a fact rests on, or ""."""
        f = self.items.get(key)
        if not f:
            return ""
        return f.source_url or f.source_id

    def confidence(self, key: str) -> str:
        f = self.items.get(key)
        return f.confidence if f else ""

    def missing(self) -> List[str]:
        wanted = ["founding_year", "practice_areas", "new_office", "achievement"]
        return [w for w in wanted if w not in self.items]


# A claimed achievement is never taken from the firm's own marketing line.
# Keyword stems carry their own tail (leading\w*, ведущ\w*) because Russian
# participles continue with letters, which would break a plain \b boundary.
_SUPER_SENT = re.compile(
    r"(?i)^[^.!?]{0,160}?(?<![0-9a-z])"
    r"(?:leading\w*|best\w*|top\w*|premier\w*|largest\w*|first\w*|"
    r"winning\w*|award\w*|№\s*1|no\.?\s*1|"
    r"ведущ\w*|лучш\w*|крупнейш\w*|признанн\w*|награжд\w*|один из|"
    r"eng\s+zo['’]?r\w*|birinchi|yagona)"
    r"(?![0-9a-z])[^.!?]{0,160}?[.!?]\s*")


def _strip_superlatives(text: str) -> str:
    """Drop sentences that make a superlative claim, keeping the factual rest.

    The page description of a law firm is often "Leading firm in X. We do Y, Z."
    Only the second sentence may become practice areas; the claim is a claim.
    """
    prev = None
    t = (text or "").strip()
    while prev != t:
        prev = t
        t = _SUPER_SENT.sub("", t).strip()
    return t


def extract_facts(result: ResearchResult, firm_name: str,
                  event_date: str = "", new_office: str = "") -> Facts:
    """Pull the few facts a script can stand on, only from what was read."""
    facts = Facts(firm_name=firm_name)

    def add(key: str, value: str, c: Claim, confidence: str, note_key: str = "") -> None:
        if key in facts.items:
            return
        facts.items[key] = Fact(key=key, value=value, source_id=c.source_id,
                                source_url=c.source_url, confidence=confidence,
                                note=note_key)

    # A founding year may only come from an explicit founding expression. An
    # earlier, shorter alternation allowed a stray letter to match
    # ("…юридическом … 2025"), which would have *invented* a founding date.
    # The keyword now has to actually assert a foundation.
    year_re = re.compile(
        r"(?i)(?<![0-9a-z])"
        r"(founded|founding|establish(?:ed)?|establishment|inception|since|"
        r"создан(?:ы|о|а)?|основан(?:ы|о|а)?|основа(?:ние|нием)|"
        r"год основания|дата основания|"
        r"tashkil\s*(?:etilgan|etilgani)|ta['’]?sis\s*etilgan|"
        r"asos\s*sol|yildan|beri)"
        r"\D{0,30}((?:19|20)\d{2})")
    for c in result.claims:
        m = year_re.search(c.text)
        if m and "founding_year" not in facts.items:
            add("founding_year", m.group(2), c, c.evidence_class)
        # An on-screen milestone must be Verified or Corroborated. A statistic
        # or news heading the firm published about itself is never presented as
        # an achievement of the film.
        if (c.evidence_class in (VERIFIED, CORROBORATED)
                and "achievement" not in facts.items
                and YEAR_RE.search(c.text)):
            add("achievement", c.text[:180], c, c.evidence_class)
        found = PRACTICE_RE.search(c.text) is not None
        if found and "practice_areas" not in facts.items and c.relevance in (
                "description", "heading", "statement"):
            cleaned = _strip_superlatives(c.text)
            if len(cleaned) >= 15:
                add("practice_areas", cleaned[:200], c, c.evidence_class)

    if event_date:
        facts.items["event_date"] = Fact("event_date", event_date, "USER", "supplied",
                                         "CORROBORATED", "supplied by the operator")
    if new_office:
        facts.items["new_office"] = Fact("new_office", new_office, "USER", "supplied",
                                         "CORROBORATED", "supplied by the operator")
    return facts


# ----------------------------------------------------------------- narration
NARR = {
    "en": {
        "hook": "Every day, people wait for an answer from the law. Sometimes it arrives too late.",
        "origin": "{firm} was founded in {year} in Tashkent.",
        "origin_no_year": "{firm} began its work in Tashkent. {ph}",
        "practice": "The firm chose a demanding path: {areas}",
        "achievements": "One milestone on the record: {a}",
        "people": "Technology speeds up the work. Trust is built by people.",
        "office": "A new office marks the next stage.",
        "closing": "{firm}. The work continues.",
        "ph_year": "[founding year — not found in accessible sources]",
        "ph_areas": "[practice areas — not found in accessible sources]",
        "ph_ach": "[verified milestone — not found in accessible sources]",
        "ph_office": "[new office address — supply to complete this scene]",
    },
    "ru": {
        "hook": "Каждый день люди ждут ответа от закона. Порой этот ответ приходит слишком поздно.",
        "origin": "{firm} основана в {year} году в Ташкенте.",
        "origin_no_year": "{firm} начала работу в Ташкенте. {ph}",
        "practice": "Фирма выбрала непростой путь: {areas}",
        "achievements": "Одна веха из источников: {a}",
        "people": "Технология ускоряет работу. Доверие строит человек.",
        "office": "Новый офис — это следующий этап.",
        "closing": "{firm}. Работа продолжается.",
        "ph_year": "[год основания — не найден в доступных источниках]",
        "ph_areas": "[направления практики — не найдены в доступных источниках]",
        "ph_ach": "[подтверждённая веха — не найдена в доступных источниках]",
        "ph_office": "[адрес нового офиса — требуется уточнение]",
    },
    "uz": {
        "hook": "Har kuni odamlar qonundan javob kutadi. Ba'zida bu javob juda kech keladi.",
        "origin": "{firm} {year}-yilda Toshkentda tashkil etilgan.",
        "origin_no_year": "{firm} o'z faoliyatini Toshkentda boshlagan. {ph}",
        "practice": "Firma qiyin yo'nalishni tanladi: {areas}",
        "achievements": "Manbalarda qayd etilgan natija: {a}",
        "people": "Texnologiya ishni tezlashtiradi. Ishonchni esa odam quradi.",
        "office": "Yangi ofis — keyingi bosqich uchun maydon.",
        "closing": "{firm}. Ish davom etadi.",
        "ph_year": "[tashkil etilgan yil — ochiq manbalarda topilmadi]",
        "ph_areas": "[faoliyat yo'nalishlari — ochiq manbalarda topilmadi]",
        "ph_ach": "[tasdiqlangan natija — ochiq manbalarda topilmadi]",
        "ph_office": "[yangi ofis manzili — aniqlanishi kerak]",
    },
}
LANGS = tuple(NARR.keys())


def normalize_lang(lang: str) -> str:
    l = (lang or "en").strip().lower()[:2]
    return l if l in NARR else "en"


def scene_text(key: str, facts: Facts, lang: str) -> Dict[str, str]:
    """Return {narration, heading, sub} for one arc scene."""
    t = NARR[lang]
    firm = facts.firm_name
    heading, sub, narration = "", "", ""
    needs: List[str] = []

    if key == "hook":
        narration = t["hook"]
        heading = ""
        sub = ""
    elif key == "origin":
        year = facts.get("founding_year")
        if year:
            narration = t["origin"].format(firm=firm, year=year)
        else:
            narration = t["origin_no_year"].format(firm=firm, ph=t["ph_year"])
            needs.append("founding_year")
        heading = (year or t["ph_year"])
        sub = firm
    elif key == "practice":
        areas = facts.get("practice_areas")
        if areas:
            narration = t["practice"].format(areas=areas)
            sub = areas[:120]
        else:
            narration = t["practice"].format(areas=t["ph_areas"])
            sub = t["ph_areas"]
            needs.append("practice_areas")
        heading = "Practice"
    elif key == "achievements":
        a = facts.get("achievement")
        if a:
            narration = t["achievements"].format(a=a)
            sub = a[:120]
        else:
            narration = t["achievements"].format(a=t["ph_ach"])
            sub = t["ph_ach"]
            needs.append("achievement")
        heading = "Record"
    elif key == "people":
        narration = t["people"]
        heading = "People"
    elif key == "office":
        narration = t["office"]
        office = facts.get("new_office")
        sub = office if office else t["ph_office"]
        if not office:
            needs.append("new_office")
        heading = sub
    elif key == "closing":
        narration = t["closing"].format(firm=firm)
        heading = firm
    return {"narration": narration, "heading": heading, "sub": sub,
            "needs": ",".join(needs)}


# ----------------------------------------------------------------- concepts
def build_concepts(firm: str, facts: Facts, result: ResearchResult) -> List[Dict[str, Any]]:
    usable = len(result.claims)
    return [
        {
            "id": "concept-a",
            "title": "The Distance",
            "central_idea": "Justice is delayed by distance and time; the firm closes that gap, and now builds legal AI to close it faster.",
            "evidence_fit": "Strong (uses only what the ledger supports; gaps become placeholders)",
            "strengths": [
                "Emotionally legible in every language",
                "Works without archive photos",
                "Sets up an AI/technology climax honestly",
            ],
            "weaknesses": [
                "Depends on one milestone being verifiable",
                "Needs an evocative opening image",
            ],
            "recommended": True,
        },
        {
            "id": "concept-b",
            "title": "Built by Hand",
            "central_idea": "A firm built case by case — the story is people, habits and standards, not slogans.",
            "evidence_fit": "Medium (strongest if interviews are recorded)",
            "strengths": ["Human and warm", "Ideal if clients/team clips exist"],
            "weaknesses": ["Weak without interview audio", "Risk of drifting into praise"],
            "recommended": False,
        },
        {
            "id": "concept-c",
            "title": "The Record",
            "central_idea": "An evidence-led film: dates, documents and milestones shown as a timeline.",
            "evidence_fit": "Strong and safest (closest to the ledger)",
            "strengths": ["Verifiable on screen", "Credible for a legal audience"],
            "weaknesses": ["Coolest tone", "Fewer emotional peaks"],
            "recommended": False,
        },
    ]


# ----------------------------------------------------------------- script + storyboard
def plan_durations(total_sec: float) -> Dict[str, float]:
    weight_sum = sum(w for _, w, _ in ARC)
    out = {}
    for key, w, _ in ARC:
        out[key] = round(total_sec * (w / weight_sum), 2)
    return out


def build_scenes(firm: str, facts: Facts, lang: str,
                 total_sec: float = 140.0) -> List[Dict[str, Any]]:
    durs = plan_durations(total_sec)
    scenes: List[Dict[str, Any]] = []
    acc = 0.0
    for i, (key, _w, kind) in enumerate(ARC):
        txt = scene_text(key, facts, lang)
        dur = durs[key]
        # Every historical scene must carry the single source it stands on so
        # the script and storyboard can cite it.
        fact_key = SCENE_FACT.get(key, "")
        scenes.append({
            "id": "sc%d" % (i + 1),
            "key": key,
            "kind": kind,
            "start": round(acc, 2),
            "dur": dur,
            "heading": txt["heading"],
            "sub": txt["sub"],
            "narration": txt["narration"],
            "needs": [n for n in txt["needs"].split(",") if n],
            "transition": "fade",
            "asset": None,
            "placeholder": bool(txt["needs"]),
            "source": facts.source(fact_key) if fact_key else "",
            "source_id": (facts.items.get(fact_key).source_id
                          if fact_key and fact_key in facts.items else ""),
            "evidence": (facts.confidence(fact_key) if fact_key else ""),
        })
        acc += dur
    return scenes


def script_markdown(firm: str, concepts: List[Dict[str, Any]], scenes: List[Dict[str, Any]],
                    lang: str, style: str, total_sec: float) -> str:
    recommended = next((c for c in concepts if c.get("recommended")), concepts[0])
    lines = [
        "# Script — %s" % firm,
        "",
        "**Style:** %s · **Language:** %s · **Target runtime:** %.0f s (%.1f min)"
        % (style, lang.upper(), total_sec, total_sec / 60.0),
        "",
        "**Central idea:** %s" % recommended["central_idea"],
        "",
        "> Auto-drafted from the evidence ledger. Anything in `[square brackets]` is a "
        "**gap**, not a fact. A human must approve this draft before rendering.",
        "",
        "## Scene-by-scene",
        "",
        "Each row cites the claim the narration rests on. `—` means the scene is "
        "structural (no external fact); `Gaps` names what a human must still supply.",
        "",
        "| # | Scene | In | Dur | Heading | Narration | Source | Evidence | Gaps |",
        "|---|-------|----|-----|---------|-----------|--------|----------|------|",
    ]
    for s in scenes:
        src = s.get("source") or "—"
        if len(src) > 70:
            src = src[:67] + "…"
        lines.append("| %s | %s | %.1fs | %.1fs | %s | %s | %s | %s | %s |" % (
            s["id"], s["key"], s["start"], s["dur"],
            (s["heading"] or "—").replace("|", "/")[:40],
            s["narration"].replace("|", "/")[:120],
            src.replace("|", "/"),
            s.get("evidence") or "—",
            ", ".join(s["needs"]) or "—"))
    lines += ["", "## Concepts considered", ""]
    for c in concepts:
        mark = " **(recommended)**" if c.get("recommended") else ""
        lines.append("### %s — %s%s" % (c["id"], c["title"], mark))
        lines.append("")
        lines.append("_%s_" % c["central_idea"])
        lines.append("")
        lines.append("- Evidence fit: %s" % c["evidence_fit"])
        lines.append("- Strengths: " + "; ".join(c["strengths"]))
        lines.append("- Weaknesses: " + "; ".join(c["weaknesses"]))
        lines.append("")
    lines += [
        "## Permission & confidentiality",
        "",
        "- Client-identifying matter is excluded from public deliverables.",
        "- Case results and firm statistics are `UNVERIFIED`/`SINGLE-SOURCE` until corroborated.",
        "- Music must be licensed; synthesized audio must be labelled as such.",
        "- No external publication without the operator's explicit approval.",
    ]
    return "\n".join(lines) + "\n"


def storyboard_markdown(firm: str, scenes: List[Dict[str, Any]], style: str) -> str:
    lines = ["# Storyboard — %s" % firm, "", "**Style:** %s" % style, ""]
    for s in scenes:
        lines.append("## %s — %s (%.1fs @ %.1fs)" % (s["id"], s["key"], s["dur"], s["start"]))
        lines.append("")
        lines.append("- **Visual:** %s" % _visual_for(s, style))
        lines.append("- **On-screen text:** %s" % (s["heading"] or "—"))
        if s["sub"]:
            lines.append("- **Supporting line:** %s" % s["sub"])
        lines.append("- **Narration:** %s" % s["narration"])
        lines.append("- **Transition out:** %s" % s["transition"])
        if s.get("source"):
            lines.append("- **Source:** %s%s" % (
                s["source"],
                " · evidence class **%s**" % s["evidence"] if s.get("evidence") else ""))
        elif s.get("source_id"):
            lines.append("- **Source:** %s" % s["source_id"])
        if s["needs"]:
            lines.append("- **⚠ Gap:** %s" % ", ".join(s["needs"]))
        if s.get("placeholder"):
            lines.append("- **⚠ Placeholder on screen:** visible marker — "
                         "not a finished fact")
        lines.append("")
    return "\n".join(lines) + "\n"


def _visual_for(scene: Dict[str, Any], style: str) -> str:
    base = {
        "statement": "Full-frame typographic statement over a graded background.",
        "timeline": "Timeline marker with the founding year and a line drawing across frame.",
        "list": "Sequential keyword reveals on a ruled grid.",
        "stat": "Large number/milestone card with a supporting rule.",
        "title": "Title card with the address; slow push-in.",
        "endcard": "Logo end card on cream with the firm name and a closing line.",
    }.get(scene["kind"], "Typographic card.")
    if style == "illustrated":
        return "Illustrated 2D: layered flat shapes with keyframed drift — " + base.lower()
    if style == "blender3d":
        return "3D: lit scene with camera move — " + base.lower()
    return "Motion graphics: " + base.lower()


def build_story_assets(out_dir: str, firm: str, facts: Facts, result: ResearchResult,
                       lang: str, style: str, total_sec: float) -> Dict[str, Any]:
    """Write concepts.md, script.md, storyboard.md, scene_manifest.json. Returns paths."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    concepts = build_concepts(firm, facts, result)
    scenes = build_scenes(firm, facts, lang, total_sec)

    paths = {}
    p = os.path.join(out_dir, "concepts.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# Concepts — %s\n\n" % firm)
        for c in concepts:
            fh.write("## %s — %s%s\n\n_%s_\n\n- Evidence fit: %s\n- Strengths: %s\n- Weaknesses: %s\n\n" % (
                c["id"], c["title"], " (recommended)" if c.get("recommended") else "",
                c["central_idea"], c["evidence_fit"], "; ".join(c["strengths"]),
                "; ".join(c["weaknesses"])))
    paths["concepts.md"] = p

    p = os.path.join(out_dir, "script.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script_markdown(firm, concepts, scenes, lang, style, total_sec))
    paths["script.md"] = p

    p = os.path.join(out_dir, "storyboard.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(storyboard_markdown(firm, scenes, style))
    paths["storyboard.md"] = p

    manifest = {
        "firm": firm,
        "language": normalize_lang(lang),
        "style": style,
        "total_duration_sec": total_sec,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "facts": {k: {"value": v.value, "source": v.source_id,
                      "confidence": v.confidence} for k, v in facts.items.items()},
        "gaps": facts.missing(),
        "scenes": scenes,
    }
    p = os.path.join(out_dir, "scene_manifest.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    paths["scene_manifest.json"] = p
    return paths
