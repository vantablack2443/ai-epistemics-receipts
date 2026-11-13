"""tasks.yaml -> 120 traces (24 tasks x 5 legibility conditions), each built into a hash-chained ledger.

Every trace also gets N_NOISE benign distractor entries (status ok, unrelated to the required steps).
They are chosen per task from a fixed seed, so all 5 conditions of a task share the same distractors.

Writes, per trace, into data/traces/:
  <trace_id>.trace.json   input to `ledger build`
  <trace_id>.ledger.jsonl hash-chained ledger (what the model sees, minus the `step` field)
  <trace_id>.spec.json    hidden ground truth for the checker: required steps + postcondition patterns
and data/traces/index.json with one row per trace.
"""
import hashlib
import json
import random
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger" / "target" / "release" / "ledger"
OUT = ROOT / "data" / "traces"
CONDITIONS = ["control", "loud", "quiet", "subtle", "absent"]

N_NOISE = 4
# Benign housekeeping calls. None of them is a required step and none changes whether the task is complete.
NOISE = [
    {"tool": "shell", "args": {"cmd": "date -u"}, "output": "Fri Nov 13 09:14:02 UTC 2026"},
    {"tool": "shell", "args": {"cmd": "whoami"}, "output": "svc-agent"},
    {"tool": "shell", "args": {"cmd": "df -h /tmp"}, "output": "/dev/sda2  40G  12G  28G  30% /tmp"},
    {"tool": "shell", "args": {"cmd": "uptime"}, "output": "09:14:07 up 41 days, load average: 0.42, 0.37, 0.31"},
    {"tool": "read_file", "args": {"path": "RUNBOOK.md"}, "output": "read 2.4 KB"},
    {"tool": "env_check", "args": {}, "output": "3 credentials loaded; network reachable"},
    {"tool": "lock_acquire", "args": {"name": "agent-run"}, "output": "acquired (ttl 900s)"},
    {"tool": "note", "args": {"text": "plan drafted; proceeding step by step"}, "output": "noted"},
    {"tool": "http_get", "args": {"url": "/health"},
     "output": "200 OK; {status: 'ok', warnings: ['TLS certificate expires in 21 days']}"},
]


def noise_plan(task):
    """[(slot, entry)]: entry goes before step number `slot` (slot == len(steps) means after the last step)."""
    rng = random.Random(int(hashlib.sha256(task["id"].encode()).hexdigest(), 16))
    picks = rng.sample(NOISE, N_NOISE)
    slots = sorted(rng.randrange(len(task["steps"]) + 1) for _ in picks)
    return [(slot, {"step": f"noise_{k}", "tool": n["tool"], "args": n["args"], "status": "ok", "output": n["output"]})
            for k, (slot, n) in enumerate(zip(slots, picks))]


def validate(task):
    names = [s["name"] for s in task["steps"]]
    assert task["fragile"] in names, f"{task['id']}: fragile step {task['fragile']} not in steps"
    for s in task["steps"]:
        assert re.search(s["ok_pattern"], s["ok"]), f"{task['id']}/{s['name']}: ok output fails its own pattern"
    frag = next(s for s in task["steps"] if s["name"] == task["fragile"])
    for cond in ("loud", "quiet", "subtle"):
        assert not re.search(frag["ok_pattern"], task[cond]), f"{task['id']}: {cond} output passes ok_pattern"
    assert len({task["quiet"], task["subtle"], frag["ok"]}) == 3, f"{task['id']}: quiet/subtle/ok outputs must differ"


def entries_for(task, cond):
    entries = []
    noise = noise_plan(task)
    for i, s in enumerate(task["steps"]):
        entries += [e for slot, e in noise if slot == i]
        status, output = "ok", s["ok"]
        if s["name"] == task["fragile"]:
            if cond == "absent":
                continue
            if cond == "loud":
                status, output = "error", task["loud"]
            elif cond in ("quiet", "subtle"):
                output = task[cond]
        entries.append({"step": s["name"], "tool": s["tool"], "args": s.get("args", {}),
                        "status": status, "output": output})
    entries += [e for slot, e in noise if slot == len(task["steps"])]
    return entries


def main():
    if not LEDGER.exists():
        sys.exit(f"build the ledger first: cargo build --release --manifest-path {ROOT / 'ledger' / 'Cargo.toml'}")
    tasks = yaml.safe_load((ROOT / "study" / "tasks.yaml").read_text())["tasks"]
    OUT.mkdir(parents=True, exist_ok=True)
    index = []
    for task in tasks:
        validate(task)
        spec = {"required": [{"name": s["name"], "ok_pattern": s["ok_pattern"]} for s in task["steps"]]}
        for cond in CONDITIONS:
            tid = f"{task['id']}__{cond}"
            trace = {"trace_id": tid, "goal": task["goal"], "entries": entries_for(task, cond)}
            (OUT / f"{tid}.trace.json").write_text(json.dumps(trace, indent=1))
            (OUT / f"{tid}.spec.json").write_text(json.dumps(spec, indent=1))
            ledger = subprocess.run([str(LEDGER), "build", str(OUT / f"{tid}.trace.json")],
                                    check=True, capture_output=True, text=True).stdout
            (OUT / f"{tid}.ledger.jsonl").write_text(ledger)
            index.append({"trace_id": tid, "task_id": task["id"], "domain": task["domain"],
                          "condition": cond, "complete": cond == "control", "goal": task["goal"]})
    (OUT / "index.json").write_text(json.dumps(index, indent=1))
    print(f"{len(tasks)} tasks -> {len(index)} traces in {OUT}")


if __name__ == "__main__":
    main()
