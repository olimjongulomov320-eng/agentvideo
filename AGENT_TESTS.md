# AGENT_TESTS.md — Law Firm Research & Video Script Agent

**Installation:** OpenCode **v2.0.26** (V2 conventions).
**Agent:** `law-firm-researcher` (`.opencode/agents/law-firm-researcher.md`), `mode: all`.
**Command:** `law-firm-run` (`.opencode/commands/law-firm-run.md`).
**Tested:** 2026-10-15 · **Method:** real command executions; results recorded verbatim.
**Test model:** `opencode/step-5-preview-free` (see Limitation L1 — default model unavailable here).

Every test below was actually run. Where a test failed first, the cause and fix are noted.

---

## 1. Configuration matches installed OpenCode version — PASS
- `opencode --version` → `v2.0.26`.
- Agent defined as a Markdown file with YAML frontmatter per the V2 agents guide
  (`description`, `mode`, `color`, `permissions` + Markdown body as `system` prompt).
- Confirmed the V2 field set is valid: `opencode debug agents` parses the file and
  reports `mode: all`, the full description, and the complete system prompt.

## 2. Agent is discoverable — PASS
- `opencode debug agents` → includes `law-firm-researcher`.
- API: `GET /api/agent?location[directory]=<project>` → `[..., "law-firm-researcher"]`.
- **Finding (not a defect):** the shared background service scopes `/api/agent` and
  `/api/command` by `location[directory]`. Querying those endpoints with **no**
  directory returns only global-scope items and omits project agents. With the project
  directory passed, both the agent and command appear. The TUI and `opencode run`
  discover them correctly regardless (proven in test 3).

## 3. Command is discoverable — PASS
- API: `GET /api/command?location[directory]=<project>` → `[..., "law-firm-run"]`.
- The command's `agent: law-firm-researcher` binding uses the same frontmatter
  convention as the pre-existing, working `impeccable` command (`agent: build`).

## 4. Agent is callable — PASS
- `opencode run --agent law-firm-researcher ...` launched the agent (header
  `> law-firm-researcher · step-5-preview-free`) and it responded in role.
- The agent inherits a model when none is pinned, and accepts an explicit `-m`.

## 5. Intake workflow — PASS
Prompt: *"A new user has only said: 'Hi, I want to make a video about my law firm.'"*
Result: the agent asked one compact intake list (firm name, website, Facebook,
narration language + master, event + date, archive material, demo yes/no) and stated
it can begin research immediately once the website/Facebook links are supplied.
It did **not** re-ask for anything already given and did **not** start fabricating.

## 6. No fabrication / gap honesty — PASS
Prompt: intake for a fictional firm "Vega Legal" with **no** website and **no** Facebook.
Result: the agent listed what it could still prepare (folder structure, intake/gap
record, generic questionnaires, concept frameworks, a script skeleton with marked
placeholders, register/log formats) and stated explicitly:
> "I will not invent Vega Legal's founding year, awards, cases, outcomes, statistics,
> or quotations. Every date, claim, and quote will be sourced or logged as a gap."

## 7. Inaccessible-source handling — PASS
Prompt: try to access `https://www.facebook.com/gsplaw.uz`.
Result: the agent used webfetch on `facebook.com` and `m.facebook.com`, reported both
returned a login/redirect wall with **no** retrievable profile, posts, dates or photos,
and asked the user for the website URL, dated screenshots/exports of older posts, and
permission status instead. **No facts were invented.** (Independently re-confirms the
Facebook login wall noted in the GSP research.)

## 8. Source extraction with citation + classification — PASS
Prompt: fetch `https://gsplaw.co.uz` and report exactly two claims, each with source
URL, evidence class, and public-use safety.
Result: the agent returned two claims, each with URL, an evidence class
("single-source self-description"; "unverified marketing statistic"), and a public-use
verdict ("Not safe without corroboration"). It flagged the site's **"16+ лет"** figure as
an unverified statistic and connected it to the "say *since 2010*, never a count" rule.
- *Note:* this prompt **timed out once** when run concurrently with another test; it
  passed when run alone with a longer timeout. Cause: parallel contentions on the
  shared free-model backend, not an agent defect.

## 9. Shell + video-verification capability — PASS
Prompt: run `ffprobe` on `demo/GSP_demo_UZ.mp4` and report the real result.
Result: the agent executed the command and reported the verified file:
duration **143.400000 s**, streams **h264 (1920×1080)** and **aac**. It did not claim a
video without checking the actual file — satisfying the "never claim a rendered video
without verifying it" rule.

## 10. Citations preserved in real deliverables — PASS
The GSP research does not use inline URLs; it uses citation keys
(`[SM-06]`, `[PB-16]`, …) mapped to real URLs in `research/01_source_inventory.md`
(e.g. SM-06 → `linkedin.com/company/gsplaw`, PB-07 → Stanford CodeX TechIndex
`techindex.law.stanford.edu/companies/wakilai`). The verification log
(`research/10_fact_verification_log.md`) cites these keys beside every claim and
classifies each as VERIFIED / CORROBORATED / SINGLE-SOURCE / UNVERIFIED / CONFLICTING.
Every claim traces to a source. (URLs are stored without the `https://` scheme, which is
why a scheme-prefixed grep returns none.)

## 11. Script timing realism — PASS
- `production/03_final_video_script.md` → **Runtime 2:26**; 8 scenes with timecodes
  (0:00→2:26) and a duration table summing to 2:26.
- `demo/build/timeline.py` → **total 143.4 s** (2:23.4), 9 scene blocks with
  in/out times; scene durations sum to 146 s minus crossfade overlaps.
- Both runtimes fall inside the required **2:00–2:30** and are internally consistent.

## 12. Environment capabilities (Phase 0) — VERIFIED
| Capability | Result |
|---|---|
| ffmpeg | 8.1.2 (`/opt/homebrew/bin/ffmpeg`) |
| ffprobe | present |
| python3 | 3.9.6 |
| Pillow | 11.2.1 |
| macOS `say` | Russian **Milena** only — **no Uzbek** voice |
| Georgia font | present (Regular/Bold/Italic) |
| curl | present |
| Browser automation | **Not available** — the `browser` action is set to `deny`; the agent has no browser tool and does not claim one. |

---

## Capabilities that need external tools/integrations (documented limitations)

- **Facebook post-level research:** blocked by a login wall in this environment. The
  agent records the block and requests user-supplied exports/screenshots. It will not
  bypass access controls or ask for credentials/cookies.
- **Uzbek text-to-speech:** no Uzbek `say` voice exists here. The UZ cut has no voice;
  final Uzbek narration needs a human narrator (RU TTS via Milena is available as a
  temporary stand-in only).
- **Licensed music:** none installed. Demo music is synthesized and labelled; a finished
  film needs properly licensed music.
- **Image/audio viewing:** the agent cannot see images or hear audio. All media QA is
  programmatic; **a human must watch the final video** before any external use.
- **Model availability:** the environment's default model was rejected with
  "This model is not available in your country." Available providers here are `openai`
  and `opencode`; tests used `-m opencode/step-5-preview-free`. Select an available
  model before running the agent interactively.

## Safety permissions enforced by configuration (defense-in-depth)
In addition to instruction-level rules, these are hard-enforced:
`browser *` → **deny**; `git push *`, `npm publish *`, `gh release create *`,
`gh issue create *`, `gh pr create *` → **deny**; outbound `curl -X POST`/`curl -d`/
`wget --post-data` → **ask**. These block the most likely ways research material could
leave the project or a demo could be published accidentally. Merging with the base
rules was verified: base `allow` remains, and the new deny/ask rules append after it
(14 total rules on the agent).

## How to re-run these tests
```sh
cd "<project>"
opencode debug agents | grep law-firm-researcher
opencode api get "/api/command?location[directory]=$PWD"
opencode run --agent law-firm-researcher -m opencode/step-5-preview-free "<prompt from any test>"
```

## Python test suite (agent_system)

The `agent_system/` package (pipeline, Telegram bot, renderer, research/story) passes **172 tests** (**0 failures, 0 errors, 0 skipped**, ~21.7 s):
- Per-module: config_security 17, jobs 18, orchestrator 13, parsing 16, render 14, research 16, spec_backends 15, story 17, telegrambot 30, integration 16.
- Mocked integration (`tests/test_integration.py`) validates authorised/unauthorised, dedupe, malformed/unavailable-style handling, lifecycle, mocked render, render failure with redaction, cancellation consistency, and **no-render mode** (research/script/storyboard only; no renderer started).
- Commands:
```sh
cd "<project>"
python3 -W ignore::ResourceWarning -m unittest discover -s tests -t . -v
python3 -m agent_system selftest
python3 -m agent_system styles
python3 -m agent_system health
```
- Evidence (ffprobe verified): `output/jobs/JYDV8WGZQ/` has `final.mp4` (h264 960×540 @24fps, aac 2ch 48kHz, 35.79 s) and `preview.mp4`; no-render honours `--no-render` and `AGENT_NO_RENDER=1`. See `TEST_REPORT.md`, `MAC_LAUNCH.md`, `TELEGRAM_SETUP.md`, `VPS_DEPLOYMENT.md`.
