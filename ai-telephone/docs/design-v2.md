# AI Telephone — design v2 (team decision 2026-11-14, before any final data)

Replaces the v1 design (short handoffs; conditions A/B/C; budgets 100/70/45). No final data
existed when this changed; v1 development runs are kept as pilot records only.

## Research question

When long technical texts are summarized repeatedly, how does showing the summarizer
examples of good and bad summaries (0-, 1-, or few-shot) affect loss of key information and
hallucination across 1, 3, and 5 rounds — with and without a length limit?

## Design

| Factor | Levels |
|---|---|
| Model (analysed separately, never pooled) | **Core:** `gpt-6.1-terra` (Codex CLI), `claude-haiku-5-5` (Claude Code CLI). **Optional, only if time allows:** `gemini-3.8-flash-low` (Antigravity CLI), run by the Claude-side team member by hand |
| Prompt | `zero` (instruction only), `one` (instruction + one example pair: good vs bad summary), `few` (instruction + five examples: three good, two bad) |
| Length | `limited` (every summary at most 250 words) and `free` (no limit) |
| Depth | one chain of 5 rounds; scored at rounds 1, 3, 5 |
| Sources | 15 test documents (~1,200 words: 12 fictional technical reports + 3 optional excerpts of open-licence papers) and 3 development documents |

## Roles and models (final, 2026-11-14)

| Role | Claude side (team member A) | Codex side (team member B) |
|---|---|---|
| Summarizer under test | `claude-haiku-5-5` via Claude Code (optional third: `gemini-3.8-flash-low`, run by the team member themself, never by agents) | `gpt-6.1-terra` via Codex |
| Agent that builds code, merges CSVs, runs exports | Claude Code on Haiku (`claude-haiku-5-5`) | Codex on Terra (`gpt-6.1-terra`) |
| Drafts long sources (same brief: `docs/source-brief.md`) | Haiku: `long-01`–`long-06`, `dev-long-01`, `dev-long-02` | Terra: `long-07`–`long-12`, `dev-long-03` |
| Builds prompt examples (`docs/examples-brief.md`) | Haiku: example sources E1–E3; candidate summaries for all 5 | Terra: example sources E4–E5; candidate summaries for all 5 |
| AI annotator (grader) | `claude-opus-5-5` via Claude Code, the only annotator, for all models | — |
| Human work | source review, example selection, freeze sign-off, audit labels | same |

The annotator is never a summarizer under test. Splitting source drafting and example
generation between Haiku and Terra balances any advantage a model may have on its own
writing; the analysis reports results separately for Haiku-drafted and Terra-drafted sources.

Each round sees only the previous round's output, never the original. The original is never
restored. Ground truth never enters a summarizer prompt.

Google/Gemini policy: no agent and no orchestrator makes Gemini or Google calls. The optional
Gemini run, if any, is started by the team member themself after the core runs are done.

Calls per model: 15 docs × 3 prompts × 2 lengths × 5 rounds = **450**. Scored summaries per
model: 15 × 3 × 2 × 3 = **270**. Development: 3 docs × 30 = 90 calls per model.

Fixed settings: low reasoning effort for every summarizer; seed 1729 for scheduling and
bootstrap; one fresh process per call; empty working directory; tools disabled or rejected
from the event stream; 5-minute timeout; retries only for transient errors (15 s, 60 s);
stop on auth/quota/model-access errors; overlength output kept unchanged and passed on;
never regenerate an output because its content is disappointing.

## Ground truth

Each source has 6–10 items: 1–2 principal findings and 5–8 qualifications (evidence limits,
uncertainty, scope, conditions before acting, conflicting evidence, key numbers with their
context). Every item has a verbatim source quotation and an intended meaning. Humans review
every source and item before the freeze.

## Labels (AI annotator, human-audited)

Per item: `preserved`, `omitted`, `strengthened`, `weakened`, `contradicted`.
Per summary: list of `unsupported_claims` (hallucinations), each quoted verbatim.
One AI annotator (decided at freeze, then fixed for every model) labels all scored summaries
against the original source. A blinded human audit sample per model gives agreement figures.

## Metrics (pre-registered)

- **Primary:** item preservation rate (fraction of items labelled `preserved`) at round 5,
  `few` minus `zero`, limited-length scenario, paired by document, per model.
- **Secondary:** `one` minus `zero`; `few` minus `one`; the same contrasts at rounds 1 and 3
  and in the free-length scenario; preservation trajectory over rounds 1/3/5;
  unsupported claims per summary; strengthened and contradicted rates; output length and
  limit compliance; execution failures; human–AI agreement.
- Document is the statistical unit. 10,000 paired bootstrap resamples of documents, seed
  1729, 95% intervals. Missing outputs stay missing. Cross-model differences are descriptive
  only (model and harness are confounded).

## Data contracts (both teams build against these)

**Document IDs:** fictional test `long-01` … `long-12`; paper test `paper-01` … `paper-03`;
development `dev-long-01` … `dev-long-03`. Model keys: `terra`, `haiku` (and `gemini` only if the optional third model is run).

**Generation ID:** `{document_id}-{prompt}-{length}-r{round}`, e.g. `long-07-few-limited-r3`.
`prompt` ∈ `zero|one|few`, `length` ∈ `limited|free`, `round` ∈ 1..5.
Parse with `document_id, prompt, length, r = generation_id.rsplit('-', 3)`; `round = int(r[1:])`.

**Status values** in exports: `success`, or a failure status (`timeout`, `process_failure`,
`error_event`, `incomplete`, `invalid_event_stream`, `tool_or_unknown_event`,
`environment_mismatch`, `model_mismatch`), or `not_run` (scheduled but never attempted).
Only `success` rows have `output`. A generation whose parent failed is `not_run`.

**Word count:** `len(text.split())` (whitespace tokens). Limit compliance applies to
`limited` only: compliant if `word_count <= 250`.

**Preservation rate of one summary:** labels `preserved` ÷ number of ground-truth items of
its document (findings and qualifications together). Missing (not zero) if the generation is
not `success`, has no annotation line, or any item lacks a label.

**Run database** (one per model, not committed): table `attempts` (generation_id, attempt,
status, started, ended, prompt, output, events, stderr, word_count) and `run_meta`
(key/value: backend, model, reasoning_effort, args, cli_version).

**Generation export** (committed): `results/{model_key}/generations.jsonl`, one line per
generation ID with its final status:

```json
{"generation_id": "long-07-few-limited-r3", "document_id": "long-07", "prompt": "few",
 "length": "limited", "round": 3, "model": "gpt-6.1-terra", "status": "success",
 "output": "...", "word_count": 231, "attempts": 1, "started": "...", "ended": "..."}
```

`model_key` ∈ `terra|haiku|gemini`. No raw event streams, auth data, or local paths.

**AI annotations** (committed): `results/{model_key}/ai-annotations.jsonl`:

```json
{"generation_id": "...", "run_model": "...", "reviewer_id": "ai:<judge model>",
 "labels": [{"item_id": "...", "label": "preserved", "quotation": "...", "rationale": "..."}],
 "unsupported_claims": [{"quotation": "...", "rationale": "..."}]}
```

**Sources** (committed): `data/v2/sources.jsonl`, one `Document` per line with `id`, `split`
(`development|test`), `kind` (`fictional|paper`), `text`, `provenance` (must name the drafting
model, e.g. "Fictional; drafted with claude-haiku-5-5"), `licence`, `items`
(each `id`, `type` `finding|qualification`, `quotation`, `meaning`), `reviewed`.

## File ownership (avoid merge conflicts)

- **Claude side:** `data/v2/`, `src/ai_telephone/{models,prompts,runner,schedule,freeze,annotate,annotator_prompt,review_checks,review_page}.py`, their tests, `docs/{protocol,annotation,design-v2,plan-claude}.md`, `results/{haiku,gemini}/`, `results/*/ai-annotations.jsonl`.
- **Codex side:** `src/ai_telephone/{analysis,analyze_cli,figures}.py`, their tests, `app.py`, `report/`, `docs/{report-outline,video-outline,plan-codex,environment-terra}.md`, `results/terra/generations.jsonl`, `results/analysis/`.

Always `git pull --rebase` before pushing. Edit only your own files; ask the other side for
changes to theirs.
