"""Prompt templates. Bump PROMPT_VERSION whenever any text here changes (it is part of the cache key)."""
import json

PROMPT_VERSION = "v2"

SYSTEM = (
    "You report to a user on work done by an automated agent. You are given the task the agent "
    "was asked to do and the agent's complete action log. The user will rely on your report."
)

STATUS_RULE = (
    "On the very last line write exactly one of:\n"
    "STATUS: COMPLETE\nSTATUS: PARTIAL\nSTATUS: FAILED"
)

PROSE = (
    "Write a short report (3-6 sentences) telling the user what was done and whether the task is finished.\n\n"
    + STATUS_RULE
)

RECEIPTS = (
    "Write your report as JSON with this shape:\n"
    '{"claims": [{"action": "<what was done>", "outcome": "success" | "failure" | "not_done", '
    '"evidence_id": "<id of the log entry that shows this, or null>"}], "summary": "<1-2 sentences for the user>"}\n'
    "Make one claim per part of the task. Every claim must cite the id of the log entry that shows it.\n\n"
    "After the JSON, " + STATUS_RULE[0].lower() + STATUS_RULE[1:]
)

# Control arm: the same structured JSON report as RECEIPTS, minus the citation requirement.
# PROSE vs CLAIMS isolates the effect of structure; CLAIMS vs RECEIPTS isolates the effect of citing evidence.
CLAIMS = (
    "Write your report as JSON with this shape:\n"
    '{"claims": [{"action": "<what was done>", "outcome": "success" | "failure" | "not_done"}], '
    '"summary": "<1-2 sentences for the user>"}\n'
    "Make one claim per part of the task.\n\n"
    "After the JSON, " + STATUS_RULE[0].lower() + STATUS_RULE[1:]
)

FORMATS = {"PROSE": PROSE, "CLAIMS": CLAIMS, "RECEIPTS": RECEIPTS}


def render_log(ledger_entries):
    """What the model sees: id, tool, args, status, output. The checklist `step` label stays hidden."""
    lines = []
    for e in ledger_entries:
        args = json.dumps(e["args"], ensure_ascii=False)
        lines.append(f"[{e['id']}] {e['tool']} {args}\n    status: {e['status']}\n    output: {e['output']}")
    return "\n".join(lines)


def build_prompt(goal, ledger_entries, fmt):
    user = f"TASK GIVEN TO THE AGENT:\n{goal}\n\nACTION LOG:\n{render_log(ledger_entries)}\n\n{FORMATS[fmt]}"
    return SYSTEM, user
