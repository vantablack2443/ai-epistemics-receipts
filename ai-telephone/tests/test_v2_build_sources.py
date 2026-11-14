import json
from pathlib import Path

import pytest

from ai_telephone.build_sources import build, main
from ai_telephone.models import DocumentV2

LABEL = 'AI review (test agent)'


def make_doc(doc_id, split='development', n_items=6, findings=1):
    quotes = [f'Quotation number {n} for {doc_id} holds.' for n in range(n_items)]
    text = ' '.join(['background'] * 1000) + ' ' + ' '.join(quotes)
    items = [{'id': f'{doc_id}-{"f" if n < findings else "q"}{n + 1}',
              'type': 'finding' if n < findings else 'qualification',
              'quotation': q, 'meaning': f'original meaning {n}'} for n, q in enumerate(quotes)]
    return DocumentV2(id=doc_id, split=split, kind='fictional', text=text,
                      provenance='synthetic draft', licence='CC0', items=items)


def write_drafts(path: Path, docs):
    path.write_text(''.join(d.model_dump_json() + '\n' for d in docs), encoding='utf-8')
    return path


def item(item_id, decision='approve', new_meaning=None):
    d = {'item_id': item_id, 'decision': decision, 'note': 'checked'}
    if new_meaning is not None:
        d['new_meaning'] = new_meaning
    return d


def review_line(doc, items, verdict='accept', note=''):
    ids = [i.id for i in doc.items] if isinstance(doc, DocumentV2) else [doc]
    doc_id = doc.id if isinstance(doc, DocumentV2) else doc
    return {'document_id': doc_id, 'reviewer': 'agent', 'strength_ok': True, 'realistic': True,
            'doc_verdict': verdict, 'doc_note': note, 'items': items}


def all_approve(doc):
    return [item(i.id) for i in doc.items]


def write_reviews(path: Path, lines):
    path.write_text(''.join(json.dumps(line, ensure_ascii=False) + '\n' for line in lines), encoding='utf-8')
    return path


def read_out(path: Path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def run(tmp_path, docs, lines, drafts_extra=(), overwrite=False, out_name='sources.jsonl'):
    drafts = write_drafts(tmp_path / 'drafts.jsonl', docs) if docs is not None else None
    reviews = write_reviews(tmp_path / 'review.jsonl', lines)
    out = tmp_path / out_name
    draft_paths = ([drafts] if drafts else []) + [Path(p) for p in drafts_extra]
    return build(draft_paths, reviews, out, LABEL, overwrite=overwrite), out


def test_accept_writes_document_and_report(tmp_path):
    doc = make_doc('dev-01')
    report, out = run(tmp_path, [doc], [review_line(doc, all_approve(doc))])
    assert report['included'] == ['dev-01'] and report['excluded'] == []
    assert report['items'] == {'approved': 6, 'revised': 0, 'rejected': 0}
    rows = read_out(out)
    assert len(rows) == 1 and rows[0]['reviewed'] is True
    assert rows[0]['text'] == doc.text
    assert [i['quotation'] for i in rows[0]['items']] == [i.quotation for i in doc.items]


def test_redraft_is_excluded_with_reason(tmp_path):
    good, bad = make_doc('dev-01'), make_doc('dev-02')
    report, out = run(tmp_path, [good, bad], [review_line(good, all_approve(good)),
                                             review_line(bad, all_approve(bad), verdict='redraft', note='weak')])
    assert report['included'] == ['dev-01']
    assert report['excluded'] == [{'id': 'dev-02', 'reason': 'doc_verdict is redraft: weak'}]
    assert [r['id'] for r in read_out(out)] == ['dev-01']


def test_rejected_item_is_dropped(tmp_path):
    doc = make_doc('dev-01', n_items=7)
    decisions = all_approve(doc)
    decisions[-1] = item(doc.items[-1].id, 'reject')
    report, out = run(tmp_path, [doc], [review_line(doc, decisions)])
    row = read_out(out)[0]
    assert [i['id'] for i in row['items']] == [i.id for i in doc.items[:-1]]
    assert report['items'] == {'approved': 6, 'revised': 0, 'rejected': 1}


def test_meaning_is_revised_and_quotation_kept(tmp_path):
    doc = make_doc('dev-01')
    decisions = all_approve(doc)
    decisions[2] = item(doc.items[2].id, 'revise_meaning', new_meaning='a corrected meaning')
    report, out = run(tmp_path, [doc], [review_line(doc, decisions)])
    row = read_out(out)[0]
    assert row['items'][2]['meaning'] == 'a corrected meaning'
    assert row['items'][2]['quotation'] == doc.items[2].quotation
    assert row['items'][0]['meaning'] == 'original meaning 0'
    assert report['items']['revised'] == 1 and report['items']['approved'] == 5


@pytest.mark.parametrize('new_meaning', [None, '', '   '])
def test_revise_meaning_requires_non_empty_new_meaning(tmp_path, new_meaning):
    doc = make_doc('dev-01')
    decisions = all_approve(doc)
    decisions[0] = item(doc.items[0].id, 'revise_meaning', new_meaning=new_meaning)
    with pytest.raises(ValueError, match='new_meaning'):
        run(tmp_path, [doc], [review_line(doc, decisions)])


def test_provenance_suffix_is_exact(tmp_path):
    doc = make_doc('dev-01')
    _, out = run(tmp_path, [doc], [review_line(doc, all_approve(doc))])
    assert read_out(out)[0]['provenance'] == (
        'synthetic draft; reviewed by AI review (test agent); not reviewed by a human')


def test_missing_review_line_raises(tmp_path):
    a, b = make_doc('dev-01'), make_doc('dev-02')
    with pytest.raises(ValueError, match='dev-02'):
        run(tmp_path, [a, b], [review_line(a, all_approve(a))])


def test_item_missing_from_review_raises(tmp_path):
    doc = make_doc('dev-01')
    with pytest.raises(ValueError, match='dev-01'):
        run(tmp_path, [doc], [review_line(doc, all_approve(doc)[:5])])


def test_item_duplicated_in_review_raises(tmp_path):
    doc = make_doc('dev-01')
    decisions = all_approve(doc) + [item(doc.items[0].id)]
    with pytest.raises(ValueError, match='dev-01'):
        run(tmp_path, [doc], [review_line(doc, decisions)])


def test_unknown_item_in_review_raises(tmp_path):
    doc = make_doc('dev-01')
    decisions = all_approve(doc) + [item('dev-01-zz')]
    with pytest.raises(ValueError, match='unknown'):
        run(tmp_path, [doc], [review_line(doc, decisions)])


def test_document_below_six_items_after_rejects_is_excluded(tmp_path):
    doc = make_doc('dev-01')
    decisions = all_approve(doc)
    decisions[0] = item(doc.items[0].id, 'reject')
    report, out = run(tmp_path, [doc], [review_line(doc, decisions)])
    assert report['included'] == []
    assert len(report['excluded']) == 1 and report['excluded'][0]['id'] == 'dev-01'
    assert '6 to 10 items' in report['excluded'][0]['reason']
    assert read_out(out) == []


def test_removing_all_findings_excludes_document(tmp_path):
    doc = make_doc('dev-01', findings=1, n_items=7)
    decisions = all_approve(doc)
    decisions[0] = item(doc.items[0].id, 'reject')
    report, _ = run(tmp_path, [doc], [review_line(doc, decisions)])
    assert report['excluded'][0]['id'] == 'dev-01'
    assert '1 or 2 findings' in report['excluded'][0]['reason']


def test_duplicate_ids_across_draft_files_raise(tmp_path):
    doc = make_doc('dev-01')
    first = write_drafts(tmp_path / 'a.jsonl', [doc])
    second = write_drafts(tmp_path / 'b.jsonl', [doc])
    reviews = write_reviews(tmp_path / 'r.jsonl', [review_line(doc, all_approve(doc))])
    with pytest.raises(ValueError, match='duplicate document id'):
        build([first, second], reviews, tmp_path / 'out.jsonl', LABEL)


def test_missing_draft_file_is_skipped(tmp_path):
    doc = make_doc('dev-01')
    report, out = run(tmp_path, [doc], [review_line(doc, all_approve(doc))],
                      drafts_extra=[tmp_path / 'does-not-exist.jsonl'])
    assert report['included'] == ['dev-01']
    assert report['missing_drafts'] == [str(tmp_path / 'does-not-exist.jsonl')]


def test_no_overwrite_without_flag(tmp_path):
    doc = make_doc('dev-01')
    _, out = run(tmp_path, [doc], [review_line(doc, all_approve(doc))])
    before = out.read_text(encoding='utf-8')
    with pytest.raises(FileExistsError):
        run(tmp_path, [doc], [review_line(doc, all_approve(doc))])
    assert out.read_text(encoding='utf-8') == before


def test_overwrite_flag_replaces_output(tmp_path):
    doc = make_doc('dev-01')
    _, out = run(tmp_path, [doc], [review_line(doc, all_approve(doc))])
    out.write_text('stale\n', encoding='utf-8')
    report, _ = run(tmp_path, [doc], [review_line(doc, all_approve(doc))], overwrite=True)
    assert report['included'] == ['dev-01']
    assert [r['id'] for r in read_out(out)] == ['dev-01']


def test_output_ordered_development_then_test(tmp_path):
    test_b, test_a = make_doc('test-b', split='test'), make_doc('test-a', split='test')
    dev_z, dev_m = make_doc('dev-z'), make_doc('dev-m')
    docs = [test_b, dev_z, test_a, dev_m]
    lines = [review_line(d, all_approve(d)) for d in docs]
    report, out = run(tmp_path, docs, lines)
    assert [r['id'] for r in read_out(out)] == ['dev-m', 'dev-z', 'test-a', 'test-b']
    assert report['included'] == ['dev-m', 'dev-z', 'test-a', 'test-b']


def test_cli_prints_report_json(tmp_path, capsys):
    doc = make_doc('dev-01')
    drafts = write_drafts(tmp_path / 'd.jsonl', [doc])
    reviews = write_reviews(tmp_path / 'r.jsonl', [review_line(doc, all_approve(doc))])
    out = tmp_path / 'sources.jsonl'
    code = main(['--drafts', str(drafts), str(tmp_path / 'absent.jsonl'), '--reviews', str(reviews),
                 '--out', str(out), '--reviewer-label', LABEL])
    assert code == 0
    report = json.loads(capsys.readouterr().out)
    assert report['included'] == ['dev-01']
    assert [r['id'] for r in read_out(out)] == ['dev-01']
