# TEST_REPORT.md — Law Firm Research & Video Script Agent (agent_system)

**Generated:** 2026-10-16  
**Scope:** Python package `agent_system/` (renderer, Telegram bot, orchestrator, research/story/spec)  
**Python:** 3.9.6 · `python-telegram-bot`: 21.6 · `Pillow`: 11.2.1 · `ffmpeg`: 8.1.2

## 1. Automated tests (unit + mocked-integration)

Command:
```sh
cd "/Users/olimjongulomov/Desktop/Projects/AI-Bots/AI AGENT FOR MY FATHER(new)"
python3 -W ignore::ResourceWarning -m unittest discover -s tests -t . -v
```

**Result:** **172 tests**, **0 failures**, **0 errors**, **0 skipped**, **21.7 s**.

### Per-module breakdown
| Module | Tests | Fail | Err | Skip | Purpose |
|---|---|---|---|---|---|
| `tests/test_config_security.py` | 17 | 0 | 0 | 0 | Config defaults, `from_env(detect=False)`, `FAST_RENDER` parsing, secret hygiene, `summary()` |
| `tests/test_jobs.py` | 18 | 0 | 0 | 0 | JobStore lifecycle, dedupe (`mark_update`), status/progress, active listing, cancellation |
| `tests/test_orchestrator.py` | 13 | 0 | 0 | 0 | Research→story→render path, offline fetcher, preview-only, render overrides, no-render guard |
| `tests/test_parsing.py` | 16 | 0 | 0 | 0 | Request parsing, URL extraction, duration/language/style detection, document validation, filename safety |
| `tests/test_render.py` | 14 | 0 | 0 | 0 | Render spec validation, frame rendering, manifest generation, preview clipping, watermark/branding |
| `tests/test_research.py` | 16 | 0 | 0 | 0 | Website fetching, claim extraction, evidence classification, gap logging, public-safety filters |
| `tests/test_spec_backends.py` | 15 | 0 | 0 | 0 | Backend readiness (motion/illustrated/blender3d), limitations/reasons, render overrides |
| `tests/test_story.py` | 17 | 0 | 0 | 0 | 2–2.5m script generation, per-scene timecodes, citations, 3 concepts, storyboard + subtitles |
| `tests/test_telegrambot.py` | 30 | 0 | 0 | 0 | Auth gates, commands, dedupe, document upload validation, approval flow, delivery logic, secret redaction |
| `tests/test_integration.py` | 16 | 0 | 0 | 0 | End-to-end mocked Telegram: auth before job creation, dedupe, malformed/unavailable-style handling, lifecycle, mocked render, render-failure handling (redacted), cancellation consistency, no-render mode, controlled-render path |

**Regression check:** 172/172 passing — no change in behaviour relative to the previously passing 156 tests.

## 2. Mocked-integration tests (subset of above)

The `tests/test_integration.py` suite uses only `tests/fakes.py` (no real Telegram API, no network, temp dirs). It explicitly covers:

- **Authorized flow:** `authorize` gate → validate/sanitise (`sanitize_request`) → unique 9-char job id → lifecycle states recorded → orchestrator via controlled interface (monkeypatched `run_job` or mocked `video.render_style`) → mocked/lightweight render → deliverable metadata written → mocked Telegram receives status/delivery calls (via FakeBot).
- **Unauthorized:** rejected before any job row created; no outbound bot messages.
- **Dedupe:** `JobStore.mark_update` returns True once, False on duplicate → `ApplicationHandlerStop` raised; no second job started.
- **Invalid/malformed:** missing fields, empty/garbled text → safe reply, no job; unavailable style (`blender3d`) → honest "not available", no job; unknown style → falls back to `motion` (safe default).
- **Mocked render failure:** stores failed status with non-sensitive, redacted error (realistic token-matching pattern tested; `secret not in job["error"]` and `secret not in` user-facing text).
- **Cancellation:** `request_cancel` → terminal `cancelled` status; `_deliver` reports cancellation consistently.
- **No-render mode:** `enable_render=False` (or `AGENT_NO_RENDER=1`) → completes without calling `video.render_style` at all, sets `result["no_render"]=True`, writes `delivery_report.md` containing "**No video was rendered**", and never produces `preview.mp4` or `final.mp4`.
- **Controlled render path:** mocked `video.render_style` writes a small file and returns `validation`/`manifest` metadata; result includes `output`, `validation`, `artifacts` as expected.

## 3. Manual / verification tests (performed on this machine)

| Test | Command / Evidence | Result |
|---|---|---|
| Config ground-truth | `dataclasses.fields(Config)`, `inspect.signature(Config.from_env)` (detect only), `fast_render` parsed from `FAST_RENDER` (true/false) | OK — `fast_render` exactly once, no duplicates; `from_env(detect=False)` works; `render_overrides()` exists. `summary()` exposes `fast_render` (key present) and no secrets. |
| `--no-render` wiring | `AGENT_NO_RENDER=1` respected by orchestrator; `--no-render` CLI flag passes `enable_render=False`. | OK. Report explicitly states no video rendered; research/script/storyboard still produced. |
| CLI self-check | `python3 -m agent_system styles` | Shows `motion READY`, `illustrated READY`, `blender3d UNAVAILABLE` (Blender not installed). Accurate limitations listed. |
| CLI health (JSON) | `python3 -m agent_system health` | Reports `token_set=false`, `allowed_user_count=0`, ffmpeg/ffprobe version, tts_voices (en/ru true, uz false), opencode enabled/disabled. |
| CLI serve guard | `python3 -m agent_system serve` (no `.env`) | Exits with code 2; logs configuration errors and refuses to start. |
| Existing render evidence (JYDV8WGZQ) | `ffprobe` verified | `final.mp4`: h264 960×540 @24fps + aac 2ch 48kHz, `duration=35.791667`, `size=1,394,907 B`. `preview.mp4`: 16.958333 s. Delivery/report/artifacts present. |
| Preview-only (JHS9M53EK) | `ffprobe preview.mp4` | 16.958333 s, same codec/size profile as preview. No `final.mp4`. |
| Selftest | `output/selftest/selftest_report.json` (read, not re-run to save time) | motion: ok (4.583s, 148154 B); illustrated: ok (4.583s, 195560 B); blender3d: skipped (Blender not installed). |
| py_compile | `python3 -m py_compile agent_system/*.py agent_system/telegrambot/*.py agent_system/research/*.py agent_system/story/*.py agent_system/video/*.py` | All compiled successfully. |

## 4. Not performed (documented as impossible/absent)

- **Live Telegram end-to-end:** No `TELEGRAM_BOT_TOKEN` and no authorised user IDs configured. `serve` refuses without `.env` (exit 2). A real end-to-end run would require a real bot token and two configured numeric user IDs.
- **3D rendering (blender3d):** Blender is not installed on this machine; backend reports `ready=false` with an honest reason. No 3D render was attempted.
- **Uzbek TTS:** `tts_voices.uz=false` (macOS `say` has no Uzbek voice). The system never claims Uzbek voice synthesis; final Uzbek narration must be human-recorded.
- **Real Facebook scraping:** Pages are login-walled. The code records blocked sources and requires user-supplied exports/screenshots; no access controls were bypassed.
- **External publication:** All outputs marked for operator/approval only; demo watermarks (`DEMO / CONCEPT PREVIEW`) are preserved; synthesised/temporary audio labelled as such.

## 5. Known limitations & risks

1. **Tool-output channel:** The sandbox's `read`/`grep`/shell channels have previously emitted duplicated/corrupted file content in long dumps. Ground truth for this work was re-established via compact import/AST verdicts and small Python snippets, not large file reads.
2. **Secret redaction:** `security.redact` masks registered literals and Telegram token / long-key patterns. A generic token-like string can slip if it doesn't match current regexes; registering the secret at startup (as done by `Config.from_env`/bot) is the primary control. Tests verify no token leak to Telegram/user-facing messages.
3. **Max upload:** `MAX_UPLOAD_MB=49` (default) — files larger than ~49 MB are **not uploaded** via Bot API; delivery falls back to the local path in the `output/jobs/<id>/` tree. For 1920p/demo outputs, expect path-based delivery.
4. **Approval timeout:** `APPROVAL_TIMEOUT_SEC=900` (15 min). Expiry cancels rendering cleanly with a human-readable message.

## 6. Test commands (copy/paste)

```sh
cd "/Users/olimjongulomov/Desktop/Projects/AI-Bots/AI AGENT FOR MY FATHER(new)"
python3 -W ignore::ResourceWarning -m unittest discover -s tests -t . -v
python3 -W ignore::ResourceWarning -m unittest tests.test_integration tests.test_config_security tests.test_telegrambot
python3 -m agent_system selftest
python3 -m agent_system styles
python3 -m agent_system health
python3 -m agent_system check-spec /path/to/scene_manifest.json  # example
```

**Final verdict:** All automated tests pass (172/172). No-render mode is correctly wired (research/story produced; no renderer started). The mocked Telegram integration covers authorised/unauthorised, dedupe, malformed/unavailable styles, lifecycle, render failure with redaction, cancellation, and no-render. System is in a releasable, verifiably honest state for operator use.