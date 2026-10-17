#!/usr/bin/env python3
"""Safely write TELEGRAM_BOT_TOKEN into .env.

Why this exists: a bot token is a credential. Typing it into a chat window,
a shell command line, or a log leaks it. This script reads the token from a
hidden prompt (or piped stdin) and updates exactly one line in .env, without
ever echoing the value.

Usage
-----
    python3 scripts/set_telegram_token.py                 # hidden prompt
    python3 scripts/set_telegram_token.py --env-file X     # other file
    printf '%s' "$TOKEN" | python3 scripts/set_telegram_token.py   # piped

The script never prints the token, never writes it anywhere except the target
file, and refuses tokens that do not look like Telegram bot tokens.

Exit codes
----------
    0  token saved
    1  no token supplied / invalid shape
    2  target file missing and could not be created from .env.example
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# BotFather tokens look like  <digits>:<35-ish url-safe chars>
TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,50}$")

PLACEHOLDER_MARKERS = ("REPLACE_WITH", "YOUR_BOT_TOKEN", "000000000:")


def looks_like_placeholder(value: str) -> bool:
    return any(m in value for m in PLACEHOLDER_MARKERS)


def mask(token: str) -> str:
    """Show only enough to let a human confirm they pasted the right thing."""
    head, _, tail = token.partition(":")
    return "%s…%s (len=%d)" % (head[:4], tail[-3:] if len(tail) >= 3 else "***", len(token))


def read_token(interactive_prompt: str = "Paste Telegram bot token (input hidden): ") -> str:
    if sys.stdin.isatty():
        import getpass

        return getpass.getpass(interactive_prompt).strip()
    return sys.stdin.read().strip()


def upsert_token(text: str, token: str) -> tuple[str, bool]:
    """Replace the TELEGRAM_BOT_TOKEN line; append it if absent.

    Returns (new_text, was_updated_in_place).
    """
    pattern = re.compile(r"(?m)^[ \t]*(?:export[ \t]+)?TELEGRAM_BOT_TOKEN[ \t]*=.*$")
    if pattern.search(text):
        return pattern.sub("TELEGRAM_BOT_TOKEN=" + token, text, count=1), True
    if not text.endswith("\n"):
        text += "\n"
    return text + "TELEGRAM_BOT_TOKEN=" + token + "\n", False


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Safely set TELEGRAM_BOT_TOKEN in an env file.")
    ap.add_argument("--env-file", default=".env", help="target env file (default: .env)")
    ap.add_argument(
        "--example",
        default=".env.example",
        help="template used if the target file does not exist (default: .env.example)",
    )
    ap.add_argument("--quiet", action="store_true", help="only print errors")
    args = ap.parse_args(argv)

    target = Path(args.env_file)

    if not target.exists():
        example = Path(args.example)
        if example.exists():
            target.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            if not args.quiet:
                print("Created %s from %s" % (target, example))
        else:
            print("ERROR: %s not found and no template at %s" % (target, example), file=sys.stderr)
            return 2

    token = read_token()

    if not token:
        print("ERROR: empty token — nothing written.", file=sys.stderr)
        return 1

    if looks_like_placeholder(token):
        print("ERROR: that looks like the placeholder from .env.example, not a real token.", file=sys.stderr)
        return 1

    if not TOKEN_RE.match(token):
        print(
            "ERROR: token does not match the expected <digits>:<secret> shape "
            "(length %d). Nothing written." % len(token),
            file=sys.stderr,
        )
        return 1

    original = target.read_text(encoding="utf-8")
    updated, in_place = upsert_token(original, token)
    target.write_text(updated, encoding="utf-8")

    try:
        os.chmod(target, 0o600)
    except OSError:
        pass

    if not args.quiet:
        print("Saved TELEGRAM_BOT_TOKEN to %s (%s)." % (target, "replaced existing line" if in_place else "appended new line"))
        print("Token fingerprint: %s" % mask(token))
        print("Next: restart the bot so it picks up the new token.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
