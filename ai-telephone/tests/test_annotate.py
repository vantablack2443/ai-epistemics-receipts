"""AI annotator and human-audit mechanics with a mocked judge; no real model calls."""
import csv
import json
from types import SimpleNamespace
import pytest
from ai_telephone.analysis import agreement, cohen_kappa
from ai_telephone.annotate import JUDGE, JUDGE_MODEL, LABELS, agree, audit, label, parse_judgement
from ai_telephone.annotator_prompt import EXAMPLES, make_annotation_prompt
from ai_telephone.runner import BACKENDS, database
from test_haiku import stream

def test_examples_are_internally_consistent():
    kinds = [e['kind'] for e in EXAMPLES]
    assert kinds.count('keeps information') == 3 and kinds.count('loses information') == 2
    seen = set()
    for e in EXAMPLES:
        for item in e['items']:
            assert item['quotation'] in e['original']
        ids = [i['item_id'] for i in e['items']]
        labels, claims = parse_judgement(json.dumps(e['answer']), ids, e['round2'])
        seen |= {x['label'] for x in labels}
        if e['kind'] == 'keeps information':
            assert all(x['label'] == 'preserved' for x in labels)
        else:
            assert any(x['label'] != 'preserved' for x in labels)
    assert seen == LABELS

def test_prompt_is_blinded():
    p = make_annotation_prompt('orig text', [{'item_id': 'x-q1', 'type': 'qualification', 'quotation': 'q', 'meaning': 'm'}], 'sum')
    tail = p.split('NOW ANNOTATE')[1]
    for leaked in ['condition', 'Condition', 'round 3', 'haiku', 'terra', 'gpt-6.1']:
        assert leaked not in tail
    assert JUDGE_MODEL not in {b.model for b in BACKENDS.values()}

@pytest.mark.parametrize('payload,error', [
    ({'items': [{'item_id': 'a', 'label': 'preserved', 'quotation': 'x', 'rationale': 'r'}]}, 'exactly once'),
    ({'items': [{'item_id': 'a', 'label': 'great', 'quotation': '', 'rationale': 'r'},
                {'item_id': 'b', 'label': 'omitted', 'quotation': '', 'rationale': 'r'}]}, 'invalid label'),
    ({'items': [{'item_id': 'a', 'label': 'preserved', 'quotation': 'not in summary', 'rationale': 'r'},
                {'item_id': 'b', 'label': 'omitted', 'quotation': '', 'rationale': 'r'}]}, 'verbatim'),
    ({'items': [{'item_id': 'a', 'label': 'preserved', 'quotation': 'kept', 'rationale': ''},
                {'item_id': 'b', 'label': 'omitted', 'quotation': '', 'rationale': 'r'}]}, 'rationale'),
])
def test_judgement_validation(payload, error):
    with pytest.raises(ValueError, match=error):
        parse_judgement(json.dumps(payload), ['a', 'b'], 'the kept summary')

def test_kappa_hand_calculated():
    assert cohen_kappa([('a', 'a'), ('b', 'b')]) == 1
    # observed 0.5; expected 0.5*0.5 + 0.5*0.5 = 0.5 -> kappa 0
    assert cohen_kappa([('a', 'a'), ('a', 'b'), ('b', 'a'), ('b', 'b')]) == 0
    r = agreement([('preserved', 'preserved'), ('omitted', 'strengthened')])
    assert r['percent_agreement'] == 0.5 and r['percent_agreement_preserved_vs_not'] == 1.0

def make_run(tmp_path):
    from test_runner import document
    doc = document()
    data = tmp_path / 'sources.jsonl'
    data.write_text(doc.model_dump_json() + '\n', encoding='utf-8')
    run = database(tmp_path / 'run.sqlite', BACKENDS['haiku'])
    for gid, out in [('dev-A-1', 'finding with one'), ('dev-A-2', 'finding only'), ('dev-direct-3', 'two and three')]:
        run.execute("INSERT INTO attempts VALUES (?,1,'success','t','t','p',?,'','',1)", (gid, out))
    run.execute("INSERT INTO attempts VALUES ('dev-A-3',1,'timeout','t','t','p',NULL,'','',NULL)")
    run.commit(); run.close()
    return doc, data

def test_label_resumes_and_skips_failed_generations(tmp_path):
    doc, data = make_run(tmp_path)
    prompts = []
    def invoke(args, **kwargs):
        assert args == list(JUDGE.args)
        prompts.append(kwargs['input'])
        summary = kwargs['input'].split('SUMMARY to annotate:\n')[-1].rsplit('\nANSWER:', 1)[0]
        items = [{'item_id': i.id, 'label': 'omitted', 'quotation': '', 'rationale': 'gone'} for i in doc.items]
        return SimpleNamespace(returncode=0, stdout=stream(json.dumps({'items': items, 'unsupported_claims': []}),
                                                           model=JUDGE_MODEL), stderr='')
    args = SimpleNamespace(data=str(data), run_db=str(tmp_path / 'run.sqlite'),
                           judge_db=str(tmp_path / 'judge.sqlite'), out=str(tmp_path / 'ai.jsonl'))
    label(args, invoke)
    assert len(prompts) == 3  # the timed-out generation is never labelled
    assert all('SECRET GROUND TRUTH' in p for p in prompts)  # judge does see the intended meaning
    label(args, invoke)
    assert len(prompts) == 3
    lines = [json.loads(l) for l in (tmp_path / 'ai.jsonl').read_text().splitlines()]
    assert {l['generation_id'] for l in lines} == {'dev-A-1', 'dev-A-2', 'dev-direct-3'}
    assert all(l['reviewer_id'] == f'ai:{JUDGE_MODEL}' for l in lines)

def test_audit_is_blinded_and_agreement_joins_by_key(tmp_path):
    doc, data = make_run(tmp_path)
    sheet, key = tmp_path / 'audit.csv', tmp_path / 'key.json'
    audit(SimpleNamespace(data=str(data), run_db=str(tmp_path / 'run.sqlite'), n=2, seed=1729, sheet=str(sheet), key=str(key)))
    text = sheet.read_text(encoding='utf-8-sig')
    for leaked in ['dev-A-', 'direct', 'haiku', 'preserved', 'omitted']:
        assert leaked not in text
    rows = list(csv.DictReader(sheet.open(encoding='utf-8-sig')))
    assert len({r['audit_id'] for r in rows}) == 2
    mapping = json.loads(key.read_text())['key']
    ai = tmp_path / 'ai.jsonl'
    ai.write_text(''.join(json.dumps({'generation_id': g, 'labels': [{'item_id': i.id, 'label': 'omitted'} for i in doc.items]}) + '\n'
                          for g in mapping.values()))
    for r in rows: r['label'] = 'omitted'
    with sheet.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
    agree(SimpleNamespace(sheet=str(sheet), key=str(key), ai=str(ai)))
