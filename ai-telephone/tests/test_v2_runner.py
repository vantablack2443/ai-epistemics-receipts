"""Design v2 runner: chains, IDs, failure handling, resume, export, schedule, final-run guard, CLI plumbing.

Mocked invocations only (no real model calls). Terra's Codex stream is used because its
parser is the simplest: one agent_message and a turn.completed event.
"""
import json
import sys
from types import SimpleNamespace

import pytest

from ai_telephone import runner
from ai_telephone.freeze import FROZEN_FILES, freeze_v2
from ai_telephone.prompts import make_prompt_v2
from ai_telephone.runner import (BACKENDS, GenerationError, database, export_generations, generation_id,
                                 parse_generation_id, run_chain_v2, run_dev, run_final)
from ai_telephone.schedule import all_chains, schedule_v2, shuffled_chains
from test_v2_models import v2_document

TERRA = BACKENDS['terra']
PROJECT = runner.Path(__file__).resolve().parents[1]


def codex_stream(text):
    return '\n'.join([json.dumps({'type': 'item.completed', 'item': {'type': 'agent_message', 'text': text}}),
                      json.dumps({'type': 'turn.completed'})])


class Fake:
    """Returns OUT<n> for the n-th call and records each prompt (Codex receives it on stdin)."""
    def __init__(self, fail_on=None, returncode=0, stderr=''):
        self.prompts, self.fail_on, self.returncode, self.stderr = [], fail_on, returncode, stderr

    def __call__(self, args, **kwargs):
        n = len(self.prompts) + 1
        self.prompts.append(kwargs['input'])
        if n == self.fail_on:
            return SimpleNamespace(returncode=self.returncode, stdout=codex_stream(f'OUT{n}'), stderr=self.stderr)
        return SimpleNamespace(returncode=0, stdout=codex_stream(f'OUT{n}'), stderr='')


def fresh_db(tmp_path, name='run.sqlite'):
    return database(tmp_path / name, TERRA)


def test_generation_id_round_trip():
    for doc in ['long-01', 'dev-long-03', 'paper-02']:
        for p in ['zero', 'one', 'few']:
            for l in ['limited', 'free']:
                for r in range(1, 6):
                    gid = generation_id(doc, p, l, r)
                    assert gid == f'{doc}-{p}-{l}-r{r}'
                    assert parse_generation_id(gid) == (doc, p, l, r)


def test_chain_isolation_over_five_rounds(tmp_path):
    doc = v2_document('long-01')
    fake = Fake()
    run_chain_v2(fresh_db(tmp_path), doc, 'few', 'limited', tmp_path, invoke=fake, backend=TERRA)
    assert len(fake.prompts) == 5
    assert fake.prompts[0] == make_prompt_v2(doc.text, 'few', 'limited')
    for k in range(1, 5):  # round k+1 sees exactly round k's output and nothing older
        assert fake.prompts[k] == make_prompt_v2(f'OUT{k}', 'few', 'limited')
        assert doc.text not in fake.prompts[k]


def test_failure_stops_chain_and_later_rounds_are_not_run(tmp_path):
    doc = v2_document('long-01')
    db = fresh_db(tmp_path)
    fake = Fake(fail_on=2, returncode=1)  # process failure, not transient: no retries
    assert run_chain_v2(db, doc, 'zero', 'free', tmp_path, invoke=fake, backend=TERRA) is None
    assert len(fake.prompts) == 2
    rows = db.execute("SELECT generation_id, status, COUNT(*) FROM attempts GROUP BY generation_id ORDER BY generation_id").fetchall()
    assert rows == [('long-01-zero-free-r1', 'success', 1), ('long-01-zero-free-r2', 'process_failure', 1)]


def test_fatal_failure_stops_the_whole_run(tmp_path):
    doc = v2_document('long-01')
    fake = Fake(fail_on=1, returncode=1, stderr='quota exceeded')
    with pytest.raises(GenerationError) as exc:
        run_chain_v2(fresh_db(tmp_path), doc, 'zero', 'free', tmp_path, invoke=fake, backend=TERRA)
    assert exc.value.fatal


def test_resume_skips_completed_calls(tmp_path):
    doc = v2_document('long-01')
    db = fresh_db(tmp_path)
    first = Fake()
    out = run_chain_v2(db, doc, 'one', 'free', tmp_path, invoke=first, backend=TERRA)
    again = Fake()
    assert run_chain_v2(db, doc, 'one', 'free', tmp_path, invoke=again, backend=TERRA) == out == 'OUT5'
    assert again.prompts == []


def test_run_dev_uses_seeded_chain_order(tmp_path):
    doc = v2_document('dev-long-01', split='development')
    fake = Fake()
    run_dev(fresh_db(tmp_path), doc, tmp_path, invoke=fake, backend=TERRA)
    assert len(fake.prompts) == 30
    first = shuffled_chains(1729)[0]
    assert fake.prompts[0] == make_prompt_v2(doc.text, first['prompt'], first['length'])


def test_schedule_v2_is_deterministic_and_test_only():
    docs = [v2_document(f'long-{n:02d}') for n in range(1, 4)] + [v2_document('dev-long-01', split='development')]
    first = schedule_v2(docs, 1729)
    assert first == schedule_v2(docs, 1729)
    assert sorted(e['document_id'] for e in first) == ['long-01', 'long-02', 'long-03']
    for entry in first:
        assert sorted((c['prompt'], c['length']) for c in entry['chains']) == sorted(
            (c['prompt'], c['length']) for c in all_chains())


def test_export_marks_unattempted_generations_not_run(tmp_path):
    doc = v2_document('long-01')
    db = fresh_db(tmp_path)
    run_chain_v2(db, doc, 'few', 'limited', tmp_path, invoke=Fake(fail_on=2, returncode=1), backend=TERRA)
    out = tmp_path / 'generations.jsonl'
    rows = export_generations(tmp_path / 'run.sqlite', [doc], TERRA, out, 'test')
    assert len(rows) == 30  # 6 chains x 5 rounds
    by_id = {r['generation_id']: r for r in rows}
    assert by_id['long-01-few-limited-r1']['status'] == 'success'
    assert by_id['long-01-few-limited-r1']['output'] == 'OUT1'
    assert by_id['long-01-few-limited-r2']['status'] == 'process_failure'
    assert [by_id[f'long-01-few-limited-r{r}']['status'] for r in (3, 4, 5)] == ['not_run'] * 3
    assert by_id['long-01-few-limited-r3']['attempts'] == 0
    assert len(out.read_text(encoding='utf-8').splitlines()) == 30


def test_run_final_refuses_a_changed_file_and_resumes(tmp_path):
    root = tmp_path / 'root'
    for name in FROZEN_FILES:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes((PROJECT / name).read_bytes())
    (root / 'data/v2').mkdir(parents=True)
    sources = root / 'data/v2/sources.jsonl'
    docs = [v2_document('long-01'), v2_document('long-02')]
    sources.write_text(''.join(d.model_dump_json() + '\n' for d in docs), encoding='utf-8')
    signoff = tmp_path / 'signoff.json'
    signoff.write_text(json.dumps({k: 'Named Person' for k in ['source_review', 'development_review',
                                                               'environment_review', 'analysis_plan']}), encoding='utf-8')
    version = lambda backend: 'codex-test 1.0'
    manifest = root / 'freeze.json'
    freeze_v2('terra', sources, signoff, manifest, root=root, version_fn=version)
    db_path = tmp_path / 'final.sqlite'

    (root / 'src/ai_telephone/prompts.py').write_text('# changed after freeze\n', encoding='utf-8')
    refused = Fake()
    with pytest.raises(RuntimeError, match='hash mismatch'):
        run_final(manifest, TERRA, db_path, invoke=refused, version_fn=version, root=root)
    assert refused.prompts == []

    (root / 'src/ai_telephone/prompts.py').write_bytes((PROJECT / 'src/ai_telephone/prompts.py').read_bytes())
    first = Fake()
    run_final(manifest, TERRA, db_path, invoke=first, version_fn=version, root=root)
    assert len(first.prompts) == 60  # 2 documents x 6 chains x 5 rounds
    second = Fake()
    run_final(manifest, TERRA, db_path, invoke=second, version_fn=version, root=root)
    assert second.prompts == []


def test_cli_validate_export_run_dev_and_run_final(tmp_path, monkeypatch, capsys):
    data = tmp_path / 'sources.jsonl'
    dev = v2_document('dev-long-01', split='development')
    docs = [v2_document('long-01'), dev]
    data.write_text(''.join(d.model_dump_json() + '\n' for d in docs), encoding='utf-8')
    db = tmp_path / 'cli.sqlite'
    fresh_db(tmp_path, 'cli.sqlite')

    monkeypatch.setattr(sys, 'argv', ['runner', 'validate', '--data', str(data)])
    runner.main()
    assert '2 valid documents' in capsys.readouterr().out

    out = tmp_path / 'gen.jsonl'
    monkeypatch.setattr(sys, 'argv', ['runner', 'export', '--model', 'terra', '--db', str(db),
                                      '--data', str(data), '--out', str(out)])
    runner.main()
    assert len(out.read_text(encoding='utf-8').splitlines()) == 30
    assert 'not_run' in capsys.readouterr().out

    calls = {}
    monkeypatch.setattr(runner, 'cli_version', lambda backend: 'test-version')
    monkeypatch.setattr(runner, 'run_dev', lambda db_, doc, cwd, invoke=None, backend=None: calls.update(doc=doc.id))
    monkeypatch.setattr(sys, 'argv', ['runner', 'run-dev', '--model', 'terra', '--data', str(data),
                                      '--document', 'dev-long-01', '--db', str(tmp_path / 'dev.sqlite')])
    runner.main()
    assert calls == {'doc': 'dev-long-01'}

    final = {}
    monkeypatch.setattr(runner, 'run_final', lambda manifest, backend, db_path, **k: final.update(m=manifest))
    monkeypatch.setattr(sys, 'argv', ['runner', 'run-final', '--model', 'terra', '--manifest', 'freeze/terra.json',
                                      '--db', str(tmp_path / 'f.sqlite')])
    runner.main()
    assert final == {'m': 'freeze/terra.json'}


def test_cli_missing_sources_is_a_clean_error(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['runner', 'validate', '--data', str(tmp_path / 'absent.jsonl')])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert 'cannot load sources' in str(exc.value)


def test_cli_help_lists_v2_commands(monkeypatch, capsys):
    monkeypatch.setattr(sys, 'argv', ['runner', '--help'])
    with pytest.raises(SystemExit) as exc:
        runner.main()
    assert exc.value.code == 0
    text = capsys.readouterr().out
    for command in ['validate', 'smoke', 'run-dev', 'run-final', 'export']:
        assert command in text
