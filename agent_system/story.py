# -*- coding: utf-8 -*-
"""story.py — concepts, script, storyboard and the scene manifest.

The story builder is **template-driven, not generative**: it only writes
sentences that the evidence ledger can support. When a fact is missing it emits
an explicit placeholder like ``[founding year — not found in accessible
sources]`` so a human sees the gap rather than a confident invention.
"""
import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .research import (CORROBORATED, Claim, ResearchResult, SINGLE_SOURCE,
                       UNVERIFIED, VERIFIED)

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

    _extract_site_data_facts(result, facts)
    _apply_confirmed_facts(facts, firm_name)

    if event_date:
        facts.items["event_date"] = Fact("event_date", event_date, "USER", "supplied",
                                         "CORROBORATED", "supplied by the operator")
    if new_office:
        facts.items["new_office"] = Fact("new_office", new_office, "USER", "supplied",
                                         "CORROBORATED", "supplied by the operator")
    return facts



# ----------------------------------------------------------- language guard
# A fact scraped from a Russian page must not leak raw Russian into an Uzbek or
# English film. Known practice areas are translated; anything else is treated
# as missing rather than shown in the wrong language.
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")
_AREA_GLOSSARY = [
    (r"(?<![а-яa-z])it(?![а-яa-z])|(?<![а-я])ит(?![а-я])|кибер", {
        "en": "IT and cyber law", "uz": "IT va kiber huquq", "ru": "IT- и киберправо"}),
    (r"m\s*&\s*a|слиян\w*", {"en": "M&A", "uz": "M&A", "ru": "M&A"}),
    (r"корпоративн\w*", {
        "en": "corporate law", "uz": "korporativ huquq", "ru": "корпоративное право"}),
    (r"экономическ\w*\s+спор\w*", {
        "en": "economic disputes", "uz": "iqtisodiy nizolar", "ru": "экономические споры"}),
    (r"налог\w*", {"en": "tax law", "uz": "soliq huquqi", "ru": "налоговое право"}),
    (r"банковск\w*", {"en": "banking law", "uz": "bank huquqi", "ru": "банковское право"}),
    (r"арбитраж\w*", {"en": "arbitration", "uz": "arbitraj", "ru": "арбитраж"}),
    (r"интеллектуальн\w*", {"en": "intellectual property",
                            "uz": "intellektual mulk", "ru": "интеллектуальная собственность"}),
    (r"трудов\w*", {"en": "labour law", "uz": "mehnat huquqi", "ru": "трудовое право"}),
    (r"таможенн\w*", {"en": "customs law", "uz": "bojxona huquqi", "ru": "таможенное право"}),
    (r"контракт\w*|договор\w*", {"en": "contract law", "uz": "shartnoma huquqi", "ru": "контрактное право"}),
    (r"недвижимост\w*", {"en": "real estate", "uz": "ko'chmas mulk", "ru": "недвижимость"}),
    (r"уголовн\w*", {"en": "criminal defence for business", "uz": "biznesni jinoiy himoya qilish",
                      "ru": "уголовная защита бизнеса"}),
    (r"исламск\w*", {"en": "Islamic finance", "uz": "islom moliyasi", "ru": "исламские финансы"}),
]


def localise_text(text: str, lang: str) -> str:
    """Return ``text`` in ``lang`` when it can be done safely, else "".

    Text already in the target script is returned unchanged. Cyrillic text for
    a non-Russian film is mapped through the practice-area glossary; if no term
    is recognised the result is "" so the caller records a gap instead of
    showing the wrong language on screen.
    """
    if lang == "ru" or not _CYRILLIC_RE.search(text or ""):
        return text
    low = text.lower()
    found: List[str] = []
    for pattern, names in _AREA_GLOSSARY:
        if re.search(pattern, low) and names[lang] not in found:
            found.append(names[lang])
    return ", ".join(found)


CONFIRMED_KEYS = ("years_experience", "founding_year", "new_office", "address",
                  "clients", "team_size", "achievement")


def _confirmed_facts_path() -> str:
    return os.environ.get("AGENT_CONFIRMED_FACTS") or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "confirmed_facts.json")


def _apply_confirmed_facts(facts: Facts, firm_name: str) -> None:
    """Facts the operator has confirmed outright win over anything scraped.

    ``confirmed_facts.json`` maps a firm name to values, e.g.
    ``{"gsp law firm": {"years_experience": "16"}}``. They are recorded as
    operator-confirmed, so a plain figure replaces the site's open-ended "16+".
    """
    try:
        with open(_confirmed_facts_path(), "r", encoding="utf-8") as fh:
            table = json.load(fh)
    except (OSError, ValueError):
        return
    name = (firm_name or "").strip().lower()
    for firm, values in (table or {}).items():
        if not isinstance(values, dict) or str(firm).strip().lower() not in name \
                and name not in str(firm).strip().lower():
            continue
        for key, value in values.items():
            if key in CONFIRMED_KEYS and str(value).strip():
                facts.items[key] = Fact(key, str(value).strip(), "OPERATOR",
                                        "confirmed_facts.json", "CORROBORATED",
                                        "confirmed by the operator")


_STAT_YEARS_RE = re.compile(r"(?i)^(\d+\+?)\s*(?:лет|года?|years?|yil)\b")
_STAT_LAWYERS_RE = re.compile(r"(?i)^(\d+\+?)\s*(?:адвокат\w*|юрист\w*|lawyers?|advokat\w*)")
_STAT_CLIENTS_RE = re.compile(r"(?i)^(\d+\+?)\s*(?:клиент\w*|clients?|mijoz\w*)")


def _extract_site_data_facts(result: ResearchResult, facts: Facts) -> None:
    """Facts the firm publishes about itself in its site data file.

    These are self-reported (SINGLE-SOURCE): the script phrases them as the
    firm's own figures and never as verified achievements.
    """
    areas: List[str] = []
    team: List[str] = []
    leaders: List[str] = []
    photos: Dict[str, str] = {}
    area_claim = team_claim = None
    for c in result.claims:
        t = (c.text or "").strip()
        if c.evidence_class == "CONFLICTING":
            continue    # a figure the firm contradicts itself on is never narrated
        if c.relevance == "statistic_or_superlative":
            for key, rx in (("years_experience", _STAT_YEARS_RE),
                            ("team_size", _STAT_LAWYERS_RE),
                            ("clients", _STAT_CLIENTS_RE)):
                m = rx.match(t)
                if m and key not in facts.items:
                    facts.items[key] = Fact(key, m.group(1), c.source_id, c.source_url,
                                            c.evidence_class, "self-reported")
        elif t.startswith("Address: ") and "address" not in facts.items:
            facts.items["address"] = Fact("address", t[9:].strip(), c.source_id,
                                          c.source_url, c.evidence_class, "self-reported")
        elif t.startswith("Practice area: "):
            areas.append(t[15:].strip())
            area_claim = area_claim or c
        elif t.startswith("Team member: "):
            name, _sep, role = t[13:].partition(" — ")
            name = name.strip()
            if name and name not in team:
                team.append(name)
                # Founders and partners lead the film; other staff follow.
                if re.search(r"(?i)основател|партн|founder|partner|hamkor|sherik", role):
                    leaders.append(name)
            team_claim = team_claim or c
        elif t.startswith("Team photo: ") and " | " in t:
            pname, _sep, purl = t[12:].partition(" | ")
            photos[pname.strip()] = purl.strip()
    if areas:
        # The structured list of services beats a regex over a marketing blurb.
        facts.items["practice_areas"] = Fact(
            "practice_areas", ", ".join(areas[:8]), area_claim.source_id,
            area_claim.source_url, area_claim.evidence_class, "services list")
    if team:
        team = leaders + [n for n in team if n not in leaders]
        shown = [n for n in team if n in photos][:4] or team[:4]
        facts.items["team_photos"] = Fact(
            "team_photos", ";;".join("%s|%s" % (n, photos[n]) for n in shown if n in photos),
            team_claim.source_id, team_claim.source_url, team_claim.evidence_class,
            "photos published on the firm's own site")
        facts.items["team"] = Fact("team", ", ".join(shown), team_claim.source_id,
                                   team_claim.source_url, team_claim.evidence_class,
                                   "named on the firm's site")


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
        # On-screen headings. Kept in the target language so a localised film
        # never shows a stray English word (a source-language leak).
        "h_practice": "Practice",
        "h_record": "Record",
        "h_people": "People",
        "origin_years": "By its own account, {firm} has been working for more than {n} years.",
        "origin_years_exact": "{firm} has been working for {n} years.",
        "ach_stats": "By the firm's own figures: {parts}.",
        "n_clients": "{n} clients", "n_lawyers": "{n} lawyers",
        "office_addr": "You will find us at {a}.",
        "h_address": "Address",
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
        "h_practice": "Практика",
        "h_record": "Результаты",
        "h_people": "Люди",
        "origin_years": "По данным самой фирмы, {firm} работает более {n} лет.",
        "origin_years_exact": "{firm} работает уже {n} лет.",
        "ach_stats": "По данным фирмы: {parts}.",
        "n_clients": "{n} клиентов", "n_lawyers": "{n} адвокатов",
        "office_addr": "Мы находимся по адресу: {a}.",
        "h_address": "Адрес",
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
        "h_practice": "Faoliyat",
        "h_record": "Natijalar",
        "h_people": "Odamlar",
        "origin_years": "Firma ma'lumotiga ko'ra, {firm} {n} yildan ortiq faoliyat yuritmoqda.",
        "origin_years_exact": "{firm} {n} yildan beri faoliyat yuritmoqda.",
        "ach_stats": "Firma ma'lumotiga ko'ra: {parts}.",
        "n_clients": "{n} mijoz", "n_lawyers": "{n} advokat",
        "office_addr": "Manzilimiz: {a}.",
        "h_address": "Manzil",
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
        years = facts.get("years_experience")
        if year:
            narration = t["origin"].format(firm=firm, year=year)
        elif years:
            # "16+" is an open-ended claim; a plain "16" has been confirmed exactly.
            tpl = t["origin_years"] if years.endswith("+") else t["origin_years_exact"]
            narration = tpl.format(firm=firm, n=years.rstrip("+"))
            heading, sub = years, firm
        else:
            narration = t["origin_no_year"].format(firm=firm, ph=t["ph_year"])
            needs.append("founding_year")
        if year or not years:
            heading = (year or t["ph_year"])
            sub = firm
    elif key == "practice":
        areas = localise_text(facts.get("practice_areas") or "", lang)
        # A film names a handful of practices; the full list stays in the ledger.
        areas = ", ".join(areas.split(", ")[:5])
        if areas:
            narration = t["practice"].format(areas=areas)
            sub = areas[:120]
        else:
            narration = t["practice"].format(areas=t["ph_areas"])
            sub = t["ph_areas"]
            needs.append("practice_areas")
        heading = t["h_practice"]
    elif key == "achievements":
        a = facts.get("achievement")
        if a:
            narration = t["achievements"].format(a=a)
            sub = a[:120]
        elif facts.get("clients") or facts.get("team_size"):
            parts = []
            if facts.get("clients"):
                parts.append(t["n_clients"].format(n=facts.get("clients")))
            if facts.get("team_size"):
                parts.append(t["n_lawyers"].format(n=facts.get("team_size")))
            narration = t["ach_stats"].format(parts=", ".join(parts))
            sub = " · ".join(parts)
        else:
            narration = t["achievements"].format(a=t["ph_ach"])
            sub = t["ph_ach"]
            needs.append("achievement")
        heading = (facts.get("clients") or facts.get("team_size")) if (
            not a and (facts.get("clients") or facts.get("team_size"))) else t["h_record"]
    elif key == "people":
        narration = t["people"]
        heading = t["h_people"]
        sub = facts.get("team") or ""
    elif key == "office":
        narration = t["office"]
        office = facts.get("new_office")
        address = localise_text(facts.get("address") or "", lang)
        if office:
            sub = office
            heading = sub
        elif address:
            # Only the firm's published address: it is not claimed to be new.
            narration = t["office_addr"].format(a=address)
            sub = address
            heading = t["h_address"]
        else:
            sub = t["ph_office"]
            heading = sub
            needs.append("new_office")
    elif key == "closing":
        narration = t["closing"].format(firm=firm)
        heading = firm
    return {"narration": narration, "heading": heading, "sub": sub,
            "needs": ",".join(needs)}


# ----------------------------------------------------------------- concepts
# A concept may only put a *factual* sentence about the firm into its central
# idea when the evidence ledger can carry it. Creative framing — "a story of
# people, not slogans" — is a choice about tone, not a claim, and is always
# allowed. The distinction is kept explicit so a reviewer can see, per concept,
# which words are evidence and which are craft.
_TECH_CLAIM_RE = re.compile(
    r"(?i)(?<![0-9a-z])"
    r"(?:legal\s+ai|ai[-\s]?(?:powered|driven|enabled)|"
    r"artificial\s+intelligence|machine\s+learning|deep\s+learning|"
    r"neural\s+network\w*|"
    r"искусственн\w*\s+интеллект|нейросет\w*|"
    r"suniy\s+intellekt)"
    r"(?![0-9a-z])")

FIT_STRONG = "Strong"
FIT_MEDIUM = "Medium"
FIT_LIMITED = "Limited"
_FIT_RANK = {FIT_STRONG: 3, FIT_MEDIUM: 2, FIT_LIMITED: 1}


def _line(text: str, source_id: str, evidence_class: str, suffix: str = "") -> str:
    return "%s%s [%s · %s]" % (" ".join((text or "").split())[:160],
                               suffix, source_id or "—",
                               evidence_class or UNVERIFIED)


def _dedupe(items: List[str]) -> List[str]:
    out: List[str] = []
    for it in items:
        if it and it not in out:
            out.append(it)
    return out


def tech_support(result: Optional[ResearchResult]) -> List[str]:
    """Ledger claims that actually put legal/AI technology at this firm."""
    if result is None:
        return []
    return [_line(c.text, c.source_id, c.evidence_class)
            for c in (result.claims or []) if _TECH_CLAIM_RE.search(c.text or "")]


def evidence_basis(facts: Optional[Facts], result: Optional[ResearchResult],
                   interview_claims: Sequence = ()) -> Dict[str, List[str]]:
    """Bucket what the film may stand on, keeping the categories separate.

    * ``documented_facts``      — verified/corrobated; may be stated as fact
    * ``attributed_statements`` — single-source; evidence the speaker said it
    * ``creative_framing``      — a choice of tone; never a claim
    * ``unresolved_claims``     — named gaps, disclosed rather than filled

    A privacy-flagged interview statement (client-identifying or privileged) is
    withheld from every bucket and counted instead as a disclosed gap: it stays
    in the interview analysis and the permission checklist, where a human decides
    on it, and is never copied into an artefact that could read as cleared.
    """
    facts = facts or Facts(firm_name="")
    result = result or ResearchResult(firm_name="")

    documented: List[str] = []
    attributed: List[str] = []
    for key, f in facts.items.items():
        if f.source_id == "USER":
            # Operator-supplied input, not evidence found in any source.
            continue
        text = "%s (%s)" % (key, f.value)
        bucket = documented if f.confidence in (VERIFIED, CORROBORATED) else attributed
        bucket.append(_line(text, f.source_id, f.confidence))
    for c in result.claims:
        bucket = (documented if c.evidence_class in (VERIFIED, CORROBORATED)
                  else attributed)
        bucket.append(_line(c.text, c.source_id, c.evidence_class))
    quarantined = 0
    for c in interview_claims:
        if getattr(c, "privacy_flags", None):
            # Flagged as client-identifying or privileged. The statement stays in
            # the interview analysis and the permission checklist — that is where
            # a human decides on it — but it is never carried into another
            # artefact where it could be mistaken for cleared material. The
            # content is withheld; only the fact that something was withheld is
            # disclosed, so the gap is visible without the detail leaking.
            quarantined += 1
            continue
        attributed.append(_line("recollection: %s" % getattr(c, "text", ""),
                                "interview", SINGLE_SOURCE))

    unresolved = list(facts.missing())
    if quarantined:
        unresolved.append(
            "%d interview statement(s) withheld from review artefacts "
            "(client-identifying or privileged) pending a confidentiality "
            "decision" % quarantined)
    return {"documented_facts": _dedupe(documented),
            "attributed_statements": _dedupe(attributed),
            "creative_framing": [],
            "unresolved_claims": _dedupe(unresolved)}


def build_concepts(firm: str, facts: Optional[Facts],
                   result: Optional[ResearchResult],
                   interview_claims: Sequence = ()) -> List[Dict[str, Any]]:
    """Three genuinely distinct concepts, each honest about what it may assert.

    The three keep different *approaches* (emotional framing, human texture,
    evidence timeline); what changes with the evidence is which firm-specific
    claims each is allowed to make, how candid its evidence-fit label is, and
    which gaps it discloses. Nothing the ledger cannot carry is invented, and a
    concept is never labelled "Strong" while it asserts something unsupported.

    Exactly one concept is always recommended: the highest evidence fit, with
    the list order as a stable tie-break so a thin-evidence job still gets a
    single, clearly marked suggestion.
    """
    facts = facts or Facts(firm_name=firm)
    result = result or ResearchResult(firm_name=firm)
    basis = evidence_basis(facts, result, interview_claims)
    gaps = list(basis["unresolved_claims"])
    documented = basis["documented_facts"]
    ai_claims = tech_support(result)
    # The same technology claims, but only the ones a source actually backs:
    # single-source statements say the firm *said* it, not that it is true.
    tech_documented = [
        c for c in (result.claims or [])
        if _TECH_CLAIM_RE.search(c.text or "")
        and c.evidence_class in (VERIFIED, CORROBORATED)]

    concepts: List[Dict[str, Any]] = [
        {
            "id": "concept-a",
            "title": "The Distance",
            "evidence_fit_level": FIT_LIMITED,
            "evidence_fit": "",
            "strengths": [],
            "weaknesses": [],
            "central_idea": "",
            "asserted_claims": [],
            "evidence_sources": [],
        },
        {
            "id": "concept-b",
            "title": "Built by Hand",
            "evidence_fit_level": FIT_MEDIUM,
            "evidence_fit": "",
            "strengths": [],
            "weaknesses": [],
            "central_idea": "",
            "asserted_claims": [],
            "evidence_sources": [],
        },
        {
            "id": "concept-c",
            "title": "The Record",
            "evidence_fit_level": FIT_LIMITED,
            "evidence_fit": "",
            "strengths": [],
            "weaknesses": [],
            "central_idea": "",
            "asserted_claims": [],
            "evidence_sources": [],
        },
    ]
    by_id = {c["id"]: c for c in concepts}

    # ---- concept-a: emotional framing whose spine is a technology arc. The arc
    # is a factual claim, so it is included only when the ledger carries it and
    # is dropped (and disclosed as dropped) when it does not.
    a = by_id["concept-a"]
    a["creative_framing"] = [
        "Justice is delayed by distance and time — a framing choice, not a claim",
        "The firm is shown as the force closing that distance",
    ]
    if ai_claims:
        # A single-source account is not corroboration: it records what the firm
        # said, not that it is true. "Strong" is therefore reserved for an arc a
        # verified or corroborated claim states.
        corroborated = bool(tech_documented)
        a["central_idea"] = ("Justice is delayed by distance and time; the firm "
                             "closes that gap, and builds legal AI to close it "
                             "faster.")
        a["evidence_fit_level"] = FIT_STRONG if corroborated else FIT_MEDIUM
        a["evidence_fit"] = (
            ("%s — the technology arc is corroborated by a cited source"
             % FIT_STRONG) if corroborated else
            ("%s — the technology arc rests on a single-source account that no "
             "document yet corroborates" % FIT_MEDIUM))
        a["strengths"] = ["Emotionally legible in every language",
                          "Works without archive photos",
                          ("Ends on a technology arc the ledger corroborates"
                           if corroborated else
                           "Names a technology arc a cited source states")]
        a["weaknesses"] = ["Depends on one milestone being verifiable",
                           "Needs an evocative opening image"]
        if not corroborated:
            a["weaknesses"].append("Technology arc is single-source until a dated "
                                   "document corroborates it")
        a["asserted_claims"] = ["the firm builds legal AI"]
        a["evidence_sources"] = [c.split("[")[-1].rstrip("] ") for c in ai_claims]
    else:
        a["central_idea"] = ("Justice is delayed by distance and time; the firm "
                             "closes that gap, one answered question at a time.")
        a["evidence_fit_level"] = FIT_LIMITED
        a["evidence_fit"] = ("%s — the ledger holds no technology or innovation "
                             "claim, so the arc that makes this concept distinct "
                             "was removed rather than invented" % FIT_LIMITED)
        a["strengths"] = ["Emotionally legible in every language",
                          "Works without archive photos"]
        a["weaknesses"] = ["The distinctive technology arc is not evidenced and "
                           "was dropped",
                           "Depends on one milestone being verifiable",
                           "Needs an evocative opening image"]

    # ---- concept-b: human texture, which is only evidenced by interviews.
    b = by_id["concept-b"]
    b["central_idea"] = ("A firm built case by case — the story is people, habits "
                         "and standards, not slogans.")
    b["creative_framing"] = ["The story is people, habits and standards, not "
                             "slogans — a framing choice, not a claim"]
    n_interviews = len([c for c in interview_claims
                        if not getattr(c, "privacy_flags", None)])
    if n_interviews:
        b["evidence_fit_level"] = FIT_MEDIUM
        b["evidence_fit"] = ("%s — %d interview statement(s) give real voices; each "
                             "is a single-source recollection, not established fact"
                             % (FIT_MEDIUM, n_interviews))
        b["strengths"] = ["Human and warm",
                          "%d statement(s) already on record" % n_interviews]
        b["weaknesses"] = ["Recollections are single-source until corroborated",
                           "Risk of drifting into praise"]
    else:
        b["evidence_fit_level"] = FIT_LIMITED
        b["evidence_fit"] = ("%s — no interview material was supplied, so the human "
                             "texture would rest on staging rather than evidence"
                             % FIT_LIMITED)
        b["strengths"] = ["Human and warm", "Ideal if team clips exist"]
        b["weaknesses"] = ["Weak without interview audio",
                           "Risk of drifting into praise"]

    # ---- concept-c: evidence-led timeline, which needs dated facts to stand on.
    c = by_id["concept-c"]
    c["central_idea"] = ("An evidence-led film: dates, documents and milestones "
                         "shown as a timeline.")
    c["creative_framing"] = ["Dates and documents shown as a timeline — a "
                             "presentational choice, not a claim"]
    c["weaknesses"] = ["Coolest tone", "Fewer emotional peaks"]
    c["strengths"] = ["Verifiable on screen", "Credible for a legal audience"]
    if documented:
        c["evidence_fit_level"] = FIT_STRONG
        c["evidence_fit"] = ("%s — every dated line can cite the claim it stands "
                             "on (%d verified or corroborated)"
                             % (FIT_STRONG, len(documented)))
        c["evidence_sources"] = [d.split("[")[-1].rstrip("] ") for d in documented]
    else:
        c["evidence_fit_level"] = FIT_LIMITED
        c["evidence_fit"] = ("%s — the ledger holds no corroborated fact, so a "
                             "timeline would be built from single-source items and "
                             "named gaps" % FIT_LIMITED)

    # ---- exactly one recommendation: best fit wins, list order breaks ties.
    # The tie-break matters: with thin evidence every concept is "Limited", and
    # marking them all recommended would be no recommendation at all.
    best = max(_FIT_RANK.get(x["evidence_fit_level"], 1) for x in concepts)
    winner = next(x for x in concepts
                  if _FIT_RANK.get(x["evidence_fit_level"], 1) == best)
    for con in concepts:
        con["recommended"] = con is winner
        con["evidence_basis"] = {
            "documented_facts": list(basis["documented_facts"]),
            "attributed_statements": list(basis["attributed_statements"]),
            "creative_framing": list(con["creative_framing"]),
            "unresolved_claims": list(gaps),
        }
    return concepts


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


def drop_gap_scenes(scenes: List[Dict[str, Any]], total_sec: float
                    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Remove scenes that still lack their fact; re-time the rest to ``total_sec``.

    A final film must not show ``[placeholders]``. A scene whose evidence is
    missing is left out and reported (``omitted``) instead of being drawn as a
    gap banner, so the approved script is exactly what is rendered. The first
    and last scenes are structural and never dropped.
    """
    kept = [s for s in scenes if not s.get("needs")]
    omitted = [{"id": s["id"], "key": s["key"], "needs": list(s["needs"])}
               for s in scenes if s.get("needs")]
    if not omitted or not kept:
        return scenes, []
    scale = total_sec / max(0.001, sum(s["dur"] for s in kept))
    acc = 0.0
    for s in kept:
        s["dur"] = round(s["dur"] * scale, 2)
        s["start"] = round(acc, 2)
        acc += s["dur"]
    return kept, omitted


class ConceptSelectionError(ValueError):
    """An explicit concept approval was missing or invalid for this job.

    Raised instead of silently scripting a different concept: the operator
    approved a specific idea, and a script built on another one would misrepresent
    that decision.
    """


def concept_key(value: Any) -> str:
    """A comparable form of a concept id or the operator's shorthand.

    The CLI documents ``--concept`` as "by id (e.g. A, B, C)", and the bot and
    the tests use the same short form, so ``"A"``, ``"a"``, ``"concept a"`` and
    ``"concept-a"`` must all resolve to the same concept.
    """
    s = str(value or "").strip().lower().replace("_", "-")
    s = re.sub(r"\s+", "-", s)
    return re.sub(r"-+", "-", s)


def _resolve_concept(concepts: List[Dict[str, Any]], wanted: str) -> Optional[Dict[str, Any]]:
    key = concept_key(wanted)
    if not key:
        return None
    for c in concepts:
        if concept_key(c.get("id")) == key:
            return c
    # Documented shorthand: a bare letter stands for "concept-<letter>".
    if re.fullmatch(r"[a-z]", key):
        short = "concept-" + key
        for c in concepts:
            if concept_key(c.get("id")) == short:
                return c
    if not key.startswith("concept-") and re.fullmatch(r"[a-z0-9]+", key):
        short = "concept-" + key
        for c in concepts:
            if concept_key(c.get("id")) == short:
                return c
    return None


def concept_ids_match(left: Any, right: Any) -> bool:
    """True when two concept references mean the same concept.

    Needed because the operator-facing shorthand ("A") and the canonical id
    ("concept-a") are the same choice, and an agreement check that compared the
    raw strings would wrongly report a mismatch and block a valid job.
    """
    a, b = concept_key(left), concept_key(right)
    if not a or not b:
        return False
    if a == b:
        return True
    return a == "concept-" + b or b == "concept-" + a


def select_concept(concepts: List[Dict[str, Any]],
                   concept_id: str = "") -> Tuple[Dict[str, Any], str]:
    """Return ``(concept, origin)`` where origin is ``"approved"`` or ``"recommended"``.

    An explicit ``concept_id`` must resolve to a concept in ``concepts`` or this
    raises :class:`ConceptSelectionError` — a script is never built from an idea
    the operator did not approve. Only callers that pass no id at all (the
    legacy, non-gated path) fall back to the recommended concept.
    """
    if not concepts:
        raise ConceptSelectionError("no concepts were generated for this job")
    wanted = str(concept_id or "").strip()
    if wanted:
        found = _resolve_concept(concepts, wanted)
        if found is not None:
            return found, "approved"
        available = ", ".join("%s (%s)" % (c.get("id"), c.get("title"))
                              for c in concepts)
        raise ConceptSelectionError(
            "approved concept %r does not exist for this job — available: %s. "
            "Approve one of those ids (the short form A, B, C is accepted)."
            % (concept_id, available))
    fallback = next((c for c in concepts if c.get("recommended")), concepts[0])
    return fallback, "recommended"


def script_markdown(firm: str, concepts: List[Dict[str, Any]], scenes: List[Dict[str, Any]],
                    lang: str, style: str, total_sec: float,
                    concept_id: str = "",
                    omitted: Optional[List[Dict[str, Any]]] = None) -> str:
    chosen, origin = select_concept(concepts, concept_id)
    why = ("approved by the operator" if origin == "approved"
           else "auto-selected — no explicit concept approval was supplied")
    lines = [
        "# Script — %s" % firm,
        "",
        "**Style:** %s · **Language:** %s · **Target runtime:** %.0f s (%.1f min)"
        % (style, lang.upper(), total_sec, total_sec / 60.0),
        "",
        "**Concept:** %s — %s (%s)" % (chosen.get("id"), chosen.get("title"), why),
        "",
        "**Central idea:** %s" % chosen["central_idea"],
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
    if omitted:
        lines += ["", "## Scenes left out (no supporting evidence)", "",
                  "These scenes would need a fact that no source supplied. They are "
                  "omitted from the film rather than drawn as placeholders; supply the "
                  "fact (interview, archive or intake answer) and re-run to restore them.",
                  ""]
        for o in omitted:
            lines.append("- `%s` (%s) — needs: %s" % (o["id"], o["key"], ", ".join(o["needs"])))
    lines += ["", "## Concepts considered", ""]
    for c in concepts:
        marks = []
        if c.get("recommended"):
            marks.append("recommended")
        if str(c.get("id")) == str(chosen.get("id")):
            marks.append("selected for this script")
        mark = " **(%s)**" % ", ".join(marks) if marks else ""
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


def _srt_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    ms = int(round((seconds - int(seconds)) * 1000))
    if ms == 1000:
        ms = 0
        seconds += 1
    s = int(seconds)
    return "%02d:%02d:%02d,%03d" % (s // 3600, (s % 3600) // 60, s % 60, ms)


def _wrap_caption(text: str, width: int = 42) -> str:
    """Wrap narration into at most two short lines, subtitle-style."""
    words = " ".join((text or "").split()).split(" ")
    lines: List[str] = []
    cur = ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > 2:
        # Keep it to two lines: rejoin the tail and let it overflow the width
        # rather than dropping words — a subtitle must never lose narration.
        lines = [lines[0], " ".join(lines[1:])]
    return "\n".join(lines)


def srt_from_scenes(scenes: List[Dict[str, Any]]) -> str:
    """A synchronised SubRip file built from the scene timings.

    Each scene's narration becomes one or more cues spanning exactly that
    scene's on-screen time (``start`` .. ``start + dur``), so the captions stay
    aligned with the picture without any external timing data. Scenes with no
    narration (or only a placeholder marker) are skipped: a gap banner is not
    narration and must not be captioned as if it were spoken.
    """
    cues: List[str] = []
    idx = 0
    for s in scenes:
        narration = " ".join((s.get("narration") or "").split())
        if not narration:
            continue
        start = float(s.get("start") or 0.0)
        dur = float(s.get("dur") or 0.0)
        if dur <= 0:
            continue
        idx += 1
        cues.append("%d\n%s --> %s\n%s\n" % (
            idx, _srt_time(start), _srt_time(start + dur),
            _wrap_caption(narration)))
    return "\n".join(cues)


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
                       lang: str, style: str, total_sec: float,
                       concept_id: str = "", interview_claims: Sequence = (),
                       omit_gaps: Optional[bool] = None) -> Dict[str, Any]:
    """Write concepts.md, script.md, storyboard.md, scene_manifest.json. Returns paths.

    ``concept_id`` is the concept the operator approved. When it is supplied the
    script is built from exactly that concept; when the id is invalid this raises
    :class:`ConceptSelectionError` rather than quietly scripting another one.
    Callers that pass no id (the legacy, ungated path) keep the old behaviour and
    use the recommended concept.
    """
    os.makedirs(out_dir, exist_ok=True)
    concepts = build_concepts(firm, facts, result, interview_claims)
    scenes = build_scenes(firm, facts, lang, total_sec)
    source_assets: List[Dict[str, Any]] = []
    for sc in scenes:
        if sc["key"] == "people" and facts.get("team_photos"):
            from . import assets as _assets
            got = _assets.fetch_portraits(facts.get("team_photos"),
                                          os.path.join(out_dir, "assets"))
            if got:
                sc["portraits"] = [{"name": g["name"], "file": g["file"]} for g in got]
                source_assets += [{"kind": "portrait", "name": g["name"], "url": g["url"],
                                   "permission": "published on the firm's own website; "
                                                 "operator to confirm"} for g in got]
    omitted: List[Dict[str, Any]] = []
    if omit_gaps is None:
        # AGENT_KEEP_GAP_SCENES=1 keeps unsupported scenes as visible gap
        # banners, for drafts that show a human exactly what is missing.
        import os as _os
        omit_gaps = not _os.environ.get("AGENT_KEEP_GAP_SCENES")
    if omit_gaps:
        scenes, omitted = drop_gap_scenes(scenes, total_sec)
    chosen, origin = select_concept(concepts, concept_id)

    paths = {}
    p = os.path.join(out_dir, "concepts.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# Concepts — %s\n\n" % firm)
        for c in concepts:
            fh.write("## %s — %s%s\n\n_%s_\n\n- Evidence fit: %s\n- Strengths: %s\n- Weaknesses: %s\n\n" % (
                c["id"], c["title"], " (recommended)" if c.get("recommended") else "",
                c["central_idea"], c["evidence_fit"], "; ".join(c["strengths"]),
                "; ".join(c["weaknesses"])))
            basis = c.get("evidence_basis") or {}
            for label, key in (("Documented facts", "documented_facts"),
                               ("Attributed statements", "attributed_statements"),
                               ("Creative framing", "creative_framing"),
                               ("Unresolved claims", "unresolved_claims")):
                vals = basis.get(key) or []
                fh.write("- %s: %s\n" % (
                    label, "; ".join(str(v) for v in vals) if vals else "none recorded"))
            fh.write("\n")
    paths["concepts.md"] = p

    p = os.path.join(out_dir, "script.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(script_markdown(firm, concepts, scenes, lang, style, total_sec,
                                 concept_id, omitted))
    paths["script.md"] = p

    p = os.path.join(out_dir, "storyboard.md")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(storyboard_markdown(firm, scenes, style))
    paths["storyboard.md"] = p

    # A synchronised subtitle track in the film's own language. Written here so
    # the captions travel with the script/storyboard the operator approves.
    p = os.path.join(out_dir, "subtitles.srt")
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(srt_from_scenes(scenes))
    paths["subtitles.srt"] = p

    manifest = {
        "firm": firm,
        "language": normalize_lang(lang),
        "style": style,
        "total_duration_sec": total_sec,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        # The concept this script was actually built from, so the manifest, the
        # script header and chosen_concept.md all name the same decision.
        "concept": {"id": chosen.get("id"), "title": chosen.get("title"),
                    "origin": origin,
                    "central_idea": chosen.get("central_idea", "")},
        "facts": {k: {"value": v.value, "source": v.source_id,
                      "confidence": v.confidence} for k, v in facts.items.items()},
        "gaps": facts.missing(),
        "omitted_scenes": omitted,
        "source_assets": source_assets,
        "scenes": scenes,
    }
    p = os.path.join(out_dir, "scene_manifest.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    paths["scene_manifest.json"] = p
    return paths
