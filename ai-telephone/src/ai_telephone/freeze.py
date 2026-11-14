"""Prepare a tamper-evident protocol manifest only after explicit human gates (design v2).

  freeze --model M --sources data/v2/sources.jsonl --signoff signoff.json --output freeze/M.json
  freeze --verify freeze/M.json

The legacy v1 freeze remains available as ``main_v1``.
"""
import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from .runner import BACKENDS, cli_version, load_documents, load_documents_v2
from .schedule import CATEGORIES, balanced_schedule, schedule_v2

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def project_root():
    return Path(__file__).resolve().parents[2]

FROZEN_FILES = ['src/ai_telephone/prompts.py', 'src/ai_telephone/summarizer_examples.py',
                'src/ai_telephone/runner.py', 'src/ai_telephone/annotator_prompt.py',
                'src/ai_telephone/annotate.py', 'docs/design-v2.md']
SIGNOFF_KEYS = ['source_review', 'development_review', 'environment_review', 'analysis_plan']

def rel(path, root):
    """Path as stored in a manifest: relative to the project root when inside it."""
    p = Path(path).resolve()
    try:
        return p.relative_to(Path(root).resolve()).as_posix()
    except ValueError:
        return str(p)

def verify_manifest(manifest, root=None):
    """Recompute every file hash and the schedule. Returns a list of mismatch descriptions."""
    root = Path(root) if root else project_root()
    problems = []
    for name, expected in manifest.get('files', {}).items():
        path = root / name
        if not path.is_file():
            problems.append(f'{name}: missing')
        elif sha(path) != expected:
            problems.append(f'{name}: hash mismatch')
    sources = manifest.get('sources')
    if sources and (root / sources).is_file():
        try:
            docs = load_documents_v2(root / sources)
        except ValueError:
            problems.append('sources: no longer valid v2 sources')
        else:
            if schedule_v2(docs, manifest.get('seed', 1729)) != manifest.get('schedule'):
                problems.append('schedule: does not match the schedule recomputed from the sources')
    else:
        problems.append('sources: missing')
    return problems

def freeze_v2(model, sources, signoff, output, root=None, version_fn=None):
    root = Path(root) if root else project_root()
    backend = BACKENDS[model]
    docs = load_documents_v2(sources)
    tests = [d for d in docs if d.split == 'test']
    if not tests:
        raise ValueError('no test documents')
    if any(not d.reviewed for d in docs):
        raise ValueError('every source must be marked reviewed by a human before freezing')
    people = json.loads(Path(signoff).read_text(encoding='utf-8'))
    for key in SIGNOFF_KEYS:
        if not isinstance(people.get(key), str) or not people[key].strip():
            raise ValueError(f'named human sign-off required: {key}')
    files = {name: sha(root / name) for name in FROZEN_FILES}
    files[rel(sources, root)] = sha(sources)
    examples = root / 'data/v2/examples/selected.json'  # human-selected prompt examples, once they exist
    if examples.is_file():
        files[rel(examples, root)] = sha(examples)
    manifest = {'created_utc': datetime.now(timezone.utc).isoformat(), 'status': 'frozen', 'design': 'v2',
                'seed': 1729, 'model_key': model, 'backend': backend.name, 'model': backend.model,
                'reasoning_effort': backend.reasoning_effort, 'harness': backend.harness,
                'cli_version': (version_fn or cli_version)(backend), 'args': list(backend.args),
                'sources': rel(sources, root), 'signoff_sha256': sha(signoff), 'files': files,
                'schedule': schedule_v2(docs, 1729)}
    with Path(output).open('x', encoding='utf-8') as f: json.dump(manifest, f, indent=2)
    return manifest

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--model', choices=sorted(BACKENDS))
    p.add_argument('--sources')
    p.add_argument('--signoff', help='JSON naming the humans for: ' + ', '.join(SIGNOFF_KEYS))
    p.add_argument('--output')
    p.add_argument('--verify', help='manifest to verify')
    args = p.parse_args()
    if args.verify:
        try:
            manifest = json.loads(Path(args.verify).read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f'cannot read manifest {args.verify}: {exc}')
        problems = verify_manifest(manifest)
        print('verified' if not problems else '\n'.join(problems))
        raise SystemExit(1 if problems else 0)
    if not (args.model and args.sources and args.signoff and args.output):
        p.error('--model, --sources, --signoff and --output are required')
    freeze_v2(args.model, args.sources, args.signoff, args.output)
    print('Manifest written; final collection is not started by this command.')

def main_v1():
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
