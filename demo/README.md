# GSP LAW — Opening-film DEMO (visual prototype)

**Status: DEMO / CONCEPT PREVIEW — not a final, approved film.**
Nothing here is cleared for publication or for sending to third parties without
the client's explicit written approval.

Two playable prototypes of the 2–2.5 min opening film for the new office of
**Gulyamov, Sadikov and Partners** (Tashkent, opening 20 October 2026):

| File | Language | Audio | Runtime | Notes |
|---|---|---|---|---|
| `GSP_demo_UZ.mp4` | Uzbek (master) | synthesized music bed only | 2:23 | Uzbek narration shown as on-screen titles; **voice-over to be recorded** |
| `GSP_demo_RU.mp4` | Russian | music bed + **temporary** TTS voice-over | 2:23 | voice is a placeholder (macOS "Milena") |
| `GSP_demo_UZ.srt` / `GSP_demo_RU.srt` | — | — | 2:23 | sidecar subtitles synced to the picture |

Specs (both): 1920×1080 · 30 fps · H.264 High@4.1 · AAC 192 kb/s stereo 48 kHz · faststart.

---

## Read these next

| Document | What it contains |
|---|---|
| `DEMO_NOTES.md` | What was made, how it was made, honesty notes, limitations |
| `NARRATION.md` | The complete narration (Uzbek master + Russian), timed |
| `TIMELINE.md` | Scene-by-scene timeline (visuals, on-screen text, audio, sources) |
| `SOURCES_AND_ASSETS.md` | Every source and asset used, with provenance |
| `PLACEHOLDERS.md` | Everything that is illustrative/placeholder and what is missing |
| `RECOMMENDATIONS.md` | How to turn this demo into a finished film |

---

## Rebuild from scratch

Everything is reproducible. Requirements: macOS, `ffmpeg`/`ffprobe`, Python 3 with
Pillow and numpy, and the system `say` command (macOS voices).

```bash
cd demo/build
python3 render_frames.py uz ru     # draw all 18 scene frames (Pillow)
python3 make_audio.py              # synthesize music + temporary RU voice-over
python3 assemble.py uz             # -> ../GSP_demo_UZ.mp4
python3 assemble.py ru             # -> ../GSP_demo_RU.mp4
python3 make_srt.py                # -> ../GSP_demo_*.srt
```

Source files:

```
demo/
├── assets/web/            # real assets pulled from gsplaw.co.uz
│   ├── logo-full.png      # the firm's real logo (874×340)
│   ├── logo-shield.png
│   ├── data.js            # the firm's own site data (team, contacts, claims)
│   ├── style.css          # the firm's real brand colours
│   └── photos/            # 15 real team photographs
├── build/
│   ├── timeline.py        # single source of truth: scenes, durations, narration
│   ├── render_frames.py   # Pillow: all typography + graphics
│   ├── make_audio.py      # ffmpeg music synthesis + macOS TTS voice-over
│   ├── assemble.py        # ffmpeg: motion, crossfades, grade, mix, encode
│   ├── make_srt.py        # subtitles
│   ├── frames/            # generated scene stills
│   ├── audio/             # generated music + voice-over stems
│   ├── segments/          # per-scene motion clips
│   └── qa/                # frames extracted for verification
└── *.mp4, *.srt           # the deliverables
```
