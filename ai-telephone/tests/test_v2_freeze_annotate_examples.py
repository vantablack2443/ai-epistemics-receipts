"""Design v2: freeze sign-off and verification, AI annotator on v2 IDs, selected prompt examples.

Mocked judge and no real model calls.
"""
import json
from types import SimpleNamespace

import pytest

from ai_telephone import summarizer_examples as se
from ai_telephone.annotate import JUDGES, document_for, label
from ai_telephone.freeze import FROZEN_FILES, freeze_v2, verify_manifest
from ai_telephone.prompts import make_prompt_v2
from ai_telephone.runner import BACKENDS, database
from ai_telephone.summarizer_examples import EXAMPLES, load_selected, render_examples
from test_v2_models import v2_document

PROJECT = __import__('pathlib').Path(__file__).resolve().parents[1]
TERRA = BACKENDS['terra']
SIGNOFF = {k: 'Named Person' for k in ['source_review', 'development_review', 'environment_review', 'analysis_plan']}


def make_root(tmp_path, docs):
    root = tmp_path / 'root'
    for name in FROZEN_FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes((PROJECT / name).read_bytes())
    (root / 'data/v2').mkdir(parents=True)
    sources = root / 'data/v2/sources.jsonl'
    sources.write_text(''.join(d.model_dump_json() + '\n' for d in docs), encoding='utf-8')
    signoff = tmp_path / 'signoff.json'
    signoff.write_text(json.dumps(SIGNOFF), encoding='utf-8')
    return root, sources, signoff


# --- freeze -------------------------------------------------------------------------

def test_freeze_writes_manifest_and_verify_detects_changes(tmp_path):
    root, sources, signoff = make_root(tmp_path, [v2_document('long-01')])
    out = tmp_path / 'terra.json'
    manifest = freeze_v2('terra', sources, signoff, out, root=root, version_fn=lambda b: 'v-test')
    assert manifest['design'] == 'v2' and manifest['model'] == 'gpt-6.1-terra' and manifest['cli_version'] == 'v-test'
    assert set(FROZEN_FILES) <= set(manifest['files']) and 'data/v2/sources.jsonl' in manifest['files']
    assert json.loads(out.read_text(encoding='utf-8')) == manifest
    assert verify_manifest(manifest, root) == []
    (root / 'data/v2/sources.jsonl').write_text('tampered\n', encoding='utf-8')
    assert verify_manifest(manifest, root) == ['data/v2/sources.jsonl: hash mismatch', 'sources: no longer valid v2 sources']


def test_freeze_refuses_unreviewed_sources_and_missing_signoff(tmp_path):
    root, sources, signoff = make_root(tmp_path, [v2_document('long-01', reviewed=False)])
    with pytest.raises(ValueError, match='reviewed'):
        freeze_v2('terra', sources, signoff, tmp_path / 'a.json', root=root, version_fn=lambda b: 'v')
    root, sources, signoff = make_root(tmp_path / 'second', [v2_document('long-01')])
    partial = dict(SIGNOFF); partial.pop('analysis_plan')
    signoff.write_text(json.dumps(partial), encoding='utf-8')
    with pytest.raises(ValueError, match='analysis_plan'):
        freeze_v2('terra', sources, signoff, tmp_path / 'b.json', root=root, version_fn=lambda b: 'v')
    assert not (tmp_path / 'a.json').exists() and not (tmp_path / 'b.json').exists()


def test_freeze_never_overwrites_an_existing_manifest(tmp_path):
    root, sources, signoff = make_root(tmp_path, [v2_document('long-01')])
    freeze_v2('terra', sources, signoff, tmp_path / 'm.json', root=root, version_fn=lambda b: 'v')
    with pytest.raises(FileExistsError):
        freeze_v2('terra', sources, signoff, tmp_path / 'm.json', root=root, version_fn=lambda b: 'v')


def test_freeze_covers_selected_examples_once_present(tmp_path):
    root, sources, signoff = make_root(tmp_path, [v2_document('long-01')])
    examples = root / 'data/v2/examples/selected.json'
    examples.parent.mkdir(parents=True)
    examples.write_text('{}', encoding='utf-8')
    manifest = freeze_v2('terra', sources, signoff, tmp_path / 'e.json', root=root, version_fn=lambda b: 'v')
    assert 'data/v2/examples/selected.json' in manifest['files']
    examples.write_text('{"changed": true}', encoding='utf-8')
    assert verify_manifest(manifest, root) == ['data/v2/examples/selected.json: hash mismatch']


# --- annotator on v2 IDs --------------------------------------------------------------

def judge_stream(backend, text):
    """Raw stream shaped like each judge's CLI output (Claude Code for opus-5-5, agy for the alternative)."""
    if backend.name == 'judge-opus':
        model = backend.model
        events = [{'type': 'system', 'subtype': 'init', 'model': model, 'tools': [], 'mcp_servers': []},
                  {'type': 'assistant', 'message': {'model': model, 'content': [{'type': 'text', 'text': text}]}},
                  {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': text, 'num_turns': 1,
                   'modelUsage': {model: {}}}]
    else:
        events = [{'event': 'init', 'init': {'model': backend.model}},
                  {'event': 'result', 'result': {'status': 'SUCCESS', 'num_turns': 1, 'response': text}}]
    return '\n'.join(json.dumps(e) for e in events)


def all_omitted(doc):
    items = [{'item_id': i.id, 'label': 'omitted', 'quotation': '', 'rationale': 'not in summary'} for i in doc.items]
    return json.dumps({'items': items, 'unsupported_claims': []})


class Judge:
    def __init__(self, backend, doc):
        self.backend, self.text, self.calls = backend, all_omitted(doc), []

    def __call__(self, args, **kwargs):
        self.calls.append(list(args))
        return SimpleNamespace(returncode=0, stdout=judge_stream(self.backend, self.text), stderr='')


def write_run(tmp_path, doc):
    db = database(tmp_path / 'run.sqlite', TERRA)
    for r in range(1, 6):
        for gid in [f'{doc.id}-few-limited-r{r}', f'{doc.id}-zero-free-r{r}']:
            db.execute('INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (gid, 1, 'success', 'x', 'x', 'p', f'summary of {gid}', '', '', 4))
    db.commit()
    db.close()
    sources = tmp_path / 'sources.jsonl'
    sources.write_text(doc.model_dump_json() + '\n', encoding='utf-8')
    return sources


def test_document_for_scores_only_rounds_1_3_5():
    docs = {'long-01': v2_document('long-01')}
    assert document_for('long-01-few-limited-r1', docs) is docs['long-01']
    assert document_for('long-01-few-limited-r3', docs) is docs['long-01']
    assert document_for('long-01-few-limited-r5', docs) is docs['long-01']
    assert document_for('long-01-few-limited-r2', docs) is None
    assert document_for('long-01-few-limited-r4', docs) is None


@pytest.mark.parametrize('judge_key,judge_id', [('opus-5-5', 'ai:claude-opus-5-5')])
def test_label_v2_rounds_135_with_judge_recorded(tmp_path, judge_key, judge_id):
    doc = v2_document('long-01')
    sources = write_run(tmp_path, doc)
    backend = JUDGES[judge_key]
    fake = Judge(backend, doc)
    out = tmp_path / 'ai-annotations.jsonl'
    args = SimpleNamespace(data=str(sources), run_db=str(tmp_path / 'run.sqlite'), judge=judge_key,
                           judge_db=str(tmp_path / 'judge.sqlite'), out=str(out))
    label(args, invoke=fake)
    lines = [json.loads(l) for l in out.read_text(encoding='utf-8').splitlines()]
    # 2 chains x rounds 1, 3, 5 only
    assert sorted(l['generation_id'] for l in lines) == sorted(
        f'long-01-{p}-{l}-r{r}' for p in ['few'] for l in ['limited'] for r in (1, 3, 5)
    ) + sorted(f'long-01-zero-free-r{r}' for r in (1, 3, 5))
    assert {l['reviewer_id'] for l in lines} == {judge_id}
    assert len(fake.calls) == 6
    assert all(backend.model in call for call in fake.calls)  # the requested judge model was used
    assert all(len(l['labels']) == len(doc.items) for l in lines)


def test_label_resumes_without_relabelling(tmp_path):
    doc = v2_document('long-01')
    sources = write_run(tmp_path, doc)
    out = tmp_path / 'ai.jsonl'
    args = SimpleNamespace(data=str(sources), run_db=str(tmp_path / 'run.sqlite'), judge='opus-5-5',
                           judge_db=str(tmp_path / 'judge.sqlite'), out=str(out))
    label(args, invoke=Judge(JUDGES['opus-5-5'], doc))
    again = Judge(JUDGES['opus-5-5'], doc)
    label(args, invoke=again)
    assert again.calls == []


# --- selected prompt examples -----------------------------------------------------------

ORDER = ['coupons', 'rover', 'filters', 'indexes', 'molding']


def record(name, **extra):
    e = EXAMPLES[name]
    return {'source': e['source'], 'good': e['good'], 'bad': e['bad'], 'why_bad': e['why_bad'], **extra}


def expected_block(records):
    return '\n\n'.join(
        f"Source:\n{e['source']}\n\nGood summary:\n{e['good']}\n\nBad summary:\n{e['bad']}\n\n"
        f"Why the bad summary is bad:\n{e['why_bad']}" for e in records)


def test_load_selected_absent_returns_none(tmp_path):
    assert load_selected(tmp_path / 'none.json') is None


def test_selected_examples_drive_render_and_prompt(tmp_path, monkeypatch):
    path = tmp_path / 'selected.json'
    path.write_text(json.dumps({f'E{n}': record(name, good_from='haiku run 1', bad_from='constructed')
                                for n, name in enumerate(ORDER, 1)}), encoding='utf-8')
    one, few = load_selected(path)
    assert one == [few[0]] and len(few) == 5
    assert render_examples('one', path=path) == expected_block(one)
    assert render_examples('few', path=path) == expected_block(few)
    assert 'haiku run 1' not in render_examples('few', path=path)  # provenance is not shown to the summarizer
    # make_prompt_v2 reads the default location; point that at the temporary file
    real = se.load_selected
    monkeypatch.setattr(se, 'load_selected', lambda path=se.SELECTED_PATH: real(path))
    prompt = make_prompt_v2('SOURCE', 'few', 'free')
    assert expected_block(few) in prompt and prompt.endswith('Text to summarize:\nSOURCE')


def test_selected_list_form_and_validation(tmp_path):
    good_list = tmp_path / 'list.json'
    good_list.write_text(json.dumps([record(n) for n in ORDER]), encoding='utf-8')
    assert load_selected(good_list)[1][4]['source'] == EXAMPLES['molding']['source']

    short = tmp_path / 'short.json'
    short.write_text(json.dumps([record(n) for n in ORDER[:4]]), encoding='utf-8')
    with pytest.raises(ValueError, match='exactly five'):
        load_selected(short)

    long_good = dict(record('coupons'), good=' '.join(['word'] * 81))
    bad_file = tmp_path / 'long.json'
    bad_file.write_text(json.dumps([long_good] + [record(n) for n in ORDER[1:]]), encoding='utf-8')
    with pytest.raises(ValueError, match='at most 80 words'):
        load_selected(bad_file)

    missing = dict(record('coupons')); missing.pop('why_bad')
    missing_file = tmp_path / 'missing.json'
    missing_file.write_text(json.dumps([missing] + [record(n) for n in ORDER[1:]]), encoding='utf-8')
    with pytest.raises(ValueError, match='why_bad'):
        load_selected(missing_file)
