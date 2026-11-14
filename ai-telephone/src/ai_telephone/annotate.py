"""AI annotation of saved summaries (LLM judge), plus a blinded human-audit sample.

These labels are AI annotations, never human ones. The judge is claude-opus-5-5, a model
that is not under study, run through Claude Code with tools disabled. It sees only the
original source, the ground-truth items, and one summary: never the condition, round,
model, or other labels. Every summary is judged against the original source.

Commands:
  label  - label every successful generation in a run database (resumable)
  audit  - export a blinded, shuffled sample for independent human labelling
  agree  - compare filled human audit labels with the AI labels
"""
import argparse
import csv
import json
import random
import re
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from .analysis import agreement
from .annotator_prompt import make_annotation_prompt
from .models import Annotation
from .runner import (BACKENDS, Backend, agy_binary, agy_resolved_model, claude_binary, claude_resolved_model, database,
                     generate, load_documents, load_documents_v2, parse_agy_events, parse_claude_events)

JUDGE_MODEL = 'claude-opus-5-5'
JUDGE_ID = f'ai:{JUDGE_MODEL}'
JUDGE_ARGS = ['claude', '-p', '--model', JUDGE_MODEL, '--effort', 'high',
              '--tools', '', '--strict-mcp-config', '--setting-sources', '',
              '--no-session-persistence', '--output-format', 'stream-json', '--verbose',
              '--system-prompt', 'You are a careful research annotator.']
JUDGE = Backend('judge-opus', JUDGE_MODEL, 'high', 'Claude Code CLI (signed-in Claude)', tuple(JUDGE_ARGS),
                claude_binary, lambda raw: parse_claude_events(raw, JUDGE_MODEL), claude_resolved_model,
                'artifacts/ai-annotations.sqlite')
# Alternative judge, run through the Antigravity CLI (used if Claude usage is short). One judge is
# chosen for every model; the choice is recorded in each line's reviewer_id.
AGY_JUDGE_MODEL = 'claude-opus-4-6-thinking'
AGY_JUDGE = Backend('judge-opus-agy', AGY_JUDGE_MODEL, 'high', 'Antigravity CLI (signed-in Google)',
                    ('agy', '--model', AGY_JUDGE_MODEL, '--effort', 'high', '--output-format', 'stream-json',
                     '--disable-slash-commands'),
                    agy_binary, lambda raw: parse_agy_events(raw, AGY_JUDGE_MODEL), agy_resolved_model,
                    'artifacts/ai-annotations.sqlite', prompt_in_argv=True)
JUDGES = {'opus-5-5': JUDGE, 'opus-4-6-agy': AGY_JUDGE}
SCORED_ROUNDS = {1, 3, 5}
LABELS = {'preserved', 'omitted', 'strengthened', 'weakened', 'contradicted'}

def parse_judgement(text, item_ids, summary):
    """Validate the judge's JSON strictly; raise ValueError rather than guess."""
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip())
    data = json.loads(cleaned)
    items = data.get('items')
    if not isinstance(items, list) or sorted(i.get('item_id') for i in items) != sorted(item_ids):
        raise ValueError('judge must label every ground-truth item exactly once')
    for i in items:
        if i.get('label') not in LABELS:
            raise ValueError(f"invalid label {i.get('label')!r}")
        quote = i.get('quotation') or ''
        if i['label'] != 'omitted' and quote and quote not in summary:
            raise ValueError(f"{i['item_id']}: quotation is not verbatim from the summary")
        if not (i.get('rationale') or '').strip():
            raise ValueError(f"{i['item_id']}: missing rationale")
    claims = data.get('unsupported_claims', [])
    if not isinstance(claims, list) or any((c.get('quotation') or '') not in summary for c in claims):
        raise ValueError('unsupported claims must quote the summary verbatim')
    return items, claims

def successful_generations(run_db):
    with sqlite3.connect(f'file:{Path(run_db).resolve().as_posix()}?mode=ro', uri=True) as db:
        rows = db.execute("SELECT generation_id, output FROM attempts WHERE status='success' ORDER BY generation_id").fetchall()
        meta = dict(db.execute('SELECT key, value FROM run_meta'))
    return rows, meta

def is_v2_id(generation_id):
    parts = generation_id.rsplit('-', 3)
    return (len(parts) == 4 and parts[1] in {'zero', 'one', 'few'} and parts[2] in {'limited', 'free'}
            and re.fullmatch(r'r[1-5]', parts[3]) is not None)

def document_for(generation_id, docs):
    """Source document of a generation: v2 IDs split with rsplit('-', 3) and only rounds 1, 3, 5
    are scored (None otherwise); v1 IDs keep the legacy rsplit('-', 2) split."""
    if is_v2_id(generation_id):
        document_id, _, _, r = generation_id.rsplit('-', 3)
        return docs.get(document_id) if int(r[1:]) in SCORED_ROUNDS else None
    return docs.get(generation_id.rsplit('-', 2)[0])

def load_any(path):
    """Load v2 sources (have ``kind``) or v1 sources."""
    first = next((l for l in Path(path).read_text(encoding='utf-8').splitlines() if l.strip()), '{}')
    return load_documents_v2(path) if 'kind' in json.loads(first) else load_documents(path)

def label(args, invoke=subprocess.run):
    judge = JUDGES[getattr(args, 'judge', None) or 'opus-5-5']
    judge_id = f'ai:{judge.model}'
    docs = {d.id: d for d in load_any(args.data)}
    rows, meta = successful_generations(args.run_db)
    judge_db = database(args.judge_db, judge)
    out = Path(args.out)
    done = set()
    if out.exists():
        for line in out.read_text(encoding='utf-8').splitlines():
            if line.strip():
                done.add(json.loads(line)['generation_id'])
    todo = [(g, o) for g, o in rows if g not in done and document_for(g, docs)]
    print(f"run model={meta.get('model')} · {len(rows)} successful outputs · {len(todo)} to label · judge={judge.model}")
    with tempfile.TemporaryDirectory(prefix='ai-telephone-judge-') as work, out.open('a', encoding='utf-8') as f:
        for gid, summary in todo:
            doc = document_for(gid, docs)
            items = [{'item_id': i.id, 'type': i.type, 'quotation': i.quotation, 'meaning': i.meaning} for i in doc.items]
            prompt = make_annotation_prompt(doc.text, items, summary)
            raw = generate(judge_db, f"judge:{meta.get('model')}:{gid}", prompt, work, invoke=invoke, backend=judge)
            try:
                labels, claims = parse_judgement(raw, [i.id for i in doc.items], summary)
            except (ValueError, json.JSONDecodeError) as exc:
                raise SystemExit(f'{gid}: judge output failed validation ({exc}); inspect {args.judge_db}, do not relabel silently')
            for x in labels:  # validates against the shared annotation schema
                Annotation(generation_id=gid, item_id=x['item_id'], reviewer_id=judge_id, label=x['label'],
                           quotation=x.get('quotation') or '', rationale=x['rationale'])
            f.write(json.dumps({'generation_id': gid, 'run_model': meta.get('model'), 'reviewer_id': judge_id,
                                'labels': labels, 'unsupported_claims': claims}, ensure_ascii=False) + '\n')
            f.flush()
            print(gid, ' '.join(f"{x['item_id'].rsplit('-', 1)[-1]}={x['label']}" for x in labels), flush=True)

AUDIT_FIELDS = ['audit_id', 'source_text', 'summary', 'item_id', 'item_type', 'item_quotation', 'must_preserve',
                'reviewer', 'label', 'quotation', 'rationale']

def audit(args):
    """Blinded sample: shuffled audit IDs; no model, condition, round, or AI label in the sheet."""
    docs = {d.id: d for d in load_any(args.data)}
    rows, meta = successful_generations(args.run_db)
    rows = [(g, o) for g, o in rows if document_for(g, docs)]
    rng = random.Random(args.seed)
    by_round = {}
    for g, o in rows:
        by_round.setdefault(g.rsplit('-', 1)[-1] + ('d' if '-direct-' in g else ''), []).append((g, o))
    sample = []
    strata = sorted(by_round)
    for k in strata:
        rng.shuffle(by_round[k])
    while len(sample) < min(args.n, len(rows)):  # round-robin across rounds and the direct control
        for k in strata:
            if by_round[k] and len(sample) < args.n:
                sample.append(by_round[k].pop())
    rng.shuffle(sample)
    key = {}
    with Path(args.sheet).open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=AUDIT_FIELDS); w.writeheader()
        for n, (gid, summary) in enumerate(sample, 1):
            audit_id = f'A{n:03d}'; key[audit_id] = gid
            for item in document_for(gid, docs).items:
                w.writerow({'audit_id': audit_id, 'source_text': document_for(gid, docs).text, 'summary': summary,
                            'item_id': item.id, 'item_type': item.type, 'item_quotation': item.quotation,
                            'must_preserve': item.meaning})
    Path(args.key).write_text(json.dumps({'run_model': meta.get('model'), 'seed': args.seed, 'key': key}, indent=2), encoding='utf-8')
    print(f'Wrote {len(sample)} blinded summaries to {args.sheet}; keep {args.key} away from human auditors')

def agree(args):
    key = json.loads(Path(args.key).read_text(encoding='utf-8'))['key']
    ai = {}
    for line in Path(args.ai).read_text(encoding='utf-8').splitlines():
        if line.strip():
            r = json.loads(line)
            for x in r['labels']:
                ai[(r['generation_id'], x['item_id'])] = x['label']
    pairs = []
    with Path(args.sheet).open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            human = row['label'].strip().lower()
            if not human:
                continue
            if human not in LABELS:
                raise ValueError(f"{row['audit_id']}/{row['item_id']}: invalid label {human!r}")
            machine = ai.get((key[row['audit_id']], row['item_id']))
            if machine is not None:
                pairs.append((human, machine))
    result = agreement(pairs)
    print(json.dumps(result, indent=2))

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('label'); a.add_argument('--model', choices=sorted(BACKENDS), required=True)
    a.add_argument('--data', default='data/v2/sources.jsonl'); a.add_argument('--run-db')
    a.add_argument('--judge', choices=sorted(JUDGES), default='opus-5-5', help='AI annotator, one for all models')
    a.add_argument('--judge-db'); a.add_argument('--out')
    b = sub.add_parser('audit'); b.add_argument('--model', choices=sorted(BACKENDS), required=True)
    b.add_argument('--data', default='data/v2/sources.jsonl'); b.add_argument('--run-db')
    b.add_argument('--n', type=int, default=60); b.add_argument('--seed', type=int, default=1729)
    b.add_argument('--sheet'); b.add_argument('--key')
    c = sub.add_parser('agree'); c.add_argument('--model', choices=sorted(BACKENDS), required=True)
    c.add_argument('--sheet'); c.add_argument('--key'); c.add_argument('--ai')
    args = p.parse_args()
    m = args.model
    args.run_db = getattr(args, 'run_db', None) or BACKENDS[m].default_db
    if args.command == 'label':
        args.judge_db = args.judge_db or f'artifacts/ai-annotations-{m}.sqlite'
        args.out = args.out or f'results/{m}/ai-annotations.jsonl'
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        label(args)
    elif args.command == 'audit':
        args.sheet = args.sheet or f'artifacts/human-audit-{m}.csv'
        args.key = args.key or f'artifacts/human-audit-{m}-key.json'
        audit(args)
    else:
        args.sheet = args.sheet or f'artifacts/human-audit-{m}.csv'
        args.key = args.key or f'artifacts/human-audit-{m}-key.json'
        args.ai = args.ai or f'results/{m}/ai-annotations.jsonl'
        agree(args)

if __name__ == '__main__': main()
