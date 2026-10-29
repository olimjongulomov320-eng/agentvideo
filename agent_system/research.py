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
import codecs
import csv
import hashlib
import html as html_lib
import io
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlsplit

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
    # ---- extended evidence-ledger fields (workflow stage B) ----
    # Every one of these is derived from the source itself. None is inferred,
    # and an empty value means "not established", never "assumed".
    excerpt: str = ""          # verbatim passage the claim was taken from
    source_date: str = ""      # when the source was published, if it says so
    event_date: str = ""       # year the SOURCE states for the event (not inferred)
    confidence: str = ""       # confidence level and its limitation
    contradiction: str = ""    # conflicting evidence, if any was found
    privacy_review: str = ""   # permission / publication requirement


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



# ----------------------------------------------------------------- telegram
# A public Telegram channel is readable without a login at t.me/s/<name>. It is
# often the only place a firm publishes its recent events (an office opening,
# a conference), so it is read as a dated source rather than skipped.
_TG_LINK_RE = re.compile(r"(?i)^https?://(?:www\.)?t\.me/(?:s/)?([A-Za-z][A-Za-z0-9_]{3,})/?$")
_TG_MSG_RE = re.compile(
    r'(?s)tgme_widget_message_text[^>]*>(.*?)</div>.*?'
    r'tgme_widget_message_date.*?datetime="([^"]+)"')
MAX_TELEGRAM_POSTS = 12


def telegram_channel_url(url: str) -> str:
    """The public-preview URL for a t.me channel link, or ''."""
    m = _TG_LINK_RE.match((url or "").strip())
    return "https://t.me/s/%s" % m.group(1) if m else ""


def telegram_posts(page_html: str, limit: int = MAX_TELEGRAM_POSTS) -> List[Tuple[str, str]]:
    """Return ``(text, iso_date)`` for the newest posts of a channel preview."""
    posts: List[Tuple[str, str]] = []
    for block in (page_html or "").split("tgme_widget_message_wrap")[1:]:
        m = _TG_MSG_RE.search(block)
        if not m:
            continue
        text = html_lib.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))
        text = _clean(text)
        if len(text) >= 30:
            posts.append((text[:400], m.group(2)[:10]))
    return posts[-limit:]


# Section labels and calls to action are navigation, not evidence.
_NAV_HEADING = re.compile(
    r"(?i)^(?:свяжитесь с нами|задать вопрос|наша миссия|области права|"
    r"наши адвокаты(?: и юристы)?|основатели и партн\w+|выигранные дела|"
    r"эффективность в цифрах|право и технологии|контакты|услуги|команда|"
    r"contact us|our (?:team|services|mission)|practice areas|"
    r"biz bilan bog['’]?lan\w*|jamoamiz|xizmatlar)\W*$")


def _is_nav_heading(text: str) -> bool:
    return bool(_NAV_HEADING.match((text or "").strip()))


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


# ---------------------------------------------------------------- decoding
# When a ``text/*`` response omits the charset, ``requests`` assumes ISO-8859-1
# (RFC 2616). A UTF-8 page served without one is then decoded one byte per
# character, turning every em dash, Cyrillic letter and Uzbek diacritic into
# mojibake long before the evidence ledger ever sees the text.
_CHARSET_RE = re.compile(r"(?i)charset\s*=\s*[\"']?([a-z0-9_:.\-]+)")
_DECODE_FALLBACK = "ISO-8859-1"      # maps every byte to a code point; never fails


def charset_from_header(value: str) -> str:
    """The charset a server declared, but only if it is a codec we really have.

    A malformed header (``charse=utf8``) or a codec this build lacks must never
    break a fetch, so an unusable declaration is reported as "not declared".
    """
    m = _CHARSET_RE.search(value or "")
    if not m:
        return ""
    name = m.group(1).strip()
    try:
        codecs.lookup(name)
    except LookupError:
        return ""
    return name


def decode_bytes(raw: Any, declared_charset: str = "") -> str:
    """Decode a fetched body without corrupting its Unicode.

    Preference order:

    1. a byte-order mark — unambiguous, so it wins;
    2. the charset the server declared, when that codec is usable;
    3. strict UTF-8, which is what modern sites actually serve;
    4. ISO-8859-1, which cannot raise, so a legacy page that was never
       converted still decodes exactly as it did before this fix.

    Step 4 is why this does not corrupt correctly decoded legacy pages: a
    genuine Latin-1 page fails step 3 and lands on the same codec ``requests``
    would have chosen for it.
    """
    if raw is None:
        return ""
    if isinstance(raw, str):
        return raw
    raw = bytes(raw)
    if not raw:
        return ""

    candidates: List[str] = []
    for magic, enc in ((codecs.BOM_UTF8, "utf-8-sig"),
                       (codecs.BOM_UTF32_LE, "utf-32-le"),
                       (codecs.BOM_UTF32_BE, "utf-32-be"),
                       (codecs.BOM_UTF16_LE, "utf-16-le"),
                       (codecs.BOM_UTF16_BE, "utf-16-be")):
        if raw.startswith(magic):
            candidates.append(enc)
            break
    declared = charset_from_header(declared_charset)
    if declared:
        candidates.append(declared)
    candidates.append("utf-8")
    candidates.append(_DECODE_FALLBACK)

    for enc in candidates:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("latin-1", "replace")


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

    # Decoded from the raw bytes rather than from r.text: for a text/* response
    # that declares no charset, requests assumes ISO-8859-1 and corrupts UTF-8.
    body = decode_bytes(r.content, r.headers.get("Content-Type", ""))
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
        if h and not is_boilerplate(h) and not _is_nav_heading(h):
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


# ----------------------------------------------------------------- discovery
# How many pages to read per site, and how deep to follow a sitemap index.
MAX_PAGES = 12
MAX_NESTED_SITEMAPS = 3

# Link targets that are never readable evidence about the firm's history.
_LINK_SKIP_EXT = (
    ".pdf", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico", ".bmp",
    ".mp4", ".mp3", ".webm", ".mov", ".avi", ".zip", ".rar", ".gz", ".tar",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".css", ".js",
)
_LINK_SKIP_SCHEME = ("mailto:", "tel:", "javascript:", "data:", "#", "sms:")

# Path fragments that usually carry firm history, best first. These only ORDER
# links the site actually published: they never invent one. Matched case-
# insensitively against the URL, so both English and Russian paths are covered.
_URL_HINTS = (
    (0, ("about", "history", "istoriya", "истори", "о-нас", "о-компан", "o-nas",
         "kompaniya", "company", "firm", "firma")),
    (1, ("team", "people", "lawyer", "partner", "attorney", "komanda", "команд",
         "сотрудник", "founder", "bio", "sotrudnik")),
    (2, ("news", "press", "novosti", "новост", "publication", "publikacii",
         "blog", "insight", "media", "event", "sobitiya")),
    (3, ("award", "recognition", "ranking", "achievement", "nagrad", "награжд",
         "laureat", "rating")),
    (4, ("practice", "service", "expertise", "uslugi", "услуг", "deyatelnost")),
    (5, ("contact", "kontakt", "контакт", "address")),
)
_GUESSED_PATHS = ("about", "history", "team", "news", "awards", "contacts")

_LOC_RE = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_SITEMAP_RE = re.compile(r"(?im)^\s*sitemap\s*:\s*(\S+)\s*$")


class _LinkExtractor(HTMLParser):
    """Collect ``<a href>`` values.

    Kept separate from :class:`_Extractor` so that claim extraction is not
    affected by link markup (anchors are navigation, not statements).
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: List[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip += 1
            return
        if tag == "a" and not self._skip:
            href = (dict(attrs).get("href") or "").strip()
            if href:
                self.hrefs.append(href)

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = max(0, self._skip - 1)


def _host_key(url: str) -> str:
    """Host without a leading ``www.``, for same-site comparison."""
    netloc = urlsplit(url or "").netloc.lower()
    if "@" in netloc:                      # strip any userinfo
        netloc = netloc.rsplit("@", 1)[1]
    if ":" in netloc:
        netloc = netloc.split(":", 1)[0]
    return netloc[4:] if netloc.startswith("www.") else netloc


def _canonical(url: str) -> str:
    """Absolute, fragment-free, query-free page URL; '' when not fetchable.

    Dropping the query and fragment is deliberate: ``?utm_source=...`` and
    ``#team`` are the same page, and fetching them repeatedly would waste the
    page budget and look like load to the server.
    """
    raw = (url or "").strip()
    if not raw or raw.startswith(_LINK_SKIP_SCHEME):
        return ""
    parts = urlsplit(raw)
    if parts.scheme not in ("http", "https"):
        return ""
    path = parts.path or "/"
    if path.lower().endswith(_LINK_SKIP_EXT):
        return ""
    return "%s://%s%s" % (parts.scheme.lower(), parts.netloc.lower(), path)


def _LinkExtractor_hrefs(html: str) -> List[str]:
    ex = _LinkExtractor()
    try:
        ex.feed(html or "")
    except Exception:
        return []
    return ex.hrefs


def extract_links(html: str, base_url: str) -> List[str]:
    """Same-site page links from one page, de-duplicated, in document order."""
    ex = _LinkExtractor()
    try:
        ex.feed(html or "")
    except Exception:
        return []
    base_host = _host_key(base_url)
    base_key = _canonical(base_url)
    out: List[str] = []
    seen = set()
    for href in ex.hrefs:
        absolute = urljoin(base_url, href)
        u = _canonical(absolute)
        if not u or _host_key(u) != base_host:
            continue
        if u == base_key or u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def parse_sitemap(xml: str, base_url: str) -> Tuple[List[str], List[str]]:
    """Return ``(page_urls, nested_sitemap_urls)`` from a sitemap or index."""
    pages: List[str] = []
    nested: List[str] = []
    for raw in _LOC_RE.findall(xml or ""):
        u = _canonical(urljoin(base_url, raw.strip()))
        if not u:
            continue
        if u.lower().endswith((".xml", ".xml.gz")):
            nested.append(u)
        elif u not in pages:
            pages.append(u)
    return pages, nested


def rank_url(url: str) -> Tuple[int, int, str]:
    """Sort key for a discovered URL: history-relevant first, then shallow."""
    low = url.lower()
    for rank, hints in _URL_HINTS:
        if any(h in low for h in hints):
            depth = low.rstrip("/").count("/") - 2
            return (rank, max(0, depth), low)
    depth = low.rstrip("/").count("/") - 2
    return (len(_URL_HINTS), max(0, depth), low)


def discover_targets(website: str, fetch: Callable[[str], FetchResult],
                     report: Callable[[str], None],
                     max_pages: int = MAX_PAGES
                     ) -> Tuple[List[Tuple[str, str]], List[str], Dict[str, FetchResult]]:
    """Build the fetch plan from the site's own published structure.

    Order of preference:

    1. the homepage;
    2. pages the homepage actually links to (same site);
    3. pages listed in ``sitemap.xml`` (following a sitemap index) and any
       ``Sitemap:`` line in ``robots.txt``;
    4. **only if all of that yields nothing**, the conventional paths
       (``/about``, ``/history``, …), which are recorded as *guesses* so the
       report can say so instead of implying the pages were known to exist.

    Returns ``(targets, notes, prefetched)``. ``prefetched`` reuses the homepage
    response in the main read loop, so no page is fetched twice.
    """
    targets: List[Tuple[str, str]] = []
    notes: List[str] = []
    prefetched: Dict[str, FetchResult] = {}
    if not website:
        return targets, notes, prefetched

    base = website.rstrip("/")
    targets.append(("site-home", website))

    discovered: List[str] = []

    # 1) homepage links
    home = None
    try:
        home = fetch(website)
    except Exception as exc:
        notes.append("Discovery: homepage could not be fetched (%s); falling "
                     "back to conventional paths." % exc)
    if home is not None:
        prefetched[website] = home
        if home.ok and home.text:
            links = extract_links(home.text, home.final_url or website)
            discovered.extend(links)
            notes.append("Discovery: %d same-site link(s) on the homepage."
                         % len(links))
        else:
            notes.append("Discovery: homepage not readable (%s), so its links "
                         "could not be discovered." % (home.note or home.state))

    # 2) sitemap.xml, plus any sitemap declared in robots.txt
    sitemap_urls = [base + "/sitemap.xml"]
    try:
        robots = fetch(base + "/robots.txt")
    except Exception:
        robots = None
    if robots is not None and robots.ok and robots.text:
        declared = [m.strip() for m in _SITEMAP_RE.findall(robots.text)]
        for d in declared:
            u = _canonical(urljoin(base + "/", d))
            if u and u not in sitemap_urls:
                sitemap_urls.append(u)
        if declared:
            notes.append("Discovery: robots.txt declares %d sitemap(s)."
                         % len(declared))

    seen_sitemaps = set()
    queue = list(sitemap_urls)[:1 + MAX_NESTED_SITEMAPS]
    sitemap_pages = 0
    while queue:
        sm = queue.pop(0)
        if sm in seen_sitemaps:
            continue
        seen_sitemaps.add(sm)
        try:
            got = prefetched.get(sm) or fetch(sm)
        except Exception:
            got = None
        if got is None or not got.ok or not got.text:
            continue
        pages, nested = parse_sitemap(got.text, got.final_url or sm)
        if pages:
            sitemap_pages += len(pages)
            discovered.extend(pages)
        for n in nested:
            if n not in seen_sitemaps and len(seen_sitemaps) < 1 + MAX_NESTED_SITEMAPS:
                queue.append(n)
    if sitemap_pages:
        notes.append("Discovery: sitemap.xml listed %d page(s)." % sitemap_pages)
    else:
        notes.append("Discovery: no readable sitemap.xml (a site without one is "
                     "normal).")

    # 3) rank and cap
    unique: List[str] = []
    seen = set()
    for u in discovered:
        if u == _canonical(website) or u in seen:
            continue
        seen.add(u)
        unique.append(u)
    unique.sort(key=rank_url)

    guessed = False
    if not unique:
        guessed = True
        for guess in _GUESSED_PATHS:
            unique.append(base + "/" + guess)
        notes.append("Discovery: no links or sitemap entries were found, so the "
                     "conventional paths %s were tried as GUESSES. They may not "
                     "exist; any that fail are recorded as gaps, not as content."
                     % ", ".join("/" + g for g in _GUESSED_PATHS))

    for u in unique[:max(0, max_pages - 1)]:
        if guessed:
            label = "site-guess-" + u.rstrip("/").rsplit("/", 1)[-1]
        else:
            tail = u.rstrip("/").rsplit("/", 1)[-1] or "home"
            label = "site-" + re.sub(r"[^a-z0-9]+", "-", tail.lower())[:30]
        targets.append((label, u))
    notes.append("Discovery: reading %d page(s) for this site."
                 % (len(targets) - 1))
    report("discovered %d page(s) to read" % (len(targets) - 1))
    return targets, notes, prefetched


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


def source_key(source: str) -> str:
    """A key identifying the *publisher* of a source, for independence checks.

    Two URLs on the same website are one publisher, so they cannot corroborate
    each other. Non-URL sources (for example an interviewee's name) are used
    as-is.
    """
    raw = (source or "").strip()
    if not raw:
        return ""
    if re.match(r"^https?://", raw, re.I):
        host = re.sub(r"^https?://", "", raw.lower()).split("/")[0]
        host = host.split(":")[0]
        parts = [p for p in host.split(".") if p]
        return ".".join(parts[-2:]) if len(parts) >= 2 else host
    return raw.lower()


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


# --------------------------------------------------- extended ledger helpers
CONFIDENCE_NOTE: Dict[str, str] = {
    VERIFIED: "Confirmed by two or more independent sources.",
    CORROBORATED: "Supported by more than one source.",
    SINGLE_SOURCE: "Single source only — not independently confirmed.",
    UNVERIFIED: "No supporting evidence located.",
    CONFLICTING: "Sources disagree; unresolved.",
    UNAVAILABLE: "Source could not be read; nothing verified.",
}


def confidence_note(evidence_class: str) -> str:
    """The limitation attached to an evidence class, in one line."""
    return CONFIDENCE_NOTE.get(evidence_class, "Unclassified — review manually.")


def stated_year(text: str) -> str:
    """The earliest 4-digit year the *source itself states*, or ''.

    This is a year the text mentions, not a confirmed event date, and the
    chronology labels it exactly that way. Nothing is inferred from context.
    """
    years = [int(y) for y in re.findall(r"\b(1[89]\d{2}|20\d{2})\b", text or "")]
    return str(min(years)) if years else ""


def privacy_requirement(kind: str, safe_for_public: bool) -> str:
    """What must happen before this claim may be published."""
    if kind == "case_figure":
        return "Client matter — client clearance required before any public use."
    if safe_for_public:
        return "Cleared for public use by classification."
    return "Not cleared for public use — human review required before publication."


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
        discovered, discovery_notes, prefetched = discover_targets(
            website, fetch, report)
        targets.extend(discovered)
        # Discovery notes belong with the research notes: they state exactly how
        # the pages were found, which a reader needs in order to judge coverage.
        result.notes.extend(discovery_notes)
    else:
        prefetched = {}
    if facebook:
        targets.append(("facebook", facebook))
    for i, u in enumerate(extra_urls or []):
        targets.append(("extra-%d" % (i + 1), u))

    # Social channels the homepage links to (public Telegram previews only).
    home_resp = prefetched.get(website) if website else None
    if home_resp is not None and home_resp.ok and home_resp.text:
        have = {u for _l, u in targets}
        for href in _LinkExtractor_hrefs(home_resp.text):
            tg = telegram_channel_url(urljoin(website, href))
            if tg and tg not in have:
                have.add(tg)
                targets.append(("telegram-" + tg.rsplit("/", 1)[-1], tg))
                result.notes.append("Discovery: the homepage links to the public "
                                    "Telegram channel %s; its recent posts were read." % tg)

    sid = 0
    cid = 0
    seen_pages: Dict[str, str] = {}
    seen_claims = set()
    for label, url in targets:
        sid += 1
        source = Source(id="S%02d" % sid, kind=classify_source_kind(url), url=url)
        report("fetching %s" % label)
        try:
            # Reuse the homepage response found during discovery instead of
            # requesting the same page a second time.
            fr = prefetched.get(url)
            if fr is None:
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

        if telegram_channel_url(url) and "t.me/s/" in url:
            # Only posts that are about the firm are statements about it; the
            # rest of a legal-news channel is general news, never a firm fact.
            tokens = [w for w in re.findall(r"[^\W\d_]{4,}", firm_name.lower())
                      if w not in ("firm", "law", "legal", "partners", "group")]
            tokens += ["firmamiz", "gulyamov", "gsp"]
            statements = [(t, "statement" if any(k in t.lower() for k in tokens)
                           else "news", d) for t, d in telegram_posts(fr.text)]
            source.title = "Telegram channel " + url.rsplit("/", 1)[-1]
            if not statements:
                source.note = "channel preview had no readable posts"
        else:
            ex = parse_html(fr.text)
            source.title = _clean(ex.title)[:200]
            # A second URL that serves the same page (/ and /index.html) adds
            # no evidence and would double every claim.
            digest = hashlib.sha1(" ".join(
                [ex.title, ex.description] + ex.headings + ex.paragraphs
            ).encode("utf-8")).hexdigest()
            if digest in seen_pages:
                source.note = "duplicate of %s — same content, not counted again" % seen_pages[digest]
                result.sources.append(source)
                continue
            seen_pages[digest] = source.id
            statements = [(t, k, "") for t, k in candidate_statements(ex)]
        result.sources.append(source)

        for text, kind, posted in statements:
            if not text:
                continue
            norm = " ".join(text.lower().split())
            if norm in seen_claims:
                continue
            seen_claims.add(norm)
            cid += 1
            evc, safe, needs = classify_claim(text, kind, url, official)
            result.claims.append(Claim(
                id="C%03d" % cid, text=text[:500], source_id=source.id,
                source_url=url, page_title=source.title, evidence_class=evc,
                safe_for_public=safe, relevance=kind, needs=needs,
                excerpt=text[:2000],
                confidence=confidence_note(evc),
                source_date=posted,
                event_date=stated_year(text),
                privacy_review=privacy_requirement(kind, safe)))

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
                "source_id", "source_url", "page_title", "relevance", "needs",
                "excerpt", "source_date", "event_date", "confidence",
                "contradiction", "privacy_review"])
    for c in result.claims:
        w.writerow([c.id, c.text, c.evidence_class, "yes" if c.safe_for_public else "no",
                    c.source_id, c.source_url, c.page_title, c.relevance, c.needs,
                    c.excerpt, c.source_date, c.event_date, c.confidence,
                    c.contradiction, c.privacy_review])
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
    lines.append("## 3. Verification and permission detail")
    lines.append("")
    if not result.claims:
        lines.append("_No claims to detail._")
    else:
        lines.append("| ID | Class | Confidence / limitations | Event year as stated by source | Privacy / permission |")
        lines.append("|----|-------|--------------------------|-------------------------------|----------------------|")
        for c in result.claims:
            lines.append("| %s | %s | %s | %s | %s |" % (
                c.id, c.evidence_class, c.confidence or "-",
                c.event_date or "not stated",
                (c.privacy_review or "-").replace("|", "/")))
    lines.append("")
    lines.append("_An empty cell means \"not established\" — never \"assumed\". A year \"as "  # noqa: E501
                 "stated by source\" is what the page says, not a confirmed date; the "  # noqa: E501
                 "chronology labels it accordingly._")
    lines.append("")
    lines.append("## 4. Gaps and blocked sources")
    lines.append("")
    if result.gaps:
        for g in result.gaps:
            lines.append("- %s" % g)
    else:
        lines.append("- None recorded.")
    lines.append("")
    lines.append("## 5. Notes")
    lines.append("")
    for n in result.notes:
        lines.append("- %s" % n)
    lines.append("")
    lines.append("> **Anti-fabrication:** every line above traces to a source row. "
                 "Where a source could not be read, the gap is stated and nothing was invented.")
    return "\n".join(lines) + "\n"


def claims_from_ledger_csv(text: str) -> List[Claim]:
    """Rebuild Claim objects from a ledger CSV written by :func:`ledger_csv`.

    Lets a later stage (chronology, interview planning) work from the saved
    ledger without re-fetching anything. Unknown columns are ignored, so an
    older CSV still loads.
    """
    claims: List[Claim] = []
    reader = csv.DictReader(io.StringIO(text or ""))
    for row in reader:
        if not row:
            continue
        safe_raw = (row.get("safe_for_public") or "").strip().lower()
        claims.append(Claim(
            id=row.get("claim_id") or "",
            text=row.get("claim") or "",
            source_id=row.get("source_id") or "",
            source_url=row.get("source_url") or "",
            page_title=row.get("page_title") or "",
            evidence_class=(row.get("evidence_class") or UNVERIFIED).strip(),
            safe_for_public=safe_raw in ("yes", "true", "1"),
            relevance=row.get("relevance") or "",
            needs=row.get("needs") or "",
            excerpt=row.get("excerpt") or "",
            source_date=row.get("source_date") or "",
            event_date=row.get("event_date") or "",
            confidence=row.get("confidence") or "",
            contradiction=row.get("contradiction") or "",
            privacy_review=row.get("privacy_review") or "",
        ))
    return claims


def result_to_dict(result: ResearchResult) -> Dict[str, Any]:
    return {
        "firm_name": result.firm_name,
        "sources": [asdict(s) for s in result.sources],
        "claims": [asdict(c) for c in result.claims],
        "gaps": list(result.gaps),
        "notes": list(result.notes),
    }


def result_from_dict(d: Optional[Dict[str, Any]]) -> ResearchResult:
    """Rebuild a :class:`ResearchResult` from :func:`result_to_dict` output.

    Used to resume a paused job from the ``research_raw.json`` it wrote, so a
    human can review findings today and continue the job days later without
    re-fetching anything (the sources are re-read by the *source*, not by this
    loader).

    Deliberately tolerant: unknown keys are ignored and missing keys take their
    dataclass default, so a file written by an older version still loads. It
    never invents a source or a claim — a field that was not recorded comes back
    empty, which downstream code already treats as "not established".
    """
    d = d or {}
    src_fields = set(Source.__dataclass_fields__)
    clm_fields = set(Claim.__dataclass_fields__)
    sources = [Source(**{k: v for k, v in s.items() if k in src_fields})
               for s in (d.get("sources") or []) if isinstance(s, dict)]
    claims = [Claim(**{k: v for k, v in c.items() if k in clm_fields})
              for c in (d.get("claims") or []) if isinstance(c, dict)]
    return ResearchResult(
        firm_name=str(d.get("firm_name") or ""),
        sources=sources,
        claims=claims,
        gaps=[str(g) for g in (d.get("gaps") or [])],
        notes=[str(n) for n in (d.get("notes") or [])],
    )


def load_raw(path: str) -> ResearchResult:
    """Load ``research_raw.json`` written by the workflow. Missing file → empty."""
    if not os.path.isfile(path):
        return ResearchResult(firm_name="")
    with open(path, "r", encoding="utf-8") as fh:
        return result_from_dict(json.load(fh))
