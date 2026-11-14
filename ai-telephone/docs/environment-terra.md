# Terra environment

Smoke test: 2026-11-14 17:03:30 Europe/Berlin (16:03:30 UTC).

```json
{
  "backend": "terra",
  "requested_model": "gpt-6.1-terra",
  "resolved_model": null,
  "cli_version": "codex-cli 0.169.0",
  "returncode": 0,
  "status": "success",
  "output": "TERRA_OK",
  "args": ["codex", "exec", "--model", "gpt-6.1-terra", "-c", "model_reasoning_effort=\"low\"", "--ephemeral", "--ignore-user-config", "--sandbox", "read-only", "--skip-git-repo-check", "--json", "--color", "never", "-"],
  "checked_utc": "2026-11-14T16:03:30.880446+00:00"
}
```

Codex version: `codex-cli 0.169.0`.

## Codex home names only

- `.chatgpt-projects`
- `.hook-trust`
- `.sandbox`
- `.sandbox-bin`
- `.sandbox-secrets`
- `.tmp`
- `app-server-control`
- `app-server-daemon`
- `archived_sessions`
- `attachments`
- `automations`
- `browser`
- `cache`
- `code-review-plugin`
- `computer-use`
- `dictation-history`
- `generated_images`
- `log`
- `logs`
- `mcp-oauth-locks`
- `node_repl`
- `packages`
- `pets`
- `plans`
- `plugins`
- `project-chatgpt-pairing`
- `project-chatgpt-provisioning`
- `project-metadata-locks`
- `rollout-migrations`
- `rules`
- `sessions`
- `shell_snapshots`
- `skills`
- `sqlite`
- `thread-writer-locks`
- `tmp`
- `tui-thread-reference-capabilities`
- `vendor_imports`
- `visualizations`
- `worktrees`
- `..codex-global-state.json.bak.tmp-1789125567174-2ecf5d0e-4286-47a5-98d5-95bda38d2965`
- `..codex-global-state.json.bak.tmp-1791114295886-b7fd049a-6330-442e-9d09-9dbcd9ad9ff9`
- `..codex-global-state.json.tmp-1784911111076-dbfe339b-0a5d-4735-bc65-c64a60b36244`
- `..codex-global-state.json.tmp-1787751818178-78d1b3d5-c7d8-47e5-8445-047ce265b533`
- `..codex-global-state.json.tmp-1788031008188-bb6024be-5d48-4c15-b6ae-46a17659ea35`
- `..codex-global-state.json.tmp-1790640807155-893e6b0e-7c24-4e14-b626-598e0e1d0a4f`
- `.codex-global-state.json`
- `.codex-global-state.json.bak`
- `.codex-provisioning-5f1c821fa440340c.guard`
- `.codex-provisioning-7406a49f4b50e420.guard`
- `.codex-provisioning-df2c9e89a6024d3c.guard`
- `.personality_migration`
- `.sandbox_migration`
- `.sqlite-maintenance.lock`
- `AGENTS.md`
- `auth.json`
- `auth.lock`
- `cap_sid`
- `chrome-native-hosts-v2.json`
- `chrome-native-hosts-v2.json.tmp-fca9683b-22a1-4b3f-b240-805c02394201`
- `config.toml`
- `goals_1.sqlite`
- `goals_1.sqlite-shm`
- `goals_1.sqlite-wal`
- `history.jsonl`
- `installation_id`
- `logs_2.sqlite`
- `logs_2.sqlite-shm`
- `logs_2.sqlite-wal`
- `memories_1.sqlite`
- `models_cache.codex_work_desktop.json`
- `models_cache.json`
- `queue_1.sqlite`
- `queue_1.sqlite-shm`
- `queue_1.sqlite-wal`
- `sandbox.2026-08-24.log`
- `sandbox.2026-08-26.log`
- `sandbox.2026-08-28.log`
- `sandbox.2026-09-03.log`
- `sandbox.2026-10-02.log`
- `session_index.jsonl`
- `session_index.jsonl.lock`
- `skill-installation-report.md`
- `state_5.sqlite`
- `state_5.sqlite-shm`
- `state_5.sqlite-wal`
- `thread_history_1.sqlite`
- `thread_history_1.sqlite-shm`
- `thread_history_1.sqlite-wal`
- `transcription-history.jsonl`
- `version.json`

## Instructions and plugins

Global Codex home AGENTS.md: yes. Repository AGENTS.md files: none found in the workspace scan (excluding ignored environments and Git metadata).

Installed, enabled plugin names: documents, pdf, spreadsheets, presentations, template-creator, codex-app-tools, browser, unified-computer-use, chrome, computer-use, visualize (two versions), ecc, gmail, google-drive, app-69ea4ed2cf7c8191b742ef3622479ddd, write-like-me, figma, app-69e1ea6c505c81918d6c8f0258a64906, browser-act, engineering-suite-grill-me, openai-templates, sites, plugin-management, work-pets. The plugin listing does not prove which instructions remain active in an experimental invocation.

Experimental calls use `--ignore-user-config`, an empty temporary working directory, and `--sandbox read-only`; the event stream is checked and any tool event invalidates the attempt.

The event stream did not expose a resolved model identity; the requested model is recorded in the invocation.
