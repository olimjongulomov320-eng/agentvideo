# -*- coding: utf-8 -*-
"""config.py — environment configuration and capability detection.

All settings come from environment variables (optionally seeded by a local
``.env``). Nothing is hardcoded; no secret is ever printed.
"""
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .security import load_dotenv_if_present, redact, register_secret

DEFAULTS = {
    "OUTPUT_DIR": "output",
    "MAX_CONCURRENT_JOBS": "1",
    "MAX_UPLOAD_MB": "49",
    "JOB_TIMEOUT_SEC": "1800",
    "LOG_LEVEL": "INFO",
    "OPENCODE_ENABLED": "false",
    "OPENCODE_BIN": "opencode",
    "OPENCODE_MODEL": "",
}

# Render quality profiles. A *deliverable* film is produced with the production
# profile (Full HD 1920x1080 @30). A fast preview is a separate, lower profile
# that must never silently become the deliverable.
#
# Note: resolution is the target *output* size — frames are rendered at this
# size from the start, never upscaled from a smaller composition.
PRODUCTION_PROFILE = {"width": 1920, "height": 1080, "fps": 30}
PREVIEW_PROFILE = {"width": 960, "height": 540, "fps": 24}
QUALITY_NAMES = ("production", "preview")

KNOWN_STYLES = ("motion", "illustrated", "blender3d")
STYLE_LABELS = {
    "motion": "Motion Graphics (2D corporate)",
    "illustrated": "Illustrated 2D Animation",
    "blender3d": "3D Animation (Blender)",
}


def _env(name: str, default: str = "") -> str:
    val = os.environ.get(name)
    if val is None or val == "":
        return DEFAULTS.get(name, default)
    return val


def _as_int(name: str, default: int) -> int:
    try:
        return int(str(_env(name, str(default))).strip())
    except (TypeError, ValueError):
        return default


def _as_bool(name: str, default: bool = False) -> bool:
    return str(_env(name, "true" if default else "false")).strip().lower() in (
        "1", "true", "yes", "on",
    )


def parse_user_ids(raw: str) -> List[int]:
    """Parse a comma/space separated list of numeric Telegram user IDs."""
    out = []
    for chunk in (raw or "").replace(";", ",").replace(" ", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if not chunk.lstrip("-").isdigit():
            raise ValueError("TELEGRAM_ALLOWED_USER_IDS must contain numeric IDs only")
        out.append(int(chunk))
    return out


def _which(binary: str) -> Optional[str]:
    return shutil.which(binary)


def _version(binary: str, args: Optional[List[str]] = None) -> Optional[str]:
    path = _which(binary)
    if not path:
        return None
    try:
        res = subprocess.run(
            [path] + (args or ["--version"]),
            capture_output=True, text=True, timeout=20,
        )
        first = (res.stdout or res.stderr or "").strip().splitlines()
        return first[0] if first else "present"
    except Exception:
        return "present"


@dataclass
class Capabilities:
    ffmpeg: Optional[str] = None
    ffprobe: Optional[str] = None
    blender: Optional[str] = None
    opencode: Optional[str] = None
    fonts: Dict[str, Optional[str]] = field(default_factory=dict)
    tts_voices: Dict[str, bool] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, object]:
        return {
            "ffmpeg": self.ffmpeg,
            "ffprobe": self.ffprobe,
            "blender": self.blender,
            "opencode": self.opencode,
            "fonts": self.fonts,
            "tts_voices": self.tts_voices,
        }

    def backend_available(self, style: str) -> bool:
        if style in ("motion", "illustrated"):
            return bool(self.ffmpeg)
        if style == "blender3d":
            return bool(self.blender and self.ffmpeg)
        return False


def detect_capabilities() -> Capabilities:
    caps = Capabilities()
    caps.ffmpeg = _version("ffmpeg", ["-version"])
    caps.ffprobe = _version("ffprobe", ["-version"])
    caps.blender = _version("blender", ["--version"])
    caps.opencode = _version(_env("OPENCODE_BIN", "opencode"), ["--version"])

    font_dirs = ["/System/Library/Fonts/Supplemental", "/System/Library/Fonts",
                 "/Library/Fonts"]
    wanted = {
        "serif": ["Georgia.ttf"],
        "serif_bold": ["Georgia Bold.ttf"],
        "sans": ["HelveticaNeue.ttc", "Helvetica.ttc", "SFNS.ttf"],
    }
    for key, names in wanted.items():
        caps.fonts[key] = None
        for d in font_dirs:
            for n in names:
                p = os.path.join(d, n)
                if os.path.isfile(p):
                    caps.fonts[key] = p
                    break
            if caps.fonts[key]:
                break

    # TTS: macOS `say` voices. We only claim a language if a voice exists.
    caps.tts_voices = {"en": bool(_which("say")), "ru": False, "uz": False}
    say = _which("say")
    if say:
        try:
            res = subprocess.run([say, "-v", "?"], capture_output=True, text=True, timeout=20)
            listing = (res.stdout or "")
            caps.tts_voices["ru"] = ("ru_RU" in listing)
            caps.tts_voices["uz"] = ("uz_" in listing or "uz_UZ" in listing)
        except Exception:
            pass
    return caps


@dataclass
class Config:
    project_root: str
    output_dir: str
    telegram_bot_token: str = ""
    allowed_user_ids: List[int] = field(default_factory=list)
    max_concurrent_jobs: int = 1
    max_upload_mb: int = 49
    job_timeout_sec: int = 1800
    log_level: str = "INFO"
    opencode_enabled: bool = False
    opencode_bin: str = "opencode"
    opencode_model: str = ""
    fast_render: bool = False
    render_quality: str = "production"
    capabilities: Optional[Capabilities] = None

    # ------------------------------------------------------------------ derived
    @property
    def jobs_dir(self) -> str:
        return os.path.join(self.output_dir, "jobs")

    @property
    def db_path(self) -> str:
        return os.path.join(self.output_dir, "jobs.sqlite3")

    def job_dir(self, job_id: str) -> str:
        return os.path.join(self.jobs_dir, job_id)

    def ensure_dirs(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.jobs_dir, exist_ok=True)

    def is_authorized(self, user_id: Optional[int]) -> bool:
        return user_id is not None and int(user_id) in set(self.allowed_user_ids)

    def style_available(self, style: str) -> bool:
        if not self.capabilities:
            return style in ("motion", "illustrated")
        return self.capabilities.backend_available(style)

    # ------------------------------------------------------------------ loading
    @classmethod
    def from_env(cls, project_root: Optional[str] = None,
                 detect: bool = True) -> "Config":
        root = project_root or os.environ.get("PROJECT_ROOT") or os.getcwd()
        root = os.path.abspath(root)
        load_dotenv_if_present(root)

        out = _env("OUTPUT_DIR", "output")
        if not os.path.isabs(out):
            out = os.path.join(root, out)

        token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        register_secret(token)

        raw_ids = os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "")
        try:
            ids = parse_user_ids(raw_ids)
        except ValueError:
            ids = []

        quality = str(_env("RENDER_QUALITY", "production")).strip().lower()
        if quality not in QUALITY_NAMES:
            quality = "production"

        cfg = cls(
            project_root=root,
            output_dir=os.path.abspath(out),
            telegram_bot_token=token,
            allowed_user_ids=ids,
            max_concurrent_jobs=max(1, _as_int("MAX_CONCURRENT_JOBS", 1)),
            max_upload_mb=max(1, _as_int("MAX_UPLOAD_MB", 49)),
            job_timeout_sec=max(30, _as_int("JOB_TIMEOUT_SEC", 1800)),
            log_level=str(_env("LOG_LEVEL", "INFO")).upper(),
            opencode_enabled=_as_bool("OPENCODE_ENABLED", False),
            opencode_bin=str(_env("OPENCODE_BIN", "opencode")),
            opencode_model=str(_env("OPENCODE_MODEL", "")),
            fast_render=_as_bool("FAST_RENDER", False),
            render_quality=quality,
        )
        if detect:
            cfg.capabilities = detect_capabilities()
        return cfg

    def validate_for_service(self) -> List[str]:
        """Return a list of blocking problems for running the bot service."""
        problems = []
        if not self.telegram_bot_token:
            problems.append("TELEGRAM_BOT_TOKEN is not set")
        if not self.allowed_user_ids:
            problems.append("TELEGRAM_ALLOWED_USER_IDS is not set (no user would be authorized)")
        if len(self.allowed_user_ids) > 10:
            problems.append("TELEGRAM_ALLOWED_USER_IDS has an implausible number of IDs")
        return problems

    def production_profile(self) -> Dict[str, object]:
        """Dimensions for a *deliverable* render: Full HD 1920x1080 @30fps."""
        return dict(PRODUCTION_PROFILE)

    def preview_profile(self) -> Dict[str, object]:
        """Dimensions for a fast, explicitly non-deliverable preview: 960x540 @24."""
        return dict(PREVIEW_PROFILE)

    def render_overrides(self) -> Dict[str, object]:
        """Legacy name, kept for backward compatibility — **preview only**.

        When ``fast_render`` is set this returns the *preview* dimensions. Using
        it for a deliverable is what silently produced a 960x540 "final" in the
        old pipeline; use :meth:`production_profile` for finals instead.
        """
        if self.fast_render:
            return self.preview_profile()
        return {}

    def encode_profile(self) -> str:
        """Encoder quality profile for the renderer: ``production`` or ``preview``."""
        if self.fast_render or self.render_quality == "preview":
            return "preview"
        return "production"

    def summary(self) -> Dict[str, object]:
        """Safe, redacted summary for logging and /health."""
        caps = self.capabilities.as_dict() if self.capabilities else {}
        return {
            "project_root": self.project_root,
            "output_dir": self.output_dir,
            "token_set": bool(self.telegram_bot_token),
            "allowed_user_count": len(self.allowed_user_ids),
            "max_concurrent_jobs": self.max_concurrent_jobs,
            "max_upload_mb": self.max_upload_mb,
            "job_timeout_sec": self.job_timeout_sec,
            "opencode_enabled": self.opencode_enabled,
            "fast_render": bool(self.fast_render),
            "render_quality": self.render_quality,
            "capabilities": caps,
        }


def redacted_env_dump(cfg: Config) -> str:
    """A redacted one-line dump safe for logs."""
    return redact(str(cfg.summary()))
