"""Sequential, checkpointed Codex runner. Final execution requires a reviewed freeze."""
import argparse
import hashlib
import json
import random
import sqlite3
import subprocess
import time
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .models import Document
from .prompts import LIMITS, make_prompt, words

MODEL = 'gpt-6.1-terra'
def codex_binary():
    if os.name == 'nt':
        candidate = Path(os.environ['APPDATA']) / 'npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
        if not candidate.is_file():
            raise RuntimeError('Codex executable not found; configure its executable path before running')
        return str(candidate)
    return 'codex'

ARGS = ['codex', 'exec', '--model', MODEL, '-c', 'model_reasoning_effort="low"',
        '--ephemeral', '--ignore-user-config', '--sandbox', 'read-only',
        '--skip-git-repo-check', '--json', '--color', 'never', '-']

def now():
    return datetime.now(timezone.utc).isoformat()

def load_documents(path):
    docs = [Document.model_validate_json(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    if len({d.id for d in docs}) != len(docs):
        raise ValueError('duplicate document IDs')
    return docs

def database(path):
    db = sqlite3.connect(path)
    db.execute('''CREATE TABLE IF NOT EXISTS attempts (
        generation_id TEXT NOT NULL, attempt INTEGER NOT NULL, status TEXT NOT NULL,
        started TEXT NOT NULL, ended TEXT NOT NULL, prompt TEXT NOT NULL, output TEXT,
        events TEXT NOT NULL, stderr TEXT NOT NULL, word_count INTEGER,
        PRIMARY KEY(generation_id, attempt))''')
    db.commit()
    return db

def parse_events(raw):
    events = []
    for line in raw.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            return None, 'invalid_event_stream'
    # Allow only message and reasoning items; unknown item types fail closed.
    items = [e.get('item', {}) for e in events if e.get('type', '').startswith('item.')]
    if any(i.get('type') not in {'agent_message', 'reasoning'} for i in items):
        return None, 'tool_or_unknown_event'
    if any(e.get('type') in {'turn.failed', 'error'} for e in events):
        return None, 'error_event'
    messages = [i.get('text', '') for e in events if e.get('type') == 'item.completed'
                for i in [e.get('item', {})] if i.get('type') == 'agent_message']
    if not any(e.get('type') == 'turn.completed' for e in events) or not messages or not messages[-1].strip():
        return None, 'incomplete'
    return messages[-1], 'success'

def successful(db, generation_id):
    row = db.execute("SELECT output FROM attempts WHERE generation_id=? AND status='success'", (generation_id,)).fetchone()
    return row[0] if row else None

def generate(db, generation_id, prompt, cwd, invoke=subprocess.run, sleep=time.sleep):
    existing = successful(db, generation_id)
    if existing is not None:
        return existing
    count = db.execute('SELECT COUNT(*) FROM attempts WHERE generation_id=?', (generation_id,)).fetchone()[0]
    # A previous invalid or failed attempt needs investigation; do not silently resume it.
    if count:
        raise RuntimeError(f'{generation_id} has prior failed attempts; inspect before proceeding')
    for attempt in range(1, 4):
        started = now()
        try:
            command = [codex_binary(), *ARGS[1:]] if invoke is subprocess.run else ARGS
            proc = invoke(command, input=prompt, text=True, encoding='utf-8', errors='replace',
                          capture_output=True, timeout=300, cwd=str(cwd), shell=False)
            output, status = parse_events(proc.stdout)
            raw, stderr = proc.stdout, proc.stderr
            if proc.returncode != 0 and status == 'success':
                status = 'process_failure'
        except subprocess.TimeoutExpired as exc:
            raw = exc.stdout or ''
            stderr = exc.stderr or ''
            if isinstance(raw, bytes): raw = raw.decode('utf-8', errors='replace')
            if isinstance(stderr, bytes): stderr = stderr.decode('utf-8', errors='replace')
            output, status = None, 'timeout'
        combined = (raw + stderr).lower()
        fatal = any(x in combined for x in ['quota', 'rate limit', 'unauthorized', 'authentication', 'model not found', 'model access'])
        db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (generation_id, attempt, status, started, now(), prompt, output, raw, stderr,
                    words(output) if output is not None else None))
        db.commit()
        if status == 'success': return output
        transient = status == 'timeout' or any(x in combined for x in ['connection reset', 'temporarily unavailable', 'connection timed out', 'service unavailable'])
        if fatal or not transient:
            raise RuntimeError(f'{generation_id}: {status}; investigation required')
        if attempt < 3: sleep([15, 60][attempt - 1])
    raise RuntimeError(f'{generation_id}: retries exhausted')

def run_chain(db, doc, condition, cwd, invoke=subprocess.run):
    parent = doc.text
    for round_number in (1, 2, 3):
        gid = f'{doc.id}-{condition}-{round_number}'
        parent = generate(db, gid, make_prompt(parent, condition, round_number), cwd, invoke=invoke)
    return parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['validate', 'run-dev'])
    parser.add_argument('--data', default='data/sources.jsonl')
    parser.add_argument('--db', default='artifacts/development.sqlite')
    parser.add_argument('--document')
    args = parser.parse_args()
    docs = load_documents(args.data)
    print(f'{len(docs)} valid documents; {sum(d.reviewed for d in docs)} marked reviewed')
    if args.command == 'validate': return
    if not args.document: parser.error('run-dev requires --document')
    selected = [d for d in docs if d.id == args.document and d.split == 'development']
    if len(selected) != 1: parser.error('select exactly one development document')
    db = database(args.db)
    doc = selected[0]
    with tempfile.TemporaryDirectory(prefix='ai-telephone-') as directory:
        work = Path(directory)
        order = list('ABC'); random.Random(1729).shuffle(order)
        for condition in order: run_chain(db, doc, condition, work)
        generate(db, f'{doc.id}-direct-3', make_prompt(doc.text, 'A', 3, direct=True), work)

if __name__ == '__main__': main()
