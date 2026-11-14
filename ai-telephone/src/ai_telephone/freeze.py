"""Prepare a tamper-evident protocol manifest only after explicit human gates."""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .runner import BACKENDS, cli_version, load_documents
from .schedule import CATEGORIES, balanced_schedule

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', required=True)
    p.add_argument('--signoff', required=True, help='JSON with human review and development gate confirmations')
    p.add_argument('--count', type=int, choices=[10,15,20,25,30], default=30)
    p.add_argument('--output', required=True)
    p.add_argument('--model', choices=sorted(BACKENDS), required=True,
                   help='one manifest per model; both models must share the same frozen sources and prompts')
    args = p.parse_args()
    backend = BACKENDS[args.model]
    docs = load_documents(args.sources)
    if len(docs) != 36 or sum(d.split == 'development' for d in docs) != 6:
        raise ValueError('expected 36 sources, including six development documents')
    tests = [d for d in docs if d.split == 'test']
    if Counter(d.category for d in tests) != {c: 6 for c in CATEGORIES}:
        raise ValueError('expected six held-out documents in each category')
    if any(not d.reviewed or not 180 <= len(d.text.split()) <= 240 for d in docs):
        raise ValueError('every source needs human review and a valid length')
    signoff = json.loads(Path(args.signoff).read_text(encoding='utf-8'))
    for key in ['source_review', 'development_pipeline_review', 'environment_review', 'analysis_plan_review']:
        if not isinstance(signoff.get(key), str) or not signoff[key].strip():
            raise ValueError(f'named human sign-off required: {key}')
    paths = [args.sources, args.signoff, 'src/ai_telephone/prompts.py', 'src/ai_telephone/runner.py',
             'src/ai_telephone/analysis.py', 'docs/protocol.md', 'docs/annotation.md']
    manifest = {'created_utc':datetime.now(timezone.utc).isoformat(), 'status':'frozen', 'seed':1729,
                'sample_size':args.count, 'backend':backend.name, 'model':backend.model,
                'reasoning_effort':backend.reasoning_effort, 'harness':backend.harness,
                'cli_version':cli_version(backend), 'args':list(backend.args),
                'files':{str(p):sha(p) for p in paths}, 'schedule':balanced_schedule(docs, args.count)}
    with Path(args.output).open('x', encoding='utf-8') as f: json.dump(manifest, f, indent=2)
    print('Manifest written; final collection is not implemented or authorized by this command.')

if __name__ == '__main__': main()
