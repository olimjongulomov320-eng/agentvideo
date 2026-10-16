# -*- coding: utf-8 -*-
"""security.py — secret redaction and safe-string helpers.

Every log line produced by the system passes through :func:`redact` so that a
bot token, API key, or Telegram ID never lands in a log file, a job record, or
a Telegram message.
"""
import os
import re
from typing import Iterable, List

# Values registered at runtime (e.g. the bot token) get masked verbatim.
_SECRETS = set()

_PATTERNS = [
    # Telegram bot tokens:  <digits>:<35-ish chars>
    re.compile(r"\b\d{6,12}:[A-Za-z0-9_-]{30,}\b"),
    # OpenAI-style keys and other long bearer-looking tokens
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{40,}\b"),
    # Authorization headers. The optional scheme is consumed together with the
    # credential so that "Authorization: Bearer <token>" cannot leak the token.
    re.compile(r"(?i)(authorization\s*[:=]\s*)(?:(?:bearer|token|basic)\s+)?(\S+)"),
    re.compile(r"(?i)(\bbearer\s+)(\S+)"),
]

MASK = "[REDACTED]"


def register_secret(value: str) -> None:
    """Register a literal secret (e.g. the bot token) for masking."""
    if value and isinstance(value, str) and len(value) >= 6:
        _SECRETS.add(value)


def redact(text: str) -> str:
    """Return *text* with any known or pattern-matched secret replaced."""
    if not text:
        return text
    out = str(text)
    for s in list(_SECRETS):
        if s and s in out:
            out = out.replace(s, MASK)
    for pat in _PATTERNS:
        if pat.groups >= 2:
            out = pat.sub(lambda m: m.group(1) + MASK, out)
        else:
            out = pat.sub(MASK, out)
    return out


def redact_lines(lines: Iterable[str]) -> List[str]:
    return [redact(ln) for ln in lines]


def load_dotenv_if_present(root: str) -> None:
    """Load ``<root>/.env`` if it exists. Never raises, never echoes values."""
    path = os.path.join(root, ".env")
    if not os.path.isfile(path):
        return
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        _manual_parse(path)
        return
    load_dotenv(path, override=False)


def _manual_parse(path: str) -> None:
    """Minimal .env parser used when python-dotenv is unavailable."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, val = line.partition("=")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = val
    except OSError:
        return
