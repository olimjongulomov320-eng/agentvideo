# -*- coding: utf-8 -*-
"""voice.py — optional synthetic narration for the finished film.

Off by default. Set ``AGENT_TTS=edge`` and install ``edge-tts`` to enable it.
The engine sends each scene's narration text to Microsoft's online speech
service, which is the only way to get an Uzbek voice on this machine; that is
why it is opt-in. If the engine is missing, offline or fails, the film is
rendered without a voice and the reason is recorded, never raised.
"""
import asyncio
import importlib.util
import os
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

VOICES = {"uz": "uz-UZ-MadinaNeural", "ru": "ru-RU-SvetlanaNeural",
          "en": "en-US-AriaNeural"}
LEAD_IN_SEC = 0.5          # silence before each scene's line
TAIL_SEC = 0.4             # breathing room after it
MAX_SPEEDUP = 1.35         # a long line is sped up at most this much

Synth = Callable[[str, str, str], None]     # (text, voice, out_mp3) -> None


def enabled() -> bool:
    return (os.environ.get("AGENT_TTS") or "").strip().lower() == "edge"


def edge_installed() -> bool:
    return importlib.util.find_spec("edge_tts") is not None


def _edge_synth(text: str, voice: str, out_path: str) -> None:
    import edge_tts

    async def go() -> None:
        await edge_tts.Communicate(text, voice).save(out_path)

    # A private loop: asyncio.run() would unset the thread's current event loop,
    # which breaks any other asyncio code (the Telegram bot) in the same process.
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(asyncio.wait_for(go(), timeout=60))
    finally:
        loop.close()


def _duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, timeout=30)
    return float((out.stdout or "0").strip() or 0)


def _fit_scene(src: str, dst: str, scene_sec: float) -> None:
    """Delay the line, speed it up if it overruns, pad/trim to the scene length."""
    room = max(0.5, scene_sec - LEAD_IN_SEC - TAIL_SEC)
    speech = _duration(src)
    tempo = min(MAX_SPEEDUP, speech / room) if speech > room else 1.0
    chain = []
    if tempo > 1.0:
        chain.append("atempo=%.3f" % tempo)
    chain += ["adelay=%d|%d" % (int(LEAD_IN_SEC * 1000), int(LEAD_IN_SEC * 1000)),
              "apad=whole_dur=%.3f" % scene_sec, "atrim=0:%.3f" % scene_sec]
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", src,
                    "-af", ",".join(chain), "-ac", "1", "-ar", "44100", dst],
                   check=True, capture_output=True, timeout=120)


def build_voiceover(scenes: List[Dict[str, Any]], lang: str, work_dir: str,
                    overlap: float = 0.0, synth: Optional[Synth] = None
                    ) -> Tuple[Optional[str], str]:
    """Return ``(wav_path or None, note)``; the note says why there is no voice."""
    voice = VOICES.get((lang or "en")[:2])
    if not voice:
        return None, "no voice configured for language %r" % lang
    if synth is None:
        if not edge_installed():
            return None, "AGENT_TTS=edge is set but the edge-tts package is not installed"
        synth = _edge_synth
    os.makedirs(work_dir, exist_ok=True)
    pieces: List[str] = []
    try:
        for i, s in enumerate(scenes):
            text = " ".join((s.get("narration") or "").split())
            dur = float(s["dur"])
            fitted = os.path.join(work_dir, "vo_%02d.wav" % i)
            if text:
                raw = os.path.join(work_dir, "vo_%02d.mp3" % i)
                synth(text, voice, raw)
                _fit_scene(raw, fitted, dur)
            else:
                subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f",
                                "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "%.3f" % dur,
                                fitted], check=True, capture_output=True, timeout=60)
            pieces.append(fitted)
        # Scenes crossfade by `overlap`, so each following line starts that much sooner.
        inputs: List[str] = []
        labels: List[str] = []
        start = 0.0
        for i, p in enumerate(pieces):
            inputs += ["-i", p]
            ms = int(start * 1000)
            labels.append("[%d:a]adelay=%d|%d[a%d]" % (i, ms, ms, i))
            start += float(scenes[i]["dur"]) - overlap
        mix = "".join("[a%d]" % i for i in range(len(pieces)))
        out = os.path.join(work_dir, "voiceover.wav")
        subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"] + inputs +
                       ["-filter_complex", ";".join(labels) + ";%samix=inputs=%d:normalize=0[o]"
                        % (mix, len(pieces)), "-map", "[o]", "-ac", "1", "-ar", "44100", out],
                       check=True, capture_output=True, timeout=300)
        return out, "synthetic voice %s" % voice
    except Exception as exc:        # offline, service refused, ffmpeg problem…
        return None, "voice-over skipped: %s" % str(exc)[:200]


def attach(spec: Any, work_dir: str, overlap: float = 0.0,
           synth: Optional[Synth] = None) -> str:
    """Add a voice-over to ``spec`` when enabled. Returns a note ('' if disabled)."""
    if not enabled() and synth is None:
        return ""
    path, note = build_voiceover(spec.scenes, spec.language, work_dir, overlap, synth)
    if path:
        spec.audio.voiceover = path
        spec.audio.voice = "synthetic"
    return note
