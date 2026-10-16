# -*- coding: utf-8 -*-
"""research.py — source discovery, extraction and the evidence ledger.

Guarantees
----------
* Nothing is invented. A source that cannot be read is recorded as
  ``INACCESSIBLE`` and produces **no** claims.
* A login wall (e.g. Facebook) is reported exactly as seen.
* Every claim carries a source id, a URL and an evidence class.
* Firm self-description is treated as a *claim*, never as fact.
"""
import csv
import io
import re
import time
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional, Tuple

# ----------------------------------------------------------------- evidence classes
VERIFIED = "VERIFIED"
CORROBORATED = "CORROBORATED"
SINGLE_SOURCE = "SINGLE-SOURCE"
UNVERIFIED = "UNVERIFIED"
CONFLICTING = "CONFLICTING"
UNAVAILABLE = "UNAVAILABLE"

EVIDENCE_CLASSES = (VERIFIED, CORROBORATED, SINGLE_SOURCE, UNVERIFIED,
                    CONFLICTING, UNAVAILABLE)

SOURCE_INSPECTED = "INSPECTED"
SOURCE_INACCESSIBLE = "INACCESSIBLE"
SOURCE_ERROR = "ERROR"
SOURCE_SKIPPED = "SKIPPED"

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36")

_NUMERIC = re.compile(r"(\d[\d\s.,]*\s*(?:\+|%|млн|million|млрд|billion|лет|yil|years|year|года|год)?)")
_SUPERLATIVE = re.compile(
    r"(?i)\b(leading|best|top|№\s*1|no\.?\s*1|first|№1|лучш|ведущ|перв|eng\s+zo['’]?r|"
    r"birinchi|yagona|largest|biggest|premier|award[- ]winning|награжд|лауреат)\b")
_MONEY = re.compile(r"[$€£]\s?\d|(\d[\d\s.,]*)\s*(?:млн|million|млрд|billion)", re.I)

# Page furniture that is never evidence about the firm's history.
_BOILERPLATE = re.compile(
    r"(?i)^(?:©|\(c\)|copyright|all rights reserved|все права защищены|"
    r"мы используем cookie|this site uses cookies|"
    r"privacy policy|политика конфиденциальности|пользовательское соглашение|"
    r"загрузка|loading|меню|menu|главная|home|следующая|предыдущая|previous|next|"
    r"назад|подробнее|read more|поделиться|share|контакты|contacts|о нас|about us)"
    r"(?![A-Za-zА-Яа-я])")
_SYMBOL_BULLET = re.compile(r"^[\u2713\u2714\u2022\u25cf\u25aa\u2192\u00bb✓✔•●▪→»\-–—]\s*")


# ----------------------------------------------------------------- dataclasses
@dataclass
class Source:
    id: str
    kind: str                 # website | facebook | linkedin | instagram | other | supplied
    url: str
    title: str = ""
    state: str = SOURCE_SKIPPED
    http_status: Optional[int] = None
    note: str = ""
    fetched_at: float = 0.0
    bytes_read: int = 0


@dataclass
class Claim:
    id: str
    text: str
    source_id: str
    source_url: str
    page_title: str = ""
    evidence_class: str = UNVERIFIED
    safe_for_public: bool = False
    relevance: str = ""
    needs: str = ""


@dataclass
class ResearchResult:
    firm_name: str
    sources: List[Source] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def inaccessible(self) -> List[Source]:
        return [s for s in self.sources if s.state in (SOURCE_INACCESSIBLE, SOURCE_ERROR)]

    def public_claims(self) -> List[Claim]:
        return [c for c in self.claims if c.safe_for_public]


# ----------------------------------------------------------------- html extraction
class _Extractor(HTMLParser):
    """Collect title, meta description, headings and visible paragraph text."""

    SKIP = {"script", "style", "noscript", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.description = ""
        self.headings: List[str] = []
        self.paragraphs: List[str] = []
        self._skip_depth = 0
        self._in_title = False
        self._buf: List[str] = []
        self._capture: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.SKIP:
            self._skip_depth += 1
            return
        if tag == "title":
            self._in_title = True
            self._buf = []
        elif tag == "meta":
            name = (a.get("name") or a.get("property") or "").lower()
            if name in ("description", "og:description") and a.get("content"):
                if not self.description:
                    self.description = a["content"].strip()
        elif tag in ("h1", "h2", "h3"):
            self._capture = "h"
            self._buf = []
        elif tag in ("p", "li"):
            self._capture = "p"
            self._buf = []

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if tag == "title":
            self._in_title = False
            self.title = " ".join("".join(self._buf).split())
            self._buf = []
        elif tag in ("h1", "h2", "h3") and self._capture == "h":
            txt = " ".join("".join(self._buf).split())
            if txt:
                self.headings.append(txt)
            self._capture, self._buf = None, []
        elif tag in ("p", "li") and self._capture == "p":
            txt = " ".join("".join(self._buf).split())
            if txt:
                self.paragraphs.append(txt)
            self._capture, self._buf = None, []

    def handle_data(self, data):
        if self._skip_depth:
            return
        if self._in_title or self._capture:
            self._buf.append(data)


def parse_html(html: str) -> _Extractor:
    ex = _Extractor()
    try:
        ex.feed(html or "")
    except Exception:
        pass
    return ex


# ----------------------------------------------------------------- fetching
class FetchResult(object):
    def __init__(self, ok: bool, status: Optional[int], text: str = "",
                 state: str = SOURCE_INSPECTED, note: str = "", final_url: str = ""):
        self.ok = ok
        self.status = status
        self.text = text or ""
        self.state = state
        self.note = note
        self.final_url = final_url


def default_fetcher(url: str, timeout: int = 25, max_bytes: int = 3_000_000) -> FetchResult:
    """Fetch a URL. Never raises; returns a classified FetchResult."""
    try:
        import requests  # local import keeps tests importable without the network
    except Exception as exc:  # pragma: no cover
        return FetchResult(False, None, state=SOURCE_ERROR, note="requests unavailable: %s" % exc)

    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "en,ru,uz"},
                         timeout=timeout, allow_redirects=True)
    except Exception as exc:
        return FetchResult(False, None, state=SOURCE_ERROR, note="request failed: %s" % exc)

    body = r.text or ""
    if len(body) > max_bytes:
        body = body[:max_bytes]

    if r.status_code in (401, 403):
        return FetchResult(False, r.status_code, body, SOURCE_INACCESSIBLE,
                           "blocked (HTTP %d)" % r.status_code, r.url)
    if r.status_code >= 400:
        return FetchResult(False, r.status_code, body, SOURCE_ERROR,
                           "HTTP %d" % r.status_code, r.url)

    # Login-wall heuristics for social platforms
    low = body.lower()
    if "facebook.com" in host:
        wall = ("log in" in low or "login" in low or "you must log in" in low
                or "not available on this browser" in low or len(body) < 4000)
        if wall:
            return FetchResult(False, r.status_code, body, SOURCE_INACCESSIBLE,
                               "login wall — public post feed not readable", r.url)
    if r.status_code == 200 and len(body.strip()) < 200 and "facebook" in host:
        return FetchResult(False, r.status_code, body, SOURCE_INACCESSIBLE,
                           "login wall — empty public body", r.url)

    return FetchResult(True, r.status_code, body, SOURCE_INSPECTED,
                       "fetched %d bytes" % len(body), r.url)


# ----------------------------------------------------------------- claim extraction
def _clean(s: str) -> str:
    return " ".join((s or "").split())


def is_boilerplate(text: str) -> bool:
    """Page furniture (copyright, nav, cookie notices) — not evidence."""
    t = (text or "").strip()
    if not t:
        return True
    if len(t) < 3:
        return True
    if _BOILERPLATE.match(t):
        return True
    if _SYMBOL_BULLET.match(t) and len(t) < 60:
        return True
    stripped = _SYMBOL_BULLET.sub("", t)
    if _BOILERPLATE.match(stripped):
        return True
    # A lone year or a bare number is not a historical statement.
    if len(t) <= 4 and re.fullmatch(r"[\d\s.,%+-]+", t):
        return True
    return False


def candidate_statements(ex: _Extractor, limit: int = 25) -> List[Tuple[str, str]]:
    """Return (text, kind) candidates worth putting in the ledger."""
    out: List[Tuple[str, str]] = []
    if ex.title and not is_boilerplate(ex.title):
        out.append((_clean(ex.title), "title"))
    if ex.description and not is_boilerplate(ex.description):
        out.append((_clean(ex.description), "description"))
    for h in ex.headings[:12]:
        h = _clean(h)
        if h and not is_boilerplate(h):
            out.append((h, "heading"))
    seen = set()
    for p in ex.paragraphs:
        p = _clean(p)
        if len(p) < 30 or len(p) > 400:
            continue
        if is_boilerplate(p):
            continue
        if p.lower() in seen:
            continue
        seen.add(p.lower())
        kind = "statement"
        if _MONEY.search(p):
            kind = "case_figure"
        elif _NUMERIC.search(p) or _SUPERLATIVE.search(p):
            kind = "statistic_or_superlative"
        out.append((p, kind))
    # keep informative kinds first, cap the list
    out.sort(key=lambda t: {"case_figure": 0, "statistic_or_superlative": 1,
                            "description": 2, "statement": 3, "heading": 4,
                            "title": 5}.get(t[1], 9))
    return out[:limit]


def classify_source_kind(url: str) -> str:
    u = (url or "").lower()
    if "facebook.com" in u:
        return "facebook"
    if "linkedin.com" in u:
        return "linkedin"
    if "instagram.com" in u:
        return "instagram"
    if "t.me" in u or "telegram" in u:
        return "telegram"
    return "website"


def same_registrable_domain(a: str, b: str) -> bool:
    def norm(u):
        u = re.sub(r"^https?://", "", (u or "").lower()).split("/")[0]
        parts = [p for p in u.split(".") if p]
        return ".".join(parts[-2:]) if len(parts) >= 2 else u
    return bool(norm(a)) and norm(a) == norm(b)


def classify_claim(text: str, kind: str, source_url: str,
                   official_domains: List[str]) -> Tuple[str, bool, str]:
    """Return (evidence_class, safe_for_public, needs)."""
    self_published = any(same_registrable_domain(source_url, d) for d in official_domains)
    if kind == "case_figure":
        return (UNVERIFIED, False,
                "Case results are client matter: verify and get client clearance before any public use.")
    if kind == "statistic_or_superlative":
        if self_published:
            return (SINGLE_SOURCE, False,
                    "Firm's own figure/superlative — needs independent corroboration before public use.")
        return (UNVERIFIED, False, "Unattributed figure/superlative — corroborate before use.")
    if kind in ("title", "description", "heading", "statement"):
        if self_published:
            return (SINGLE_SOURCE, False,
                    "Firm self-description — safe only as the firm's own account, not as fact.")
        return (SINGLE_SOURCE, False, "Single external mention — corroborate before public use.")
    return (UNVERIFIED, False, "Unclassified — review manually.")


# ----------------------------------------------------------------- orchestration
def research_firm(firm_name: str, website: str = "", facebook: str = "",
                  extra_urls: Optional[List[str]] = None,
                  fetcher: Optional[Callable[[str], FetchResult]] = None,
                  progress: Optional[Callable[[str], None]] = None) -> ResearchResult:
    """Discover and read accessible sources; build the evidence ledger."""
    fetch = fetcher or default_fetcher
    result = ResearchResult(firm_name=firm_name)
    official = [website] if website else []

    def report(msg: str) -> None:
        if progress:
            try:
                progress(msg)
            except Exception:
                pass

    targets: List[Tuple[str, str]] = []
    if website:
        targets.append(("site-home", website))
        for guess in ("about", "history", "team", "news", "awards", "contacts"):
            targets.append(("site-" + guess, website.rstrip("/") + "/" + guess))
    if facebook:
        targets.append(("facebook", facebook))
    for i, u in enumerate(extra_urls or []):
        targets.append(("extra-%d" % (i + 1), u))

    sid = 0
    cid = 0
    for label, url in targets:
        sid += 1
        source = Source(id="S%02d" % sid, kind=classify_source_kind(url), url=url)
        report("fetching %s" % label)
        try:
            fr = fetch(url)
        except Exception as exc:
            fr = FetchResult(False, None, state=SOURCE_ERROR, note="fetcher error: %s" % exc)

        source.state = fr.state
        source.http_status = fr.status
        source.note = fr.note
        source.fetched_at = time.time()
        source.bytes_read = len(fr.text)

        if not fr.ok:
            source.note = _clean(source.note) or "unavailable"
            result.sources.append(source)
            result.gaps.append("Could not read %s (%s): %s" % (label, url, source.note))
            continue

        ex = parse_html(fr.text)
        source.title = _clean(ex.title)[:200]
        result.sources.append(source)

        for text, kind in candidate_statements(ex):
            if not text:
                continue
            cid += 1
            evc, safe, needs = classify_claim(text, kind, url, official)
            result.claims.append(Claim(
                id="C%03d" % cid, text=text[:500], source_id=source.id,
                source_url=url, page_title=source.title, evidence_class=evc,
                safe_for_public=safe, relevance=kind, needs=needs))

    if not website:
        result.gaps.append("No official website supplied — research limited to supplied links.")
    if facebook and any(s.kind == "facebook" and s.state != SOURCE_INSPECTED
                        for s in result.sources):
        result.notes.append(
            "Facebook is behind a login wall. Post-level history was NOT reviewed. "
            "Supply exported posts, screenshots or files to include that content.")
    result.notes.append(
        "Only accessible public pages were read. Unreadable sources are listed as gaps; "
        "no content was inferred for them.")
    return result


# ----------------------------------------------------------------- serialisation
def ledger_csv(result: ResearchResult) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["claim_id", "claim", "evidence_class", "safe_for_public",
                "source_id", "source_url", "page_title", "relevance", "needs"])
    for c in result.claims:
        w.writerow([c.id, c.text, c.evidence_class, "yes" if c.safe_for_public else "no",
                    c.source_id, c.source_url, c.page_title, c.relevance, c.needs])
    return buf.getvalue()


def report_markdown(result: ResearchResult, generated_at: Optional[str] = None) -> str:
    lines: List[str] = []
    lines.append("# Research report — %s" % result.firm_name)
    lines.append("")
    lines.append("_Generated: %s_" % (generated_at or time.strftime("%Y-%m-%d %H:%M")))
    lines.append("")
    lines.append("Evidence classes: " + " · ".join(EVIDENCE_CLASSES))
    lines.append("")
    lines.append("## 1. Sources")
    lines.append("")
    lines.append("| ID | Kind | URL | State | HTTP | Title | Note |")
    lines.append("|----|------|-----|-------|------|-------|------|")
    for s in result.sources:
        lines.append("| %s | %s | %s | **%s** | %s | %s | %s |" % (
            s.id, s.kind, s.url, s.state, s.http_status or "-",
            (s.title or "-")[:60].replace("|", "/"), (s.note or "-")[:70].replace("|", "/")))
    lines.append("")
    lines.append("## 2. Evidence ledger")
    lines.append("")
    if not result.claims:
        lines.append("_No claims extracted._")
    else:
        lines.append("| ID | Claim | Class | Public? | Source |")
        lines.append("|----|-------|-------|---------|--------|")
        for c in result.claims:
            lines.append("| %s | %s | %s | %s | [%s](%s) |" % (
                c.id, c.text[:160].replace("|", "/"), c.evidence_class,
                "yes" if c.safe_for_public else "no", c.source_id, c.source_url))
    lines.append("")
    lines.append("## 3. Gaps and blocked sources")
    lines.append("")
    if result.gaps:
        for g in result.gaps:
            lines.append("- %s" % g)
    else:
        lines.append("- None recorded.")
    lines.append("")
    lines.append("## 4. Notes")
    lines.append("")
    for n in result.notes:
        lines.append("- %s" % n)
    lines.append("")
    lines.append("> **Anti-fabrication:** every line above traces to a source row. "
                 "Where a source could not be read, the gap is stated and nothing was invented.")
    return "\n".join(lines) + "\n"


def result_to_dict(result: ResearchResult) -> Dict[str, Any]:
    return {
        "firm_name": result.firm_name,
        "sources": [asdict(s) for s in result.sources],
        "claims": [asdict(c) for c in result.claims],
        "gaps": list(result.gaps),
        "notes": list(result.notes),
    }
