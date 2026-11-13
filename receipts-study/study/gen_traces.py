"""tasks.yaml -> 96 traces (24 tasks x 4 legibility conditions), each built into a hash-chained ledger.

Writes, per trace, into data/traces/:
  <trace_id>.trace.json   input to `ledger build`
  <trace_id>.ledger.jsonl hash-chained ledger (what the model sees, minus the `step` field)
  <trace_id>.spec.json    hidden ground truth for the checker: required steps + postcondition patterns
and data/traces/index.json with one row per trace.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger" / "target" / "release" / "ledger"
OUT = ROOT / "data" / "traces"
CONDITIONS = ["control", "loud", "quiet", "absent"]


def validate(task):
    names = [s["name"] for s in task["steps"]]
    assert task["fragile"] in names, f"{task['id']}: fragile step {task['fragile']} not in steps"
    for s in task["steps"]:
        assert re.search(s["ok_pattern"], s["ok"]), f"{task['id']}/{s['name']}: ok output fails its own pattern"
    frag = next(s for s in task["steps"] if s["name"] == task["fragile"])
    assert not re.search(frag["ok_pattern"], task["quiet"]), f"{task['id']}: quiet output passes ok_pattern"
    assert not re.search(frag["ok_pattern"], task["loud"]), f"{task['id']}: loud output passes ok_pattern"


def entries_for(task, cond):
    entries = []
    for s in task["steps"]:
        status, output = "ok", s["ok"]
        if s["name"] == task["fragile"]:
            if cond == "absent":
                continue
            if cond == "loud":
                status, output = "error", task["loud"]
            elif cond == "quiet":
                output = task["quiet"]
        entries.append({"step": s["name"], "tool": s["tool"], "args": s.get("args", {}),
                        "status": status, "output": output})
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
