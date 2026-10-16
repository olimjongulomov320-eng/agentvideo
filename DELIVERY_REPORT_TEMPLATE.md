# DELIVERY REPORT TEMPLATE — job {{JOB_ID}}

_Generated: {{TIMESTAMP}}_

## Request
- Firm: **{{FIRM}}**
- Style: `{{STYLE}}` — {{STYLE_LABEL}}
- Language: `{{LANG}}`
- Target duration: {{DURATION_SEC}}s
- Website: {{WEBSITE}}
- Facebook: {{FACEBOOK}}
- Event date: {{EVENT_DATE}}
- New office: {{NEW_OFFICE}}

## Status
**{{STATUS}}**

{% if ERRORS -%}
### Errors
{% for e in ERRORS -%}
- {{e}}
{% endfor %}
{%- endif %}

{% if WARNINGS -%}
### Warnings
{% for w in WARNINGS -%}
- {{w}}
{% endfor %}
{%- endif %}

{% if NO_RENDER -%}
**No video was rendered** — no-render mode was requested: this delivery contains research, evidence, script and storyboard only. No `preview.mp4` or `final.mp4` exists.
{%- endif %}

## Sources actually accessed
{% for s in SOURCES -%}
- `{{s.id}}` {{s.url}} — **{{s.state}}** ({{s.note or "-"}})
{% endfor %}

{% if GAPS_EVIDENCE -%}
## Missing / blocked evidence
{% for g in GAPS_EVIDENCE -%}
- {{g}}
{% endfor %}
{%- endif %}

## Evidence ledger summary
{% if EVIDENCE_COUNTS -%}
{% for k, v in EVIDENCE_COUNTS|sorted -%}
- {{k}}: {{v}}
{% endfor %}
{%- else -%}
- no claims extracted
{%- endif %}
Public-safe claims: {{PUBLIC_SAFE_COUNT}} of {{CLAIMS_COUNT}} (unverified claims are never imported into the film as fact)

## Gaps the script had to leave open
{% if MISSING_FACTS -%}
{% for m in MISSING_FACTS -%}
- {{m}}
{% endfor %}
{%- else -%}
- none
{%- endif %}

## Asset permissions
- Real brand assets used only when supplied by the operator with permission.
- Commissioned photos/illustrations: **not supplied** — placeholders are marked.
- Music: synthesized pad unless a licensed file was supplied (`synthesized_temporary` is recorded in the render manifest).
- Voice-over: no synthetic voice is used where no engine exists.

{% if VALIDATION -%}
## Technical validation (ffprobe)
- OK: **{{VALIDATION.ok}}**
- Duration: {{VALIDATION.duration_sec}}s
- Size: {{VALIDATION.size_bytes}} bytes
- Video: {{VALIDATION.video_codec}} {{VALIDATION.width}}x{{VALIDATION.height}} @ {{VALIDATION.fps}}fps
- Audio: {{VALIDATION.audio_codec}} ({{VALIDATION.audio_channels}} ch)
{% for c in VALIDATION.checks -%}
- {{c}}
{% endfor %}
> {{VALIDATION.note}}

{%- endif %}

## Limitations
{% for lim in LIMITATIONS -%}
- {{lim}}
{% endfor %}

## Next steps for a human
1. Watch the film end to end — ffprobe cannot judge visual or audio quality.
2. Fill the gaps listed above from interviews and archives.
3. License music and record narration in the target language.
4. Obtain written permission for every real photo and quote used.
5. Approve before any external publication.
