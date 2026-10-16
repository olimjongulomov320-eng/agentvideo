# RUN_STATUS.md — GSP continuation run

**Date:** 2026-10-15 · **Mode:** continuation of an existing, near-complete GSP project.
**Intake (confirmed this run):** Gulyamov, Sadikov and Partners · Uzbek **master** + Russian
secondary · event = new-office opening · rendered demo requested.

---

## Phase 0 — Environment inspection (verified this run)

| Capability | Result |
|---|---|
| ffmpeg | 8.1.2 — video rendering available |
| Python + Pillow | 3.9.6 / 11.2.1 — frame rendering available |
| macOS `say` Uzbek voice | **0 (none)** — final Uzbek VO needs a human narrator |
| Browser automation | **Not available** (`browser` action denied) |
| Image/audio viewing | **Not possible** — QA is programmatic; a human must watch the final file |
| Facebook | **Login-walled** (independently re-confirmed this session) |

## Phase 1–9 — Deliverable audit

All 17 required deliverables already exist and are non-empty:

research report · timeline · evidence register · verification log · 2 questionnaires ·
3 concepts + approval · final script · storyboard · UZ+RU subtitles · 2 demo MP4s ·
permission checklist · missing-info list · asset list · placeholder list.

## Demo status (requested — already rendered, NOT re-rendered)

Both demos were **re-verified with ffprobe this run**:

| File | Duration | Video | Audio | Size |
|---|---|---|---|---|
| `demo/GSP_demo_UZ.mp4` | **143.400 s** | h264 1920×1080 @30fps | aac | 100,595,184 B |
| `demo/GSP_demo_RU.mp4` | **143.377 s** | h264 1920×1080 @30fps | aac | 102,170,283 B |

**I did not re-render.** A verified demo already exists; re-rendering would overwrite
completed work without an approved change. Both are within the 2:00–2:30 requirement and
labelled DEMO / CONCEPT PREVIEW. Rebuild on request via the 5-command pipeline in
`demo/README.md`.

## Change made this run

- `interviews/README.md` — corrected a stale line: questionnaires are **already final**
  in `research/06` and `research/07` (not "to be generated"); added pointers.

## Blocked / awaiting human

1. **Interviews not yet conducted** — questionnaires ready; agent cannot contact anyone.
   Recordings go to `interviews/transcripts/`.
2. **Client decisions** (`research/12_open_questions.md`): Gulyamov founder-vs-2019
   wording; "among the first" dated evidence; former-name-on-screen; Lexpert clause;
   final sign-off + release venue.
3. **Website-claim corrections** (`research/10_fact_verification_log.md` §C, W1–W14):
   highest reputational risk if the site and film are seen together.
4. **Assets to request:** archive photos 2010–2012, new-office photos, 2024 event photos,
   real Wakil AI capture, brand fonts / light logo variant, written permissions.
5. **Music licensing** for the final cut (demo music is synthesized + labelled).

## Agent system (agent_system/) build status

- **Tests:** 172 automated tests pass (0 failures/errors/skipped), ~21.7 s. See `TEST_REPORT.md` for full breakdown (mocked-integration, unit, verification).
- **CLI:** `run-job`, `selftest`, `styles`, `health`, `check-spec`, `serve`. `--no-render` and `AGENT_NO_RENDER` disable rendering (research/script/storyboard only; no ffmpeg subprocess). `FAST_RENDER` controls low-res preview mode.
- **Telegram bot:** authorises numeric user IDs only; refuses to start without `.env` (exit 2). See `TELEGRAM_SETUP.md` for restricting access to exactly two users.
- **Verified artifacts:** `output/jobs/JYDV8WGZQ/` contains `final.mp4` (h264 960×540 @24fps, aac 2ch 48kHz, 35.79s, 1.39 MB) and `preview.mp4`; `output/jobs/JHS9M53EK/` is preview-only. All verified with `ffprobe`.
- **Known boundaries:** blender3d UNAVAILABLE (no Blender); Uzbek TTS unavailable on macOS; Facebook login-walled; files > `MAX_UPLOAD_MB` delivered by local path only. All demos/placeholders labelled as required.
