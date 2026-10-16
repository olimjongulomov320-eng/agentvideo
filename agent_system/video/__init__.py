# -*- coding: utf-8 -*-
"""video — render backends behind one validated scene specification.

Three styles are exposed:

* ``motion``      — Motion Graphics (Pillow typography + ffmpeg encode)
* ``illustrated`` — Illustrated 2D Animation (layered keyframed illustration)
* ``blender3d``   — 3D Animation (Blender integration boundary)

``backend_info()`` reports honestly which of them can actually render on this
machine, so no caller can accidentally present an unavailable style as working.
"""
import os
from typing import Any, Dict, List, Optional

from . import blender3d, common, draw, illustrated, motion, spec as _spec

__all__ = ["common", "draw", "motion", "illustrated", "blender3d", "spec",
           "get_backend", "backend_info", "list_backends", "render_style",
           "SpecError", "validate_render_spec"]

SpecError = _spec.SpecError
validate_render_spec = _spec.validate_render_spec

_BACKENDS = {
    "motion": motion.MotionBackend,
    "illustrated": illustrated.IllustratedBackend,
    "blender3d": blender3d.Blender3DBackend,
}

STYLE_LABELS = {
    "motion": "Motion Graphics (2D corporate)",
    "illustrated": "Illustrated 2D Animation",
    "blender3d": "3D Animation (Blender)",
}


def get_backend(style: str):
    """Return an instantiated backend for *style* (raises for unknown styles)."""
    key = (style or "").strip().lower()
    if key not in _BACKENDS:
        raise SpecError("unknown style %r (allowed: %s)"
                        % (style, ", ".join(sorted(_BACKENDS))))
    return _BACKENDS[key]()


def backend_info(style: str) -> Dict[str, Any]:
    key = (style or "").strip().lower()
    info: Dict[str, Any] = {
        "style": key,
        "label": STYLE_LABELS.get(key, key),
        "implemented": key in _BACKENDS,
        "ready": False,
        "reasons": [],
        "limitations": [],
    }
    if key not in _BACKENDS:
        info["reasons"].append("style not implemented")
        return info
    if key == "blender3d":
        avail = blender3d.availability()
        info["ready"] = bool(avail["available"])
        info["blender"] = avail
        info["limitations"] = list(blender3d.LIMITATIONS)
        if not avail["available"]:
            info["reasons"].append("Blender is not installed on this machine")
        if not common.ffmpeg_available():
            info["ready"] = False
            info["reasons"].append("ffmpeg not found")
        return info
    info["ready"] = common.ffmpeg_available()
    info["limitations"] = list((motion.LIMITATIONS if key == "motion"
                                else illustrated.LIMITATIONS))
    if not info["ready"]:
        info["reasons"].append("ffmpeg not found on PATH")
    return info


def list_backends() -> List[Dict[str, Any]]:
    return [backend_info(s) for s in ("motion", "illustrated", "blender3d")]


def render_style(spec, out_path: str, work_dir: str, asset_dir: str = "",
                 cancel=None, progress=None) -> Dict[str, Any]:
    """Render *spec* with the backend its ``style`` selects.

    Each backend performs its own availability check and raises a precise,
    actionable error (e.g. the Blender install steps), so the reason a style
    could not render is always specific rather than generic.
    """
    backend = get_backend(spec.style)
    return backend.render(spec, out_path, work_dir, asset_dir, cancel, progress)
