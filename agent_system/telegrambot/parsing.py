# -*- coding: utf-8 -*-
"""telegrambot.parsing — untrusted-input parsing and validation.

Everything a Telegram user types or uploads is treated as *data*. These helpers
extract a small, bounded set of parameters and reject anything else. Nothing
here executes or evaluates user content.
"""
import os
import re
from typing import Any, Dict, List, Optional, Tuple

URL_RE = re.compile(r"https?://[^\s<>\"')]+", re.I)
BARE_DOMAIN_RE = re.compile(r"\b([a-z0-9][a-z0-9-]{1,62}\.(?:com|uz|org|net|io|co|ru|kz|law|legal)(?:\.[a-z]{2})?)\b", re.I)

ALLOWED_EXT = {
    ".txt", ".md", ".csv", ".json", ".srt", ".vtt", ".log",
    ".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".pdf",
    ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".mp4", ".mov",
    ".docx", ".pptx", ".xlsx",
}
ALLOWED_STYLES = ("motion", "illustrated", "blender3d")

_STYLE_HINTS = [
    ("blender3d", ("3d", "blender", "three-d", "трехмер", "uch olcham", "3-d")),
    ("illustrated", ("illustrated", "illustration", "2d", "cartoon", "drawn",
                     "animate", "animation", "иллюстр", "мульт", "animatsiya")),
    ("motion", ("motion graphics", "motion", "kinetic", "graphics", "график")),
]

_LANG_HINTS = [
    ("uz", ("uzbek", "o'zbek", "ozbek", "uzbekcha", "uz", "узбек")),
    ("ru", ("russian", "russian language", "русск", "ру", "ru")),
    ("en", ("english", "ingliz", "англ", "en")),
]

_DURATION_PATTERNS = [
    re.compile(r"(\d{1,3})\s*[- ]?\s*(?:minutes?|min|мин(?:ут\w*)?|daqiqa|минут\w*)\b", re.I),
    re.compile(r"(\d{2,4})\s*[- ]?\s*(?:seconds?|sec|сек\w*|sekund\w*)\b", re.I),
]


def extract_urls(text: str) -> List[str]:
    return [u.rstrip(".,;:)") for u in URL_RE.findall(text or "")][:8]


def detect_language(text: str, default: str = "en") -> str:
    # URLs and domains are removed first: "acme.uz" must not be read as Uzbek.
    low = URL_RE.sub(" ", (text or "").lower())
    low = BARE_DOMAIN_RE.sub(" ", low)
    for code, hints in _LANG_HINTS:
        for h in hints:
            if re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(h), low):
                return code
    return default


_EXPLICIT_STYLE_RE = re.compile(r"style\s*[:=]\s*([a-z0-9\- ]{2,24})")


def detect_style(text: str, default: str = "motion") -> str:
    low = (text or "").lower()
    # An explicit "Style: ..." declaration outranks incidental wording such as
    # "animated history video", which would otherwise imply illustration.
    m = _EXPLICIT_STYLE_RE.search(low)
    if m:
        declared = m.group(1)
        for style, hints in _STYLE_HINTS:
            for h in hints:
                if h in declared:
                    return style
    for style, hints in _STYLE_HINTS:
        for h in hints:
            if h in low:
                return style
    return default


def detect_duration(text: str, default: int = 140) -> int:
    for pat in _DURATION_PATTERNS:
        m = pat.search(text or "")
        if m:
            val = int(m.group(1))
            if "sec" in pat.pattern or "сек" in pat.pattern or "sekund" in pat.pattern:
                return max(20, min(400, val))
            return max(20, min(400, val * 60))
    return default


def detect_firm(text: str) -> str:
    """Best-effort firm name extraction; never invents one."""
    # Links are not part of a name: "GSP Law Firm https://x.uz" must not yield "https".
    low = BARE_DOMAIN_RE.sub(" ", URL_RE.sub(" ", text or ""))
    m = re.search(r"(?i:\bfor\s+(?:the\s+)?)([A-Z][\w'&.,\- ]{2,70}?"
                  r"(?:Law Firm|Legal|LLP|Partners|Advocates|Associates))\b", low)
    if m:
        return _clean_firm(m.group(1))
    m = re.search(r"(?i:\b(?:firm|company|kompaniya|фирм\w*)[:\s]+)([A-Z][\w'&.,\- ]{2,70})", low)
    if m:
        return _clean_firm(m.group(1))
    m = re.search(r"\b([A-Z][A-Za-z&'\-]+(?:\s+[A-Z][A-Za-z&'\-]+){0,3})\s+"
                  r"(?:Law Firm|Legal|LLP|Partners)\b", low)
    if m:
        return _clean_firm(m.group(0))
    return ""


def _clean_firm(s: str) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip(" .,:;-\u2014"))
    s = re.sub(r"(?i)^(?:the|a|an)\s+", "", s)
    # the name ends where the request's other fields begin
    s = re.sub(r"(?i)[\s,.]+(?:website|site|language|style|length|duration|web|url)\b.*$", "", s)
    return s[:120]


def parse_request_text(text: str) -> Dict[str, Any]:
    """Extract request parameters from a free-text message. Purely heuristic."""
    urls = extract_urls(text)
    if not urls:
        doms = BARE_DOMAIN_RE.findall(text or "")
        urls = ["https://" + d for d in doms][:4]
    website = ""
    facebook = ""
    extra: List[str] = []
    for u in urls:
        low = u.lower()
        if "facebook.com" in low and not facebook:
            facebook = u
        elif not website and "facebook.com" not in low:
            website = u
        else:
            extra.append(u)
    return {
        "firm_name": detect_firm(text),
        "website": website,
        "facebook": facebook,
        "extra_urls": extra,
        "language": detect_language(text),
        "style": detect_style(text),
        "duration_sec": detect_duration(text),
    }


def safe_filename(name: str, fallback: str = "upload.bin") -> str:
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base)
    base = base.lstrip(".") or fallback
    return base[:120]


def validate_incoming_document(name: str, size_bytes: Optional[int],
                               max_mb: int) -> Tuple[bool, str]:
    """Type + size gate for a Telegram attachment."""
    fn = safe_filename(name or "")
    ext = os.path.splitext(fn)[1].lower()
    if not ext:
        return False, "file has no extension; allowed: %s" % ", ".join(sorted(ALLOWED_EXT))
    if ext not in ALLOWED_EXT:
        return False, "file type %s not allowed. Allowed: %s" % (ext, ", ".join(sorted(ALLOWED_EXT)))
    if size_bytes is None:
        return True, ""
    limit = int(max_mb) * 1024 * 1024
    if size_bytes > limit:
        return False, "file is %.1f MB; limit is %d MB" % (size_bytes / 1048576.0, max_mb)
    if size_bytes <= 0:
        return False, "file appears to be empty"
    return True, ""


def missing_required(req: Dict[str, Any]) -> List[str]:
    """Which pieces of information are genuinely required to start a job."""
    missing = []
    if not (req.get("firm_name") or "").strip():
        missing.append("firm name")
    if not (req.get("website") or "").strip() and not (req.get("facebook") or "").strip():
        missing.append("website or Facebook URL")
    return missing
