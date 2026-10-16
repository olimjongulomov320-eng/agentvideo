# 10 — Fact Verification Log

**Last updated:** 2026-10-15 (deep public-source pass)
Classifications: VERIFIED · CORROBORATED · SINGLE-SOURCE · UNVERIFIED · CONFLICTING · RESTRICTED

| # | Claim (as it might appear) | Source(s) | Classification | Safe for public use? | Action |
|---|----------------------------|-----------|----------------|----------------------|--------|
| 1 | The firm was **founded in 2010** | Firm LinkedIn `[SM-06]` + firm history page `[PB-16]` + founder bio `[PB-17]` | **CORROBORATED** (still no registration doc) | **Yes** — as the firm's founding year | Obtain founding document to upgrade to VERIFIED |
| 2 | **2011 = start of activity; 2012 = recognition** | Firm history page `[PB-16]` | **SINGLE-SOURCE** (firm's own) | Yes, as the firm's own account | Corroborate if possible |
| 3 | **Abdulloh Sodiq** is founder / Managing Partner (since Jan 2010) | LinkedIn `[SM-07]`; firm IG "Asoschi" `[SM-01]`; **family confirmation** | **VERIFIED** (family + public record) | Yes, with consent | On-screen name: "Abdulloh Sodiq" |
| 4 | The founder was formerly known as **"Ruslan Sadikov"** (old site/IFCB) | `[PB-16, PB-17]` + **family confirmation** | **RESOLVED** — same person, name changed | Internal note only; **not spoken on screen** by default | Confirm if the firm wants it referenced |
| 5 | The firm is **"Gulyamov, Sadikov and Partners" (GSP)** | IG, website, LinkedIn, directories | **VERIFIED** | Yes | — |
| 6 | Firm specialises in **IT/cyber law, corporate, economic disputes** | Firm site `[PB-01]`; LinkedIn `[PB-03]` | **CORROBORATED** | Yes (as its own description) | — |
| 7 | Firm is **"among the first in Uzbekistan"** to offer **Islamic-law / Cyber-law** services | IFCB bio `[PB-17]` | **SINGLE-SOURCE** (firm's own) | Yes, phrased exactly as "among the first" | Find dated corroboration if possible |
| 8 | **Prof. Said Gulyamov** is Deputy Director **since 2019** | His own bio `[PB-05]` | **SINGLE-SOURCE** | Qualified | Corroborate; confirm he is/isn't a 2010 founder |
| 9 | **Wakil AI** co-founded by Abdulloh Sodiq (2026) | LinkedIn `[PB-04]`; Stanford CodeX `[PB-07]`; Academy of Justice `[PB-11]` | **VERIFIED** | Yes | — |
| 10 | Wakil AI is an Uzbek legal-AI ecosystem on `lex.uz` | Stanford CodeX `[PB-07]` | **VERIFIED** | Yes | — |
| 11 | **2024 — Tahota (China) partnership** | Firm LinkedIn `[PB-18]` | **SINGLE-SOURCE** (firm's own) | Qualified — **needs Tahota's OK to name them** | Get permission or drop the name |
| 12 | **2024 — Al Baraka Islamic-finance summit** attendance | Firm LinkedIn `[PB-18]` | **SINGLE-SOURCE** (firm's own) | Qualified | Corroborate |
| 13 | **Lexpert** = "Uzbekistan's first legal-AI platform", prize Oct 2023 | Aliboyev `[PB-21]`; Chinese delegation source `[PB-20]`; ProLex `[PB-24]` | **CORROBORATED** (external) but a **separate company**; firm lawyers behind it | Only with careful wording ("a lawyer of the firm co-founded…") | Keep out of v1 script unless cleared |
| 14 | Founder spoke on AI in law, Tashkent Law Spring 2025 | IG `[PB-13]` | **SINGLE-SOURCE** (social) | Qualified | Find programme |
| 15 | **Current address** = Yakkasaroy 5 | Directories `[PB-09, PB-16, PB-23]` | **CORROBORATED** | Yes (current, not the new office) | — |
| 16 | Firm also at Babur Street 58 | Yandex Maps `[PB-10]` | **CONFLICTING** | No | Clarify (old? second?) |
| 17 | Firm team size | TheOrg "1–10" `[PB-06]`; Lawzana "16" `[PB-08]` | **CONFLICTING** | No | Count from the firm |
| 18 | Firm has **"15 / 16+ / 20+ years"** | Site `[PB-01]` "16+"; IG `[SM-02]` "20+"; advice.uz `[PB-25]` "20 yil staj" | **CONFLICTING** | **No number** | Recommend "since 2010" only. 2026−2010 = **16 years** |
| 19 | Attorney **Saidov Elyorbek** posted a client "victory" (unnamed) | LinkedIn `[PB-19]`, 2024-07-25 | **SINGLE-SOURCE** (firm's own) | **NO** without client clearance | Keep out of film |

---
## Banned without evidence
No superlatives ("leading / best law firm"), no invented dates, no invented awards, no invented client outcomes, no invented founding story, no invented quotations.

## Key upgrades this pass
- **Founding 2010** moved from `CONFLICTING` → `CORROBORATED`.
- **Founder identity resolved:** one person, **Abdulloh Sodiq** (formerly Ruslan Sadikov) — family-confirmed.
- **Firm age conflict** resolved in practice: speak **"since 2010"**, never a count.
- **New office address** supplied: **Mirobod tumani, Mirobod ko'chasi, 46a** (user).

---
## C. Website self-description audit (added 2026-10-15, from `gsplaw.co.uz/data.js`)

While collecting real assets for the demo, the firm's own website data was read in
full. It publishes, as fact, a set of claims that are **not corroborated** and that
fall into the categories excluded for privilege and accuracy. **None is used in the
demo film as fact** (see `demo/DEMO_NOTES.md` §4). Flagged for the client to verify,
correct on the site, or substantiate.

| # | Website claim (`data.js`) | Status | Action |
|---|---|---|---|
| W1 | Case result: "$5.2M dispute victory" (2024, IT licensing, mediation) | **UNVERIFIED · CLIENT-CONFIDENTIAL** | Exclude; verify before any use |
| W2 | Case result: "$18M merger" | **UNVERIFIED · CLIENT-CONFIDENTIAL** | Exclude |
| W3 | Case result: "$1.2M VAT recovery" | **UNVERIFIED · CLIENT-CONFIDENTIAL** | Exclude |
| W4 | Aggregate "$100M+ / $250M+ portfolio" | **UNVERIFIED** | Exclude |
| W5 | "94 % win rate" | **UNVERIFIED** | Exclude (also ethically fraught) |
| W6 | "1000+ clients" | **UNVERIFIED** | Exclude |
| W7 | "15 advocates" | **CONFLICTING** with team-size sources | Do not state |
| W8 | Founder bio: "LLM, London School of Economics (2012)" | **UNVERIFIED** | Do not state |
| W9 | Founder award: "Best M&A Lawyer Uzbekistan — Deal Makers Awards (2022)" | **UNVERIFIED** | Do not state |
| W10 | Founder role: "Chairman of the Corporate Law Committee" | **UNVERIFIED** | Do not state |
| W11 | Gulyamov role: "Advisor to the Ministry of Digital Development (2020–2024)" | **UNVERIFIED** | Do not state |
| W12 | Gulyamov award: "Legal Awards — Best IT Law Lawyer Central Asia (2023)" | **UNVERIFIED** | Do not state |
| W13 | Website calls Prof. Gulyamov a **founder** | **CONFLICTING** with his own bio (firm role dated 2019) | Client to decide wording; demo uses "Partner · Professor" |
| W14 | Website firm stats show "16+ лет опыта" | Matches 2010→2026, but keep to "since 2010" (no spoken count) | Language rule holds |

**Note:** the website's published address (`Mirobod, 46a`) matches the new-office
address supplied by the client — consistent with the demo's scene 7.

**Highest reputational risk on the project:** the gap between the website's
claims and what is verifiable, if the site and the film are seen together.
