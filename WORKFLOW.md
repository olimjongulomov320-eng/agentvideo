# WORKFLOW.md — the staged documentary workflow

This describes the staged workflow used to reconstruct a firm's real history and
produce a 2–2.5-minute corporate history film. It records **what is implemented in
code, what is document-only, and what still needs a human**. Nothing here invents
history: where a fact is unknown, the system records a gap.

> **Scope note.** The GSP Law Firm deliverables already in `research/`,
> `production/`, `demo/` and `.opencode/` are finished human-reviewed work. They
> are treated as read-only inputs. The code below *generalises* those stages so a
> fresh run (or a fresh firm) can produce them, and never silently replaces them.

---

## 1. The seven stages

| Stage | Purpose | Where it lives | Status |
|-------|---------|----------------|--------|
| **A. Access & inventory** | Identify public sources, authorized files, recordings; record what is inaccessible | `agent_system/research.py` (`Source`, source states) | Implemented |
| **B. Research & evidence** | Collect dated evidence; keep an evidence ledger with classes, confidence, contradictions, privacy flags | `agent_system/research.py` (`Claim`, `ledger_csv`, `report_markdown`) | Implemented |
| **C. Interview preparation** | Per-role questionnaires driven by the evidence gaps, each with what it closes and what would corroborate it | `agent_system/interviews.py` | Implemented |
| **D. Transcription & interview analysis** | Turn a recording or supplied transcript into attributed, timestamped statements | `agent_system/transcripts.py` | Implemented (analysis); see transcription limits below |
| **E. Chronology & story selection** | Cited, confidence-labelled timeline; documented history separated from interpretation | `agent_system/chronology.py` | Implemented |
| **F. Human review & approval gates** | Stop before the script; permission checklist; confidentiality quarantine | `agent_system/orchestrator.py` (approval callback) + `permission_checklist_*.md` | Implemented (approval gate already existed; checklist added) |
| **G. Final script & production** | Script, storyboard, subtitles, render | `agent_system/story.py`, `agent_system/video/` | Pre-existing |

---

## 2. Evidence discipline (why the outputs can be trusted)

These rules are enforced in code, and covered by regression tests.

- **Evidence classes.** `VERIFIED` · `CORROBORATED` · `SINGLE-SOURCE` ·
  `UNVERIFIED` · `CONFLICTING` · `UNAVAILABLE`.
- **A quotation proves the statement, not the fact.** Every statement extracted
  from an interview is `SINGLE-SOURCE`, `safe_for_public=False`,
  `quoted_ok=False`, and marked `publication-review`. Nothing is auto-promoted.
- **The firm's own marketing is a claim.** Case figures, win rates, "1000+
  clients" and awards taken from the firm's own site are `SINGLE-SOURCE` at best
  and are never promoted into the film as fact.
- **Corroboration requires independent publishers.** Two pages on the same
  website are one publisher and cannot corroborate each other. An `UNVERIFIED`
  claim never corroborates a `VERIFIED` one.
- **A year appears only if a source states it.** Years are read from the claim
  text; they are never inferred from context, page order or a copyright line.
- **Undated material is kept.** It goes into a separate section rather than being
  dated by guesswork.
- **Nothing is invented.** Inaudible speech is recorded as a gap and never
  filled in; missing dialogue is never reconstructed.

---

## 3. Running the stages

Requirements: Python 3.9+, `ffmpeg`/`ffprobe` on `PATH`. No paid API, no API key,
no external account, and no network call is required by any command below.

```bash
# A/B — research a firm (writes research_report.md + evidence_ledger.csv)
python3 -m agent_system run-job --firm "Firm Name" --website https://example.uz --no-render

# D — check honestly whether this machine can transcribe audio
python3 -m agent_system transcribe-info

# D — analyse a transcript the human supplied (SRT / VTT / TXT / JSON)
python3 -m agent_system analyse-interview path/to/interview.srt --language uz --out interviews/analysis

# C — build per-role questionnaires from the evidence gaps
python3 -m agent_system interview-plans --firm "Firm Name" \
    --ledger output/jobs/<JOB>/evidence_ledger.csv --out interviews

# E — build a cited chronology from the saved ledger
python3 -m agent_system chronology output/jobs/<JOB>/evidence_ledger.csv --firm "Firm Name"
```

`interview-plans` **refuses to overwrite an existing questionnaire** unless
`--force` is passed, so a reviewed plan cannot be replaced by a generated one.

### Evidence-ledger columns

`claim_id, claim, evidence_class, safe_for_public, source_id, source_url,
page_title, relevance, needs, excerpt, source_date, event_date, confidence,
contradiction, privacy_review`

An empty cell means **"not established"**, never "assumed". Older ledgers without
the newer columns still load.

---

## 4. Interview procedure (human-in-the-loop)

The agent **never contacts anybody**. It does not send messages, make calls, or
post anything.

1. `interview-plans` writes `questionnaires…​.md` into `interviews/`.
2. **A human conducts the interview** and records it (or takes notes).
3. The human supplies the recording or transcript to `interviews/transcripts/`.
4. If a local speech-to-text engine is installed, it can be run locally. If not,
   `transcribe-info` says so plainly and the transcript is supplied by hand.
5. `analyse-interview` produces:
   - `interview_findings_<name>.md` — attributed statements, the question that
     prompted each, items needing verification, confidentiality flags, gaps;
   - `permission_checklist_<name>.md` — the sign-off a human must complete before
     anything is quoted;
   - `interview_analysis_<name>.json` — machine-readable equivalent.

### Transcription capability — honest status

Detection is real, not assumed. Run `transcribe-info` to see the truth for the
machine in front of you. On the machine used for this run:

- **No local speech-to-text engine is installed** (no whisper.cpp binary, no
  `openai-whisper`, `faster-whisper`, `mlx-whisper` or `vosk`). Audio therefore
  **cannot** be transcribed here; the module says so and returns a non-zero exit
  code rather than pretending.
- Each engine it *would* use is listed in `ENGINE_CAPABILITIES`, and every entry
  is marked `verified: False` because none has been exercised end to end here.
- **Uzbek is a known weak point** of every whisper-family model (low-resource
  language): expect errors in names, dates and legal terms. The text must be
  verified against the audio by a speaker of the language before it is quoted.
- Free options if you choose to install one: `whisper.cpp` (binary + GGML model),
  or `pip install faster-whisper`. No paid service is used by this project.

The analysis half does not depend on any of this: it works on a human-supplied
SRT, VTT, plain-text or JSON transcript, preserving timestamps and marking
uncertain names and dates for correction.

---

## 5. Privacy, permissions and confidentiality

- **Quotation is not granted by being interviewed.** Consent to record and
  consent to quote are separate, statement-by-statement, and recorded in the
  permission checklist.
- **Confidentiality markers quarantine statements.** Words such as
  "confidential", "off the record", "privileged", "attorney-client", or a mention
  of a client, flag the statement for review; it stays out of the film until a
  human clears it.
- **Client-identifying and privileged matter is excluded** from public-facing
  deliverables unless separately authorised in writing.
- An archive item is **not** publication-approved merely because it exists.
- No secrets are written to source, logs, reports or videos. `.env` is ignored by
  Git and never committed.

---

## 6. Testing

```bash
python3 -W ignore::ResourceWarning -m unittest discover -s tests -t .
```

Current result on this machine: **335 tests — OK** (~28 s). The build added 53
regression tests in `tests/test_workflow_stages.py` covering:

- transcript parsing (SRT/VTT/TXT/JSON), timestamps, speaker linking;
- inaudible speech preserved as a gap and never invented;
- questions never stored as statements;
- every extracted statement staying `SINGLE-SOURCE` / not public;
- hedges, privacy markers, names and dates flagged for human correction;
- interview plans covering every gap exactly once, each with a corroboration path;
- a finished questionnaire never being overwritten;
- an unverified claim never corroborating a verified one;
- one website never corroborating itself;
- undated evidence kept, conflicting years reported rather than averaged;
- ledger round-tripping, including older ledgers without the new columns.

`test_config_security.py` expects no `.env` in the working tree: move it aside
(**never delete it**), run the suite, then move it back.

---

## 7. Sample workflow (synthetic test data only)

The stages were exercised end to end with synthetic fixtures — a fictional
"Acme Legal LLP" ledger, a fabricated interview transcript, and invented gap
names. **No GSP Law Firm history was invented to make a demo look complete.**
The sample proves the rules hold; it is not evidence about any real firm.

---

## 8. What remains unavailable / needs a human

- **No local speech-to-text engine** on this machine — install one or supply
  transcripts.
- **No real interviews yet.** The agent prepares questions; a human must conduct
  the interviews and supply the recordings or transcripts.
- **Nothing about the firm is `VERIFIED` until corroborated** by an independent,
  preferably dated, source.
- **Quotation permission and confidentiality clearance** can only be given by the
  interviewee and the firm.
- **Human visual review of any video** is still required: this environment cannot
  view frames, so render QA is programmatic only.
- The film must not be produced while critical historical questions remain open.
