# AI Telephone

**Status: research prototype; a preliminary development chain exists, but no final results or human-reviewed dataset exist.** Do not use this directory as a completed study or submission. The existing `receipts-study` is separate; no code or data has been reused from it.

The study tests preservation of a finding and three qualifications in repeated summaries. The planned comparison is structured preservation (C) minus ordinary prose (A), paired by document. B isolates the preservation instruction. A direct 45-word summary provides a control for the ordinary chain only. See `docs/protocol.md` and `docs/annotation.md`.

## Access check

On 2026-11-13, Codex CLI 0.169.0 reported ChatGPT login. The nonexperimental command `codex exec --model gpt-6.1-terra --ephemeral --sandbox read-only --skip-git-repo-check --json --color never 'Return exactly: TERRA_OK'` exited successfully and returned `TERRA_OK`. The event stream reported usage and a thread ID but did not expose a resolved model ID. This establishes successful execution with the requested model argument, not independent verification of the resolved model identity. The workspace sandbox could not open Codex state; the successful check ran outside it. ECC 2.2.3 was already enabled.

On 2026-11-14, `uv run python -m ai_telephone.runner smoke --model haiku` (Claude Code 2.1.325, signed-in) returned `HAIKU_OK`; Claude Code's init event and usage both reported the resolved model `claude-haiku-5-5`, with an empty tool list and no MCP servers.

The study runs two models as separate experiments: `gpt-6.1-terra` via Codex (`--model terra`, the default, database `artifacts/development.sqlite`) and `claude-haiku-5-5` via Claude Code (`--model haiku`, database `artifacts/development-haiku.sqlite`). A database is bound to one model and configuration and refuses the other. Results are analysed per model and never pooled; see `docs/protocol.md`.

The Terra `dev-01` development chain and direct control completed ten calls on 2026-11-13. Seven outputs exceeded their budgets. The Haiku `dev-01` run completed ten calls on 2026-11-14 in about 62 seconds; eight exceeded their budgets (round one 125–166 words against 100; round two 81–133 against 70; round three 44–68 against 45; direct 45). Prompt revision for budget compliance must therefore be checked against both models before freezing. Only agent-message item events appeared in the stored event streams. This is one unreviewed development source, not an estimate of final performance. Exact prompts, event streams, outputs, timestamps, and counts are in `artifacts/development.sqlite`; these artifacts must be reviewed and sanitized before sharing. The runner still lacks the full final-run manifest, freeze controls, and publication export, so it intentionally offers no final-collection command.

## Remaining gates

1. Human-review the 36 draft sources and their four ground-truth items each; verify distinctness and six strongly supported findings, then freeze test data and prompts. Drafts are in `data/drafts/` and `data/sources.jsonl`, with the combined review sheet at `data/source-review.csv`.
2. Implement and verify the runner, immutable artifacts, annotation workflow, analysis, and local app against the brief. A smoke test is not a pipeline test.
3. Run and review the development study, then freeze the protocol before final collection. Do not treat this document as a frozen protocol.
4. Collect and independently annotate outputs; calculate results from exports. Secure actual authors' details and approval before submission.

No final data, findings, PDF, video, or submission are claimed here. Recording and editing are deferred. The user's supplied brief is the controlling specification; the notes here are a concise starting point, not a substitute for it.

### Human source review

Run `uv run python -m ai_telephone.review_export` after all drafts exist. Open `data/source-review.csv` in a spreadsheet editor and review the source and each of its four items. For each approved item, enter the human reviewer's name in `reviewer` and `approve` in `decision`; record problems in `review_notes`. Check scenario distinctness, word count, wording, source quotations, item meaning, category, and the six strongly established findings requirement. The importer rejects missing decisions and altered source/quotation text; corrections should be made to the draft records and a new review sheet created, rather than silently approving changed content. `uv run python -m ai_telephone.review_import` writes a separate reviewed file only after all rows are approved. It does not freeze the protocol or replace independent annotation.

## Fixture demonstration

After installing Python 3.11 and running `uv sync`, start `uv run streamlit run app.py`. The app reads the two locally drafted development sources and development SQLite database without making model calls. It exposes the source, chain, comparison, and draft ground truth; final results and annotations are not yet available. `uv run pytest` checks selected mechanics, not the complete research pipeline. `uv run python -m ai_telephone.runner validate` validates the records in `sources.jsonl`. `uv run python -m ai_telephone.runner smoke --model {terra,haiku}` is a nonexperimental access check that writes nothing. `uv run python -m ai_telephone.runner run-dev --model {terra,haiku} --document dev-01` makes up to ten model calls if outputs are not already present, using signed-in usage; it resumes completed calls. Analysis and freeze commands also require `--model`; the app has a model-run selector. Never use the development database for final study results.
