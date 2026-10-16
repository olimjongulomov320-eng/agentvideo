# Sources and assets used — GSP LAW opening film DEMO

## A. Real assets (downloaded from the firm's own website, `https://gsplaw.co.uz/`)

The client granted full permission to use the firm's own material, and these are
public files on the firm's site.

| Asset | File | Size | Used for |
|---|---|---|---|
| Firm logo (874×340, RGBA, dark-navy on transparency) | `assets/web/logo-full.png` | 28,207 B | closing card (authentic, un-inverted, on cream) |
| Shield/favicon | `assets/web/logo-shield.png` | 3,894 B | not used in picture (available) |
| Brand colours | `assets/web/style.css` | 44,090 B | the entire palette below |
| Site data (team, contacts, address, claims) | `assets/web/data.js` | 160,462 B | names/roles/titles only (claims excluded — see below) |
| Team photographs | `assets/web/photos/*.jpeg` (15 files, ≈11 MB) | — | founder portrait + 4×2 team grid |

**Brand palette (taken verbatim from the firm's `style.css`):**
`--dark #0e2d3e`, `--navy #17435a`, `--gold #c9a96e`, `--gold-light #e8c98a`,
`--cream #f8f6f1`. The film's navy/gold/cream look is therefore the firm's own.

**Team photographs used in the demo (scene 6) and the founder hero (scene 2):**

| On-screen name | Source file | Role shown |
|---|---|---|
| Abdulloh Sodiq | `photos/abdulloh-sodiq.jpeg` | Asoschi, boshqaruvchi sherik |
| Said Gulyamov | `photos/gulyamov-said.jpeg` | Sherik, professor |
| Firuz Abrayev | `photos/abraev-firuz.jpeg` | Sherik |
| Ulug'bek Xayitmurodov | `photos/xaytmurodov-ulugbek.jpeg` | Sherik |
| Saidulla Mixliyev | `photos/mikhilyev-saidulla.jpeg` | Advokat |
| Ulug'bek Isamutdinov | `photos/isamutdinov-ulugbek.jpeg` | Moliyaviy yurist |
| Darya Alijonova | `photos/alijonova-daria.jpeg` | Advokat, xalqaro yurist |
| Sevinch Ergasheva | `photos/ergasheva-sevinch.jpeg` | Advokat |

(The site lists 15 people; eight were used to keep the grid legible. The remaining
seven are available for a longer cut: `azimjon-zuxurov`, `boytrayev-dilshod`,
`orinov-xayrullo`, `saidov-elyor`, `sardor`, `sattorov-shohruh`, `zayniyev-mujohid`.)

## B. Facts used in the narration (verified / labelled)

| Fact | As used | Sourcing status |
|---|---|---|
| Founded 2010 in Tashkent | "since 2010" | firm history + user confirmation |
| Founder / Managing Partner: Abdulloh Sodiq | founder portrait & name plate | user confirmation (formerly Ruslan Sadikov — kept off screen) |
| 2011 practice, 2012 recognition | milestone bullets | firm's own history |
| Practice areas: economic disputes, corporate, IT/cyber law | scene 3 | firm's own + directories |
| "Among the first in Uzbekistan" for Islamic & cyber law | scene 3 | **labelled** "the firm's own statement — unconfirmed" |
| 2024 Tahota (China) partnership; Al Baraka Islamic-finance summit | scene 4 | **labelled** "source: the firm itself (LinkedIn)" |
| Wakil AI: Uzbek-language legal AI; cited to lex.uz; Stanford CodeX TechIndex; presented at the Academy of Justice | scene 5 | independently corroborated (Stanford CodeX TechIndex; Academy of Justice) — mock-up graphics labelled illustrative |

## C. Every source consulted (project-wide)

* **Firm's own:** `gsplaw.co.uz` (site, `data.js`, `style.css`), firm Instagram
  (`@gsplawuzb`), firm Telegram (`t.me/gsplawfirm`), firm YouTube channel, firm
  Facebook (`facebook.com/legality.uz` — login-walled, not read).
* **Independent / public record:** Stanford CodeX TechIndex; Academy of Justice of
  Uzbekistan; `gulyamov.org` (Prof. S. Gulyamov); LinkedIn (firm and people);
  Uzbek business directories; International Finance & Banking sources.
* **Direct-fetch failures (read only via search snippets):** `it-gsp.uz`,
  `legality.uz`, `gsplaw.uz` returned transport errors.

Full detail and the verification log live in `../research/`
(`01_source_inventory.md`, `10_fact_verification_log.md`, `13_research_summary.md`).

## D. Material deliberately **not** used

* All **client case results and dollar figures** from the firm's website
  ($5.2M / $18M / $1.2M / "$100M+ / $250M+" / "94 % win rate" / "1000+ clients").
* Personal **credentials/awards** from the website (LSE LLM 2012; "Deal Makers
  Awards 2022"; committee chairmanship; ministry advisor role) — uncorroborated.
* The founder's publicly reported **criminal case** and any unnamed "victory" posts.
* The founder's **former name** in any on-screen text.
* **Third-party music/stock** — none used; the music is synthesized.

## E. Generated assets (all produced in this build, no external rights)

* Music bed — synthesized from sine waves (`build/audio/music.wav`).
* Temporary Russian voice-over — macOS `say` (voice "Milena"), respelled phonetically
  for names/terms (`build/audio/ru_*.wav`).
* All backgrounds, gold rules, practice cards, the "distance" and "threshold" motifs,
  the globe arcs, the Wakil AI window, labels and the watermark — drawn in Pillow
  (`build/render_frames.py`).
* Subtitles (`GSP_demo_UZ.srt`, `GSP_demo_RU.srt`) — generated from `timeline.py`.
