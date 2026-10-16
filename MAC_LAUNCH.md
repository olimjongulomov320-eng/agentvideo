# MAC_LAUNCH.md — Running on macOS

## Prerequisites
- macOS (tested on this machine)
- Python 3.9.6 (system or via `pyenv`)
- `ffmpeg` 8.1.2+ (video processing). Install: `brew install ffmpeg`
- `blender` — optional (3D). If missing, `blender3d` style reports `UNAVAILABLE` (honest, never faked).
- Telegram access for bot interaction (if using `serve`)

Python packages (already installed here): `python-telegram-bot==21.6`, `Pillow==11.2.1`. If missing, install:
```sh
pip install -r requirements.txt  # if present
# or
pip install python-telegram-bot==21.6 Pillow requests
```

## Setup
```sh
cd "/Users/olimjongulomov/Desktop/Projects/AI-Bots/AI AGENT FOR MY FATHER(new)"
cp .env.example .env
# Edit .env: set TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_IDS (two numeric IDs)
```

## Commands
| Command | Purpose |
|---|---|
| `python3 -m agent_system styles` | List backends and readiness/limitations. |
| `python3 -m agent_system health` | JSON summary (token_set, allowed_user_count, capabilities, limits). |
| `python3 -m agent_system run-job --firm "Name" --website "https://..." --language uz --style motion --duration 140` | Headless pipeline run. Add `--fast` for 960×540, `--no-preview`/`--preview-only`, `--no-render`. |
| `python3 -m agent_system selftest` | Render a short clip per ready backend; writes `output/selftest/selftest_report.json`. |
| `python3 -m agent_system check-spec output/jobs/<id>/scene_manifest.json` | Validate a scene manifest. |
| `python3 -m agent_system serve` | Start Telegram bot (polling). Requires `.env`; refuses with exit 2 if missing. Stop with Ctrl+C. |

## No-render (research/script/storyboard only)
```sh
python3 -m agent_system run-job --firm "Test" --website "https://example.com" --language uz --style motion --duration 120 --no-render
# or
AGENT_NO_RENDER=1 python3 -m agent_system run-job --firm "Test" --website "https://example.com" ...
```
Result: no `preview.mp4`/`final.mp4`; `delivery_report.md` contains "**No video was rendered**". Research/script/storyboard artifacts are produced.

## Behaviour notes
- **Uzbek TTS:** macOS `say` has no Uzbek voice (`tts_voices.uz=false`). Final Uzbek narration must be human-recorded.
- **Blender:** absent → `blender3d` reported UNAVAILABLE (honest). No fake renders.
- **Uploads > MAX_UPLOAD_MB (49):** Bot API won’t upload the large file; a local path is given instead.
- **QA:** Agent cannot view images/hear audio. All QC is programmatic; a human must watch the final video.
- **Output location:** `output/jobs/<job_id>/` contains all artifacts; `output/jobs.sqlite3*` stores job state.
- **Secrets:** `TELEGRAM_BOT_TOKEN` is redacted by `security.redact` in logs and messages. Never echo `.env`.