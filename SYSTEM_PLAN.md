# SYSTEM_PLAN.md — implementation plan (Telegram-controlled video production)

**Written:** 2026-10-15, after repository inspection.

## Repository findings (actual)

| Item | Finding |
|---|---|
| Git | **Not a repository** (no `.git`) — changes are file writes only |
| Python | **3.9.6** (system) — code must be 3.9-compatible |
| telegram lib | **python-telegram-bot 21.6** already installed (async) |
| Other libs | `requests`, `numpy`, `scipy`, `pydantic`, `dotenv`, `sqlite3`, `aiohttp`, `PIL` — all present |
| Missing libs | `pytelegrambotapi`, `matplotlib`, `cairo`, `svgwrite`, `moderngl`, `pyrr`, `bs4` |
| FFmpeg / FFprobe | **8.1.2** present |
| Blender | **NOT installed** |
| Node/npm | v26.7.0 / 11.19.0 (not needed) |
| OpenCode CLI | `opencode run --agent <id> -m <model> "<prompt>"` — noninteractive works (verified in AGENT_TESTS.md); default model rejected in this region |
| Existing renderer | `demo/build/`: Pillow → PNG frames → ffmpeg `zoompan` segments → `xfade` → audio → mux; **reusable**, GSP-specific |
| Tests | **None** — only the `AGENT_TESTS.md` document |
| Secrets | No `.env` exists yet |

## Plan

1. **`agent_system/` Python package** (3.9-safe, stdlib-first, no new dependencies):
   - `config.py` — env vars, paths, capability detection, validation
   - `security.py` — secret redaction for logs
   - `jobs.py` — SQLite job store: unique IDs, states, dedupe by `update_id`, cancellation, limits
   - `research.py` — fetch + extract + evidence ledger (stdlib `html.parser`), classification, no fabrication
   - `story.py` — concepts / script / storyboard / scene manifest from the evidence ledger
   - `video/` — `spec.py` (validated scene spec), `motion.py`, `illustrated.py`, `blender3d.py`, `common.py` (ffmpeg + ffprobe validation + render manifest)
   - `orchestrator.py` — predefined job workflow (research → story → approve → render → validate → report)
   - `opencode_bridge.py` — optional, controlled `opencode run` invocation (arg arrays, timeout, bounded output)
   - `telegrambot/` — auth, commands, handlers, delivery
   - `cli.py` — `run-job` / `serve` / `styles` / `health`

2. **Three real backends**, honestly labelled:
   - **motion** — animated typography, logo reveal, pan/zoom/parallax, lower thirds, end cards (ffmpeg + Pillow)
   - **illustrated** — layered raster illustrations, keyframed movement, camera moves, scene transitions
   - **blender3d** — integration boundary; **Blender absent** → honest unavailability error + generated Blender script for when it is installed

3. **Telegram bot** (python-telegram-bot 21.6, polling): two authorized users, 8 commands, validated inputs, progress updates, dedupe, file-size/type limits, safe alternative delivery when > limit.

4. **Tests** (`tests/`, stdlib `unittest`): run for real; mocked Telegram; no real messages sent.

5. **Docs**: README, `.env.example`, Telegram setup + ID guide, Mac launch, VPS, troubleshooting, test report.

## Honest limitations to carry through
- No permission to install software → **Blender/3D stays an integration boundary**, not a working renderer.
- No Uzbek TTS → synthetic audio only where a real engine exists; human narration tracked as a requirement.
- Facebook login wall → reported, never claimed as reviewed.
- Telegram Bot API upload cap → configurable; oversize files delivered via local path/secure link instead.
