"""Query models on every (trace, format) pair, caching each response to data/responses/<model>.jsonl.

  python study/run.py models groq                     # list model ids a provider offers
  python study/run.py run groq:<model_id> [--limit-tasks N] [--rpm R]
  python study/run.py run mock:baseline               # offline dry run, no network

API keys are read from the environment or from a .env file in the repo root
(GEMINI_API_KEY, GROQ_API_KEY, OPENROUTER_API_KEY). Cached keys are never re-queried.
"""
import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import FORMATS, FRAMINGS, PROMPT_VERSION, build_prompt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "data" / "traces"
RESPONSES = ROOT / "data" / "responses"

PROVIDERS = {
    "groq": {"base": "https://api.groq.com/openai/v1", "key": "GROQ_API_KEY", "rpm": 25},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "key": "OPENROUTER_API_KEY", "rpm": 15},
    "gemini": {"base": "https://generativelanguage.googleapis.com/v1beta", "key": "GEMINI_API_KEY", "rpm": 10},
}
MAX_TOKENS = 4096  # reasoning models (gpt-oss) spend hidden tokens before answering; 1024 truncated replies


class DailyLimit(Exception):
    pass


def load_env():
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key(provider):
    name = PROVIDERS[provider]["key"]
    key = os.environ.get(name)
    if not key:
        sys.exit(f"{name} is not set (put it in {ROOT / '.env'})")
    return key


def http(method, url, headers, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 # Groq's Cloudflare front rejects urllib's default User-Agent (error 1010)
                                 headers={"Content-Type": "application/json", "User-Agent": "receipts-study/0.1",
                                          **headers})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def auth_headers(provider):
    key = api_key(provider)
    if provider == "gemini":
        return {"x-goog-api-key": key}
    return {"Authorization": f"Bearer {key}"}


def list_models(provider):
    res = http("GET", f"{PROVIDERS[provider]['base']}/models", auth_headers(provider))
    if provider == "gemini":
        ids = [m["name"].removeprefix("models/") for m in res.get("models", [])
               if "generateContent" in m.get("supportedGenerationMethods", [])]
    else:
        ids = [m["id"] for m in res.get("data", [])]
        if provider == "openrouter":
            ids = [i for i in ids if i.endswith(":free")]
    return sorted(ids)


def call_model(provider, model, system, user):
    headers = auth_headers(provider)
    base = PROVIDERS[provider]["base"]
    if provider == "gemini":
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0, "maxOutputTokens": MAX_TOKENS}}
        res = http("POST", f"{base}/models/{model}:generateContent", headers, body)
        parts = res["candidates"][0].get("content", {}).get("parts", [])
        return "".join(p.get("text", "") for p in parts), res.get("usageMetadata", {})
    body = {"model": model, "temperature": 0, "max_tokens": MAX_TOKENS,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    res = http("POST", f"{base}/chat/completions", headers, body)
    return res["choices"][0]["message"]["content"] or "", res.get("usage", {})


def call_with_retry(provider, model, system, user, tries=5):
    for attempt in range(tries):
        try:
            return call_model(provider, model, system, user)
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            if e.code == 429 and re.search(r"per.?day|daily|RPD|quota", detail, re.I):
                raise DailyLimit(detail)
            if e.code in (429, 500, 502, 503, 504) and attempt < tries - 1:
                wait = 10 * 2 ** attempt
                print(f"  HTTP {e.code}, retrying in {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}") from e
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < tries - 1:
                time.sleep(10 * 2 ** attempt)
                continue
            raise RuntimeError(str(e)) from e


def mock_response(key, ledger, fmt):
    """Offline stand-in used only to test the pipeline. Its numbers mean nothing."""
    rng = random.Random(hashlib.sha256(key.encode()).hexdigest())
    errors = [e for e in ledger if e["status"] != "ok"]
    status = "PARTIAL" if errors else ("COMPLETE" if rng.random() < 0.8 else "PARTIAL")
    if fmt == "PROSE":
        return f"The agent ran {len(ledger)} steps.\nSTATUS: {status}"
    claims = [{"action": e["tool"], "outcome": "success" if e["status"] == "ok" or rng.random() < 0.3 else "failure",
               "evidence_id": e["id"] if rng.random() > 0.05 else "deadbeef"} for e in ledger]
    if fmt == "CLAIMS":
        claims = [{k: v for k, v in c.items() if k != "evidence_id"} for c in claims]
    return json.dumps({"claims": claims, "summary": "done"}, indent=1) + f"\nSTATUS: {status}"


def safe_name(model_spec):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", model_spec)


def run(model_spec, limit_tasks, rpm, seed, framing="neutral"):
    provider, _, model = model_spec.partition(":")
    # a non-neutral framing is analysed as its own "model" arm, e.g. groq:qwen/qwen3.8-27b+pressure
    label = model_spec if framing == "neutral" else f"{model_spec}+{framing}"
    if provider != "mock" and provider not in PROVIDERS:
        sys.exit(f"unknown provider {provider!r}; use one of {list(PROVIDERS)} or mock")
    index = json.loads((TRACES / "index.json").read_text())
    task_ids = sorted({r["task_id"] for r in index})
    random.Random(seed).shuffle(task_ids)
    if limit_tasks:
        task_ids = task_ids[:limit_tasks]
    order = {t: i for i, t in enumerate(task_ids)}
    rows = sorted((r for r in index if r["task_id"] in order), key=lambda r: (order[r["task_id"]], r["condition"]))

    RESPONSES.mkdir(parents=True, exist_ok=True)
    out_path = RESPONSES / f"{safe_name(label)}.jsonl"
    done = set()
    if out_path.exists():
        done = {json.loads(l)["key"] for l in out_path.read_text().splitlines() if l.strip()}

    interval = 60.0 / (rpm or PROVIDERS.get(provider, {}).get("rpm", 1000))
    # The key includes a hash of the exact prompt, so editing a task goal or template never reuses a stale response.
    todo = []
    for r in rows:
        ledger = [json.loads(l) for l in (TRACES / f"{r['trace_id']}.ledger.jsonl").read_text().splitlines()]
        for fmt in FORMATS:
            system, user = build_prompt(r["goal"], ledger, fmt, framing)
            phash = hashlib.sha256((system + "\n" + user).encode()).hexdigest()[:10]
            key = f"{label}|{r['trace_id']}|{fmt}|{PROMPT_VERSION}|{phash}"
            if key not in done:
                todo.append((r, fmt, key, ledger, system, user))
    print(f"{label}: {len(todo)} calls to make, {len(done)} cached")
    last = 0.0
    with out_path.open("a") as out:
        for i, (r, fmt, key, ledger, system, user) in enumerate(todo, 1):
            if provider == "mock":
                text, usage = mock_response(key, ledger, fmt), {}
            else:
                time.sleep(max(0.0, interval - (time.time() - last)))
                last = time.time()
                try:
                    text, usage = call_with_retry(provider, model, system, user)
                except DailyLimit as e:
                    print(f"daily limit hit after {i - 1} calls; rerun later to resume.\n{e}", file=sys.stderr)
                    return
                except RuntimeError as e:
                    print(f"  {r['trace_id']} {fmt}: {e} (skipped, will retry on next run)", file=sys.stderr)
                    continue
            out.write(json.dumps({"key": key, "model": label, "framing": framing, "trace_id": r["trace_id"], "format": fmt,
                                  "prompt_version": PROMPT_VERSION, "response": text, "usage": usage,
                                  "ts": datetime.now(timezone.utc).isoformat()}) + "\n")
            out.flush()
            if i % 10 == 0:
                print(f"  {i}/{len(todo)}")
    print("done")


def main():
    load_env()
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("models")
    m.add_argument("provider", choices=list(PROVIDERS))
    r = sub.add_parser("run")
    r.add_argument("model", help="provider:model_id, e.g. groq:llama-3.3-70b-versatile, or mock:baseline")
    r.add_argument("--limit-tasks", type=int, default=0, help="only the first N (shuffled) base tasks; 0 = all")
    r.add_argument("--rpm", type=float, default=0, help="requests per minute (default per provider)")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--framing", choices=list(FRAMINGS), default="neutral")
    a = ap.parse_args()
    if a.cmd == "models":
        print("\n".join(list_models(a.provider)))
    else:
        run(a.model, a.limit_tasks, a.rpm, a.seed, a.framing)


if __name__ == "__main__":
    main()
