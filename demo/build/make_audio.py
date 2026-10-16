#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_audio.py — builds the demo's audio bed.

  * music.wav  : a slow, license-free ambient pad, synthesized from scratch with
                 ffmpeg (no third-party music is used or licensed).
  * ru_<scene>.wav : temporary Russian voice-over via macOS `say` (voice "Milena").
  * vo_manifest.json : durations + start offsets for the assembler.

NOTE: TTS pronunciation is approximate and the voice is a placeholder; the final
film must use a human narrator. Phonetic respellings are used only for the TTS
input, never for on-screen text.
"""
import os, json, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from timeline import SCENES, scene_starts, total_duration

HERE = os.path.dirname(os.path.abspath(__file__))
AUD  = os.path.join(HERE, "audio")
os.makedirs(AUD, exist_ok=True)

FF = "ffmpeg"
TOTAL = total_duration()
MUSIC_LEN = TOTAL + 2.0

# phonetically respelled tokens so the Russian TTS says them sensibly
TTS_FIX = {
    "«Wakil AI»": "«Вакил Эй-Ай»",
    "Wakil AI": "Вакил Эй-Ай",
    "Stanford CodeX": "Стэнфорд Кодэкс",
    "lex.uz": "лекс точка уз",
    "Tahota": "Тахота",
    "Gulyamov, Sadikov and Partners": "Гулямов, Садиков энд Партнёрс",
}

def run(args):
    r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode != 0:
        print("CMD FAILED:", " ".join(args[:6]), "...")
        print(r.stderr[-1500:])
        raise SystemExit(1)
    return r

def dur(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True)
    return float(r.stdout.strip())

# ---------------------------------------------------------------- music
def make_music():
    print("== music ==")
    # three slow, consonant pads (A minor -> F major -> G), crossfaded
    def pad(freqs, amps, secs):
        expr = "+".join(f"{a}*sin(2*PI*{f}*t)" for f, a in zip(freqs, amps))
        expr = f"({expr})*(0.70+0.30*sin(2*PI*0.030*t))"
        return expr

    A = pad([110.00, 164.81, 220.00, 261.63, 329.63], [0.22, 0.14, 0.11, 0.09, 0.06], 62)
    F = pad([87.31, 174.61, 220.00, 261.63, 349.23], [0.24, 0.13, 0.11, 0.09, 0.06], 62)
    G = pad([98.00, 146.83, 196.00, 261.63, 329.63], [0.23, 0.14, 0.11, 0.09, 0.06], 62)

    tmp = os.path.join(AUD, "pad_%s.wav")
    for name, ex in [("A", A), ("F", F), ("G", G)]:
        run([FF, "-y", "-f", "lavfi", "-i", f"aevalsrc={ex}:s=48000:d=62",
             "-af", "lowpass=f=1400,aecho=0.8:0.85:420|760:0.30|0.20",
             tmp % name])

    out = os.path.join(AUD, "music.wav")
    run([FF, "-y",
         "-i", tmp % "A", "-i", tmp % "F", "-i", tmp % "G",
         "-filter_complex",
         "[0:a][1:a]acrossfade=d=8:c1=tri:c2=tri[a];"
         "[a][2:a]acrossfade=d=8:c1=tri:c2=tri[b];"
         f"[b]atrim=0:{MUSIC_LEN:.2f},asetpts=N/SR/TB,"
         f"afade=t=in:d=4,afade=t=out:st={MUSIC_LEN-9:.2f}:d=9,"
         "volume=0.85,aresample=48000[aout]",
         "-map", "[aout]", "-ac", "2", out])
    print("  music:", round(dur(out), 2), "s ->", out)
    return out

# ---------------------------------------------------------------- RU VO
def make_vo():
    print("== russian temporary voice-over ==")
    starts = scene_starts()
    manifest = []
    for (key, d, ru, _uz), st in zip(SCENES, starts):
        if not ru:
            continue
        txt = ru
        for a, b in TTS_FIX.items():
            txt = txt.replace(a, b)
        aiff = os.path.join(AUD, f"ru_{key}.aiff")
        wav  = os.path.join(AUD, f"ru_{key}.wav")
        run(["say", "-v", "Milena", "-r", "165", "-o", aiff, txt])
        run([FF, "-y", "-i", aiff, "-ar", "48000", "-ac", "1", wav])
        dlen = dur(wav)
        off = 0.15 if key == "closing" else 0.5
        manifest.append({"key": key, "file": os.path.basename(wav),
                         "start": round(st + off, 3), "len": round(dlen, 3),
                         "scene_dur": d})
        flag = "  <-- OVERRUNS SCENE" if dlen > d - off else ""
        print(f"  {key:9s} vo={dlen:5.2f}s scene={d:4.1f}s start={st+off:5.2f}{flag}")
        os.remove(aiff)
    with open(os.path.join(AUD, "vo_manifest.json"), "w") as f:
        json.dump({"total": TOTAL, "music_len": MUSIC_LEN, "vo": manifest}, f, indent=2)
    return manifest

if __name__ == "__main__":
    make_music()
    make_vo()
    print("done.")
