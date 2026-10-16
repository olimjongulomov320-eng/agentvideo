#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble.py — builds the demo film with ffmpeg (split, verifiable stages).

  python3 assemble.py uz     ->  demo/GSP_demo_UZ.mp4   (Uzbek titles, music bed)
  python3 assemble.py ru     ->  demo/GSP_demo_RU.mp4   (Russian titles, music + temp VO)

Stages
  A. per scene : still frame -> subtle zoom/pan (zoompan)  -> light intermediate
  B. video     : chained crossfades (xfade) + cinematic grade, no audio -> video_<lang>.mp4
  C. audio     : synthesized pad, side-chain ducked under the temporary VO, loudnorm -> audio_<lang>.wav
  D. mux       : video (copied) + audio (AAC) + faststart -> final file
"""
import os, sys, json, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from timeline import SCENES, TRANSITION, FPS, total_duration

ROOT   = os.path.dirname(HERE)                  # demo/
FRAMES = os.path.join(HERE, "frames")
AUD    = os.path.join(HERE, "audio")
SEGS   = os.path.join(HERE, "segments")
os.makedirs(SEGS, exist_ok=True)

FF = "ffmpeg"
BIGW, BIGH = 2400, 1350
CROSS = TRANSITION

def run(args, tag=""):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAILED {tag}:", " ".join(args[:8]), "...")
        print(r.stderr[-3000:])
        raise SystemExit(1)
    return r

def frames_for(d):
    return max(2, int(round(d * FPS)))

# ---------------------------------------------------------------- A. segments
def build_segments(lang):
    segs = []
    for i, (key, d, _, _) in enumerate(SCENES):
        src = os.path.join(FRAMES, f"{lang}_{key}.png")
        out = os.path.join(SEGS, f"{lang}_{i:02d}_{key}.mp4")
        N = frames_for(d)
        z = f"1+0.085*on/{N}" if i % 2 == 0 else f"1.085-0.085*on/{N}"
        vf = (f"scale={BIGW}:{BIGH}:flags=bicubic,"
              f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={N}:s=1920x1080:fps={FPS},setsar=1,format=yuv420p")
        run([FF, "-y", "-i", src, "-vf", vf, "-frames:v", str(N),
             "-c:v", "libx264", "-preset", "veryfast", "-crf", "14",
             "-pix_fmt", "yuv420p", out], f"segment {key}")
        segs.append(out)
        print(f"  seg {i} {key:9s} ok", flush=True)
    return segs

# ---------------------------------------------------------------- B. video
def build_video(lang, segs):
    out = os.path.join(HERE, f"video_{lang}.mp4")
    parts, acc = [], float(SCENES[0][1])
    prev = "[0:v]"
    for i in range(1, len(segs)):
        off = acc - CROSS
        lbl = f"[x{i}]"
        parts.append(f"{prev}[{i}:v]xfade=transition=fade:duration={CROSS}:offset={off:.3f}{lbl}")
        prev = lbl
        acc += float(SCENES[i][1]) - CROSS
    parts.append(f"{prev}eq=contrast=1.035:saturation=0.96:brightness=-0.004,"
                 "unsharp=5:5:0.45:5:5:0.0,"
                 "noise=alls=5:allf=t+u,"
                 f"fade=t=in:st=0:d=0.6,fade=t=out:st={acc-0.9:.3f}:d=0.9,"
                 "format=yuv420p[vout]")
    cmd = [FF, "-y"]
    for s in segs: cmd += ["-i", s]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[vout]",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
            "-profile:v", "high", "-level", "4.1", "-r", str(FPS), out]
    run(cmd, "video pass")
    return out, acc

# ---------------------------------------------------------------- C. audio
def build_audio(lang, vo_manifest):
    out = os.path.join(HERE, f"audio_{lang}.wav")
    music = os.path.join(AUD, "music.wav")
    parts = ["[0:a]volume=1.15,highpass=f=45,lowpass=f=6500,aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000[music]"]
    vo_files = []
    if lang == "ru" and vo_manifest:
        labels = []
        for j, item in enumerate(vo_manifest["vo"]):
            idx = 1 + j
            ms = int(round(item["start"] * 1000))
            parts.append(f"[{idx}:a]adelay={ms}:all=1,"
                         "aformat=sample_fmts=fltp:channel_layouts=stereo,aresample=48000[v%d]" % j)
            labels.append(f"[v{j}]")
            vo_files.append(os.path.join(AUD, item["file"]))
        parts.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[voall]")
        # split so the same voice can both duck the music AND be mixed back in
        parts.append("[voall]asplit=2[vo_sc][vo_mix]")
        parts.append("[music][vo_sc]sidechaincompress=threshold=0.04:ratio=6:attack=15:release=500:makeup=1[ducked]")
        parts.append("[ducked][vo_mix]amix=inputs=2:normalize=0,alimiter=limit=0.95[amix]")
    else:
        parts.append("[music]alimiter=limit=0.95[amix]")
    dur = total_duration()
    parts.append(f"[amix]afade=t=in:d=2.5,afade=t=out:st={dur-4:.2f}:d=4,"
                 "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,apad[aout]")
    cmd = [FF, "-y", "-i", music]
    for v in vo_files: cmd += ["-i", v]
    cmd += ["-filter_complex", ";".join(parts), "-map", "[aout]",
            "-t", f"{dur:.3f}", "-ac", "2", "-ar", "48000", out]
    run(cmd, "audio pass")
    return out

# ---------------------------------------------------------------- D. mux
def mux(lang, video, audio):
    out = os.path.join(ROOT, f"GSP_demo_{lang.upper()}.mp4")
    run([FF, "-y", "-i", video, "-i", audio,
         "-map", "0:v:0", "-map", "1:a:0",
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
         "-movflags", "+faststart", "-shortest", out], "mux")
    return out

def main(lang):
    print(f"=== building {lang.upper()} demo ===", flush=True)
    print("A) segments", flush=True)
    segs = build_segments(lang)
    print("B) video (xfade + grade)", flush=True)
    video, vdur = build_video(lang, segs)
    print(f"   video = {vdur:.2f}s -> {video}", flush=True)
    vo_manifest = None
    if lang == "ru":
        mp = os.path.join(AUD, "vo_manifest.json")
        if os.path.exists(mp):
            vo_manifest = json.load(open(mp))
    print("C) audio", flush=True)
    audio = build_audio(lang, vo_manifest)
    print("D) mux", flush=True)
    out = mux(lang, video, audio)
    print("   DONE ->", out, flush=True)
    return out

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "uz")
