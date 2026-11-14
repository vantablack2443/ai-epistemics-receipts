# Source drafting brief (identical for Haiku and Terra)

Both sides use this brief word for word, so the two halves of the dataset are comparable.
Draft one document per run. Paste the **Drafting prompt** below into the agent (Claude Code on
Haiku, or Codex on Terra), replacing the three `<...>` fields. Then check the result with the
**Checks** section before saving it.

## Assignments

| Side | Document IDs | Split |
|---|---|---|
| Haiku (Claude side) | `long-01`–`long-06` | test |
| Haiku (Claude side) | `dev-long-01`, `dev-long-02` | development |
| Terra (Codex side) | `long-07`–`long-12` | test |
| Terra (Codex side) | `dev-long-03` | development |

Genre and domain per document (fixed here so the two sides never overlap):

| ID | Genre | Domain | Finding strength |
|---|---|---|---|
| long-01 | incident review | municipal water-treatment dosing pump | strong |
| long-02 | evaluation report | speech-to-text model for call-centre notes | tentative |
| long-03 | field-trial report | agricultural soil-moisture sensors | strong |
| long-04 | migration post-mortem | hospital appointment-booking system | tentative |
| long-05 | safety assessment | warehouse autonomous forklift | mixed (conflicting evidence) |
| long-06 | benchmark write-up | battery cells for e-bikes | strong |
| long-07 | design review | rail-signal power supply | tentative |
| long-08 | energy-system pilot | rooftop solar with home battery | strong |
| long-09 | data-pipeline audit | retail sales forecasting feed | mixed (conflicting evidence) |
| long-10 | medical-device bench test | infusion-pump occlusion alarm | strong |
| long-11 | procurement acceptance test | wind-turbine blade coating | tentative |
| long-12 | ML model evaluation | fraud-detection classifier | tentative |
| dev-long-01 | incident review | ski-lift brake controller | strong |
| dev-long-02 | evaluation report | library book-recommendation model | tentative |
| dev-long-03 | field-trial report | street-light dimming controller | mixed |

## Drafting prompt

```
Write a fictional technical report for a research dataset. Do not use tools, browse, or read
files. Return only one JSON object, no code fences.

Document ID: <ID>   Genre: <GENRE>   Domain: <DOMAIN>   Finding strength: <STRENGTH>

Requirements for "text":
- 1,000 to 1,400 words of plain prose paragraphs separated by blank lines. No headings, no
  bullet lists, no markdown.
- Invented teams, systems and places only. No real companies, people, products, brand names,
  URLs, emails, credentials or personal data.
- One or two principal findings. If strength is "strong": large sample, replicated, clearly
  established. If "tentative": honest hedges ("may", "early results suggest") and a small or
  short test. If "mixed": two sources of evidence that disagree.
- Five to eight qualifications spread across the whole report, not in one paragraph: limits of
  the evidence, uncertainty with numbers, limited scope, untested assumptions, conflicting
  evidence, conditions that must be met before acting.
- Realistic background detail that a summary could safely leave out (history, people's roles,
  logistics, tooling).

Return this JSON shape:
{"id": "<ID>", "split": "<test or development>", "kind": "fictional",
 "text": "...",
 "provenance": "Fictional; drafted with <MODEL ID>",
 "licence": "CC0 (team-authored)",
 "items": [
   {"id": "<ID>-f1", "type": "finding", "quotation": "...", "meaning": "..."},
   {"id": "<ID>-q1", "type": "qualification", "quotation": "...", "meaning": "..."}
 ],
 "reviewed": false}

Rules for "items": 6 to 10 items in total; 1 or 2 with type "finding", the rest
"qualification"; ids <ID>-f1, <ID>-f2, <ID>-q1, <ID>-q2, ...; each "quotation" copied
exactly, character for character, from "text" (one sentence or clause that appears only once);
each "meaning" is one sentence saying what a summary must keep.
```

Replace `<MODEL ID>` with `claude-haiku-5-5` or `gpt-6.1-terra`, `<test or development>`
from the Assignments table.

## Checks (run after every document; fix by asking the agent to redraft, never by hand-editing quotations)

```
uv run python -m ai_telephone.review_checks --v2
```
reads `data/v2/drafts/fictional.jsonl` and must show **no flags** for the document: length
900–1,500 words (target 1,000–1,400), 6–10 items, 1–2 findings, every quotation found exactly
once, no URLs/emails/credentials, word overlap with every other document below 0.20.

Save each accepted document as one line appended to `data/v2/drafts/fictional.jsonl`
(Claude side) or `data/v2/drafts/fictional-terra.jsonl` (Codex side). The orchestrator merges
both files. Commit and push the drafts file; never commit model transcripts.
