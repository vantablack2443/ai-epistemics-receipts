# Orchestrator status

A step moves to **done** only after its gate is verified. Plans: `docs/plan-claude.md`
(Claude side: Haiku agents, steps 1–8), `docs/plan-codex.md` (Codex side: Terra, phases
0–5). Design and roles: `docs/design-v2.md`. Briefs: `docs/source-brief.md`,
`docs/examples-brief.md`.

**Mode (team decision 16:56): run continuously, no human-review pauses. All review, selection and sign-off steps are done by AI agents (Haiku) and verified by the orchestrator, and recorded as AI, never as human. Opus annotation runs later. Terra-side pieces not pushed by their cutoff are drafted by Haiku as a recorded fallback.**

| Step | Owner | Status |
|---|---|---|
| 1 Pipeline v2 code | Claude side (Haiku agent) | **done** — gate verified 16:30: 97 tests; exact prompt text for all 6 variants; all CLI commands; Gemini tools blocked (sandbox + deny rules) and detected; real Gemini smoke `GEMINI_OK` |
| 2.1 Sources long-01–06, dev-long-01–02 | Claude side (Haiku) | **done** — gate 16:50: 8 docs, 0 flags, max overlap 0.18 |
| 2.1 Sources long-07–12, dev-long-03 | Codex side (Terra) | not started |
| 2.1b Examples E1–E3 + Haiku candidates | Claude side (Haiku) | **done** — E1–E3 (153/184/244 words), 6 candidates (4 over 60 words, kept) |
| 2.1b Examples E4–E5 + Terra candidates | Codex side (Terra) | not started |
| 2.2 Paper excerpts (optional) | Team (human) | not started |
| 3 Source review (AI) | Haiku agent + orchestrator | **done for Haiku half** — 50 approved, 7 meanings revised, 0 rejected; `data/v2/sources.jsonl` built (interim, 8 docs; rebuilt when Terra half arrives) |
| 3b Example selection (AI) | Haiku agent | running for E1–E3; E4–E5 cutoff 18:00 |
| 4 Development runs | both sides | Haiku dev run done (60/60 success, 6.8 s/call); prompt fixed; one/few dev chains to rerun once examples are final |
| 5 Freeze | Team sign-off | blocked by 4 |
| 6 Final collection | both sides | blocked by 5 |
| 7 Opus annotation + human audit | Claude side + team | blocked by 6 |
| 8 Analysis + report check | Codex side + Claude side | blocked by 7 |
| Codex phases 0, 0b, 1 | Codex side | ready to start |

## Log
- 2026-11-14 17:20 — Team decision: use the Haiku backups now. All 15 sources (12 test, 3 dev) and
  all 5 examples are Haiku-drafted and AI-reviewed (98 items approved, 9 revised, 0 rejected).
  `data/v2/sources.jsonl` rebuilt; `data/v2/examples/selected.json` installed (bad types: 2
  hallucination, 3 drop/strengthen). Codex Phase 0b cancelled; Terra freeze made by the Codex
  side from the same frozen files.
- 2026-11-14 17:15 — Haiku dev run: 60/60 success, mean 6.8 s/call, no tool events. Problem:
  zero-shot limited outputs were 10/10 over 250 words and used markdown, example-based ones
  were plain and shorter. Prompt fixed for every variant (hard-limit wording; plain-prose
  line). Check run (10 zero-limited calls): 9/10 within 250 (one at 262), all plain prose.
  Free-length outputs differ strongly by prompt (≈620 zero vs ≈190 few words): report as a
  finding and treat length as a covariate; the limited scenario is the controlled comparison.
- 2026-11-14 17:10 — Gate 3 (AI review, Haiku half) passed; revisions are accuracy fixes (e.g.
  long-06-f1 "replicated" → repeated by the same group). Noted: long-05 and dev-long-02 text
  contains the words "invented"/"fictional" (harmless, left unedited). build_sources tool: 20
  tests, suite 116. Haiku development run started (artifacts/v2-haiku-dev-provisional.sqlite;
  one/few chains use provisional examples and will be rerun after selection).
- 2026-11-14 16:56 — Continuous mode. Dispatched Haiku agents: AI review of the 8 Haiku sources;
  AI selection of good/bad examples for E1–E3. Cutoffs for Terra-side pieces: E4–E5 by 18:00,
  long-07–12 + dev-long-03 by 20:00; otherwise Haiku drafts them (recorded fallback).
- 2026-11-14 16:50 — Gate 2 (Claude half) passed. long-03 and long-06 failed the agent's
  stricter 1,000-word floor; the brief's rule is 900–1,500, so the **first attempt passing the
  brief's checks** was used (long-03 attempt 1, 961 words; long-06 attempt 1, 909 words), no
  text edited. For human review: several quotations are short anchors (long-03-q1, -q4,
  long-04-f2, long-05-f2, long-06-f1); their `meaning` carries the content to preserve.
- 2026-11-14 16:40 — Team decision: Gemini Flash is only an optional third test model, run by
  the team member by hand at the end if time allows. No agent or orchestrator makes Gemini or
  Google calls. Antigravity backup annotator removed; Opus 5.5 is the only annotator.
- 2026-11-14 16:30 — Gate 1 passed. Orchestrator fix: Antigravity executed tool calls in
  headless mode (detected, but after running). Added `--sandbox` and session-only deny rules;
  verified a tool-tempting prompt ends with run_command/read_file in state ERROR (not run).
  Provisional prompt examples remain until `selected.json` exists (loader in place).
- 2026-11-14 16:00 — Plans v2 written and pushed.
- 2026-11-14 16:05 — Step 1 started on Sonnet; stopped at the team's request (all agent work
  must use the cheapest model: Haiku on the Claude side, Terra on the Codex side). Partial
  code kept for the Haiku agent to finish. No sources drafted.
- 2026-11-14 16:45 — Team said go. Haiku agents dispatched: Step 1 (finish pipeline) and
  Step 2 (long-01–06, dev-long-01–02, E1–E3, Haiku candidates for E1–E3), each document in a
  fresh `claude -p --model claude-haiku-5-5` session. Papers picked (2610.27380, 2611.15142,
  2609.32390; fallback 2604.02351); excerpts and their items are a human task.
- 2026-11-14 16:20 — Final roles: annotator stays `claude-opus-5-5`; sources and prompt
  examples split between Haiku and Terra; examples built from real cheap-model outputs.
