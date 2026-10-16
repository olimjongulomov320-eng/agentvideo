# Law Firm Research & Video Script Agent — Operator Guide

This project contains a **reusable OpenCode agent** named `law-firm-researcher`.
It researches a law firm's real history (website, Facebook, supplied archives),
verifies every fact against sources, prepares interview questionnaires, and
writes a production-ready 2–2.5-minute presentation video script with storyboard,
subtitles, and (where tools allow) a rendered demo video.

It was built and tested here for **Gulyamov, Sadikov and Partners (GSP)**,
Tashkent — the completed GSP run lives in `research/`, `production/`, and `demo/`
and serves as the reference example of the agent's output quality.

## How to use it (non-technical)

1. Open this project folder in OpenCode.
2. Start the agent in one of two ways:
   - **Easiest:** type the slash command `/law-firm-run` and paste the intake
     answers (see below), or
   - **Explicit:** start a new session and say
     *"Use the law-firm-researcher agent to research <firm name> (<website URL>)"*
3. Pick a model if prompted. On this machine the default model may be rejected
   with *"This model is not available in your country."* The providers that work
   here are `openai` and `opencode`; a free option is `opencode/step-5-preview-free`
   (used for all tests — see `AGENT_TESTS.md`).
4. Answer the intake questions once. The agent will not ask again for anything
   you already provided.
5. Review deliverables as they appear in `research/`, `interviews/`,
   `assets/`, `production/`, and `demo/`.

### Intake answers to have ready

- Firm name
- Official website URL
- Facebook page URL
- Narration language(s) — which one is the master
- Event type and date (e.g. new-office opening, 20 Oct 2026)
- Archive material you can supply (photos, documents, interview recordings)
- Whether you want a rendered demo video

## What it can and cannot do on this machine

| Capability | Status |
|---|---|
| Web page fetching & search | ✅ works |
| Facebook pages | ⚠️ login-walled — agent records this honestly and uses your exports/screenshots instead |
| Video rendering (ffmpeg) | ✅ works — real MP4s can be produced |
| Frame/typography rendering (Python + Pillow) | ✅ works |
| Uzbek text rendering | ✅ works (OpenType fonts with Latin Extended) |
| Text-to-speech | ⚠️ macOS `say` has Russian (Milena) but **no Uzbek** — final Uzbek narration needs a human narrator |
| Viewing images / hearing audio | ❌ impossible for the agent — all QA is programmatic; **a human must watch the final video** |
| Licensed music | ❌ none installed — demo music is synthesized and labelled; final film needs properly licensed music |

## Safety rules the agent follows (by design)

- Never invents dates, awards, cases, quotations, or statistics; every fact in a
  deliverable cites a source URL or supplied document.
- Treats the firm's own website marketing claims as unverified claims, logs
  conflicts, and keeps unverified figures out of public-facing scripts.
- Excludes confidential/privileged client matter from public deliverables and
  maintains a permission checklist.
- Never contacts anyone, posts anywhere, or bypasses access controls.
- Labels every demo/placeholder/stock/synthesised element as DEMO / CONCEPT
  PREVIEW and never publishes anything without approval.
- Never claims a rendered video without verifying the actual file.

## Files

| File | Purpose |
|---|---|
| `.opencode/agents/law-firm-researcher.md` | The agent definition (instructions, role, workflow) |
| `.opencode/commands/law-firm-run.md` | Slash command to launch a run with intake |
| `agent-instructions.md` | Human-readable copy of the agent's operating procedure |
| `AGENT_TESTS.md` | Real tests executed against this installation, with results |
| `TEST_REPORT.md` | Python `agent_system/` test report (172 tests, automated/mocked/manual) |
| `TELEGRAM_SETUP.md` | BotFather setup, numeric user IDs, `.env`, access control (exactly two users) |
| `MAC_LAUNCH.md` | macOS commands: styles/health/run-job/selftest/serve, no-render mode |
| `VPS_DEPLOYMENT.md` | Linux VPS deployment with systemd, security, backups |
| `DELIVERY_REPORT_TEMPLATE.md` | Operator template for delivery reports |
| `interviews/` | Questionnaires and user-supplied transcripts |
| `research/`, `production/`, `demo/`, `assets/` (GSP run) | Reference deliverables from the completed GSP project |

## Running for a different firm

The agent creates `clients/<firm-slug>/` with the same subfolders so runs never
mix. Nothing from the GSP run will be overwritten.
