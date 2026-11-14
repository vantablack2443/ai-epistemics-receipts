# Orchestrator status

A step moves to **done** only after its gate is verified. Plans: `docs/plan-claude.md`
(Claude side: Haiku agents, steps 1–8), `docs/plan-codex.md` (Codex side: Terra, phases
0–5). Design and roles: `docs/design-v2.md`. Briefs: `docs/source-brief.md`,
`docs/examples-brief.md`.

**Paused: nothing runs until the Claude-side team member says go.**

| Step | Owner | Status |
|---|---|---|
| 1 Pipeline v2 code | Claude side (Haiku agent) | partly built, uncommitted, 74 tests pass; paused |
| 2.1 Sources long-01–06, dev-long-01–02 | Claude side (Haiku) | not started |
| 2.1 Sources long-07–12, dev-long-03 | Codex side (Terra) | not started |
| 2.1b Examples E1–E3 + Haiku candidates | Claude side (Haiku) | not started |
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
- 2026-11-14 16:00 — Plans v2 written and pushed.
- 2026-11-14 16:05 — Step 1 started on Sonnet; stopped at the team's request (all agent work
  must use the cheapest model: Haiku on the Claude side, Terra on the Codex side). Partial
  code kept for the Haiku agent to finish. No sources drafted.
- 2026-11-14 16:20 — Final roles: annotator stays `claude-opus-5-5`; sources and prompt
  examples split between Haiku and Terra; examples built from real cheap-model outputs.
