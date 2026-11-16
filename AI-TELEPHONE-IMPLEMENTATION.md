# AI Telephone: implementation plan

## Goal
Build a reproducible experiment and local demo that measure how repeated summaries change the qualifications in fictional engineering handoffs. Compare ordinary prose, prose instructed to preserve qualifications, and structured summaries with the same preservation instruction. Submit a research report; prepare the video script but do not record the video yet.

## Step 1: Access and setup
1. Check `codex login status` in a normal user terminal. The sandboxed check previously failed to find the home directory; this does not establish whether the account is authenticated.
2. Install ECC for Codex using `codex plugin marketplace add affaan-m/ECC`, `codex plugin add ecc@ecc`, and `codex plugin list --json`. Restart Codex and review any hook trust request. For Claude Code, use `/plugin marketplace add https://github.com/affaan-m/ECC` and `/plugin install ecc@ecc` inside Claude Code.
3. Choose the cheapest model available on the team's existing account. If using Claude Code, choose `claude-haiku-5-5` with `claude --model claude-haiku-5-5`. Do not purchase credits or upgrade without authorization. Smoke-test model access and record the actual model and tool version. Pin one model and one configuration throughout the final experiment; do not silently change models between conditions.
4. Create a separate `ai-telephone` project in this workspace. Use Python 3.11, uv, Streamlit, pandas, NumPy, matplotlib, Pydantic and pytest. Keep the existing receipts study untouched. Record any reused pre-sprint code in the README and report.

## Step 2: Data and protocol
1. Write 36 fictional engineering handoffs, 180–240 words each: six development examples and 30 held-out examples. Divide held-out examples equally among tentative findings, limited scope, untested assumptions, conditional approval, and conflicting evidence. Include genuinely well-supported findings as controls.
2. For each source, identify its principal finding and three critical qualifications. Record source quotations, intended meanings and acceptable paraphrases. Two people review the ground truth before final collection. Do not include credentials, personal data or real private company documents.
3. Freeze the sources, split, prompts, scoring rubric, model, configuration and metrics before generating the final set. Randomize the execution order with seed 1729.
4. Apply three prompts to each document, using limits of 100, 70 and 45 words across successive rounds. A is ordinary prose; B adds instructions to preserve evidence limits, uncertainty and conditions; C uses B's instructions with Finding, Evidence, Limits and Action headings. Headings count toward the limit. Later rounds receive only the prior output, never the original or the ground truth.
5. Add a direct 45-word ordinary summary from each original as a compression control. This yields 60 development outputs and 300 final outputs. Save the first successful output even if it violates the budget; log violations rather than regenerating preferred results.

## Step 3: Runner and local application
1. Implement an experiment CLI, analysis CLI and read-only Streamlit viewer. Use one SQLite writer for results and annotations; retain exact prompts, raw outputs, event logs, versions, settings, failure details and usage when available. Export results as CSV and JSONL.
2. Use a provider adapter appropriate to the selected coding tool. Launch each summary in a fresh noninteractive process with the pinned model, an isolated working directory and no tools or file access. Audit event output for actual tool use. A run through an agent harness measures that harness plus the model; do not describe it as a bare-model API experiment.
3. Resume by stable generation ID; never overwrite successful outputs. Retry transient operational failures at most twice; preserve failed attempts. Stop on account, quota or model-access errors. Do not treat missing outputs as observations.
4. Build views for source and summary chains, side-by-side method comparisons, evidence and annotation review, and aggregate results. Show model, run ID, sample size, completion status and output length. Merely viewing the app must never launch a model call.

## Step 4: Annotation and analysis
1. Score every output against the original source for each ground-truth item: preserved, omitted, strengthened, weakened or contradicted. Record unsupported new claims separately and supply quotations and explanations for non-preserved labels.
2. One reviewer scores all 300 final outputs. A second independently scores the 120 endpoints and 30 balanced intermediate outputs. Hide condition labels and prior annotations where feasible; acknowledge that visible formatting prevents complete blinding. Report agreement before adjudication and retain the original ratings.
3. The primary metric is the fraction of three critical qualifications preserved per document at round three. Compare structured preservation versus ordinary prose as paired document-level differences. Report instruction-only versus ordinary prose, structured versus instruction-only, direct versus chained summaries, trajectories, main-finding retention, overstatement, contradiction, unsupported claims, conditional-approval loss and word-limit compliance.
4. Compute paired document bootstrap intervals using 10,000 resamples and seed 1729. Produce preservation-by-round, error-category and direct-versus-chain figures, plus a paired comparison table. Explicitly disclose sample size, missing outputs, single-model scope and annotation uncertainty.

## Step 5: Verification
Test that later rounds receive only the preceding summary; ground truth never enters prompts; budgets and model settings are consistent; headings count as words; resume cannot duplicate outputs; missing and failed runs are distinct; overlength results are retained; prohibited tool events are flagged; and metrics/bootstrap calculations match hand-checked examples. Automated tests use fixtures, never fabricated research results. Run one real development case through the complete pipeline before the remaining development cases, then freeze the protocol.

## Step 6: Report, video package and submission
1. Use the official template at https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs/edit. Write the 150–250 word abstract last. Include introduction, related work, methods, measured results, discussion, conclusion, verified references, code/data links, contributions, and an LLM usage statement.
2. Include the required Limitations and Dual-Use / Ethical Considerations appendix: synthetic data, small sample, one model/harness, limited reviewer blinding, model failures, risks of misleading summaries, and data handling. Add exact prompts and detailed results to appendices. Never fabricate results or references.
3. Package code, frozen data, instructions, dependency lockfile, protocol, annotations, analysis and figures; disclose external tools and preexisting work. Remove secrets and unrelated personal metadata.
4. Prepare six slides and a four-minute script covering the problem, one actual chain, methods, results, limitations and artifacts. Defer recording and editing.
5. Verify the PDF against the event guidelines at https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15: at most eight body pages excluding references and appendices, required appendix, authors and affiliations, 25 MB upload maximum. Check every page and link. Obtain actual team information and agreement to the submission terms. Target November 15 at 20:00 Berlin; the official deadline is November 16 at 12:59 Berlin. Submit through the official form and verify the confirmation email and PDF.

## Delivery order and fallback
Prepare the dataset and report skeleton while building the runner. Run and annotate development examples, freeze the protocol, execute and review the final set, calculate results, then complete the app and report. If time or quota is limited, collect a predetermined balanced prefix of at least ten documents and disclose the smaller sample. Cut visual polish before research integrity. If model access fails, deliver a clearly labeled prototype and protocol rather than claimed findings.
