"""Sequential, checkpointed runner for two CLI backends. Final execution requires a reviewed freeze.

Backends are separate experimental runs and never share a database:
- ``terra``: ``gpt-6.1-terra`` through the signed-in Codex CLI harness.
- ``haiku``: ``claude-haiku-5-5`` through the signed-in Claude Code CLI harness.
- ``gemini``: ``gemini-3.8-flash-low`` through the signed-in Antigravity CLI (``agy``) harness.

Design v2 (docs/design-v2.md) adds ``run_chain_v2``, ``run_final``, ``export_generations`` and
the ``run-dev``/``run-final``/``export``/``validate`` commands; the v1 functions remain.
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

from .models import Document, DocumentV2
from .prompts import make_prompt, make_prompt_v2, words
from .schedule import all_chains, shuffled_chains

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

# --- Antigravity CLI / Gemini ------------------------------------------------------

GEMINI_MODEL = 'gemini-3.8-flash-low'
# agy print mode takes the prompt as the value of -p (it does not read stdin), so the prompt
# is appended to this argv as ``-p=<prompt>``. Tools are blocked two ways: --sandbox plus
# session-only deny rules (verified 2026-11-14: run_command and read_file attempts end in state
# ERROR without executing), and the event stream is still checked: any step that is not
# user_input/agent_response invalidates the attempt.
GEMINI_DENY = json.dumps({'permissions': {'deny': ['command(*)', 'read_file(*)', 'write_file(*)',
                                                   'browser(*)', 'mcp(*)']}}, separators=(',', ':'))
GEMINI_ARGS = ['agy', '--model', GEMINI_MODEL, '--effort', 'low', '--output-format', 'stream-json',
               '--disable-slash-commands', '--sandbox', '--settings', GEMINI_DENY]

def agy_binary():
    found = shutil.which('agy')
    if not found:
        raise RuntimeError('Antigravity CLI (agy) not found on PATH; install it and sign in before running')
    return found

AGY_EVENT_TYPES = {'init', 'step_update', 'result'}
AGY_STEP_TYPES = {'user_input', 'agent_response'}

def agy_resolved_model(raw):
    for line in raw.splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get('event') == 'init':
            return (e.get('init') or {}).get('model')
    return None

def parse_agy_events(raw, model=GEMINI_MODEL):
    """Parse an ``agy --output-format stream-json`` stream. Returns (output, status).

    Fails closed: unknown event types, any step other than user_input/agent_response (tool
    steps), a different model, a non-SUCCESS result, more than one turn, or an empty response
    invalidate the attempt. Token usage stays in the raw stream stored in the events column.
    """
    events = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            return None, 'invalid_event_stream'
        if not isinstance(e, dict):
            return None, 'invalid_event_stream'
        events.append(e)
    if any(e.get('event') not in AGY_EVENT_TYPES for e in events):
        return None, 'tool_or_unknown_event'
    steps = [e.get('step_update') or {} for e in events if e.get('event') == 'step_update']
    if any(s.get('step_type') not in AGY_STEP_TYPES or s.get('tool_name') or 'tool_info' in s for s in steps):
        return None, 'tool_or_unknown_event'
    init = [e for e in events if e.get('event') == 'init']
    if len(init) != 1:
        return None, 'incomplete'
    if (init[0].get('init') or {}).get('model') != model:
        return None, 'model_mismatch'
    results = [e.get('result') or {} for e in events if e.get('event') == 'result']
    if len(results) != 1:
        return None, 'incomplete'
    result = results[0]
    if result.get('status') != 'SUCCESS':
        return None, 'error_event'
    if result.get('num_turns') != 1:
        return None, 'tool_or_unknown_event'
    output = result.get('response')
    if not isinstance(output, str) or not output.strip():
        return None, 'incomplete'
    return output.strip(), 'success'

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
    prompt_in_argv: bool = False

    def command(self, real: bool, prompt: str | None = None):
        command = [self.binary(), *self.args[1:]] if real else list(self.args)
        if self.prompt_in_argv:
            command.append(f'-p={prompt}')  # list element, never a shell string
        return command

BACKENDS = {
    'terra': Backend('terra', MODEL, 'low', 'Codex CLI (signed-in ChatGPT)', tuple(ARGS),
                     codex_binary, parse_events, codex_resolved_model, 'artifacts/v2-terra.sqlite'),
    'haiku': Backend('haiku', HAIKU_MODEL, 'low', 'Claude Code CLI (signed-in Claude)', tuple(HAIKU_ARGS),
                     claude_binary, lambda raw: parse_claude_events(raw, HAIKU_MODEL), claude_resolved_model,
                     'artifacts/v2-haiku.sqlite'),
    'gemini': Backend('gemini', GEMINI_MODEL, 'low', 'Antigravity CLI (signed-in Google)', tuple(GEMINI_ARGS),
                      agy_binary, lambda raw: parse_agy_events(raw, GEMINI_MODEL), agy_resolved_model,
                      'artifacts/v2-gemini.sqlite', prompt_in_argv=True),
}
V1_DBS = {'terra': 'artifacts/development.sqlite', 'haiku': 'artifacts/development-haiku.sqlite'}
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

class GenerationError(RuntimeError):
    """A generation failed. ``fatal`` (auth, quota, model access) means the whole run must stop."""
    def __init__(self, message, fatal=False):
        super().__init__(message)
        self.fatal = fatal

def is_fatal(text):
    text = text.lower()
    return any(x in text for x in FATAL)

def generate(db, generation_id, prompt, cwd, invoke=subprocess.run, sleep=time.sleep, backend=TERRA):
    existing = successful(db, generation_id)
    if existing is not None:
        return existing
    count = db.execute('SELECT COUNT(*) FROM attempts WHERE generation_id=?', (generation_id,)).fetchone()[0]
    # A previous invalid or failed attempt needs investigation; do not silently resume it.
    if count:
        raise GenerationError(f'{generation_id} has prior failed attempts; inspect before proceeding', fatal=True)
    for attempt in range(1, 4):
        started = now()
        try:
            command = backend.command(real=invoke is subprocess.run, prompt=prompt)
            proc = invoke(command, input=None if backend.prompt_in_argv else prompt, text=True, encoding='utf-8', errors='replace',
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
            raise GenerationError(f'{generation_id}: {status}; investigation required', fatal=fatal)
        if attempt < 3: sleep([15, 60][attempt - 1])
    raise GenerationError(f'{generation_id}: retries exhausted')

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
        prompt = f'Return exactly: {token}'
        proc = subprocess.run(backend.command(real=True, prompt=prompt),
                              input=None if backend.prompt_in_argv else prompt, text=True,
                              encoding='utf-8', errors='replace', capture_output=True, timeout=300,
                              cwd=directory, shell=False)
    output, status = backend.parse(proc.stdout)
    report = {'backend': backend.name, 'requested_model': backend.model, 'resolved_model': backend.resolved_model(proc.stdout),
              'cli_version': cli_version(backend), 'returncode': proc.returncode, 'status': status,
              'output': output, 'args': list(backend.args), 'checked_utc': now()}
    print(json.dumps(report, indent=2))
    if status != 'success' or output.strip() != token:
        raise SystemExit('smoke test failed; do not run experiments with this backend')

# --- Design v2: chains, final run, export ------------------------------------------

def generation_id(doc_id, prompt, length, round_):
    return f'{doc_id}-{prompt}-{length}-r{round_}'

def parse_generation_id(gid):
    """Inverse of generation_id: returns (document_id, prompt, length, round)."""
    document_id, prompt, length, r = gid.rsplit('-', 3)
    return document_id, prompt, length, int(r[1:])

def load_documents_v2(path):
    docs = [DocumentV2.model_validate_json(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    if len({d.id for d in docs}) != len(docs):
        raise ValueError('duplicate document IDs')
    return docs

def prior_failure(db, gid):
    """Last failed attempt of a generation that never succeeded: (status, fatal), else None."""
    row = db.execute('SELECT status, events, stderr FROM attempts WHERE generation_id=? ORDER BY attempt DESC LIMIT 1', (gid,)).fetchone()
    if row is None or row[0] == 'success' or successful(db, gid) is not None:
        return None
    return row[0], is_fatal(row[1] + row[2])

def run_chain_v2(db, doc, prompt, length, cwd, invoke=subprocess.run, backend=TERRA, rounds=5):
    """Run rounds 1..5; round n sees only round n-1's output. Returns the last output, or None if
    the chain stopped at a failure (its remaining rounds are never attempted: ``not_run``)."""
    parent = doc.text
    for round_ in range(1, rounds + 1):
        gid = generation_id(doc.id, prompt, length, round_)
        failure = prior_failure(db, gid)
        if failure is not None:
            if failure[1]:
                raise GenerationError(f'{gid}: earlier fatal failure ({failure[0]}); inspect before proceeding', fatal=True)
            return None
        try:
            parent = generate(db, gid, make_prompt_v2(parent, prompt, length), cwd, invoke=invoke, backend=backend)
        except GenerationError as exc:
            if exc.fatal:
                raise
            return None
    return parent

def run_dev(db, doc, cwd, invoke=subprocess.run, backend=TERRA):
    """All six chains of one development document, in the seeded shuffled order."""
    for chain in shuffled_chains(1729):
        run_chain_v2(db, doc, chain['prompt'], chain['length'], cwd, invoke=invoke, backend=backend)

def run_final(manifest_path, backend, db_path, invoke=subprocess.run, version_fn=None, root=None):
    """Verify the frozen manifest, then run its schedule in order. Resumable."""
    from .freeze import project_root, verify_manifest
    root = Path(root) if root else project_root()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    problems = verify_manifest(manifest, root)
    expected = {'model': backend.model, 'reasoning_effort': backend.reasoning_effort, 'harness': backend.harness,
                'args': list(backend.args), 'backend': backend.name}
    problems += [f'setting {k}: manifest {manifest.get(k)!r} != code {v!r}' for k, v in expected.items() if manifest.get(k) != v]
    if problems:
        raise RuntimeError('manifest verification failed; refusing to run:\n' + '\n'.join(problems))
    version = (version_fn or cli_version)(backend)
    if version != manifest.get('cli_version'):
        raise RuntimeError(f"CLI version {version!r} differs from frozen {manifest.get('cli_version')!r}; refusing to run")
    docs = {d.id: d for d in load_documents_v2(root / manifest['sources'])}
    db = database(db_path, backend)
    db.execute('INSERT OR IGNORE INTO run_meta VALUES (?, ?)', ('cli_version', version)); db.commit()
    with tempfile.TemporaryDirectory(prefix='ai-telephone-') as directory:
        for entry in manifest['schedule']:
            for chain in entry['chains']:
                run_chain_v2(db, docs[entry['document_id']], chain['prompt'], chain['length'], Path(directory),
                             invoke=invoke, backend=backend)
    return db

def final_status(rows):
    """rows: attempts (status, started, ended, output, word_count) ordered by attempt."""
    if not rows:
        return {'status': 'not_run', 'output': None, 'word_count': None, 'attempts': 0, 'started': None, 'ended': None}
    win = next((r for r in rows if r[0] == 'success'), None)
    return {'status': 'success' if win else rows[-1][0], 'output': win[3] if win else None,
            'word_count': win[4] if win else None, 'attempts': len(rows), 'started': rows[0][1], 'ended': rows[-1][2]}

def export_generations(db_path, docs, backend, out_path, split='test'):
    """One row per scheduled generation ID with its final status, including not_run rows."""
    with sqlite3.connect(f'file:{Path(db_path).resolve().as_posix()}?mode=ro', uri=True) as db:
        meta = dict(db.execute('SELECT key, value FROM run_meta'))
        if meta.get('model') != backend.model:
            raise ValueError(f'database model {meta.get("model")!r} does not match {backend.model!r}')
        attempts = {}
        for row in db.execute('SELECT generation_id, status, started, ended, output, word_count FROM attempts ORDER BY generation_id, attempt'):
            attempts.setdefault(row[0], []).append(row[1:])
    rows = []
    for doc in sorted((d for d in docs if d.split == split), key=lambda d: d.id):
        for chain in all_chains():
            for round_ in range(1, 6):
                gid = generation_id(doc.id, chain['prompt'], chain['length'], round_)
                rows.append({'generation_id': gid, 'document_id': doc.id, 'prompt': chain['prompt'],
                             'length': chain['length'], 'round': round_, 'model': backend.model,
                             **final_status(attempts.get(gid, []))})
    out = Path(out_path); out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')
    return rows

def export_path(model, split):
    return f"results/{model}/generations{'' if split == 'test' else '-development'}.jsonl"

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', choices=['validate', 'smoke', 'run-dev', 'run-final', 'export'])
    parser.add_argument('--model', choices=sorted(BACKENDS), default='terra',
                        help='experimental backend; each model uses its own database')
    parser.add_argument('--data', default='data/v2/sources.jsonl')
    parser.add_argument('--db', help='SQLite run database (default artifacts/v2-<model>.sqlite)')
    parser.add_argument('--document')
    parser.add_argument('--manifest', help='frozen manifest for run-final')
    parser.add_argument('--split', choices=['development', 'test'], default='test')
    parser.add_argument('--out', help='export destination (default results/<model>/generations[-development].jsonl)')
    parser.add_argument('--v1', action='store_true', help='legacy v1 validate/run-dev (conditions A/B/C)')
    args = parser.parse_args()
    backend = BACKENDS[args.model]
    if args.command == 'smoke':
        return smoke(backend)
    if args.command == 'run-final':
        if not args.manifest: parser.error('run-final requires --manifest')
        db_path = Path(args.db or backend.default_db); db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            run_final(args.manifest, backend, db_path)
        except (GenerationError, RuntimeError) as exc:
            raise SystemExit(f'stopped: {exc}')
        return
    if args.v1:
        return main_v1(args, parser, backend)
    try:
        docs = load_documents_v2(args.data)
    except (OSError, ValueError) as exc:
        raise SystemExit(f'cannot load sources {args.data}: {exc}')
    if args.command == 'validate':
        from collections import Counter
        print(f'{len(docs)} valid documents; {sum(d.reviewed for d in docs)} marked reviewed')
        print('by split:', dict(Counter(d.split for d in docs)), 'by kind:', dict(Counter(d.kind for d in docs)))
        return
    db_path = Path(args.db or backend.default_db)
    if args.command == 'export':
        rows = export_generations(db_path, docs, backend, args.out or export_path(args.model, args.split), args.split)
        from collections import Counter
        print(f'{len(rows)} rows;', dict(Counter(r['status'] for r in rows)))
        return
    if not args.document: parser.error('run-dev requires --document')
    selected = [d for d in docs if d.id == args.document and d.split == 'development']
    if len(selected) != 1: parser.error('select exactly one development document')
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = database(db_path, backend)
    version = cli_version(backend)
    stored = run_meta(db).get('cli_version')
    if stored and stored != version:
        raise SystemExit(f'CLI version changed ({stored} -> {version}); start a new database for a new run')
    db.execute('INSERT OR IGNORE INTO run_meta VALUES (?, ?)', ('cli_version', version)); db.commit()
    print(f'backend={backend.name} model={backend.model} db={db_path}')
    with tempfile.TemporaryDirectory(prefix='ai-telephone-') as directory:
        try:
            run_dev(db, selected[0], Path(directory), backend=backend)
        except GenerationError as exc:
            raise SystemExit(f'stopped: {exc}')

def main_v1(args, parser, backend):
    docs = load_documents(args.data)
    print(f'{len(docs)} valid documents; {sum(d.reviewed for d in docs)} marked reviewed')
    if args.command == 'validate': return
    if args.command != 'run-dev': parser.error('--v1 supports validate and run-dev only')
    if not args.document: parser.error('run-dev requires --document')
    selected = [d for d in docs if d.id == args.document and d.split == 'development']
    if len(selected) != 1: parser.error('select exactly one development document')
    db_path = Path(args.db or V1_DBS.get(backend.name, backend.default_db))
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
