# -*- coding: utf-8 -*-
"""assets.py — fetch the firm's own published team portraits for the film.

The photos come from the firm's own website (the same source as the facts) and
are used only to illustrate the people scene. Every download is size-capped and
verified as a real image; anything that fails is skipped, and the scene falls
back to the names-only layout. Nothing here raises into the pipeline.
"""
import os
import re
from typing import Any, Callable, Dict, List, Optional

MAX_PHOTO_BYTES = 4_000_000
MAX_PORTRAITS = 4


def _default_download(url: str) -> Optional[bytes]:
    import requests
    r = requests.get(url, timeout=20, stream=True,
                     headers={"User-Agent": "Mozilla/5.0 (law-firm-research-agent)"})
    if r.status_code != 200 or "image" not in (r.headers.get("content-type") or ""):
        return None
    data = r.raw.read(MAX_PHOTO_BYTES + 1, decode_content=True)
    return data if 0 < len(data) <= MAX_PHOTO_BYTES else None


def _valid_image(data: bytes) -> bool:
    try:
        import io
        from PIL import Image
        with Image.open(io.BytesIO(data)) as im:
            im.verify()
        return True
    except Exception:
        return False


def fetch_portraits(team_photos: str, dest_dir: str,
                    download: Optional[Callable[[str], Optional[bytes]]] = None
                    ) -> List[Dict[str, Any]]:
    """``"Name|url;;Name|url"`` -> ``[{"name", "file", "url"}]`` for good photos."""
    download = download or _default_download
    out: List[Dict[str, Any]] = []
    for item in (team_photos or "").split(";;"):
        name, _sep, url = item.partition("|")
        name, url = name.strip(), url.strip()
        if not name or not re.match(r"^https?://", url):
            continue
        try:
            data = download(url)
        except Exception:
            data = None
        if not data or not _valid_image(data):
            continue
        os.makedirs(dest_dir, exist_ok=True)
        ext = os.path.splitext(url.split("?")[0])[1].lower()
        ext = ext if ext in (".jpg", ".jpeg", ".png") else ".jpg"
        path = os.path.join(dest_dir, "team_%d%s" % (len(out) + 1, ext))
        with open(path, "wb") as fh:
            fh.write(data)
        out.append({"name": name, "file": path, "url": url})
        if len(out) >= MAX_PORTRAITS:
            break
    return out
