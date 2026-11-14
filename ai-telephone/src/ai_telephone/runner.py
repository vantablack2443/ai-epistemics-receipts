"""Sequential, checkpointed runner for two CLI backends. Final execution requires a reviewed freeze.

Backends are separate experimental runs and never share a database:
- ``terra``: ``gpt-6.1-terra`` through the signed-in Codex CLI harness.
- ``haiku``: ``claude-haiku-5-5`` through the signed-in Claude Code CLI harness.
"""
import argparse
import json
import os
import random
import shutil
import sqlite3
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .models import Document
from .prompts import make_prompt, words

# --- Codex / Terra -----------------------------------------------------------------

MODEL = 'gpt-6.1-terra'
ARGS = ['codex', 'exec', '--model', MODEL, '-c', 'model_reasoning_effort="low"',
        '--ephemeral', '--ignore-user-config', '--sandbox', 'read-only',
        '--skip-git-repo-check', '--json', '--color', 'never', '-']

def codex_binary():
    if os.name == 'nt':
        candidate = Path(os.environ['APPDATA']) / 'npm/node_modules/@openai/codex/node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe'
        if not candidate.is_file():
            raise RuntimeError('Codex executable not found; configure its executable path before running')
        return str(candidate)
    return 'codex'

def parse_events(raw):
    """Parse a Codex ``--json`` event stream. Returns (output, status)."""
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

def codex_resolved_model(raw):
    """Codex 0.169 does not expose a resolved model ID in its event stream."""
    return None

# --- Claude Code / Haiku -----------------------------------------------------------

HAIKU_MODEL = 'claude-haiku-5-5'
# Replaces Claude Code's default agent system prompt. All study instructions live in the
# user prompt, exactly as for Codex; this line only gives the harness a neutral role.
HAIKU_SYSTEM_PROMPT = 'You are a text summarization assistant.'
HAIKU_ARGS = ['claude', '-p', '--model', HAIKU_MODEL, '--effort', 'low',
              '--tools', '', '--strict-mcp-config', '--setting-sources', '',
              '--no-session-persistence', '--output-format', 'stream-json', '--verbose',
              '--system-prompt', HAIKU_SYSTEM_PROMPT]

def claude_binary():
    found = shutil.which('claude')
    if not found:
        raise RuntimeError('Claude Code executable not found on PATH; install it and sign in before running')
    return found

CLAUDE_EVENT_TYPES = {'system', 'assistant', 'result', 'rate_limit_event'}
CLAUDE_BLOCK_TYPES = {'text', 'thinking', 'redacted_thinking'}

def claude_resolved_model(raw):
    """Model reported by Claude Code's init event, or None."""
    for line in raw.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get('type') == 'system' and e.get('subtype') == 'init':
            return e.get('model')
    return None

def parse_claude_events(raw, model=HAIKU_MODEL):
    """Parse a Claude Code ``--output-format stream-json`` stream. Returns (output, status).

    Fails closed: unknown event types, any non-text content block (tool use), a non-empty
    tool or MCP list, a model other than the requested one, or more than one turn all
    invalidate the attempt.
    """
    events = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            return None, 'invalid_event_stream'
    if any(e.get('type') not in CLAUDE_EVENT_TYPES for e in events):
        return None, 'tool_or_unknown_event'
    blocks = [b for e in events if e.get('type') == 'assistant'
              for b in e.get('message', {}).get('content', [])]
    if any(b.get('type') not in CLAUDE_BLOCK_TYPES for b in blocks):
        return None, 'tool_or_unknown_event'
    init = [e for e in events if e.get('type') == 'system' and e.get('subtype') == 'init']
    if len(init) != 1:
        return None, 'incomplete'
    if init[0].get('tools') or init[0].get('mcp_servers'):
        return None, 'environment_mismatch'
    used = {e.get('message', {}).get('model') for e in events if e.get('type') == 'assistant'}
    if init[0].get('model') != model or used - {model}:
        return None, 'model_mismatch'
    results = [e for e in events if e.get('type') == 'result']
    if len(results) != 1:
        return None, 'incomplete'
    result = results[0]
    if result.get('is_error') or result.get('subtype') != 'success':
        return None, 'error_event'
    if set(result.get('modelUsage') or {}) - {model}:
        return None, 'model_mismatch'
    if result.get('num_turns') != 1:
        return None, 'tool_or_unknown_event'
    output = result.get('result')
    if not isinstance(output, str) or not output.strip():
        return None, 'incomplete'
    return output, 'success'

# --- Backend registry --------------------------------------------------------------

@dataclass(frozen=True)
class Backend:
    name: str
    model: str
    reasoning_effort: str
    harness: str
    args: tuple
    binary: Callable[[], str]
    parse: Callable
    resolved_model: Callable
    default_db: str

    def command(self, real: bool):
        return [self.binary(), *self.args[1:]] if real else list(self.args)

BACKENDS = {
    'terra': Backend('terra', MODEL, 'low', 'Codex CLI (signed-in ChatGPT)', tuple(ARGS),
                     codex_binary, parse_events, codex_resolved_model, 'artifacts/development.sqlite'),
    'haiku': Backend('haiku', HAIKU_MODEL, 'low', 'Claude Code CLI (signed-in Claude)', tuple(HAIKU_ARGS),
                     claude_binary, lambda raw: parse_claude_events(raw, HAIKU_MODEL), claude_resolved_model,
                     'artifacts/development-haiku.sqlite'),
}
TERRA = BACKENDS['terra']

FATAL = ['quota', 'rate limit', 'usage limit', 'unauthorized', 'authentication', 'invalid api key',
         'credit balance', 'model not found', 'model access', 'not_found_error', 'permission_error']
TRANSIENT = ['connection reset', 'temporarily unavailable', 'connection timed out', 'service unavailable',
             'overloaded', 'api_error', 'internal server error']

# --- Storage -----------------------------------------------------------------------

def now():
    return datetime.now(timezone.utc).isoformat()

def load_documents(path):
    docs = [Document.model_validate_json(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    if len({d.id for d in docs}) != len(docs):
        raise ValueError('duplicate document IDs')
    return docs

def database(path, backend=None):
    """Open a run database. With a backend, bind the database to it and refuse any other."""
    db = sqlite3.connect(path)
    db.execute('''CREATE TABLE IF NOT EXISTS attempts (
        generation_id TEXT NOT NULL, attempt INTEGER NOT NULL, status TEXT NOT NULL,
        started TEXT NOT NULL, ended TEXT NOT NULL, prompt TEXT NOT NULL, output TEXT,
        events TEXT NOT NULL, stderr TEXT NOT NULL, word_count INTEGER,
        PRIMARY KEY(generation_id, attempt))''')
    db.execute('CREATE TABLE IF NOT EXISTS run_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    if backend is not None:
        bind(db, backend)
    db.commit()
    return db

def bind(db, backend):
    expected = {'backend': backend.name, 'model': backend.model,
                'reasoning_effort': backend.reasoning_effort, 'args': json.dumps(list(backend.args))}
    stored = dict(db.execute('SELECT key, value FROM run_meta'))
    if not stored and db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0]:
        # Pre-existing database from before run metadata existed: only Terra wrote these.
        if backend.name != 'terra':
            raise RuntimeError('database already holds Terra attempts; use a separate database per model')
    for key, value in expected.items():
        if key in stored and stored[key] != value:
            raise RuntimeError(f'database is bound to a different configuration ({key}: {stored[key]!r}); '
                               'changed models or settings require a new database')
        db.execute('INSERT OR IGNORE INTO run_meta VALUES (?, ?)', (key, value))

def run_meta(db):
    return dict(db.execute('SELECT key, value FROM run_meta'))

def successful(db, generation_id):
    row = db.execute("SELECT output FROM attempts WHERE generation_id=? AND status='success'", (generation_id,)).fetchone()
    return row[0] if row else None

# --- Execution ---------------------------------------------------------------------

def generate(db, generation_id, prompt, cwd, invoke=subprocess.run, sleep=time.sleep, backend=TERRA):
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
            command = backend.command(real=invoke is subprocess.run)
            proc = invoke(command, input=prompt, text=True, encoding='utf-8', errors='replace',
                          capture_output=True, timeout=300, cwd=str(cwd), shell=False)
            output, status = backend.parse(proc.stdout)
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
        fatal = any(x in combined for x in FATAL)
        db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,?)',
                   (generation_id, attempt, status, started, now(), prompt, output, raw, stderr,
                    words(output) if output is not None else None))
        db.commit()
        if status == 'success': return output
        transient = status == 'timeout' or any(x in combined for x in TRANSIENT)
        if fatal or not transient:
            raise RuntimeError(f'{generation_id}: {status}; investigation required')
        if attempt < 3: sleep([15, 60][attempt - 1])
    raise RuntimeError(f'{generation_id}: retries exhausted')

def run_chain(db, doc, condition, cwd, invoke=subprocess.run, backend=TERRA):
    parent = doc.text
    for round_number in (1, 2, 3):
        gid = f'{doc.id}-{condition}-{round_number}'
        parent = generate(db, gid, make_prompt(parent, condition, round_number), cwd, invoke=invoke, backend=backend)
    return parent

def cli_version(backend):
    proc = subprocess.run([backend.binary(), '--version'], capture_output=True, text=True, timeout=60, shell=False)
    return (proc.stdout or proc.stderr).strip()

def smoke(backend):
    """Nonexperimental access check. Writes nothing to any run database."""
    token = f'{backend.name.upper()}_OK'
    with tempfile.TemporaryDirectory(prefix='ai-telephone-smoke-') as directory:
        proc = subprocess.run(backend.command(real=True), input=f'Return exactly: {token}', text=True,
                              encoding='utf-8', errors='replace', capture_output=True, timeout=300,
                              cwd=directory, shell=False)
    output, status = backend.parse(proc.stdout)
    report = {'backend': backend.name, 'requested_model': backend.model, 'resolved_model': backend.resolved_model(proc.stdout),
              'cli_version': cli_version(backend), 'returncode': proc.returncode, 'status': status,
              'output': output, 'args': list(backend.args), 'checked_utc': now()}
    print(json.dumps(report, indent=2))
    if status != 'success' or output.strip() != token:
        raise SystemExit('smoke test failed; do not run experiments with this backend')

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['validate', 'smoke', 'run-dev'])
    parser.add_argument('--model', choices=sorted(BACKENDS), default='terra',
                        help='experimental backend; each model uses its own database')
    parser.add_argument('--data', default='data/sources.jsonl')
    parser.add_argument('--db', help='SQLite run database (default depends on --model)')
    parser.add_argument('--document')
    args = parser.parse_args()
    backend = BACKENDS[args.model]
    if args.command == 'smoke':
        return smoke(backend)
    docs = load_documents(args.data)
    print(f'{len(docs)} valid documents; {sum(d.reviewed for d in docs)} marked reviewed')
    if args.command == 'validate': return
    if not args.document: parser.error('run-dev requires --document')
    selected = [d for d in docs if d.id == args.document and d.split == 'development']
    if len(selected) != 1: parser.error('select exactly one development document')
    db_path = Path(args.db or backend.default_db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = database(db_path, backend)
    version = cli_version(backend)
    stored = run_meta(db).get('cli_version')
    if stored and stored != version:
        raise SystemExit(f'CLI version changed ({stored} -> {version}); start a new database for a new run')
    db.execute('INSERT OR IGNORE INTO run_meta VALUES (?, ?)', ('cli_version', version)); db.commit()
    doc = selected[0]
    print(f'backend={backend.name} model={backend.model} db={db_path}')
    with tempfile.TemporaryDirectory(prefix='ai-telephone-') as directory:
        work = Path(directory)
        order = list('ABC'); random.Random(1729).shuffle(order)
        for condition in order: run_chain(db, doc, condition, work, backend=backend)
        generate(db, f'{doc.id}-direct-3', make_prompt(doc.text, 'A', 3, direct=True), work, backend=backend)

if __name__ == '__main__': main()
