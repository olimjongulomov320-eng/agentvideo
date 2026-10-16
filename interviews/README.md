# Interviews

This folder holds interview materials produced and managed by the
`law-firm-researcher` agent.

## Files the agent writes here

- `questionnaireManagingPartner.md` — tailored questions for the managing partner
- `questionnaireFoundingPartners.md` — tailored questions for founding partners
- `questionnairePartners.md` — tailored questions for other current partners
- `transcripts/` — transcripts or recordings the **user** supplies after
  conducting interviews (the agent never contacts anyone itself)

## Rules

- The agent prepares questions; the user conducts the interviews.
- The agent analyzes only transcripts/recordings supplied by the user.
- The agent must record, for every quotation considered for the film, whether
  the interviewee granted permission to use it publicly.
- Client-identifying or privileged matter heard in interviews is flagged and
  excluded from public-facing deliverables unless explicitly authorized.

## Status (GSP run)

The per-role questionnaires **already exist and are final** — they were written in
`research/` during the gap-analysis phase and are the canonical versions:

- **Managing partner (Abdulloh Sodiq):** `research/06_interview_plan_managing_partner.md` — FINAL DRAFT v3
- **Founding/name partner (Prof. Said Gulyamov) + team partners:** `research/07_interview_plan_partners.md` — FINAL DRAFT v4

**No interviews have been conducted yet.** The agent does not contact anyone.
When you run them, drop the recordings/transcripts here (in `transcripts/`) and the
agent will analyse them into `research/08_interview_findings.md`.

Questions these questionnaires must close are listed in `research/12_open_questions.md`
(items 12–16) and `research/10_fact_verification_log.md` (founding document, team-size
and address conflicts, dated evidence for "among the first").
