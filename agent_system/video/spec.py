# -*- coding: utf-8 -*-
"""video/spec.py — the shared, validated scene/render specification.

Every backend (motion, illustrated, blender3d) consumes the same shape, so a
scene manifest produced by the story module renders identically across styles.
"""
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

ALLOWED_KINDS = ("statement", "timeline", "list", "stat", "title", "endcard",
                 "photo", "illustration",
                 # composition kinds added with the design system
                 "quote", "comparison", "process", "logo", "profile")
ALLOWED_TRANSITIONS = ("fade", "dissolve", "wipe", "slide", "cut")
ASPECTS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080),
           "4:5": (1080, 1350)}

MAX_SCENES = 40
MAX_SCENE_SEC = 120.0
MIN_SCENE_SEC = 1.0
NARRATION_MAX = 1200
NEED_MAX = 60        # characters allowed per named evidence gap
MAX_NEEDS = 8        # named evidence gaps allowed per scene


class SpecError(ValueError):
    """Raised when a render specification fails validation."""


@dataclass
class AudioSpec:
    music: Optional[str] = None
    voiceover: Optional[str] = None
    license: str = "synthesized_temporary"
    voice: str = "none"          # none | human | synthetic
    music_gain_db: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RenderSpec:
    firm_name: str
    language: str = "en"
    style: str = "motion"
    width: int = 1920
    height: int = 1080
    fps: int = 30
    aspect: str = "16:9"
    transition: str = "fade"
    transition_sec: float = 0.7
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    audio: AudioSpec = field(default_factory=AudioSpec)
    watermark: str = ""
    output_name: str = "video.mp4"

    @property
    def total_duration(self) -> float:
        return sum(float(s["dur"]) for s in self.scenes)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["audio"] = self.audio.to_dict()
        d["total_duration_sec"] = self.total_duration
        return d


def _check_text(value: Any, name: str, errors: List[str], max_len: int = 500) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        errors.append("%s must be a string" % name)
        return ""
    if len(value) > max_len:
        errors.append("%s exceeds %d characters" % (name, max_len))
        return value[:max_len]
    return value


def _normalise_needs(value: Any) -> List[str]:
    """Normalise a scene's named evidence gaps into a list of short tokens.

    The story module emits ``needs`` as a comma-joined string (see
    ``story.scene_text``) and the scene manifest stores the split list. Both
    shapes are accepted here.

    This field MUST survive normalisation: it is the caption the GAP banner
    prints, so discarding it silently degrades an actionable gap
    ("founding_year") into a vague one ("unverified content").
    """
    if value in (None, ""):
        return []
    if isinstance(value, str):
        items: List[Any] = value.split(",")
    elif isinstance(value, (list, tuple)):
        items = list(value)
    else:
        return []
    out: List[str] = []
    for item in items:
        token = str(item).strip()
        if token:
            out.append(token[:NEED_MAX])
        if len(out) >= MAX_NEEDS:
            break
    return out


def _clean_portraits(raw: Any) -> List[Dict[str, str]]:
    """Up to four ``{name, file}`` pairs whose image file really exists."""
    out: List[Dict[str, str]] = []
    if isinstance(raw, list):
        for p in raw[:4]:
            if isinstance(p, dict) and isinstance(p.get("name"), str) \
                    and isinstance(p.get("file"), str) and os.path.isfile(p["file"]):
                out.append({"name": p["name"][:80], "file": p["file"]})
    return out


def gap_banner_text(scene: Dict[str, Any]) -> str:
    """The exact caption the GAP banner draws for ``scene``.

    Returns the specific missing evidence when the manifest names it, so the
    film states *which* fact a human must supply. Falls back to a deliberately
    generic phrase only when a scene is flagged as a placeholder without naming
    what is missing. Returns "" for a scene with no declared gap, so verified
    scenes are never marked.
    """
    if not scene.get("placeholder"):
        return ""
    named = scene.get("needs") or []
    if isinstance(named, str):
        named = [named]
    text = ", ".join(str(n).strip() for n in named if str(n).strip())
    return text or "unverified content"


def validate_render_spec(raw: Dict[str, Any]) -> Tuple[RenderSpec, List[str]]:
    """Validate a raw dict. Returns (spec, errors). Raises only on hard failures."""
    errors: List[str] = []
    if not isinstance(raw, dict):
        raise SpecError("spec must be an object")

    style = str(raw.get("style", "motion") or "motion").strip().lower()
    if style not in ("motion", "illustrated", "blender3d"):
        errors.append("unknown style %r (allowed: motion, illustrated, blender3d)" % style)
        style = "motion"

    aspect = str(raw.get("aspect", "16:9") or "16:9")
    if aspect not in ASPECTS:
        errors.append("unknown aspect %r (allowed: %s)" % (aspect, ", ".join(ASPECTS)))
        aspect = "16:9"
    dw, dh = ASPECTS[aspect]

    def _int(name: str, floor: int, ceil: int, default: int = 0) -> int:
        raw_val = raw.get(name)
        if raw_val in (None, ""):
            return default
        try:
            v = int(raw_val)
        except (TypeError, ValueError):
            errors.append("%s must be an integer" % name)
            return default
        if v < floor or v > ceil:
            errors.append("%s must be between %d and %d" % (name, floor, ceil))
            return max(floor, min(ceil, v))
        return v

    width = _int("width", 128, 7680, dw)
    height = _int("height", 128, 7680, dh)
    fps = _int("fps", 8, 60, 30)

    # H.264 (libx264, yuv420p) requires even dimensions; an odd value makes the
    # encoder fail with a cryptic "incorrect parameters such as ... width or
    # height" error. Snap to the nearest even number here so a hand-written
    # manifest can never break the render.
    if width % 2:
        width += 1
    if height % 2:
        height += 1

    transition = str(raw.get("transition", "fade") or "fade").lower()
    if transition not in ALLOWED_TRANSITIONS:
        errors.append("unknown transition %r" % transition)
        transition = "fade"
    try:
        transition_sec = float(raw.get("transition_sec", 0.7))
    except (TypeError, ValueError):
        errors.append("transition_sec must be a number")
        transition_sec = 0.7
    if not (0.0 <= transition_sec <= 2.0):
        errors.append("transition_sec must be within 0..2 s")
        transition_sec = 0.7

    raw_scenes = raw.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise SpecError("spec.scenes must be a non-empty list")
    if len(raw_scenes) > MAX_SCENES:
        raise SpecError("too many scenes (%d > %d)" % (len(raw_scenes), MAX_SCENES))

    scenes: List[Dict[str, Any]] = []
    for i, rs in enumerate(raw_scenes):
        if not isinstance(rs, dict):
            errors.append("scene %d is not an object" % i)
            continue
        sid = _check_text(rs.get("id", "sc%d" % (i + 1)), "scene.id", errors, 40) or ("sc%d" % (i + 1))
        kind = str(rs.get("kind", "statement") or "statement").lower()
        if kind not in ALLOWED_KINDS:
            errors.append("scene %s: unknown kind %r" % (sid, kind))
            kind = "statement"
        try:
            dur = float(rs.get("dur", 0) or 0)
        except (TypeError, ValueError):
            errors.append("scene %s: dur must be a number" % sid)
            dur = 0.0
        if dur < MIN_SCENE_SEC or dur > MAX_SCENE_SEC:
            errors.append("scene %s: dur %.2f outside %.0f..%.0f s"
                          % (sid, dur, MIN_SCENE_SEC, MAX_SCENE_SEC))
            dur = max(MIN_SCENE_SEC, min(MAX_SCENE_SEC, dur))
        scene = {
            "id": sid,
            "key": _check_text(rs.get("key", ""), "scene.key", errors, 40),
            "kind": kind,
            "dur": round(dur, 3),
            "heading": _check_text(rs.get("heading", ""), "scene.heading", errors, 160),
            "sub": _check_text(rs.get("sub", ""), "scene.sub", errors, 300),
            "narration": _check_text(rs.get("narration", ""), "scene.narration",
                                     errors, NARRATION_MAX),
            "transition": str(rs.get("transition", transition) or transition).lower(),
            "asset": rs.get("asset") if isinstance(rs.get("asset"), (str, type(None))) else None,
            "portraits": _clean_portraits(rs.get("portraits")),
            # `needs` names what evidence is missing; the renderer prints it on
            # the GAP banner. Keep it, or the banner degenerates to a generic
            # phrase and the film stops saying which fact is unsupplied.
            "needs": _normalise_needs(rs.get("needs")),
            # Never *un*-flag a scene. A manifest that names gaps but forgets the
            # placeholder flag is still a scene with missing evidence, so the
            # banner is shown rather than a gap being silently hidden.
            "placeholder": bool(rs.get("placeholder", False))
                           or bool(_normalise_needs(rs.get("needs"))),
        }
        if scene["transition"] not in ALLOWED_TRANSITIONS:
            errors.append("scene %s: unknown transition %r" % (sid, scene["transition"]))
            scene["transition"] = transition
        scenes.append(scene)

    audio_raw = raw.get("audio") or {}
    if not isinstance(audio_raw, dict):
        errors.append("audio must be an object")
        audio_raw = {}
    audio = AudioSpec(
        music=audio_raw.get("music"),
        voiceover=audio_raw.get("voiceover"),
        license=str(audio_raw.get("license", "synthesized_temporary")),
        voice=str(audio_raw.get("voice", "none")),
    )

    spec = RenderSpec(
        firm_name=_check_text(raw.get("firm_name") or raw.get("firm") or "", "firm_name", errors, 200) or "Untitled",
        language=str(raw.get("language", "en"))[:2].lower() or "en",
        style=style, width=width, height=height, fps=fps, aspect=aspect,
        transition=transition, transition_sec=transition_sec, scenes=scenes,
        audio=audio,
        watermark=_check_text(raw.get("watermark", ""), "watermark", errors, 60),
        output_name=_check_text(raw.get("output_name", "video.mp4"), "output_name", errors, 80)
        or "video.mp4",
    )
    return spec, errors
