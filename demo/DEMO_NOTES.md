# DEMO_NOTES — GSP LAW opening film (visual prototype)

> **This is a DEMO / CONCEPT PREVIEW.** It is not a final film and must not be
> published, broadcast or sent to any third party without the client's explicit
> written authorisation. Every illustrative element is labelled in the picture
> itself and in `PLACEHOLDERS.md`.

---

## 1. What was produced

A real, playable 2:23 cinematic prototype of the opening film — produced from
scratch with `ffmpeg` + Pillow, using the firm's **real logo, real brand colours
and 15 real team photographs**, plus verified facts from the research file.

Two language versions (the language pair was already fixed by the client:
Uzbek master, Russian secondary):

* `GSP_demo_UZ.mp4` — Uzbek titles, synthesized music bed. The Uzbek narration
  appears as on-screen titles because **no Uzbek text-to-speech voice exists on
  this machine**; the final film needs a human Uzbek narrator.
* `GSP_demo_RU.mp4` — Russian titles + a **temporary** Russian voice-over
  (macOS `say`, voice "Milena", phonetically corrected for names/terms) + music.

Both are 1920×1080 / 30 fps / H.264 / AAC, with synced sidecar `.srt` subtitles.

## 2. How it was built (and why it is genuinely a video, not a mock-up)

The pipeline is real and reproducible (`demo/build/`):

1. **Frames** — all typography and graphics are drawn in Pillow (this ffmpeg
   build has no `drawtext`, so text is pre-rendered — which also gives finer
   control of letter-spacing and layout).
2. **Motion** — each still is given a slow zoom/pan via `zoompan`, so nothing
   sits frozen.
3. **Timeline** — nine scenes are joined with 0.7 s crossfades.
4. **Grade** — one cinematic pass: contrast/saturation, unsharp, film grain,
   vignette, fade-in/out.
5. **Audio** — a music bed *synthesized from sine waves* (no third-party music,
   so no licensing issue) and, in the Russian cut, a side-chain-ducked temporary
   voice-over, normalised to −16 LUFS.
6. **Encode** — H.264 High@4.1, AAC 192 kb/s, faststart.

Quality control performed: both files probed (duration/streams/levels) and nine
frames per film extracted at scene midpoints and verified against the source
designs (layout correlation 0.80–0.89 for the ambiguous navy cards; all other
scenes matched exactly).

## 3. Honesty and labelling (how the demo keeps verification and confidentiality intact)

* A **"DEMO · CONCEPT PREVIEW"** tag is burned into every frame except the final
  cream logo card; the opening slate states in-language that this is not the
  final video and that illustrative material and a temporary voice are used.
* On-screen, every non-verified item is labelled at the point of use, e.g.
  *"firmaning o'z bayonoti — mustaqil tasdiqlanmagan"* (the firm's own statement —
  independently unconfirmed), *"manba: firmaning o'zi (LinkedIn)"*, *"illyustrativ
  maket"* (illustrative mock-up).
* **No client case, no dollar figure, no award, no win-rate and no personal
  credential from the firm's website was used** in the narration or as on-screen
  "fact". See §5.

## 4. Important finding — the firm's own website contains unverified claims

`gsplaw.co.uz` (`data.js`) advertises, as fact:

* case results — a "$5.2M dispute victory", an "$18M merger", a "$1.2M VAT
  recovery";
* aggregate claims — "$100M+ / $250M+ portfolio", "94 % win rate", "1000+ clients",
  "15 advocates";
* personal credentials — an **LSE LLM (2012)**, a **"Best M&A Lawyer Uzbekistan —
  Deal Makers Awards (2022)"**, a **"Chairman of the Corporate Law Committee"**
  role, a **"Ministry of Digital Development advisor (2020–2024)"**.

None of these could be corroborated during research, and several conflict with
what is independently verifiable. They therefore appear **nowhere** in the demo
as fact (they are also exactly the categories — client matters and unverified
honours — that the brief excludes for privilege and accuracy).

**Recommendation:** the client should have the website's claims independently
verified — or softened — before the film and the site are shown side by side,
because a viewer may cross-check. This is the single biggest reputational risk
found in the whole project.

## 5. What the demo deliberately does **not** claim

* Firm founding **2010** is stated as "since 2010" (never as a spoken year-count;
  the site's "16+ лет" is left out).
* "Among the first in Uzbekistan for Islamic and cyber law" is shown only with the
  label *the firm's own statement — independently unconfirmed*.
* The 2024 Tahota partnership and the Al Baraka Islamic-finance summit are shown
  with a *source: the firm itself (LinkedIn)* label.
* The founder's former name ("Ruslan Sadikov") is **not** shown on screen; the film
  uses **Abdulloh Sodiq** throughout.
* Prof. Said Gulyamov is labelled **Partner · Professor**, not "founder", because
  his own scholarly biography dates his firm role to 2019 while the firm's site
  calls him a founder — an unresolved discrepancy, so the neutral label is used.
* Wakil AI graphics are explicitly an *illustrative mock-up*, not a real product
  screenshot.

## 6. Honest technical limitations

* **I cannot see images or hear audio.** In this environment the model cannot view
  pictures, so all visual QA here is *programmatic* (brightness/variance/correlation
  tests), not aesthetic. A human must watch both files before anything ships. In
  particular the **photo crops** (faces framed by an automatic rule) need a human eye.
* **No Uzbek TTS** exists on this machine, so the Uzbek cut has no voice. This is a
  limitation of the tooling, not a design choice.
* **Music is a synthesized pad**, deliberately restrained; it is a placeholder for a
  licensed score, not a final soundtrack.
* **No historical or new-office photographs were provided**, so those beats are
  typographic/illustrative rather than photographic (see `PLACEHOLDERS.md`).
* The screenshot placed in `archive-input/` (a 472×1140 phone screenshot) **could not
  be viewed** either; it has not influenced the demo. If it shows something the film
  should reflect, please describe it or supply the original knowledge.

## 7. Deliverables map (against the request)

| Requested | Delivered as |
|---|---|
| Demo video (if rendering supported) | `GSP_demo_UZ.mp4`, `GSP_demo_RU.mp4` (real, playable) |
| Complete narration script | `NARRATION.md` (+ `production/03`, `production/06`) |
| Scene-by-scene timeline | `TIMELINE.md` |
| Sources and assets used | `SOURCES_AND_ASSETS.md` |
| Placeholders / missing materials | `PLACEHOLDERS.md` |
| Recommendations | `RECOMMENDATIONS.md` |
