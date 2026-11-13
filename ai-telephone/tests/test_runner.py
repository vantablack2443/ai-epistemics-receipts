import json
from types import SimpleNamespace
import pytest
from ai_telephone.models import Document
from ai_telephone.runner import ARGS, database, generate, parse_events, run_chain

def event_output(text):
    return '\n'.join(json.dumps(x) for x in [
        {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': text}},
        {'type': 'turn.completed'}])

def document():
    return Document(id='dev', split='development', category='scope', text='original finding limit one two three', provenance='fixture', items=[
        {'id':'f', 'type':'finding', 'quotation':'finding', 'meaning':'finding'},
        *[{'id':str(i), 'type':'qualification', 'quotation':x, 'meaning':'SECRET GROUND TRUTH'} for i,x in enumerate(['one','two','three'])]])

def test_chain_isolation_and_resume(tmp_path):
    db = database(tmp_path / 'run.sqlite')
    prompts = []
    def invoke(args, **kwargs):
        assert args == ARGS and 'gpt-6.1-terra' in args and 'model_reasoning_effort="low"' in args
        prompts.append(kwargs['input'])
        return SimpleNamespace(returncode=0, stdout=event_output(f'output {len(prompts)}'), stderr='')
    run_chain(db, document(), 'A', tmp_path, invoke)
    assert 'original finding' in prompts[0]
    assert prompts[1].endswith('output 1') and 'original finding' not in prompts[1]
    assert prompts[2].endswith('output 2') and 'output 1' not in prompts[2]
    assert all('SECRET GROUND TRUTH' not in p for p in prompts)
    run_chain(db, document(), 'A', tmp_path, invoke)
    assert len(prompts) == 3

def test_tool_event_stops_and_failure_is_retained(tmp_path):
    db = database(tmp_path / 'run.sqlite')
    raw = json.dumps({'type':'item.completed','item':{'type':'command_execution'}})
    def invoke(*args, **kwargs): return SimpleNamespace(returncode=0, stdout=raw, stderr='')
    with pytest.raises(RuntimeError): generate(db, 'x', 'prompt', tmp_path, invoke=invoke)
    assert db.execute('select status from attempts').fetchone()[0] == 'tool_or_unknown_event'

def test_overlength_is_unchanged(tmp_path):
    db = database(tmp_path / 'run.sqlite')
    output = ' '.join(['word'] * 101)
    def invoke(*args, **kwargs): return SimpleNamespace(returncode=0, stdout=event_output(output), stderr='')
    assert generate(db, 'x', 'prompt', tmp_path, invoke=invoke) == output
    assert db.execute('select word_count from attempts').fetchone()[0] == 101
