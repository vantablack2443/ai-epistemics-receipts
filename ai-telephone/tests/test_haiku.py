"""Mocked Claude Code stream-json responses; no real model calls. Fixture shapes follow a
real `claude -p --output-format stream-json --verbose` smoke run (Claude Code 2.1.325)."""
import json
from types import SimpleNamespace
import pytest
from ai_telephone.runner import (ARGS, BACKENDS, HAIKU_MODEL, database, generate, parse_claude_events,
                                 run_chain)
from test_runner import document

HAIKU = BACKENDS['haiku']

def stream(text, *, model=HAIKU_MODEL, blocks=None, tools=(), extra=(), result_model=None, is_error=False, turns=1):
    events = [
        {'type': 'system', 'subtype': 'init', 'model': model, 'tools': list(tools), 'mcp_servers': []},
        {'type': 'assistant', 'message': {'model': model, 'content': blocks or [{'type': 'text', 'text': text}]}},
        {'type': 'rate_limit_event', 'rate_limit_info': {'status': 'allowed'}},
        *extra,
        {'type': 'result', 'subtype': 'success', 'is_error': is_error, 'result': text, 'num_turns': turns,
         'modelUsage': {result_model or model: {'outputTokens': 10}}},
    ]
    return '\n'.join(json.dumps(e) for e in events)

def test_haiku_args_disable_tools_and_fix_effort():
    args = list(HAIKU.args)
    assert args[args.index('--model') + 1] == 'claude-haiku-5-5'
    assert args[args.index('--effort') + 1] == 'low'
    assert args[args.index('--tools') + 1] == ''
    assert '--strict-mcp-config' in args and '--no-session-persistence' in args
    assert args[args.index('--output-format') + 1] == 'stream-json'
    assert BACKENDS['terra'].args == tuple(ARGS)
    assert HAIKU.reasoning_effort == BACKENDS['terra'].reasoning_effort == 'low'

def test_parse_success():
    assert parse_claude_events(stream('summary text')) == ('summary text', 'success')

@pytest.mark.parametrize('raw,status', [
    (stream('x', blocks=[{'type': 'text', 'text': 'x'}, {'type': 'tool_use', 'name': 'Read'}]), 'tool_or_unknown_event'),
    (stream('x', blocks=[{'type': 'server_tool_use', 'name': 'web_search'}]), 'tool_or_unknown_event'),
    (stream('x', extra=[{'type': 'user', 'message': {'content': [{'type': 'tool_result'}]}}]), 'tool_or_unknown_event'),
    (stream('x', turns=2), 'tool_or_unknown_event'),
    (stream('x', tools=['Read']), 'environment_mismatch'),
    (stream('x', model='claude-sonnet-5-5'), 'model_mismatch'),
    (stream('x', result_model='claude-sonnet-5-5'), 'model_mismatch'),
    (stream('x', is_error=True), 'error_event'),
    (stream('   '), 'incomplete'),
    ('not json', 'invalid_event_stream'),
])
def test_parse_rejects(raw, status):
    assert parse_claude_events(raw) == (None, status)

def test_haiku_chain_isolation_and_resume(tmp_path):
    db = database(tmp_path / 'haiku.sqlite', HAIKU)
    prompts = []
    def invoke(args, **kwargs):
        assert args == list(HAIKU.args)
        prompts.append(kwargs['input'])
        return SimpleNamespace(returncode=0, stdout=stream(f'output {len(prompts)}'), stderr='')
    run_chain(db, document(), 'C', tmp_path, invoke, backend=HAIKU)
    assert 'original finding' in prompts[0]
    assert prompts[1].endswith('output 1') and 'original finding' not in prompts[1]
    assert prompts[2].endswith('output 2') and 'output 1' not in prompts[2]
    assert all('SECRET GROUND TRUTH' not in p for p in prompts)
    run_chain(db, document(), 'C', tmp_path, invoke, backend=HAIKU)
    assert len(prompts) == 3

def test_haiku_tool_use_stops_and_is_retained(tmp_path):
    db = database(tmp_path / 'haiku.sqlite', HAIKU)
    raw = stream('x', blocks=[{'type': 'tool_use', 'name': 'Bash'}])
    def invoke(*a, **k): return SimpleNamespace(returncode=0, stdout=raw, stderr='')
    with pytest.raises(RuntimeError): generate(db, 'g', 'prompt', tmp_path, invoke=invoke, backend=HAIKU)
    assert db.execute('select status from attempts').fetchone()[0] == 'tool_or_unknown_event'

def test_haiku_overlength_is_unchanged(tmp_path):
    db = database(tmp_path / 'haiku.sqlite', HAIKU)
    output = ' '.join(['word'] * 52)
    def invoke(*a, **k): return SimpleNamespace(returncode=0, stdout=stream(output), stderr='')
    assert generate(db, 'g', 'prompt', tmp_path, invoke=invoke, backend=HAIKU) == output
    assert db.execute('select word_count from attempts').fetchone()[0] == 52

def test_usage_limit_is_fatal_without_retry(tmp_path):
    db = database(tmp_path / 'haiku.sqlite', HAIKU)
    calls, sleeps = [], []
    def invoke(*a, **k):
        calls.append(1)
        return SimpleNamespace(returncode=1, stdout='', stderr='Claude usage limit reached')
    with pytest.raises(RuntimeError):
        generate(db, 'g', 'prompt', tmp_path, invoke=invoke, sleep=sleeps.append, backend=HAIKU)
    assert len(calls) == 1 and sleeps == []

def test_overloaded_is_retried(tmp_path):
    db = database(tmp_path / 'haiku.sqlite', HAIKU)
    responses = [SimpleNamespace(returncode=1, stdout='', stderr='API Error: 529 Overloaded'),
                 SimpleNamespace(returncode=0, stdout=stream('ok now'), stderr='')]
    sleeps = []
    def invoke(*a, **k): return responses.pop(0)
    assert generate(db, 'g', 'prompt', tmp_path, invoke=invoke, sleep=sleeps.append, backend=HAIKU) == 'ok now'
    assert sleeps == [15]
    assert [r[0] for r in db.execute('select status from attempts order by attempt')] == ['incomplete', 'success']

def test_database_refuses_mixing_models(tmp_path):
    path = tmp_path / 'run.sqlite'
    database(path, BACKENDS['terra']).close()
    with pytest.raises(RuntimeError, match='different configuration'):
        database(path, HAIKU)

def test_legacy_terra_database_cannot_be_reused_for_haiku(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    db = database(path)  # pre-metadata database, as produced by the first Terra development run
    db.execute("INSERT INTO attempts VALUES ('dev-01-A-1',1,'success','t','t','p','o','','',1)"); db.commit(); db.close()
    with pytest.raises(RuntimeError, match='Terra'):
        database(path, HAIKU)
    database(path, BACKENDS['terra']).close()
