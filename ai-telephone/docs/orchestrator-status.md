# Orchestrator status

A step moves to **done** only after its gate is verified. Plans: `docs/plan-claude.md`
(Claude side: Haiku agents, steps 1–8), `docs/plan-codex.md` (Codex side: Terra, phases
0–5). Design and roles: `docs/design-v2.md`. Briefs: `docs/source-brief.md`,
`docs/examples-brief.md`.

**Paused: nothing runs until the Claude-side team member says go.**

| Step | Owner | Status |
|---|---|---|
| 1 Pipeline v2 code | Claude side (Haiku agent) | **done** — gate verified 17:20: 97 tests; exact prompt text for all 6 variants; all CLI commands; Gemini tools blocked (sandbox + deny rules) and detected; real Gemini smoke `GEMINI_OK` |
| 2.1 Sources long-01–06, dev-long-01–02 | Claude side (Haiku) | **done** — gate 18:05: 8 docs, 0 flags, max overlap 0.18 |
| 2.1 Sources long-07–12, dev-long-03 | Codex side (Terra) | not started |
| 2.1b Examples E1–E3 + Haiku candidates | Claude side (Haiku) | **done** — E1–E3 (153/184/244 words), 6 candidates (4 over 60 words, kept) |
| 2.1b Examples E4–E5 + Terra candidates | Codex side (Terra) | not started |
| 2.2 Paper excerpts (optional) | Team (human) | not started |
| 3 Source review + example selection | Team (human) | blocked by 2 |
| 4 Development runs | both sides | blocked by 1, 3 |
| 5 Freeze | Team sign-off | blocked by 4 |
| 6 Final collection | both sides | blocked by 5 |
| 7 Opus annotation + human audit | Claude side + team | blocked by 6 |
| 8 Analysis + report check | Codex side + Claude side | blocked by 7 |
| Codex phases 0, 0b, 1 | Codex side | ready to start |

## Log
- 2026-11-14 18:05 — Gate 2 (Claude half) passed. long-03 and long-06 failed the agent's
  stricter 1,000-word floor; the brief's rule is 900–1,500, so the **first attempt passing the
  brief's checks** was used (long-03 attempt 1, 961 words; long-06 attempt 1, 909 words), no
  text edited. For human review: several quotations are short anchors (long-03-q1, -q4,
  long-04-f2, long-05-f2, long-06-f1); their `meaning` carries the content to preserve.
- 2026-11-14 17:35 — Team decision: Gemini Flash is only an optional third test model, run by
  the team member by hand at the end if time allows. No agent or orchestrator makes Gemini or
  Google calls. Antigravity backup annotator removed; Opus 5.5 is the only annotator.
- 2026-11-14 17:20 — Gate 1 passed. Orchestrator fix: Antigravity executed tool calls in
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
