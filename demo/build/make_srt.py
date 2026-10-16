#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_srt.py — emits demo subtitles timed to the crossfaded timeline.

  demo/GSP_demo_RU.srt : matches the temporary Russian voice-over
  demo/GSP_demo_UZ.srt : Uzbek narration (the intended master read; VO to be recorded)
"""
import os, json, sys, textwrap
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from timeline import SCENES, scene_starts, total_duration

ROOT = os.path.dirname(HERE)
AUD = os.path.join(HERE, "audio")

def ts(s):
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

def wrap(t, width=44):
    return textwrap.wrap(t, width=width)

def build(lang, vo_manifest=None):
    cues = []
    starts = scene_starts()
    for i, ((key, d, ru, uz), st) in enumerate(zip(SCENES, starts)):
        if key == "slate":
            continue
        if lang == "ru":
            item = next((v for v in (vo_manifest or {}).get("vo", []) if v["key"] == key), None)
            text = ru
            if not text:
                continue
            a = item["start"] if item else st + 0.5
            b = a + (item["len"] if item else d - 1.0)
        else:
            text = uz
            if not text:
                continue
            a = st + 0.6
            b = st + d - 0.6
        cues.append((a, b, text))
    lines, n = [], 1
    for a, b, text in cues:
        lines.append(str(n)); n += 1
        lines.append(f"{ts(a)} --> {ts(b)}")
        lines.extend(wrap(text))
        lines.append("")
    return "\n".join(lines)

if __name__ == "__main__":
    vm = json.load(open(os.path.join(AUD, "vo_manifest.json")))
    for lang in ("ru", "uz"):
        out = os.path.join(ROOT, f"GSP_demo_{lang.upper()}.srt")
        open(out, "w", encoding="utf-8").write(build(lang, vm))
        print("wrote", out)
    print("total duration:", round(total_duration(), 2), "s")
