# -*- coding: utf-8 -*-
"""transcripts.py — interview transcription and analysis (workflow stage D).

This module turns interview recordings or human-supplied transcripts into
timestamped, *attributed* evidence for the documentary workflow.

Two rules are inherited from the project's anti-fabrication policy and are
enforced here rather than merely documented:

1.  **The agent never invents dialogue.** If a passage is inaudible, or no
    transcript was supplied at all, the gap is recorded as a gap. Nothing is
    reconstructed, smoothed over, or "corrected" from guesswork.
2.  **A quotation is evidence that the speaker said it — not that it is true.**
    Interview statements are attributed to a speaker and default to
    ``SINGLE_SOURCE`` with ``safe_for_public=False``, until (a) the speaker
    grants permission to quote it and (b) any historical fact inside it is
    corroborated by another source.

Transcription is done by a **local** engine when one is installed (whisper.cpp,
openai-whisper, faster-whisper, mlx-whisper or vosk). No paid API is contacted,
and no network call is made. When no engine is installed the module states that
plainly; the workflow then continues with a transcript the user supplies as
SRT / VTT / plain text / JSON, which is the realistic path for this project.

Nothing in this module writes outside the directory it is given.
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------- constants
KIND_SRT = "srt"
KIND_VTT = "vtt"
KIND_TXT = "txt"
KIND_JSON = "json"
TRANSCRIPT_KINDS = (KIND_SRT, KIND_VTT, KIND_TXT, KIND_JSON)

LANG_EN = "en"
LANG_RU = "ru"
LANG_UZ = "uz"
KNOWN_LANGS = (LANG_EN, LANG_RU, LANG_UZ)

# engine id -> the languages that engine can realistically handle today.
# `verified` is False for every entry: no engine is installed on this machine,
# so nothing here has been exercised end-to-end. Callers must not present an
# unverified engine as working.
ENGINE_CAPABILITIES: Dict[str, Dict[str, Any]] = {
    "whisper.cpp": {"langs": ("en", "ru", "uz"), "uz_quality": "low",
                    "note": "whisper.cpp `main`/`whisper-cli` binary + a GGML model"},
    "openai-whisper": {"langs": ("en", "ru", "uz"), "uz_quality": "low",
                       "note": "pip install openai-whisper (pulls torch)"},
    "faster-whisper": {"langs": ("en", "ru", "uz"), "uz_quality": "low",
                       "note": "pip install faster-whisper (CTranslate2)"},
    "mlx-whisper": {"langs": ("en", "ru", "uz"), "uz_quality": "low",
                    "note": "pip install mlx-whisper (Apple silicon)"},
    # Corrected 2026-10-17: this entry previously read {"langs": ("ru",),
    # "uz_quality": "unsupported", "note": "vosk has a Russian model; no Uzbek
    # model"}, which is false. Vosk publishes a dedicated Uzbek model
    # (vosk-model-small-uz-0.22, 49 MB, Apache-2.0) with a vendor-reported WER of
    # 13.54 (CV) / 12.92 (IS2AI USC), sourced from
    # https://alphacephei.com/vosk/models. Vosk is therefore the only
    # whisper-alternative here with *native* Uzbek support rather than
    # multilingual transfer.
    #
    # Two caveats are recorded here rather than hidden:
    #   * the figures are vendor-published and have NOT been verified on this
    #     machine (no engine is installed);
    #   * transcribe_audio() has no vosk invocation branch yet, so an installed
    #     vosk still fails loudly with "no implemented invocation".
    "vosk": {"langs": ("en", "ru", "uz"), "uz_quality": "medium",
             "note": "Kaldi-based, fully offline; model is a separate download. "
                     "Uzbek: vosk-model-small-uz-0.22 (49 MB, Apache-2.0, "
                     "vendor WER 13.54 CV / 12.92 IS2AI). Needs 16 kHz mono WAV "
                     "input; pin 'vosk==0.3.44' (0.3.45 ships no macOS wheel)."},
}

# Hedges and recollection markers. A sentence containing one of these is a
# *recollection*, not a record, and is flagged for the human to pin down.
UNCERTAINTY_MARKERS = (
    # English
    "i think", "i believe", "maybe", "perhaps", "possibly", "probably",
    "not sure", "not certain", "if i remember", "if i recall", "as far as i remember",
    "around", "roughly", "approximately", "circa", "something like", "about ",
    "i guess", "sort of", "kind of",
    # Russian
    "наверное", "кажется", "не помню", "не уверен", "примерно", "где-то",
    "возможно", "по-моему", "вроде", "около ", "приблизительно",
    # Uzbek
    "balki", "ehtimol", "esimda yo'q", "esimda yoq", "taxminan", "chamasi",
    "bilmayman", "yaxshi eslay olmayman", "o'ylaymanki",
)

# Markers a transcriber inserts when audio could not be understood. These are
# *preserved verbatim* and never replaced with guessed words.
INAUDIBLE_MARKERS = (
    "[inaudible]", "[unclear]", "[crosstalk]", "[noise]", "[silence]",
    "(inaudible)", "(unclear)", "[?]", "(?)", "[indistinct]",
    "неразборчиво", "не слышно", "непонятно", "eshitilmadi", "tushunarsiz",
)

# Confidentiality / privilege language. A sentence matching one of these, or
# mentioning a client, is quarantined from public-facing output until a human
# clears it.
PRIVACY_MARKERS = (
    "privileged", "attorney-client", "attorney client", "legal privilege",
    "off the record", "off-the-record", "confidential", "without prejudice",
    "under nda", "nda", "settlement", "не под запись", "конфиденциальн",
    "адвокатск", "тайна", "sir", "maxfiy", "oshkor qilmaslik",
)

CLIENT_MARKERS = ("client", "клиент", "mijoz", "заказчик", "buyurtmachi")

# Capitalised multi-word runs are usually proper nouns: a person, a company or
# a place. They are *flagged for spelling verification*, never auto-corrected.
_PROPER_NOUN = re.compile(r"\b([A-ZÀ-Þ][a-zà-þ'’\-]{1,}(?:\s+(?:[A-ZÀ-Þ][a-zà-þ'’\-]{1,}|de|van|von|bin|al)){1,3})\b")

# Dates and durations people misremember.
_YEAR = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
_DMY = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b")
_MONTH_DATE = re.compile(
    r"\b(\d{1,2}\s+)?(january|february|march|april|may|june|july|august|september|"
    r"october|november|december|январ\w*|феврал\w*|март\w*|апрел\w*|ма[йя]\w*|"
    r"июн\w*|июл\w*|август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)"
    r"(?:\s+\d{1,2})?(?:\s+\d{4})?\b", re.I)
_NUMERIC_CLAIM = re.compile(r"\b\d[\d\s.,]*\s*(?:\+|%|million|млн|mln|billion|млрд|"
                            r"thousand|тыс|ming)?\b", re.I)

_SENT_SPLIT = re.compile(r"(?<=[.!?…])\s+")
_TIMESTAMP_LINE = re.compile(
    r"^\s*(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})\s*-->\s*"
    r"(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})")
_SPEAKER_PREFIX = re.compile(r"^\s*(?:\[([^\]]{1,40})\]|([A-ZА-Я][^:：]{0,38}))\s*[:：]\s*(.*)$")
_SRT_INDEX = re.compile(r"^\s*\d+\s*$")


class TranscriptionUnavailable(RuntimeError):
    """Raised when a recording cannot be transcribed with the tools present."""


class TranscriptError(ValueError):
    """Raised when a supplied transcript cannot be parsed."""


# ---------------------------------------------------------------- dataclasses
@dataclass
class Segment:
    """One timed (or untimed) block of speech."""
    index: int
    start: float = 0.0
    end: float = 0.0
    speaker: str = ""
    text: str = ""
    # Set when the transcriber could not make out the words. Such a segment is
    # never treated as content.
    inaudible: bool = False

    @property
    def timed(self) -> bool:
        return self.end > 0.0 or self.start > 0.0

    def stamp(self) -> str:
        """Human-readable timecode, or '' when the transcript carries no timing."""
        if not self.timed:
            return ""
        return "%s–%s" % (_fmt(self.start), _fmt(self.end))

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Transcript:
    """A parsed interview transcript with its provenance."""
    kind: str
    language: str = ""
    source_path: str = ""
    # "human" for a transcript the user supplied, or the engine name.
    produced_by: str = "human"
    segments: List[Segment] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "language": self.language,
            "source_path": self.source_path,
            "produced_by": self.produced_by,
            "segment_count": len(self.segments),
            "segments": [s.as_dict() for s in self.segments],
            "notes": list(self.notes),
        }


@dataclass
class InterviewClaim:
    """A statement a named person made. Speech is evidence of the *statement*.

    It is deliberately not evidence that the statement is historically true, so
    every claim starts as ``SINGLE_SOURCE`` and not cleared for publication.
    """
    id: str
    text: str
    speaker: str = ""
    timestamp: str = ""
    start: float = 0.0
    end: float = 0.0
    # The question that immediately preceded this answer, when a different
    # speaker asked it. Keeps the answer interpretable.
    preceded_by: str = ""
    evidence_class: str = "SINGLE-SOURCE"
    attributed_to: str = ""
    # Hedges found in the sentence ("I think", "примерно", "taxminan").
    uncertainty: List[str] = field(default_factory=list)
    # Things a human must check: spellings, dates, numbers.
    needs_confirmation: List[str] = field(default_factory=list)
    privacy_flags: List[str] = field(default_factory=list)
    quoted_ok: bool = False          # permission to quote, granted by the speaker
    safe_for_public: bool = False    # stays False until a human clears it
    review_required: str = "publication-review"

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InterviewAnalysis:
    """Everything derived from one transcript, with the gaps made explicit."""
    source_name: str
    language: str = ""
    produced_by: str = "human"
    claims: List[InterviewClaim] = field(default_factory=list)
    # Questions are context, not evidence: they are never quoted as statements.
    questions: List[Dict[str, Any]] = field(default_factory=list)
    inaudible_segments: List[int] = field(default_factory=list)
    speakers: List[str] = field(default_factory=list)
    flagged_terms: Dict[str, List[str]] = field(default_factory=dict)
    privacy_flags: List[str] = field(default_factory=list)
    gaps: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def quotable(self) -> List[InterviewClaim]:
        return [c for c in self.claims if c.quoted_ok and c.safe_for_public]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "language": self.language,
            "produced_by": self.produced_by,
            "speakers": list(self.speakers),
            "claim_count": len(self.claims),
            "question_count": len(self.questions),
            "questions": [dict(q) for q in self.questions],
            "inaudible_segments": list(self.inaudible_segments),
            "flagged_terms": {k: list(v) for k, v in self.flagged_terms.items()},
            "privacy_flags": list(self.privacy_flags),
            "gaps": list(self.gaps),
            "notes": list(self.notes),
            "claims": [c.as_dict() for c in self.claims],
        }


# ---------------------------------------------------------------- helpers
def _fmt(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(int(m), 60)
    if h:
        return "%d:%02d:%02d" % (h, m, int(s))
    return "%02d:%02d" % (m, int(s))


def parse_timestamp(value: str) -> float:
    """'00:01:02,500' / '01:02.5' -> seconds. Raises TranscriptError."""
    v = (value or "").strip().replace(",", ".")
    if not v:
        raise TranscriptError("empty timestamp")
    parts = v.split(":")
    if len(parts) > 3:
        raise TranscriptError("bad timestamp %r" % value)
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        raise TranscriptError("bad timestamp %r" % value)
    while len(nums) < 3:
        nums.insert(0, 0.0)
    return nums[0] * 3600.0 + nums[1] * 60.0 + nums[2]


def is_inaudible(text: str) -> bool:
    low = (text or "").lower()
    if any(m in low for m in INAUDIBLE_MARKERS):
        return True
    stripped = re.sub(r"[\s.…\-–—,?()\[\]]+", "", low)
    return stripped == ""


def find_uncertainty(text: str) -> List[str]:
    low = (text or "").lower()
    return sorted({m.strip() for m in UNCERTAINTY_MARKERS if m in low})


def find_privacy_flags(text: str) -> List[str]:
    low = (text or "").lower()
    flags = {m for m in PRIVACY_MARKERS if m in low}
    if any(m in low for m in CLIENT_MARKERS):
        flags.add("client-mention")
    return sorted(flags)


def find_flagged_terms(text: str) -> Dict[str, List[str]]:
    """Items a human must verify: dates, numbers, proper-noun spellings."""
    out: Dict[str, List[str]] = {}
    years = _YEAR.findall(text or "")
    if years:
        out["years"] = sorted(set(years))
    dmy = ["%s.%s.%s" % t for t in _DMY.findall(text or "")]
    if dmy:
        out["dates"] = sorted(set(dmy))
    months = [m.group(0).strip() for m in _MONTH_DATE.finditer(text or "")]
    if months:
        out["dates"] = sorted(set(out.get("dates", []) + months))
    nums = [n.strip().strip(",.;:") for n in _NUMERIC_CLAIM.findall(text or "")]
    nums = [n for n in nums if n and n not in years]
    if nums:
        # dedupe while keeping the order they were spoken in
        seen: List[str] = []
        for n in nums:
            if n not in seen:
                seen.append(n)
        out["numbers"] = seen
    names = [n.strip() for n in _PROPER_NOUN.findall(text or "")]
    if names:
        out["proper_nouns"] = sorted(set(names))
    return out


# ---------------------------------------------------------------- STT detection
def _has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def detect_speech_backends() -> Dict[str, Any]:
    """Report *honestly* which local transcription engines exist here.

    Only the local filesystem and the Python import path are inspected: no
    network probe, no account, no key. ``available`` is False when nothing can
    transcribe audio, which is the correct answer on a machine with no engine —
    the caller must then ask a human for a transcript rather than pretend.
    """
    found: List[Dict[str, Any]] = []

    for binary, engine in (("whisper-cli", "whisper.cpp"), ("whisper", "whisper.cpp"),
                           ("main", "whisper.cpp")):
        path = shutil.which(binary)
        if path:
            found.append({"engine": engine, "binary": binary, "path": path,
                          "verified": False, "capabilities": ENGINE_CAPABILITIES[engine]})
            break

    for module, engine in (("faster_whisper", "faster-whisper"),
                           ("mlx_whisper", "mlx-whisper"),
                           ("whisper", "openai-whisper"),
                           ("vosk", "vosk")):
        if _has_module(module):
            caps = ENGINE_CAPABILITIES[engine]
            found.append({"engine": engine, "module": module, "verified": False,
                          "capabilities": caps})

    ffmpeg = shutil.which("ffmpeg")
    notes: List[str] = []
    if not found:
        notes.append(
            "No local speech-to-text engine is installed, so audio cannot be "
            "transcribed on this machine. Supply the interview as a transcript "
            "(SRT, VTT, plain text or JSON) and it will be analysed directly.")
        notes.append(
            "Free local options, if you choose to install one: whisper.cpp "
            "(binary + GGML model), or `pip install faster-whisper` / "
            "`openai-whisper`. No paid service is used by this project.")
    if not ffmpeg:
        notes.append("ffmpeg is not on PATH; audio conversion and duration "
                     "probing are unavailable.")
    notes.append(
        "Uzbek accuracy is a known limitation of every whisper-family model "
        "(low-resource language): expect errors in names, dates and legal "
        "terms, and verify them against the audio before quoting.")
    return {
        "available": bool(found),
        "backends": found,
        "ffmpeg": ffmpeg or "",
        "notes": notes,
    }


def transcribe_audio(audio_path: str, language: str = "",
                     backend: Optional[str] = None,
                     runner: Optional[Callable[[List[str]], Any]] = None) -> Transcript:
    """Transcribe with a **local** engine, or fail loudly.

    Raises :class:`TranscriptionUnavailable` when no local engine is present.
    Never falls back to a network service, and never returns invented text.

    ``runner`` exists so the command construction can be tested without a real
    engine installed; it receives the argv list and must return an object with
    ``returncode`` and ``stdout``.
    """
    info = detect_speech_backends()
    if not info["available"]:
        raise TranscriptionUnavailable(
            "no local speech-to-text engine is installed\n" + "\n".join(info["notes"]))

    chosen = None
    for b in info["backends"]:
        if backend is None or b["engine"] == backend:
            chosen = b
            break
    if chosen is None:
        raise TranscriptionUnavailable("backend %r is not available" % backend)

    if not os.path.exists(audio_path):
        raise TranscriptError("audio file not found: %s" % audio_path)

    argv: List[str] = []
    if chosen["engine"] == "whisper.cpp":
        argv = [chosen["path"], "-f", audio_path, "-otxt"]
        if language:
            argv += ["-l", language]
    elif chosen["engine"] in ("openai-whisper", "faster-whisper", "mlx-whisper"):
        argv = ["python3", "-m", chosen["module"].replace("_", "-"),
                audio_path, "--output_format", "json"]
        if language:
            argv += ["--language", language]
    else:
        raise TranscriptionUnavailable(
            "engine %r has no implemented invocation" % chosen["engine"])

    run = runner or (lambda a: subprocess.run(a, capture_output=True, text=True))
    proc = run(argv)
    if getattr(proc, "returncode", 1) != 0:
        raise TranscriptionUnavailable(
            "%s failed (exit %s): %s" % (chosen["engine"], proc.returncode,
                                         (getattr(proc, "stderr", "") or "")[:400]))

    out_dir = os.path.dirname(os.path.abspath(audio_path))
    produced = _find_transcript_output(out_dir, audio_path)
    if produced is None:
        raise TranscriptionUnavailable(
            "%s exited cleanly but produced no transcript file next to %s"
            % (chosen["engine"], audio_path))
    tr = load_transcript(produced, language=language)
    tr.produced_by = chosen["engine"]
    tr.notes.append("Produced by %s (unverified on this machine)." % chosen["engine"])
    return tr


def _find_transcript_output(directory: str, audio_path: str) -> Optional[str]:
    stem = os.path.splitext(os.path.basename(audio_path))[0]
    for ext in (".json", ".srt", ".vtt", ".txt"):
        cand = os.path.join(directory, stem + ext)
        if os.path.exists(cand):
            return cand
    return None


# ---------------------------------------------------------------- parsing
def parse_srt(text: str) -> List[Segment]:
    blocks = re.split(r"\r?\n\s*\r?\n", (text or "").strip())
    segments: List[Segment] = []
    idx = 0
    for block in blocks:
        lines = [ln for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        if _SRT_INDEX.match(lines[0]):
            lines = lines[1:]
        if not lines:
            continue
        m = _TIMESTAMP_LINE.match(lines[0])
        if not m:
            continue
        start, end = parse_timestamp(m.group(1)), parse_timestamp(m.group(2))
        body = "\n".join(lines[1:]).strip()
        speaker, spoken = _split_speaker(body)
        idx += 1
        segments.append(Segment(index=idx, start=start, end=end, speaker=speaker,
                                text=spoken, inaudible=is_inaudible(spoken)))
    return segments


def parse_vtt(text: str) -> List[Segment]:
    body = re.sub(r"^\ufeff?WEBVTT[^\n]*\n", "", (text or ""), flags=re.I)
    body = re.sub(r"^\s*(NOTE|STYLE|REGION)[^\n]*(\n(?![ \t]*\n).*)*\n", "",
                  body, flags=re.I | re.M)
    return parse_srt(body)


def parse_json(text: str) -> List[Segment]:
    try:
        data = json.loads(text or "{}")
    except ValueError as exc:
        raise TranscriptError("transcript JSON is not valid JSON: %s" % exc)
    raw: Any = data.get("segments") if isinstance(data, dict) else data
    if raw is None and isinstance(data, dict):
        raw = data.get("items")
    if not isinstance(raw, list):
        raise TranscriptError("transcript JSON has no 'segments' list")
    segments: List[Segment] = []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue
        spoken = str(item.get("text", "") or "").strip()
        segments.append(Segment(
            index=i,
            start=float(item.get("start", 0) or 0),
            end=float(item.get("end", 0) or 0),
            speaker=str(item.get("speaker", "") or ""),
            text=spoken,
            inaudible=is_inaudible(spoken)))
    return segments


def parse_txt(text: str) -> List[Segment]:
    """Plain text: no timing exists, so none is invented.

    A leading ``Name:`` or ``[Name]`` becomes the speaker; everything else is
    kept as a single untimed segment.
    """
    segments: List[Segment] = []
    idx = 0
    for block in re.split(r"\r?\n\s*\r?\n", (text or "").strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue
        speaker, spoken = _split_speaker("\n".join(lines))
        idx += 1
        segments.append(Segment(index=idx, speaker=speaker, text=spoken,
                                inaudible=is_inaudible(spoken)))
    if len(segments) == 1 and "\n" not in (text or ""):
        # a bare one-liner: split into sentences so it can still be analysed
        spoken = segments[0].text
        parts = [p.strip() for p in _SENT_SPLIT.split(spoken) if p.strip()]
        if len(parts) > 1:
            segments = [Segment(index=i + 1, text=p, inaudible=is_inaudible(p))
                        for i, p in enumerate(parts)]
    return segments


def _split_speaker(body: str) -> Tuple[str, str]:
    m = _SPEAKER_PREFIX.match(body or "")
    if not m:
        return "", (body or "").strip()
    bracketed, bare, rest = m.group(1), m.group(2), m.group(3)
    name = (bracketed or bare or "").strip()
    # A bare prefix is only a speaker when it is short and name-like; otherwise
    # "In 2010: we began" would be mistaken for a speaker called "In 2010".
    if bracketed is None:
        if not name or len(name) > 40 or re.search(r"\d", name) or len(name.split()) > 4:
            return "", (body or "").strip()
    return name, (rest or "").strip()


def load_transcript(path: str, language: str = "",
                    produced_by: str = "human") -> Transcript:
    """Load SRT / VTT / TXT / JSON. The extension decides the parser."""
    if not os.path.exists(path):
        raise TranscriptError("transcript not found: %s" % path)
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    kind = ext if ext in TRANSCRIPT_KINDS else KIND_TXT
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        raw = fh.read()
    if kind == KIND_SRT:
        segments = parse_srt(raw)
    elif kind == KIND_VTT:
        segments = parse_vtt(raw)
    elif kind == KIND_JSON:
        segments = parse_json(raw)
    else:
        segments = parse_txt(raw)
    if not segments:
        raise TranscriptError("no speech segments found in %s" % path)
    tr = Transcript(kind=kind, language=language or "", source_path=path,
                    produced_by=produced_by, segments=segments)
    if not any(s.timed for s in segments):
        tr.notes.append("This transcript carries no timestamps; quotations from "
                        "it cannot be located in the recording.")
    missing = sum(1 for s in segments if s.inaudible)
    if missing:
        tr.notes.append("%d of %d segments are marked inaudible or empty; they "
                        "are recorded as gaps and were not guessed at."
                        % (missing, len(segments)))
    return tr


# ---------------------------------------------------------------- analysis
def _sentences(seg: Segment) -> List[str]:
    """Split one segment into sentences, preserving order and wording."""
    text = (seg.text or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(text) if p.strip()]
    return parts or [text]


def analyse_transcript(transcript: Transcript, min_words: int = 4) -> InterviewAnalysis:
    """Turn a transcript into attributed, timestamped, reviewable claims.

    Sentences too short to carry meaning, and segments marked inaudible, are
    recorded as gaps rather than promoted into evidence.
    """
    analysis = InterviewAnalysis(
        source_name=os.path.basename(transcript.source_path) or "supplied transcript",
        language=transcript.language,
        produced_by=transcript.produced_by)
    analysis.notes.extend(transcript.notes)

    speakers: List[str] = []
    flagged: Dict[str, List[str]] = {}
    privacy: List[str] = []
    counter = 0
    question_counter = 0
    # Claim ids are scoped to the source file. Without this, every transcript
    # numbers its statements from "iq01", so two interviews would share claim
    # ids and the chronology would read as one source contradicting itself when
    # it is really two people disagreeing.
    id_stem = re.sub(r"[^A-Za-z0-9._-]+", "_",
                     os.path.splitext(analysis.source_name)[0]) or "interview"
    prev_speaker = ""
    prev_text = ""

    for seg in transcript.segments:
        if seg.speaker and seg.speaker not in speakers:
            speakers.append(seg.speaker)
        if seg.inaudible:
            analysis.inaudible_segments.append(seg.index)
            continue

        for sentence in _sentences(seg):
            terms = find_flagged_terms(sentence)
            for key, values in terms.items():
                bucket = flagged.setdefault(key, [])
                for v in values:
                    if v not in bucket:
                        bucket.append(v)

            flags = find_privacy_flags(sentence)
            for f in flags:
                if f not in privacy:
                    privacy.append(f)

            if len(sentence.split()) < max(1, int(min_words)) and not sentence.rstrip().endswith("?"):
                continue

            # Someone else's previous line is the question this answers.
            preceded = prev_text if (prev_speaker and prev_speaker != seg.speaker) else ""

            if sentence.rstrip().endswith("?"):
                # A question is context, not a statement. Storing it as a claim
                # would let an interviewer's words be quoted as the firm's
                # history, so it is kept in its own list.
                question_counter += 1
                analysis.questions.append({
                    "id": "%s-q%02d" % (id_stem, question_counter),
                    "text": sentence,
                    "speaker": seg.speaker or "unattributed speaker",
                    "timestamp": seg.stamp(),
                })
                continue

            counter += 1
            needs: List[str] = []
            if terms.get("years") or terms.get("dates"):
                needs.append("verify date against a dated document")
            if terms.get("proper_nouns"):
                needs.append("confirm spelling of names/places")
            if terms.get("numbers"):
                needs.append("confirm figures against a record")
            if flags:
                needs.append("confidentiality review before any use")

            analysis.claims.append(InterviewClaim(
                id="%s-iq%02d" % (id_stem, counter),
                text=sentence,
                speaker=seg.speaker,
                timestamp=seg.stamp(),
                start=seg.start,
                end=seg.end,
                preceded_by=preceded,
                attributed_to=seg.speaker or "unattributed speaker",
                uncertainty=find_uncertainty(sentence),
                needs_confirmation=needs,
                privacy_flags=flags,
                quoted_ok=False,
                safe_for_public=False))

        if not seg.inaudible:
            prev_speaker = seg.speaker or prev_speaker
            prev_text = seg.text

    analysis.speakers = speakers
    analysis.flagged_terms = flagged
    analysis.privacy_flags = privacy

    if not speakers:
        analysis.gaps.append(
            "No speaker labels were found, so statements cannot be attributed to "
            "a named person. Add 'Name:' prefixes to the transcript.")
        analysis.notes.append(
            "Unattributed statements are still single-source recollections and "
            "must not be presented as the words of a named individual.")
    if not any(c.timestamp for c in analysis.claims):
        analysis.gaps.append("No timestamps available: quotes cannot be located "
                             "in the recording for verification.")
    if analysis.inaudible_segments:
        analysis.gaps.append(
            "Segments %s were inaudible; their content is missing and was not "
            "reconstructed." % ", ".join(str(i) for i in analysis.inaudible_segments))
    if privacy:
        analysis.gaps.append(
            "Confidentiality markers present (%s). Affected statements are "
            "quarantined pending human review." % ", ".join(sorted(privacy)))
    if not analysis.claims:
        analysis.gaps.append("No usable statements were extracted from this transcript.")
    if transcript.language in ("uz",):
        analysis.notes.append(
            "Uzbek: transcription and quoted wording should be checked line by "
            "line by a speaker of the language before the text is published.")
    return analysis


def analyse_file(path: str, language: str = "", min_words: int = 4) -> InterviewAnalysis:
    return analyse_transcript(load_transcript(path, language=language), min_words=min_words)


# ---------------------------------------------------------------- reporting
def findings_markdown(analysis: InterviewAnalysis, generated_at: Optional[str] = None) -> str:
    """Human-reviewable findings. Nothing here is asserted as historical fact."""
    lines: List[str] = []
    lines.append("# Interview analysis — %s" % analysis.source_name)
    lines.append("")
    lines.append("_Generated: %s_" % (generated_at or time.strftime("%Y-%m-%d %H:%M")))
    lines.append("")
    lines.append("**Transcript produced by:** %s" % (analysis.produced_by or "human"))
    lines.append("**Language:** %s" % (analysis.language or "unspecified"))
    lines.append("**Speakers:** %s" % (", ".join(analysis.speakers) or "not labelled"))
    lines.append("**Statements extracted:** %d" % len(analysis.claims))
    lines.append("**Questions recorded (context only):** %d" % len(analysis.questions))
    lines.append("")
    lines.append("> **Evidence rule.** Every statement below is recorded as "
                 "*attributed speech* (`SINGLE-SOURCE`). It is evidence that the "
                 "speaker said it, not evidence that it is historically true. "
                 "Nothing is cleared for publication until permission is given "
                 "and the fact is corroborated.")
    lines.append("")

    lines.append("## 1. Statements")
    lines.append("")
    if not analysis.claims:
        lines.append("_None extracted._")
    else:
        lines.append("| ID | Time | Speaker | Statement | Uncertainty | Review |")
        lines.append("|----|------|---------|-----------|-------------|--------|")
        for c in analysis.claims:
            lines.append("| %s | %s | %s | %s | %s | %s |" % (
                c.id, c.timestamp or "—", c.speaker or "—",
                c.text[:200].replace("|", "/"),
                ", ".join(c.uncertainty) or "—",
                ", ".join(c.privacy_flags) or "publication-review"))
    lines.append("")

    if analysis.claims:
        lines.append("### Statements with the question that prompted them")
        lines.append("")
        for c in analysis.claims:
            if not c.preceded_by:
                continue
            lines.append("- **%s** (%s)" % (c.id, c.timestamp or "untimed"))
            lines.append("  - Q: %s" % c.preceded_by[:220])
            lines.append("  - A: %s" % c.text[:260])
        lines.append("")

    if analysis.questions:
        lines.append("### Questions asked (context, not evidence)")
        lines.append("")
        lines.append("_A question is the interviewer's wording. It is never quoted "
                     "as a statement about the firm._")
        lines.append("")
        for q in analysis.questions:
            lines.append("- **%s** (%s) %s: %s" % (
                q.get("id", ""), q.get("timestamp") or "untimed",
                q.get("speaker", "—"), str(q.get("text", ""))[:220]))
        lines.append("")

    lines.append("## 2. Items needing human verification")
    lines.append("")
    if not analysis.flagged_terms:
        lines.append("- None detected.")
    else:
        for key in ("years", "dates", "numbers", "proper_nouns"):
            vals = analysis.flagged_terms.get(key)
            if vals:
                lines.append("- **%s:** %s" % (key.replace("_", " "), ", ".join(vals)))
        lines.append("")
        lines.append("_These are flagged for correction, never auto-corrected: "
                     "a misheard name or date must be fixed by a human who can "
                     "hear the recording._")
    lines.append("")

    lines.append("## 3. Confidentiality and publication review")
    lines.append("")
    if not analysis.privacy_flags:
        lines.append("- No confidentiality markers detected. This does **not** "
                     "mean the material is safe: a human review is still required.")
    else:
        for f in analysis.privacy_flags:
            lines.append("- **%s** — quarantine affected statements until reviewed."
                         % f)
    lines.append("")
    lines.append("- Quotation permission: **not yet granted** for %d statement(s). "
                 "Only the interviewee can grant it." % len(analysis.claims))
    lines.append("")

    lines.append("## 4. Gaps and limitations")
    lines.append("")
    if not analysis.gaps:
        lines.append("- None recorded.")
    else:
        for g in analysis.gaps:
            lines.append("- %s" % g)
    lines.append("")
    if analysis.notes:
        lines.append("## 5. Notes")
        lines.append("")
        for n in analysis.notes:
            lines.append("- %s" % n)
        lines.append("")
    lines.append("> **Anti-fabrication:** no missing dialogue was invented, no "
                 "statement was promoted to *verified*, and no quotation is "
                 "cleared for publication by this report.")
    return "\n".join(lines) + "\n"


def permission_checklist(analysis: InterviewAnalysis) -> str:
    """The sign-off a human must complete before any statement can be used."""
    lines: List[str] = []
    lines.append("# Permission checklist — %s" % analysis.source_name)
    lines.append("")
    lines.append("Complete this before quoting anyone in a public-facing film.")
    lines.append("Tick each item only when it is genuinely true.")
    lines.append("")
    lines.append("| # | Statement | Speaker | Quote permitted? | Corroborated? "
                 "| Confidentiality cleared? |")
    lines.append("|---|-----------|---------|------------------|---------------|"
                 "-------------------------|")
    for c in analysis.claims:
        lines.append("| %s | %s | %s | [ ] | [ ] | [ ] |" % (
            c.id, c.text[:90].replace("|", "/"), c.attributed_to))
    lines.append("")
    lines.append("## Blanket items")
    lines.append("")
    for item in (
        "Written or recorded consent to be interviewed, and to be named",
        "Consent to quote, granted statement by statement (not assumed)",
        "Client-identifying matter excluded, or separately authorised in writing",
        "Privileged material excluded from all public-facing deliverables",
        "Photographs and archive items cleared by their rights holder",
        "Any factual claim used in the film corroborated by a second source",
        "Uzbek/Russian wording checked by a native speaker where quoted",
    ):
        lines.append("- [ ] %s" % item)
    lines.append("")
    lines.append("_Until every relevant box is ticked, the statement stays out of "
                 "the film. This checklist is a record, not an approval._")
    return "\n".join(lines) + "\n"


def write_analysis(out_dir: str, analysis: InterviewAnalysis,
                   stamp: Optional[str] = None) -> Dict[str, str]:
    """Write findings + permission checklist + machine-readable JSON.

    Writes into ``out_dir`` only; creates it if needed and never overwrites an
    existing findings file from a different transcript run.
    """
    os.makedirs(out_dir, exist_ok=True)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", os.path.splitext(analysis.source_name)[0])
    paths = {
        "interview_findings.md": os.path.join(out_dir, "interview_findings_%s.md" % stem),
        "permission_checklist.md": os.path.join(out_dir, "permission_checklist_%s.md" % stem),
        "interview_analysis.json": os.path.join(out_dir, "interview_analysis_%s.json" % stem),
    }
    with open(paths["interview_findings.md"], "w", encoding="utf-8") as fh:
        fh.write(findings_markdown(analysis, generated_at=stamp))
    with open(paths["permission_checklist.md"], "w", encoding="utf-8") as fh:
        fh.write(permission_checklist(analysis))
    payload = analysis.as_dict()
    payload["generated_at"] = stamp or time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(paths["interview_analysis.json"], "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return paths
