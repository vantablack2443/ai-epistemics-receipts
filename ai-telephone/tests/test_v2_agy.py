"""Gemini backend: parser against streams captured from real `agy` runs (tests/fixtures) and mocked variants."""
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from ai_telephone.runner import BACKENDS, GEMINI_MODEL, database, generate, parse_agy_events

FIX = Path(__file__).parent / 'fixtures'
GEMINI = BACKENDS['gemini']
SAMPLE = (FIX / 'agy_stream_sample.jsonl').read_text(encoding='utf-8')
TOOL = (FIX / 'agy_stream_tool.jsonl').read_text(encoding='utf-8')

def mutate(raw, fn):
    return '\n'.join(json.dumps(fn(json.loads(l))) for l in raw.splitlines() if l.strip())

def test_backend_settings():
    assert GEMINI.model == GEMINI_MODEL == 'gemini-3.8-flash-low'
    assert GEMINI.reasoning_effort == 'low' and GEMINI.harness == 'Antigravity CLI (signed-in Google)'
    assert GEMINI.default_db == 'artifacts/v2-gemini.sqlite'
    cmd = GEMINI.command(real=False, prompt='-p=tricky --flag')
    assert cmd[:-1] == list(GEMINI.args) and cmd[-1] == '-p=-p=tricky --flag'
    assert GEMINI.prompt_in_argv

def test_real_sample_parses_and_event_types():
    types = {json.loads(l)['event'] for l in SAMPLE.splitlines()}
    assert types == {'init', 'step_update', 'result'}
    out, status = parse_agy_events(SAMPLE)
    assert status == 'success' and out.startswith('The rover traversed 40 meters')

def test_real_tool_stream_is_rejected():
    steps = {json.loads(l)['step_update']['step_type'] for l in TOOL.splitlines() if '"step_update"' in l}
    assert 'tool' in steps
    result = [json.loads(l) for l in TOOL.splitlines() if '"result"' in l][-1]['result']
    assert result['status'] == 'SUCCESS' and result['num_turns'] == 1  # the result alone would look fine
    assert parse_agy_events(TOOL) == (None, 'tool_or_unknown_event')

@pytest.mark.parametrize('fn,status', [
    (lambda e: {**e, 'event': 'mystery'} if e['event'] == 'result' else e, 'tool_or_unknown_event'),
    (lambda e: {**e, 'result': {**e['result'], 'num_turns': 2}} if e['event'] == 'result' else e, 'tool_or_unknown_event'),
    (lambda e: {**e, 'result': {**e['result'], 'status': 'FAILED'}} if e['event'] == 'result' else e, 'error_event'),
    (lambda e: {**e, 'result': {**e['result'], 'response': '  \n'}} if e['event'] == 'result' else e, 'incomplete'),
    (lambda e: {**e, 'init': {**e['init'], 'model': 'gemini-3.8-flash-high'}} if e['event'] == 'init' else e, 'model_mismatch'),
])
def test_parse_rejects_variants(fn, status):
    assert parse_agy_events(mutate(SAMPLE, fn)) == (None, status)

def test_parse_rejects_malformed_and_incomplete():
    assert parse_agy_events('not json') == (None, 'invalid_event_stream')
    lines = SAMPLE.splitlines()
    assert parse_agy_events('\n'.join(l for l in lines if '"result"' not in l.split(',')[0])) == (None, 'incomplete')
    assert parse_agy_events('\n'.join(lines[1:])) == (None, 'incomplete')  # no init event

def test_generate_passes_prompt_in_argv_not_stdin(tmp_path):
    db = database(tmp_path / 'g.sqlite', GEMINI)
    seen = {}
    def invoke(args, **kwargs):
        seen.update(args=args, kwargs=kwargs)
        return SimpleNamespace(returncode=0, stdout=SAMPLE, stderr='')
    out = generate(db, 'long-01-zero-free-r1', 'my prompt', tmp_path, invoke=invoke, backend=GEMINI)
    assert out.startswith('The rover') and seen['args'][-1] == '-p=my prompt'
    assert seen['kwargs']['input'] is None and seen['kwargs']['shell'] is False
    row = db.execute('select status, events from attempts').fetchone()
    assert row[0] == 'success' and '"usage"' in row[1]  # usage stays in the events column

def test_tool_stream_fails_generation_and_is_retained(tmp_path):
    db = database(tmp_path / 'g.sqlite', GEMINI)
    def invoke(*a, **k): return SimpleNamespace(returncode=0, stdout=TOOL, stderr='')
    with pytest.raises(RuntimeError):
        generate(db, 'g', 'p', tmp_path, invoke=invoke, backend=GEMINI)
    assert db.execute('select status from attempts').fetchone()[0] == 'tool_or_unknown_event'
