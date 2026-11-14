# Orchestrator status

Updated by the orchestrator only. A step moves to **done** only after its gate is verified.
Plans: `docs/plan-claude.md` (Claude side, steps 1–8), `docs/plan-codex.md` (Codex side,
phases 0–5). Design: `docs/design-v2.md`.

| Step | Owner | Status | Gate evidence |
|---|---|---|---|
| 1 Pipeline v2 code | Claude (Sonnet agent) | in progress | — |
| 2.1 Fictional sources | Claude (Sonnet agent) | in progress | — |
| 2.2 Paper excerpts | **Team (human)** | waiting for a teammate | — |
| 3 Source review | **Team (human)** | blocked by 1, 2 | — |
| 4 Development runs | Claude + Codex | blocked by 3 | — |
| 5 Freeze | **Team sign-off** | blocked by 4 | — |
| 6 Final collection | Claude + Codex | blocked by 5 | — |
| 7 Annotation + audit | Claude + **Team** | blocked by 6 | — |
| 8 Analysis + report check | Codex + Claude | blocked by 7 | — |
| Codex phase 0–1 | Codex teammate | can start now | — |

## Log
- 2026-11-14 16:30 — Plans v2 written; Steps 1 and 2.1 dispatched.
