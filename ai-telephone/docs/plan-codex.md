# Execution plan — Codex side (Terra runs, analysis, figures, app, report)

This plan is written for an AI coding agent. Follow it step by step, in order. Do not skip
the checks. When a step says **STOP**, stop and report to the human teammate; do not work
around it.

Read `ai-telephone/docs/design-v2.md` before starting. It is the controlling design. If this
plan and `design-v2.md` disagree, `design-v2.md` wins; tell the human about the conflict.

All times are Berlin time. Internal deadline: **Sunday 15 Nov, 20:00**.
Shell: Windows PowerShell. Repository root: the folder that contains `ai-telephone/`.
Branch: `codex/ai-telephone`.

---

**Model for everything on this side:** run Codex itself on **`gpt-6.1-terra`** (reasoning
effort `low`) for all work in this plan: drafting, coding, exports. The other side uses Claude
Haiku for its work. The AI annotator (`claude-opus-5-5`) runs on the other side.

**Order of work:** Phase 0 → **Phase 0b (sources and examples, first, because the team
reviews them tonight)** → Phase 1 → later phases when the human says so.

## 0. Rules that apply to every step

1. **Files you may edit** (Codex side):
   - `ai-telephone/src/ai_telephone/analysis.py`
   - `ai-telephone/src/ai_telephone/analyze_cli.py`
   - `ai-telephone/src/ai_telephone/figures.py` (new)
   - `ai-telephone/app.py`
   - `ai-telephone/tests/test_analysis_v2.py` (new), `ai-telephone/tests/fixtures/v2/` (new)
   - `ai-telephone/report/` (new folder)
   - `ai-telephone/docs/environment-terra.md` (new), `ai-telephone/docs/plan-codex.md`,
     `ai-telephone/docs/report-outline.md`, `ai-telephone/docs/video-outline.md`
   - `ai-telephone/results/terra/generations.jsonl`, `ai-telephone/results/analysis/`
   Do **not** edit any other file. If another file needs a change, write the request in your
   report to the human instead.
2. Before every push: `git pull --rebase origin codex/ai-telephone`, then
   `uv run pytest` inside `ai-telephone/`. Push only if all tests pass.
3. Never commit: `*.sqlite` files, raw event streams, anything from `~/.codex/`,
   `auth.json`, API keys, or paths that contain a personal user name.
4. Never invent numbers. Every number in the report must come from a file in
   `results/analysis/`.
5. Experimental model calls (Phases 2 and 3) use **only** `gpt-6.1-terra` with reasoning
   effort `low`, through the signed-in Codex CLI, on **one machine and one account**.
6. Never regenerate a completed output, never delete a failed attempt, never edit prompts or
   sources after the freeze.
7. **STOP** on any authentication, quota, rate-limit, or model-access error.
8. Commit messages: short imperative summary line, then a blank line, then what changed.

---

## Phase 0 — setup and Terra access check (start now, about 30 minutes)

### Step 0.1 — get the code
```powershell
git checkout codex/ai-telephone
git pull --rebase origin codex/ai-telephone
Set-Location ai-telephone
uv sync
uv run pytest
```
**Check:** pytest reports `passed` and no failures. If anything fails: **STOP**, report the
failing test names and the last 20 lines of output.

### Step 0.2 — Terra smoke test
```powershell
uv run python -m ai_telephone.runner smoke --model terra
```
**Check:** the printed JSON has `"status": "success"` and `"output": "TERRA_OK"`.
If not: **STOP** and report the JSON (it contains no secrets).

### Step 0.3 — record the environment
Create `ai-telephone/docs/environment-terra.md` with:
1. Date and time of the smoke test.
2. The full JSON printed in Step 0.2.
3. Output of `codex --version`.
4. **File names only** in the Codex home folder:
   `Get-ChildItem $env:USERPROFILE\.codex -Name`. Do **not** print or copy the contents of
   any file there, especially `auth.json`.
5. Whether these exist (yes/no): a global `AGENTS.md` in the Codex home folder; any
   `AGENTS.md` in the repository; installed Codex plugins (`codex plugin list`).
6. One sentence: "Experimental calls use `--ignore-user-config`, an empty temporary working
   directory, and `--sandbox read-only`; the event stream is checked and any tool event
   invalidates the attempt."

### Step 0.4 — push
```powershell
git add docs/environment-terra.md
git commit -m "Record Terra smoke test and Codex environment"
git pull --rebase origin codex/ai-telephone
git push origin codex/ai-telephone
```
Tell the human: "Phase 0 done, smoke test passed."

---

## Phase 0b — Terra drafts its share of sources and examples (Saturday evening, before Phase 1)

Also allowed to create/edit: `ai-telephone/data/v2/drafts/fictional-terra.jsonl`,
`ai-telephone/data/v2/examples/E4.txt`, `E5.txt`, and append to
`ai-telephone/data/v2/examples/candidates.jsonl`.

### Step 0b.1 — draft 7 long sources
Read `docs/source-brief.md` completely. Draft **`long-07` to `long-12` and `dev-long-03`**,
one document per Codex session, using the **Drafting prompt** in that file exactly, with
`<MODEL ID>` = `gpt-6.1-terra` and the genre/domain/strength from its table.
After each document:
1. Append the JSON object as one line to `data/v2/drafts/fictional-terra.jsonl`.
2. Run `uv run python -m ai_telephone.review_checks --v2`.
3. If the new document has any flag: delete its line and redraft (new session). Never
   hand-edit a quotation to make it match.
**Check:** 7 lines, IDs exactly as listed, no flags for any of them.

### Step 0b.2 — example sources and candidates
Read `docs/examples-brief.md` completely.
1. Draft example sources **E4** and **E5** with its drafting prompt; save as
   `data/v2/examples/E4.txt` and `E5.txt`.
2. When the other side has pushed E1–E3 (pull first), write the **candidate summaries**:
   for each of E1–E5, two fresh Codex sessions with the brief's summary prompt. Append each
   result to `data/v2/examples/candidates.jsonl` as
   `{"example": "E1", "model": "gpt-6.1-terra", "run": 1, "summary": "..."}`.
**Check:** 10 Terra lines in `candidates.jsonl` (5 examples × 2 runs).

### Step 0b.3 — push
```powershell
git add data/v2/drafts/fictional-terra.jsonl data/v2/examples
git commit -m "Add Terra-drafted sources and example candidates"
git pull --rebase origin codex/ai-telephone
git push origin codex/ai-telephone
```
Tell the human: "Phase 0b done". The humans of both sides then pick the examples together
(examples brief, Step E3) and review all sources (Claude plan, Step 3).

---

## Phase 1 — analysis, figures, app (Saturday evening and night)

Real data does not exist yet. Build everything against the **fixture files** below, so it is
ready when data arrives. Read the "Data contracts" section of `design-v2.md` first.

### Step 1.1 — create the fixture files exactly as written

Create folder `ai-telephone/tests/fixtures/v2/` with these three files. Copy them exactly.
They are fake data for tests only.

`tests/fixtures/v2/sources.jsonl` (3 lines):
```json
{"id": "T1", "split": "test", "kind": "fictional", "items": [{"id": "T1-i1", "type": "finding"}, {"id": "T1-i2", "type": "qualification"}]}
{"id": "T2", "split": "test", "kind": "fictional", "items": [{"id": "T2-i1", "type": "finding"}, {"id": "T2-i2", "type": "qualification"}]}
{"id": "D1", "split": "development", "kind": "fictional", "items": [{"id": "D1-i1", "type": "finding"}, {"id": "D1-i2", "type": "qualification"}]}
```

`tests/fixtures/v2/results/terra/generations.jsonl` (9 lines):
```json
{"generation_id": "T1-zero-limited-r5", "document_id": "T1", "prompt": "zero", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a b c", "word_count": 3}
{"generation_id": "T1-one-limited-r5", "document_id": "T1", "prompt": "one", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a b c d", "word_count": 4}
{"generation_id": "T1-few-limited-r5", "document_id": "T1", "prompt": "few", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a b", "word_count": 2}
{"generation_id": "T2-zero-limited-r5", "document_id": "T2", "prompt": "zero", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a", "word_count": 1}
{"generation_id": "T2-one-limited-r5", "document_id": "T2", "prompt": "one", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "timeout", "output": null, "word_count": null}
{"generation_id": "T2-few-limited-r5", "document_id": "T2", "prompt": "few", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a b c d e", "word_count": 5}
{"generation_id": "D1-zero-limited-r5", "document_id": "D1", "prompt": "zero", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a", "word_count": 1}
{"generation_id": "D1-one-limited-r5", "document_id": "D1", "prompt": "one", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a", "word_count": 1}
{"generation_id": "D1-few-limited-r5", "document_id": "D1", "prompt": "few", "length": "limited", "round": 5, "model": "gpt-6.1-terra", "status": "success", "output": "a", "word_count": 1}
```

`tests/fixtures/v2/results/terra/ai-annotations.jsonl` (7 lines; no line for the timed-out
generation):
```json
{"generation_id": "T1-zero-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "T1-i1", "label": "preserved"}, {"item_id": "T1-i2", "label": "omitted"}], "unsupported_claims": [{"quotation": "a", "rationale": "x"}]}
{"generation_id": "T1-one-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "T1-i1", "label": "preserved"}, {"item_id": "T1-i2", "label": "preserved"}], "unsupported_claims": []}
{"generation_id": "T1-few-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "T1-i1", "label": "preserved"}, {"item_id": "T1-i2", "label": "preserved"}], "unsupported_claims": []}
{"generation_id": "T2-zero-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "T2-i1", "label": "omitted"}, {"item_id": "T2-i2", "label": "omitted"}], "unsupported_claims": []}
{"generation_id": "T2-few-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "T2-i1", "label": "preserved"}, {"item_id": "T2-i2", "label": "strengthened"}], "unsupported_claims": []}
{"generation_id": "D1-zero-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "D1-i1", "label": "omitted"}, {"item_id": "D1-i2", "label": "omitted"}], "unsupported_claims": []}
{"generation_id": "D1-few-limited-r5", "run_model": "gpt-6.1-terra", "reviewer_id": "ai:judge", "labels": [{"item_id": "D1-i1", "label": "preserved"}, {"item_id": "D1-i2", "label": "preserved"}], "unsupported_claims": []}
```

**Expected results for this fixture** (your tests must assert these exact values):

| Quantity (terra, limited, round 5) | Expected |
|---|---|
| T1 rates: zero / one / few | 0.5 / 1.0 / 1.0 |
| T2 rates: zero / one / few | 0.0 / missing / 0.5 |
| `few−zero`: n_pairs, difference, low, high | 2, 0.5, 0.5, 0.5 |
| `one−zero`: n_pairs, difference | 1, 0.5 |
| `few−one`: n_pairs, difference | 1, 0.0 |
| Mean unsupported claims per summary, prompt `zero` | 0.5 (1 claim over 2 summaries) |
| `strengthened` count, prompt `few` | 1 |
| D1 appears in any aggregate | never |
| Failures table | 1 row: status `timeout`, count 1 |

### Step 1.2 — `analysis.py`

Keep these existing functions **unchanged** (other code imports them):
`fraction_preserved`, `paired_bootstrap`, `cohen_kappa`, `agreement`.

Add these functions. Read files as plain JSON with the `json` module; do **not** import
`ai_telephone.models` (its schema is changing on the Claude side).

```python
LABELS = ('preserved', 'omitted', 'strengthened', 'weakened', 'contradicted')
PROMPTS = ('zero', 'one', 'few')
LENGTHS = ('limited', 'free')
SCORED_ROUNDS = (1, 3, 5)
CONTRASTS = (('few', 'zero'), ('one', 'zero'), ('few', 'one'))

def load_jsonl(path) -> list[dict]: ...
    # one dict per non-empty line; raise ValueError naming the line number on bad JSON

def parse_generation_id(generation_id) -> tuple[str, str, str, int]:
    # document_id, prompt, length, r = generation_id.rsplit('-', 3); return (document_id, prompt, length, int(r[1:]))

def test_documents(sources) -> dict[str, list[str]]:
    # {document_id: [item ids]} for split == 'test' ONLY

def summary_rates(generations, annotations, documents) -> list[dict]:
    # One row per generation whose document is in `documents` and round in SCORED_ROUNDS.
    # Row keys: document_id, prompt, length, round, status, n_items, n_preserved, rate,
    #           n_unsupported, labels (dict label -> count).
    # rate = n_preserved / n_items, or None when status != 'success', or no annotation line,
    # or any item of the document lacks a label. n_unsupported = None in the same cases.

def contrasts(rows, length, round_) -> list[dict]:
    # For each pair in CONTRASTS: left/right = {document_id: rate} for that prompt, length, round.
    # Use paired_bootstrap(left, right) (seed 1729, 10000 samples). Return dicts with keys:
    # contrast ('few-zero' etc.), length, round, n_pairs, difference, low, high.
```

### Step 1.3 — `analyze_cli.py`

Rewrite `main()` (the v1 version is obsolete) to:
```
uv run python -m ai_telephone.analyze_cli --results results --sources data/v2/sources.jsonl --out results/analysis
```
1. Find every folder `results/<model_key>/` that contains both `generations.jsonl` and
   `ai-annotations.jsonl`. Skip others with a printed warning.
2. Raise `ValueError` if two annotation lines share a `generation_id`, or if a generation
   ID appears twice in `generations.jsonl`.
3. For each model key write into `results/analysis/<model_key>/`:
   - `summary_rates.csv` — all rows from `summary_rates` (`labels` expanded to one column per
     label; empty cell for missing values, never 0).
   - `contrasts.csv` — `contrasts` for every length × round in `LENGTHS` × `SCORED_ROUNDS`.
   - `errors.csv` — columns `prompt,length,round,label,count,share`; share = count ÷ all item
     labels in that prompt/length/round.
   - `claims.csv` — `prompt,length,round,n_summaries,mean_unsupported`.
   - `lengths.csv` — from `generations.jsonl`, all rounds 1–5, test documents only:
     `prompt,length,round,n_success,mean_words,median_words,share_over_250`
     (`share_over_250` only for `limited`; empty for `free`).
   - `failures.csv` — `status,count` over all test-document generations that are not
     `success`.
   - `by_drafter.csv` — the round-5 preservation rate per prompt and length, split by which
     model drafted the source (read from the source's `provenance`: contains
     `claude-haiku-5-5` → `haiku`, `gpt-6.1-terra` → `terra`, otherwise `other`). Columns
     `drafter,prompt,length,n_documents,mean_rate`. This checks whether a model does better on
     sources it wrote itself.
4. Write `results/analysis/primary.csv` with one row per model: the `few-zero` contrast at
   length `limited`, round 5.
5. Print the primary rows to the terminal.

### Step 1.4 — `figures.py`

```
uv run python -m ai_telephone.figures --analysis results/analysis --out results/analysis/figures
```
Use matplotlib only. Save each figure as PNG (200 dpi) and SVG. Same colours for the same
prompt everywhere: zero = grey `#7f7f7f`, one = blue `#1f77b4`, few = orange `#ff7f0e`.
Label every axis. Titles state model and length scenario.

1. `trajectory_<model>.png`: x = round (1, 3, 5), y = mean preservation rate across test
   documents (0–1), one line per prompt, two panels side by side (limited, free).
2. `primary_contrasts.png`: one point per model for `few-zero` (limited, round 5) with a
   horizontal 95% interval; a vertical dashed line at 0.
3. `errors_<model>.png`: stacked bars of label shares at round 5, one bar per prompt,
   panels for limited and free.
4. `claims_<model>.png`: mean unsupported claims per summary by round, one line per prompt.
5. `lengths_<model>.png`: mean words by round, limited vs free, with a dashed line at 250.

If a model or cell has no data, skip that panel and write "no data" in it. Never plot a
missing value as 0.

### Step 1.5 — tests (`tests/test_analysis_v2.py`)

Write tests that load the fixture and assert every value in the "Expected results" table of
Step 1.1. Also test:
1. `parse_generation_id('long-07-few-limited-r3') == ('long-07', 'few', 'limited', 3)` and
   `parse_generation_id('dev-long-01-zero-free-r5') == ('dev-long-01', 'zero', 'free', 5)`.
2. A duplicate annotation line raises `ValueError`.
3. Running `analyze_cli` and `figures` on the fixture (output in pytest's `tmp_path`)
   produces every CSV and PNG listed above without error.

**Check:** `uv run pytest` — all tests pass, including the older ones.

### Step 1.6 — `app.py` (Streamlit, reads files only)

Rules: the app never starts a model call; it imports nothing that does (no `subprocess`,
no `runner`). It reads `data/v2/sources.jsonl`, `results/<model>/generations.jsonl`,
`results/<model>/ai-annotations.jsonl`, and `results/analysis/`. Keep the existing tests in
`tests/test_fixture.py` passing (update the asserted strings only if you also keep their
meaning: the app must say clearly when results do not exist yet).

Sidebar: model (only those with a `generations.jsonl`), document, prompt, length.
Header: requested model, number of test documents, how many generations are `success`,
and a warning banner "Results incomplete" if any scheduled generation is missing.

Tabs:
1. **Chain explorer** — original text, then rounds 1–5 for the chosen prompt and length.
   For each round: status, word count, "over 250 words; kept unchanged" when limited and
   over, and the output text. Missing rounds show "not available" with the status.
2. **Prompt comparison** — zero / one / few side by side for the chosen round.
3. **Evidence review** — table of ground-truth items with each item's label in the chosen
   summary, the quotation and rationale, then the unsupported claims. Use the wording
   "qualification omitted", "claim strengthened", etc. Never the word "safe".
4. **Results** — the tables from `results/analysis/<model>/` and the figures, with download
   buttons. If they do not exist: "No analysis results yet."

**Check:** `uv run streamlit run app.py` opens without errors with no results present, and
with the fixture copied into a temporary `results/` folder (do not commit that copy).

### Step 1.7 — push
```powershell
git add src/ai_telephone/analysis.py src/ai_telephone/analyze_cli.py src/ai_telephone/figures.py app.py tests/test_analysis_v2.py tests/fixtures/v2
git commit -m "Add v2 analysis, figures, and app"
git pull --rebase origin codex/ai-telephone
uv run pytest
git push origin codex/ai-telephone
```
Tell the human: "Phase 1 done" plus the test count.

### Step 1.8 — report skeleton (if time remains Saturday)

Create `report/report-draft.md` following the official template's section order (copy the
headings from the template; do not copy its instruction text):
Title; Authors (leave `[TEAM TO FILL]`); Abstract (`[WRITE LAST]`); 1 Introduction;
2 Related Work; 3 Methods; 4 Results (`[AWAITING DATA]` — no numbers); 5 Discussion;
6 Conclusion; Code and Data; Author Contributions (`[TEAM TO FILL]`); LLM Usage Statement;
References; Appendix A "Limitations and Dual-Use / Ethical Considerations"; Appendix B
prompts and examples; Appendix C annotator and audit; Appendix D environment and settings.
Fill Methods from `design-v2.md`. Write no results, no numbers, and no references you have
not opened and verified.

---

## Phase 2 — Terra development run (Sunday morning)

**Wait** until the human tells you the Claude side has pushed "v2 runner ready".

### Step 2.1
```powershell
git pull --rebase origin codex/ai-telephone
uv sync
uv run pytest
uv run python -m ai_telephone.runner validate --data data/v2/sources.jsonl
```
**Check:** tests pass; validate prints 18 documents. Otherwise **STOP**.

### Step 2.2 — run the three development documents
```powershell
uv run python -m ai_telephone.runner run-dev --model terra --data data/v2/sources.jsonl --document dev-long-01
uv run python -m ai_telephone.runner run-dev --model terra --data data/v2/sources.jsonl --document dev-long-02
uv run python -m ai_telephone.runner run-dev --model terra --data data/v2/sources.jsonl --document dev-long-03
```
Each makes 30 calls (3 prompts × 2 lengths × 5 rounds). Note the start and end time of
each. If a command stops with an error, rerun the **same** command once (it resumes). If it
stops again: **STOP** and report the error line.

### Step 2.3 — export and report
```powershell
uv run python -m ai_telephone.runner export --model terra --split development
git add results/terra/generations-development.jsonl
git commit -m "Add Terra development run export"
git pull --rebase origin codex/ai-telephone
git push origin codex/ai-telephone
```
Report to the human: number of `success` / failed calls, average seconds per call, and how
many `limited` outputs were over 250 words.

---

## Phase 3 — final Terra collection (Sunday from about 10:00)

**Wait** until the human says "frozen" and `freeze/terra.json` exists after pulling.

### Step 3.1 — verify the freeze
```powershell
git pull --rebase origin codex/ai-telephone
uv run python -m ai_telephone.freeze --verify freeze/terra.json
```
**Check:** it prints `verified`. If it reports any mismatch: **STOP**. Do not run.

### Step 3.2 — run
```powershell
uv run python -m ai_telephone.runner run-final --model terra --manifest freeze/terra.json
```
450 calls. Keep the laptop awake and on power. If it stops because of a network or
transient error, rerun the same command; it skips completed calls. If it stops with an
authentication, quota, or model-access error: **STOP**, push nothing, report.

### Step 3.3 — export and push
```powershell
uv run python -m ai_telephone.runner export --model terra
git add results/terra/generations.jsonl
git commit -m "Add final Terra generations"
git pull --rebase origin codex/ai-telephone
git push origin codex/ai-telephone
```
Report: counts by status, total time. The Claude side then runs the AI annotator.

---

## Phase 4 — human audit (Sunday about 13:00; the human does this, not the agent)

The human labels a blinded CSV by hand, following `docs/annotation.md`. The agent must not
fill in labels.

---

## Phase 5 — analysis and report (Sunday about 14:00 to 19:30)

### Step 5.1 — run the analysis
After `results/{terra,haiku,gemini}/generations.jsonl` and `ai-annotations.jsonl` are all
pushed:
```powershell
git pull --rebase origin codex/ai-telephone
uv run python -m ai_telephone.analyze_cli --results results --sources data/v2/sources.jsonl --out results/analysis
uv run python -m ai_telephone.figures --analysis results/analysis --out results/analysis/figures
git add results/analysis
git commit -m "Add analysis tables and figures"
git push origin codex/ai-telephone
```

### Step 5.2 — fill the report draft
1. Results section: the primary contrast per model (from `primary.csv`), trajectories,
   error categories, unsupported claims, length compliance, failures, and human–AI
   agreement (the Claude side provides `results/<model>/audit-agreement.json`). Copy
   numbers exactly; round to 2 decimals; always give n and the 95% interval.
2. A null or negative result is a valid result. Report it plainly.
3. Cross-model differences: describe only. Never write that one model "is better" causally;
   model and harness are confounded.
4. Appendix A must cover: synthetic sources plus three papers; 15 documents; one output per
   cell; vendor CLI harnesses rather than bare APIs (Terra via Codex, Haiku via Claude Code,
   Gemini via Antigravity); AI annotator validated only on an audit sample; no measurement
   of human decisions; possible memorisation of the real papers; possible misuse of polished
   summaries to make weak evidence look strong; no private or personal data used.
5. Hand the draft to the human to paste into the official template and to the Claude side
   to check every number against `results/analysis/`.
