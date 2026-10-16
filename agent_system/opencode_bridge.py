# -*- coding: utf-8 -*-
"""opencode_bridge.py — optional, controlled invocation of the OpenCode CLI.

Design decision (see README): the Telegram bot does **not** drive OpenCode for
its core workflow. Research, story and rendering are implemented as ordinary
Python functions in this package, so a tool-controlled interface exists and no
outer shell is ever exposed.

This bridge exists only as an *optional enrichment*: when ``OPENCODE_ENABLED``
is true, the operator may ask the configured agent to draft narrative copy from
an already-validated evidence ledger. Safety rules applied here:

* fixed prompt templates — user text is never passed through as a prompt;
* argument arrays, never shell string concatenation;
* bounded capture (output truncated) and a hard timeout;
* the bot cannot change its own configuration through this path.
"""
import os
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from .security import redact

DEFAULT_AGENT = "law-firm-researcher"
MAX_OUTPUT_CHARS = 20000


class BridgeUnavailable(RuntimeError):
    pass


def binary_available(binary: str = "opencode") -> bool:
    import shutil
    return shutil.which(binary) is not None


def build_research_prompt(firm_name: str, website: str, language: str) -> str:
    """A fixed template. Only short, validated values are interpolated."""
    lang = (language or "en")[:2].lower()
    firm = str(firm_name or "").strip()[:120]
    site = str(website or "").strip()[:300]
    return (
        "Research the law firm '{firm}' using only publicly accessible sources "
        "(official website: {site}). Build an evidence register with a source URL "
        "for every statement and an evidence class "
        "(Verified / Corroborated / Single-source / Unverified / Conflicting / Unavailable). "
        "Do not invent dates, awards, cases, clients or quotations. Report login-walled "
        "or blocked sources explicitly and leave gaps as gaps. "
        "Narration language: {lang}."
    ).format(firm=firm, site=site or "not supplied", lang=lang)


def run_agent(cfg, prompt: str, agent: str = DEFAULT_AGENT,
              timeout: Optional[int] = None) -> Tuple[bool, str, str]:
    """Run ``opencode run --agent <agent> -m <model> <prompt>`` non-interactively.

    Returns ``(ok, stdout, error)``. Never raises for ordinary run failures.
    """
    if not getattr(cfg, "opencode_enabled", False):
        raise BridgeUnavailable(
            "OpenCode bridge is disabled. Set OPENCODE_ENABLED=true to enable it.")
    if not binary_available(cfg.opencode_bin):
        raise BridgeUnavailable("opencode binary not found: %s" % cfg.opencode_bin)

    args: List[str] = [cfg.opencode_bin, "run", "--agent", agent]
    if getattr(cfg, "opencode_model", ""):
        args += ["-m", cfg.opencode_model]
    args.append(prompt)

    try:
        proc = subprocess.run(args, capture_output=True, text=True,
                              timeout=int(timeout or 900), cwd=cfg.project_root)
    except FileNotFoundError as exc:
        raise BridgeUnavailable("cannot execute opencode: %s" % exc)
    except subprocess.TimeoutExpired:
        return False, "", "opencode timed out after %ss" % (timeout or 900)

    out = redact((proc.stdout or "")[:MAX_OUTPUT_CHARS])
    err = redact((proc.stderr or "")[:4000])
    return proc.returncode == 0, out, err


def status(cfg) -> Dict[str, Any]:
    return {
        "enabled": bool(getattr(cfg, "opencode_enabled", False)),
        "binary": getattr(cfg, "opencode_bin", "opencode"),
        "available": binary_available(getattr(cfg, "opencode_bin", "opencode")),
        "model": getattr(cfg, "opencode_model", "") or "(default)",
        "agent": DEFAULT_AGENT,
        "note": ("Optional enrichment only. Core research/story/render run in-process; "
                 "no user-supplied text is ever executed."),
    }
