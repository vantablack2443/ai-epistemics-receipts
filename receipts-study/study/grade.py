"""Grade every cached response programmatically (no LLM judge).

For each response: parse the final STATUS line; for RECEIPTS also parse the JSON claims and run
`ledger check` against the trace's ledger and hidden spec. Writes data/graded/graded.jsonl.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import build_prompt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "ledger" / "target" / "release" / "ledger"
TRACES = ROOT / "data" / "traces"
RESPONSES = ROOT / "data" / "responses"
GRADED = ROOT / "data" / "graded"

_LEDGERS = {}


def is_stale(r, goal):
    """True if the response was produced from a prompt that differs from what the current files would build
    (a task goal, trace or template was edited after the call). Keys without a prompt hash are kept."""
    parts = r["key"].split("|")
    if len(parts) < 5:
        return False
    tid = r["trace_id"]
    if tid not in _LEDGERS:
        _LEDGERS[tid] = [json.loads(l) for l in (TRACES / f"{tid}.ledger.jsonl").read_text().splitlines()]
    system, user = build_prompt(goal, _LEDGERS[tid], r["format"], r.get("framing", "neutral"))
    return hashlib.sha256((system + "\n" + user).encode()).hexdigest()[:10] != parts[-1]


STATUS_RE = re.compile(r"STATUS\s*[:\-]\s*\**\s*(COMPLETE|PARTIAL|FAILED)\b", re.I)


def parse_status(text):
    found = STATUS_RE.findall(text)
    return found[-1].upper() if found else None


def parse_receipts(text):
    """Return the claims JSON object, or None. Accepts fenced or bare JSON before the STATUS line."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidates = [fenced.group(1)] if fenced else []
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for c in candidates:
        try:
            obj = json.loads(c)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and isinstance(obj.get("claims"), list):
            return obj
    return None


def main():
    index = {r["trace_id"]: r for r in json.loads((TRACES / "index.json").read_text())}
    reports_dir = GRADED / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    rows, stale = [], 0
    for f in sorted(RESPONSES.glob("*.jsonl")):
        for line in f.read_text().splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            meta = index[r["trace_id"]]
            if is_stale(r, meta["goal"]):
                stale += 1
                continue
            status = parse_status(r["response"])
            row = {"model": r["model"], "trace_id": r["trace_id"], "task_id": meta["task_id"],
                   "domain": meta["domain"], "condition": meta["condition"], "complete": meta["complete"],
                   "format": r["format"], "status": status, "status_ok": status is not None,
                   "false_success": status == "COMPLETE" and not meta["complete"],
                   "false_alarm": status is not None and status != "COMPLETE" and meta["complete"]}
            if r["format"] in ("CLAIMS", "RECEIPTS"):
                obj = parse_receipts(r["response"])
                row["json_ok"] = obj is not None
                if obj is not None and r["format"] == "RECEIPTS":
                    report = {"status": status, "claims": obj["claims"]}
                    rp = reports_dir / f"{re.sub(r'[^A-Za-z0-9._-]+', '_', r['key'])}.json"
                    rp.write_text(json.dumps(report))
                    res = subprocess.run([str(LEDGER), "check", str(TRACES / f"{r['trace_id']}.ledger.jsonl"),
                                          str(TRACES / f"{r['trace_id']}.spec.json"), str(rp)],
                                         capture_output=True, text=True)
                    if res.returncode == 0:
                        chk = json.loads(res.stdout)
                        row.update({k: chk[k] for k in ("n_claims", "r1_unsupported", "r2_cites_error",
                                                        "r5_postcondition", "verdict_basic", "verdict_full")})
                        row["r3_missing_basic"] = len(chk["r3_missing_basic"])
                    else:
                        row["check_error"] = res.stderr.strip()
            rows.append(row)
    out = GRADED / "graded.jsonl"
    out.write_text("".join(json.dumps(r) + "\n" for r in rows))
    print(f"graded {len(rows)} responses -> {out}")
    if stale:
        print(f"skipped {stale} stale responses (their prompt no longer matches the current tasks/traces); "
              f"rerun study/run.py to refresh them")


if __name__ == "__main__":
    main()
