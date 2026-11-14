# Prompt-example brief (1-shot and few-shot blocks)

The examples shown to the summarizers in the `one` and `few` prompt variants are built from
**real outputs of the cheap models**, not written by a stronger model. Same set for every
model under test. Example scenarios must not appear in any study document, the annotator's
examples, or the v1 drafts.

## Step E1 — example sources (5 short texts)

| ID | Drafted by | Domain |
|---|---|---|
| E1 | Haiku (Claude side) | greenhouse irrigation timer |
| E2 | Haiku (Claude side) | parcel-locker door sensor |
| E3 | Haiku (Claude side) | school-bus route optimiser |
| E4 | Terra (Codex side) | bakery oven temperature controller |
| E5 | Terra (Codex side) | museum humidity monitoring |

Drafting prompt (paste, replacing `<ID>` and `<DOMAIN>`):
```
Write a fictional technical note of 150 to 250 words about <DOMAIN>. Plain prose, no
headings or lists, invented names only. Include exactly one principal finding with a number,
and exactly three qualifications: one limit of the evidence, one limit of scope, and one
condition that must be met before acting. Add two sentences of background that a summary
could leave out. Do not use tools. Return only the note.
```
Save as `data/v2/examples/E<n>.txt`. A human writes `data/v2/examples/E<n>.items.md` listing
the finding and the three qualifications (copied from the note).

## Step E2 — candidate summaries

Each side summarizes **all five** example sources twice with this prompt (fresh session each
time), using its own model (Haiku via Claude Code, Terra via Codex):
```
Summarize the supplied text in at most 60 words for another engineer. Use only information in
the text. Do not use tools. Return only the summary.

Text:
<paste E<n>.txt>
```
Save to `data/v2/examples/candidates.jsonl`, one line per summary:
`{"example": "E1", "model": "claude-haiku-5-5", "run": 1, "summary": "..."}`.
That gives 20 candidates (5 sources × 2 runs × 2 models).

## Step E3 — human selection (both team members together)

For each example source pick:
- one **good** summary: keeps the finding and all three qualifications without changing their
  strength. Light edits allowed only to fix a lost qualification; mark the edit.
- one **bad** summary: a real candidate that drops, strengthens, or invents something. If no
  candidate fails, write one and mark it `constructed`.
- a one-sentence **why_bad** naming exactly what was dropped, strengthened, or invented.

Balance: across the five examples, at least two good and two bad summaries from each model.
Example E1 is the 1-shot example. Few-shot uses all five; at least two of the five must have
a bad summary that hallucinates (adds unsupported content) and at least two one that drops or
strengthens a qualification.

Record the selection in `data/v2/examples/selected.json` with, per example: `source`, `good`,
`good_from` (model + run, plus "edited" if edited), `bad`, `bad_from` (model + run, or
"constructed"), `why_bad`. The Claude side then loads it into
`src/ai_telephone/summarizer_examples.py` (replacing the provisional examples) and adds a test
that the rendered block matches `selected.json`. Report the provenance table in the paper's
appendix.
