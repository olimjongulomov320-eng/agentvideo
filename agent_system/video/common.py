# -*- coding: utf-8 -*-
"""video/common.py — ffmpeg helpers, ffprobe validation, render manifest.

Shared by every backend so the three styles behave identically in terms of
encoding, probing and reporting.
"""
import json
import math
import os
import shutil
import subprocess
import time
import wave
from dataclasses import asdict
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_BIN", "ffprobe")


class RenderError(RuntimeError):
    pass


# ----------------------------------------------------------------- process helpers
def run(cmd: List[str], timeout: int = 900, stdin_data: Optional[bytes] = None,
        cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a command with an argument array. Never uses a shell."""
    try:
        proc = subprocess.run(cmd, input=stdin_data, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout, cwd=cwd)
    except FileNotFoundError as exc:
        raise RenderError("executable not found: %s (%s)" % (cmd[0], exc))
    except subprocess.TimeoutExpired:
        raise RenderError("command timed out after %ss: %s" % (timeout, cmd[0]))
    return proc


def ffmpeg_available() -> bool:
    return bool(shutil.which(FFMPEG))


def ffprobe_available() -> bool:
    return bool(shutil.which(FFPROBE))


# ----------------------------------------------------------------- frame encoding
# Quality profiles. ``production`` is for the deliverable; ``preview`` is for a
# fast look. Bitrate is not the quality lever here (the frames are rendered at
# the target resolution); preset/CRF are.
ENCODE_PROFILES = {
    "production": {"crf": 18, "preset": "medium", "tune": "film"},
    "preview": {"crf": 23, "preset": "veryfast", "tune": "fastdecode"},
    "fast": {"crf": 23, "preset": "veryfast", "tune": "fastdecode"},
}


def encode_frames_to_video(frames: Iterable[Any], out_path: str, width: int,
                           height: int, fps: int, crf: Optional[int] = None,
                           preset: Optional[str] = None, timeout: int = 1800,
                           profile: Optional[str] = None) -> str:
    """Pipe PIL frames (RGB) into ffmpeg as rawvideo → H.264 mp4.

    ``crf``/``preset`` may be given explicitly; otherwise the ``profile``
    (``production`` | ``preview``) selects them. The legacy positional signature
    ``(frames, out_path, width, height, fps)`` keeps its historical defaults
    (CRF 20 / veryfast) when neither is supplied.
    """
    prof = ENCODE_PROFILES.get((profile or "").strip().lower())
    if crf is None:
        crf = prof["crf"] if prof else 20
    if preset is None:
        preset = prof["preset"] if prof else "veryfast"
    tune = prof["tune"] if prof else None
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    cmd = [
        FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", "%dx%d" % (width, height), "-r", str(fps), "-i", "pipe:0",
        "-an", "-c:v", "libx264", "-preset", preset, "-crf", str(crf),
    ]
    if tune:
        cmd += ["-tune", tune]
    cmd += [
        "-pix_fmt", "yuv420p",
        "-profile:v", "high", "-level", "4.1",
        "-g", str(max(1, int(fps * 2))),           # 2s keyframe interval
        "-movflags", "+faststart", out_path,
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)
    count = 0
    error = None
    try:
        for frame in frames:
            if frame.size != (width, height):
                frame = frame.resize((width, height))
            proc.stdin.write(frame.convert("RGB").tobytes())
            count += 1
    except BrokenPipeError:
        error = None            # ffmpeg closed the pipe: it already failed; below reports it
    except Exception as exc:     # a frame renderer failed — never deadlock on stderr
        error = exc
    finally:
        # Always close stdin first, otherwise ffmpeg waits forever and reading
        # stderr below would block the process.
        try:
            proc.stdin.close()
        except Exception:
            pass
        if error is not None:
            try:
                proc.kill()
            except Exception:
                pass
        try:
            err = proc.stderr.read()
        except Exception:
            err = b""
        try:
            proc.wait(timeout=timeout)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
    if error is not None:
        raise RenderError("frame renderer failed for %s: %s: %s"
                          % (out_path, type(error).__name__, error))
    if proc.returncode != 0:
        raise RenderError("ffmpeg frame encode failed: %s" % err.decode("utf-8", "ignore")[-800:])
    if count == 0:
        raise RenderError("no frames were produced for %s" % out_path)
    return out_path


def silent_audio(out_path: str, seconds: float, sample_rate: int = 48000) -> str:
    """Create a silent stereo bed of *seconds* length."""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        frames = int(seconds * sample_rate)
        w.writeframes(b"\x00\x00\x00\x00" * frames)
    return out_path


def synth_music(out_path: str, seconds: float, sample_rate: int = 48000,
                is_calm: bool = True) -> str:
    """Generate a calm synthesized pad (NO licensed music is bundled).

    Any file produced here is ``synthesized_temporary`` and must be labelled.
    """
    import numpy as np
    n = int(seconds * sample_rate)
    t = np.linspace(0, seconds, n, endpoint=False)
    # A minor 9 pad-ish chord, slow amplitude breathing.
    freqs = [110.0, 164.81, 220.0, 329.63]
    sig = np.zeros(n)
    for i, f in enumerate(freqs):
        sig += (0.25 / (i + 1)) * np.sin(2 * math.pi * f * t)
    lfo = 0.85 + 0.15 * np.sin(2 * math.pi * 0.05 * t)
    sig = sig * lfo
    sig += 0.02 * np.random.RandomState(7).randn(n)          # air
    peak = np.max(np.abs(sig)) or 1.0
    sig = (sig / peak) * 0.5
    stereo = np.stack([sig, np.roll(sig, 97)], axis=1)
    pcm = np.clip(stereo * 32767.0, -32768, 32767).astype("<i2")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with wave.open(out_path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())
    return out_path


def build_audio_track(out_path: str, seconds: float, spec_audio: Any,
                      work_dir: str) -> Tuple[str, Dict[str, Any]]:
    """Build the audio track: music (supplied or synthesized) + optional VO."""
    os.makedirs(work_dir, exist_ok=True)
    meta: Dict[str, Any] = {"music": None, "music_license": None,
                            "voiceover": None, "voice": "none", "mixing": []}
    music = getattr(spec_audio, "music", None)
    vo = getattr(spec_audio, "voiceover", None)

    if music and os.path.isfile(music):
        music_path = music
        meta["music"] = os.path.basename(music)
        meta["music_license"] = getattr(spec_audio, "license", "unknown")
    else:
        music_path = os.path.join(work_dir, "music_synth.wav")
        synth_music(music_path, max(1.0, seconds + 1.0))
        meta["music"] = "music_synth.wav"
        meta["music_license"] = "synthesized_temporary"
        meta["mixing"].append("music synthesized from sine waves — NOT licensed music")

    if vo and os.path.isfile(vo):
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", music_path, "-i", vo,
            "-filter_complex",
            "[0:a]volume=0.9,highpass=f=45,lowpass=f=7000,aformat=sample_fmts=fltp:"
            "channel_layouts=stereo,aresample=48000[m];"
            "[1:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000[v];"
            "[m][v]sidechaincompress=threshold=0.03:ratio=5:attack=15:release=400[duck];"
            "[duck][v]amix=inputs=2:normalize=0,alimiter=limit=0.95,"
            "loudnorm=I=-16:TP=-1.5:LRA=11[aout]",
            "-map", "[aout]", "-t", "%.3f" % seconds, "-ac", "2", "-ar", "48000", out_path,
        ]
        meta["voiceover"] = os.path.basename(vo)
        meta["voice"] = getattr(spec_audio, "voice", "human")
        meta["mixing"].append("music ducked under voice-over (sidechaincompress)")
    else:
        if getattr(spec_audio, "voice", "none") in ("human", "synthetic"):
            meta["mixing"].append("voice-over requested but no file supplied — "
                                  "final cut still needs narration")
        cmd = [
            FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
            "-i", music_path, "-filter_complex",
            "[0:a]aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000,"
            "afade=t=in:d=1.5,afade=t=out:st=%.2f:d=2.0,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,apad[aout]" % max(0.0, seconds - 2.0),
            "-map", "[aout]", "-t", "%.3f" % seconds, "-ac", "2", "-ar", "48000", out_path,
        ]
    proc = run(cmd, timeout=900)
    if proc.returncode != 0:
        raise RenderError("audio build failed: %s"
                          % proc.stderr.decode("utf-8", "ignore")[-600:])
    return out_path, meta


def mux(video_path: str, audio_path: str, out_path: str) -> str:
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    proc = run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error",
                "-i", video_path, "-i", audio_path,
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                "-shortest", out_path], timeout=900)
    if proc.returncode != 0:
        raise RenderError("mux failed: %s" % proc.stderr.decode("utf-8", "ignore")[-600:])
    return out_path


# ----------------------------------------------------------------- probing / validation
def probe(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise RenderError("file not found: %s" % path)
    proc = run([FFPROBE, "-v", "error", "-print_format", "json",
                "-show_format", "-show_streams", path], timeout=120)
    if proc.returncode != 0:
        raise RenderError("ffprobe failed: %s" % proc.stderr.decode("utf-8", "ignore")[-400:])
    return json.loads(proc.stdout.decode("utf-8", "ignore") or "{}")


def _fps_of(stream: Dict[str, Any]) -> Optional[float]:
    for key in ("avg_frame_rate", "r_frame_rate"):
        v = stream.get(key)
        if v and v != "0/0":
            try:
                num, den = v.split("/")
                if float(den) != 0:
                    return round(float(num) / float(den), 3)
            except Exception:
                continue
    return None


def validate_mp4(path: str, expect_width: Optional[int] = None,
                 expect_height: Optional[int] = None,
                 expect_fps: Optional[int] = None,
                 min_duration: Optional[float] = None,
                 max_duration: Optional[float] = None,
                 require_audio: bool = True) -> Dict[str, Any]:
    """Check a real MP4 with ffprobe. Returns a report; never claims more than it saw."""
    report: Dict[str, Any] = {"path": path, "ok": False, "checks": [],
                              "warnings": [], "errors": []}
    try:
        info = probe(path)
    except RenderError as exc:
        report["errors"].append(str(exc))
        return report

    fmt = info.get("format", {}) or {}
    streams = info.get("streams", []) or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    try:
        duration = float(fmt.get("duration", 0) or 0)
    except (TypeError, ValueError):
        duration = 0.0
    size = int(fmt.get("size", os.path.getsize(path)) or 0)

    report.update({
        "duration_sec": round(duration, 3),
        "size_bytes": size,
        "video_codec": video.get("codec_name") if video else None,
        "width": video.get("width") if video else None,
        "height": video.get("height") if video else None,
        "fps": _fps_of(video) if video else None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "audio_channels": audio.get("channels") if audio else None,
    })

    def check(cond: bool, ok_msg: str, bad_msg: str) -> None:
        if cond:
            report["checks"].append("OK: " + ok_msg)
        else:
            report["errors"].append(bad_msg)

    check(video is not None, "video stream present", "no video stream")
    check(audio is not None if require_audio else True,
          "audio stream present", "no audio stream")
    check(duration > 0, "duration > 0 (%.3fs)" % duration, "duration is zero")
    check(size > 1024, "size > 1 KiB (%d bytes)" % size, "file is suspiciously small")
    if video is not None:
        check(str(video.get("codec_name")) in ("h264", "hevc"),
              "codec %s" % video.get("codec_name"), "unexpected video codec %s" % video.get("codec_name"))
    if expect_width:
        check(report["width"] == expect_width,
              "width %d" % expect_width, "width %s != %d" % (report["width"], expect_width))
    if expect_height:
        check(report["height"] == expect_height,
              "height %d" % expect_height, "height %s != %d" % (report["height"], expect_height))
    if expect_fps and report["fps"]:
        check(abs(report["fps"] - expect_fps) <= 0.6,
              "fps %.2f" % report["fps"], "fps %s != %d" % (report["fps"], expect_fps))
    if min_duration is not None:
        check(duration >= min_duration - 0.5,
              "duration >= %.1fs" % min_duration, "duration %.1fs < %.1fs" % (duration, min_duration))
    if max_duration is not None:
        check(duration <= max_duration + 0.5,
              "duration <= %.1fs" % max_duration, "duration %.1fs > %.1fs" % (duration, max_duration))

    report["ok"] = not report["errors"]
    report["note"] = ("Technical validation only — ffprobe cannot judge how the film looks "
                      "or sounds. A human must review the picture and audio.")
    return report


# ----------------------------------------------------------------- manifest
def write_render_manifest(path: str, spec: Any, backend: str,
                          engine: Dict[str, Any], sources: Optional[List[str]] = None,
                          limitations: Optional[List[str]] = None,
                          validation: Optional[Dict[str, Any]] = None,
                          extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "backend": backend,
        "engine": engine,
        "output": {
            "name": spec.output_name,
            "width": spec.width,
            "height": spec.height,
            "fps": spec.fps,
            "aspect": spec.aspect,
            "style": spec.style,
            "language": spec.language,
            "total_duration_sec": round(spec.total_duration, 3),
        },
        "scenes": [{"id": s["id"], "key": s["key"], "kind": s["kind"], "dur": s["dur"]}
                   for s in spec.scenes],
        "audio": spec.audio.to_dict(),
        "source_assets": sources or [],
        "limitations": limitations or [],
        "validation": validation or {},
        "demo_label": spec.watermark,
    }
    if extra:
        manifest.update(extra)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
    return manifest


def engine_info(backend: str) -> Dict[str, Any]:
    ff = None
    try:
        proc = run([FFMPEG, "-version"], timeout=30)
        ff = (proc.stdout.decode("utf-8", "ignore").splitlines() or [""])[0]
    except Exception:
        pass
    return {"name": backend, "ffmpeg": ff,
            "python": "%d.%d" % (os.sys.version_info[0], os.sys.version_info[1])}
