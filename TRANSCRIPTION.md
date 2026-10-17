# Local speech-to-text for interview recordings (Uzbek / Russian)

**Status: INVESTIGATION ONLY. Nothing has been installed and no command in this
document has been run.** Section 6 lists the exact commands for approval.

Purpose: choose a free, fully local engine that can turn the partner-interview
recordings into transcripts our pipeline can analyse, without a paid API, an
account, or sending a law firm's internal interviews to a third party.

---

## 1. What this machine actually is (verified by inspection)

| Fact | Value | How it was checked |
|---|---|---|
| Chip | Apple M1 | `sysctl -n machdep.cpu.brand_string` |
| Memory | 8.0 GB | `sysctl -n hw.memsize` |
| OS | macOS 27.0.1 (build 26A434) | `sw_vers` |
| Architecture | arm64 | `uname -m` |
| Python | 3.9.6 | `python3 -V` |
| ffmpeg / ffprobe | present, `/opt/homebrew/bin` | `command -v ffmpeg` |
| Homebrew | present, `/opt/homebrew/bin/brew` | `command -v brew` |
| Free disk | 37 GiB | `df -h .` |
| Installed STT engines | **none** | import probe of `vosk`, `whisper`, `faster_whisper`, `mlx_whisper`; PATH probe of `whisper-cli`, `whisper`, `main` |

8 GB is the binding constraint: it rules out the largest Whisper models and
favours the ~300–900 MB options.

## 2. Current state of our code

`python3 -m agent_system transcribe-info` reports:

```json
{"available": false, "backends": [], "ffmpeg": "/opt/homebrew/bin/ffmpeg", ...}
```

That is the honest answer: audio cannot be transcribed here right now. The
system therefore asks a human for a transcript (SRT / VTT / TXT / JSON) instead
of pretending, and never contacts a network service.

Two facts about the current code that shape the choice:

- **`transcribe_audio()` can already drive `whisper.cpp`** (`argv = [binary, "-f",
  audio, "-otxt"]`) and finds the `.txt` it writes next to the audio. It is the
  only engine that works with **zero code changes**.
- **`transcribe_audio()` has no `vosk` branch** — an installed Vosk would raise
  `TranscriptionUnavailable: engine 'vosk' has no implemented invocation`. Using
  Vosk requires a small code change (see §7).

A correction made while researching: `ENGINE_CAPABILITIES["vosk"]` previously
claimed `"uz_quality": "unsupported"` with the note *"vosk has a Russian model;
no Uzbek model"*. **That was factually wrong** — Vosk publishes a dedicated
Uzbek model. The entry has been corrected and the reason recorded in the source.
No test or document depended on the old claim.

## 3. The options, with sources

### A. Vosk — the only option with a *native* Uzbek model

Fully offline, Kaldi-based, small models designed for desktop/mobile.

| Model | Disk | Published WER | Licence |
|---|---|---|---|
| `vosk-model-small-uz-0.22` (Uzbek) | 49 MB | 13.54 (CV Test), 12.92 (IS2AI USC test) | Apache 2.0 |
| `vosk-model-small-ru-0.22` (Russian) | 45 MB | 22.71 (openstt audiobooks), 31.97 (youtube), 29.89 (sova devices), 11.79 (golos crowd) | Apache 2.0 |
| `vosk-model-ru-0.42` (Russian, big) | large | — | Apache 2.0 |

Runtime memory: Vosk states a *small* model "is around 50Mb in size and requires
about 300Mb of memory in runtime".

Packaging — **this is the trap**:

- `vosk==0.3.44` ships `vosk-0.3.44-py3-none-macosx_10_6_universal2.whl`
  (`universal2` includes arm64; `py3` means any Python 3, so 3.9.6 is fine).
- `vosk==0.3.45` (current latest) ships **Linux and Windows wheels only** — there
  is **no macOS wheel and no source distribution**. An unpinned `pip install vosk`
  therefore fails with "No matching distribution found".

So the version pin `vosk==0.3.44` is mandatory, not a preference.

Licence: Apache-2.0 for both the wheel and the models (PyPI classifier
"OSI Approved :: Apache Software License").
Sources: <https://alphacephei.com/vosk/models>,
<https://pypi.org/pypi/vosk/json>.

### B. whisper.cpp (Homebrew) — best all-round quality, zero code change

`brew info whisper-cpp` on this machine: **stable 1.9.5 (bottled)**. MIT-licensed
port of OpenAI Whisper in C/C++. Homebrew installs the `whisper-cli` binary,
which our detector already looks for.

Model sizes and runtime memory, from the project README:

| Model | Disk | Memory |
|---|---|---|
| tiny | 75 MiB | ~273 MB |
| base | 142 MiB | ~388 MB |
| small | 466 MiB | ~852 MB |
| medium | 1.5 GiB | ~2.1 GB |
| large | 2.9 GiB | ~3.9 GB |

On 8 GB, `small` is comfortable and `medium` is the practical ceiling with other
apps closed; `large` (~3.9 GB) is not advisable. Quantised models reduce both
figures. whisper.cpp expects 16 kHz mono WAV input; ffmpeg (present) handles the
conversion.
Source: <https://raw.githubusercontent.com/ggml-org/whisper.cpp/master/README.md>.

### C. openai-whisper (pip) — MIT, but pulls PyTorch

`openai-whisper` 20250625, MIT, `requires_python >=3.8`. Pulls the full PyTorch
stack (multiple GB) and is markedly slower than whisper.cpp on CPU. Not
recommended on 8 GB when a native alternative exists.
Source: <https://pypi.org/pypi/openai-whisper/json>.

### D. faster-whisper (pip) — MIT, the best Python-side speed

`faster-whisper` 1.2.1, MIT, `requires_python >=3.9` (3.9.6 satisfies it). Uses
CTranslate2, so it is faster and lighter than openai-whisper. Still a multi-GB
dependency tree, but the lightest *Python* route.
Source: <https://pypi.org/pypi/faster-whisper/json>.

### E. mlx-whisper (pip) — MIT, tuned for Apple silicon

`mlx-whisper` 0.4.3, MIT, `requires_python >=3.8`. Uses Apple's MLX framework, so
it is the fastest option on an M1. Newer and less battle-tested than whisper.cpp;
our code cannot drive it without a new branch either (the existing Python branch
calls `python3 -m <module>` with `--output_format json`, which does not match
mlx-whisper's CLI).
Source: <https://pypi.org/pypi/mlx-whisper/json>.

## 4. Comparison

| | Vosk | whisper.cpp | openai-whisper | faster-whisper | mlx-whisper |
|---|---|---|---|---|---|
| Native **Uzbek** | **yes (49 MB model)** | transfer only | transfer only | transfer only | transfer only |
| Russian | yes (good published WER) | strong | strong | strong | strong |
| Fully offline | yes | yes | yes | yes | yes |
| Licence | Apache 2.0 | MIT | MIT | MIT | MIT |
| Disk (practical) | ~49 MB + 45 MB models | ~466 MB model + binary | multi-GB (torch) | multi-GB | model + mlx |
| Runtime RAM | ~300 MB per model | ~852 MB (small) | ≥ ~1 GB+ | ~1 GB | ~1 GB |
| Fits 8 GB well | **best** | yes (small/medium) | marginal | marginal | yes |
| Works with our code today | **no — needs a branch** | **yes — zero change** | yes (branch exists) | yes (branch exists) | no (argv mismatch) |
| Install complexity | low (pin + 2 model unzips) | low (`brew install`) | high (torch) | medium | medium |

## 5. Recommendation

For Uzbek as the master language, **Vosk is the only option with a genuine
Uzbek model** rather than multilingual transfer, and its published Uzbek WER
(13.54 CV / 12.92 IS2AI) is credible for interview speech — while being by far
the lightest on an 8 GB machine (~300 MB runtime).

whisper.cpp remains valuable as a **second opinion for Russian** and because it
is the only engine that works with **no code change**, which makes it the
cheapest way to prove the audio→transcript→chronology path end to end.

Suggested order, both local and free:

1. **`brew install whisper-cpp`** + a `small` model — proves the whole pipeline
   works today with no code change, and gives a cross-check for Russian.
2. **`vosk==0.3.44`** + the Uzbek and Russian small models — gives native Uzbek,
   after a ~30-line change to `transcripts.py` (§7).

Both use ffmpeg (already present) to produce the 16 kHz mono WAV the engines want.

## 6. Exact commands — **DO NOT RUN UNTIL APPROVED**

Step 1 — whisper.cpp (no code change needed):

```bash
brew install whisper-cpp
# 466 MB; the ./models/ script is the project's own documented method
cd /tmp && git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git wcpp \
  && cd wcpp && sh ./models/download-ggml-model.sh small && ls -la models/ggml-small.bin
# convert any recording to the required format
ffmpeg -i INTERVIEW.m4a -ar 16000 -ac 1 -c:a pcm_s16le INTERVIEW.wav
```

Step 2 — Vosk (needs the code change in §7):

```bash
python3 -m pip install "vosk==0.3.44"      # the pin is required: 0.3.45 has no macOS wheel
mkdir -p models && cd models
curl -LO https://alphacephei.com/vosk/models/vosk-model-small-uz-0.22.zip
curl -LO https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip
unzip -q vosk-model-small-uz-0.22.zip && unzip -q vosk-model-small-ru-0.22.zip
du -sh vosk-model-small-uz-0.22 vosk-model-small-ru-0.22   # expect ~49M and ~45M
```

A virtualenv is preferable to a system-wide install:

```bash
python3 -m venv .venv-stt && source .venv-stt/bin/activate
python3 -m pip install --upgrade pip && python3 -m pip install "vosk==0.3.44"
```

## 7. What must change in our code, per option

- **whisper.cpp** — nothing. `detect_speech_backends()` finds `whisper-cli` and
  `transcribe_audio()` builds the right argv. This is why it is step 1.
  Caveat: `brew install whisper-cpp` puts the binary on PATH, and our probe
  already checks `whisper-cli`, so detection should succeed.
- **Vosk** — a new branch in `transcribe_audio()` plus a small adapter that maps
  Vosk's JSON (`{"result": [{"word", "start", "end"}, ...]}`) to our `Segment`
  list. Our `parse_json()` currently expects `{"segments": [...]}` or
  `{"items": [...]}`, so a direct map is needed. Roughly 30 lines and a test.
  **Not written yet — pending approval.**
- **mlx-whisper / openai-whisper / faster-whisper** — the existing branch runs
  `python3 -m <module> <audio> --output_format json`, which matches
  openai-whisper and faster-whisper but not mlx-whisper's CLI.

## 8. Language limitations (stated honestly)

- **Uzbek is low-resource.** Every Whisper-family model, including the largest,
  covers Uzbek only through multilingual transfer and is documented here as
  `uz_quality: "low"`. Vosk's dedicated model is the stronger option, but its
  published WER still implies roughly one word in eight wrong on clean test
  speech — worse on phone recordings, crosstalk and proper nouns.
- **Names, dates, legal terms and figures are the highest-risk tokens** and are
  exactly what a history film must get right. Any transcript produced by an
  engine is **UNVERIFIED** and must be checked against the audio by a human
  before it becomes evidence. The code already stamps transcripts with
  "Produced by X (unverified on this machine)" and classifies interview claims
  as `SINGLE-SOURCE`, and single-source claims can never upgrade an event to
  corroborated.
- **Russian** is much better served by all engines; Vosk's `11.79` on golos
  crowd (read speech) versus `31.97` on YouTube shows how much the recording
  conditions dominate the result.
- Voice-activity differences: Vosk needs silence conditions configured for good
  segmentation; Whisper-family models produce timestamped segments natively.

## 9. What I could NOT verify

- **No engine has been run on this machine**, so every quality number here is
  vendor-published, not measured by us. No Uzbek or Russian recording has been
  transcribed end to end.
- I did not test whether `brew install whisper-cpp` succeeds on macOS 27.0.1;
  the formula is bottled for arm64, but no install has been attempted.
- I did not measure real runtime RAM on this box; the figures are the projects'
  published numbers.
- No microphone/recording-quality assessment was possible — we have no interview
  audio yet.

## 10. Decision needed

Choose one (or both, as recommended), and I will then implement and test only
that path:

1. **whisper.cpp only** — `brew install whisper-cpp` + `small` model. Works today
   with no code change; Russian good; Uzbek weak.
2. **Vosk only** — `vosk==0.3.44` + Uzbek/Russian small models (49 MB / 45 MB).
   Native Uzbek; requires the ~30-line `transcripts.py` change first.
3. **Both (recommended)** — whisper.cpp now to prove the pipeline, then Vosk for
   native Uzbek, cross-checking the two on the same recording.

Also needed regardless of choice: **actual interview recordings**, since no
engine can be validated against the firm's real audio until they exist.
