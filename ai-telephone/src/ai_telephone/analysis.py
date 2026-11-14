"""Small, explicit document-level analysis primitives. Missing values stay missing."""
import numpy as np
import json

LABELS = ('preserved', 'omitted', 'strengthened', 'weakened', 'contradicted')
PROMPTS = ('zero', 'one', 'few')
LENGTHS = ('limited', 'free')
SCORED_ROUNDS = (1, 3, 5)
CONTRASTS = (('few', 'zero'), ('one', 'zero'), ('few', 'one'))

def load_jsonl(path):
    records = []
    with open(path, encoding='utf-8-sig') as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f'{path}: invalid JSON on line {number}') from exc
    return records

def parse_generation_id(generation_id):
    document, prompt, length, round_part = generation_id.rsplit('-', 3)
    if not round_part.startswith('r'):
        raise ValueError('invalid round')
    return document, prompt, length, int(round_part[1:])

def test_documents(sources):
    return {d['id']: [i['id'] for i in d['items']] for d in sources if d['split'] == 'test'}

def summary_rates(generations, annotations, documents):
    lookup = {}
    for annotation in annotations:
        gid = annotation['generation_id']
        if gid in lookup:
            raise ValueError(f'duplicate annotation {gid}')
        lookup[gid] = annotation
    rows = []
    seen = set()
    for generation in generations:
        gid = generation['generation_id']
        if gid in seen:
            raise ValueError(f'duplicate generation {gid}')
        seen.add(gid)
        doc = generation['document_id']
        if doc not in documents or generation['round'] not in SCORED_ROUNDS:
            continue
        annotation = lookup.get(gid)
        labels = {x['item_id']: x['label'] for x in annotation['labels']} if annotation else {}
        complete = generation['status'] == 'success' and bool(documents[doc]) and all(i in labels and labels[i] in LABELS for i in documents[doc])
        counts = {label: sum(labels.get(i) == label for i in documents[doc]) for label in LABELS} if complete else None
        rows.append({'document_id': doc, 'prompt': generation['prompt'], 'length': generation['length'],
                     'round': generation['round'], 'status': generation['status'], 'n_items': len(documents[doc]),
                     'n_preserved': counts['preserved'] if complete else None,
                     'rate': counts['preserved'] / len(documents[doc]) if complete else None,
                     'n_unsupported': len(annotation.get('unsupported_claims', [])) if complete else None,
                     'labels': counts})
    return rows

def contrasts(rows, length, round_):
    result = []
    for left, right in CONTRASTS:
        subset = [r for r in rows if r['length'] == length and r['round'] == round_]
        a = {r['document_id']: r['rate'] for r in subset if r['prompt'] == left}
        b = {r['document_id']: r['rate'] for r in subset if r['prompt'] == right}
        stats = paired_bootstrap(a, b)
        result.append({'contrast': f'{left}-{right}', 'length': length, 'round': round_,
                       'n_pairs': stats['n'], 'difference': stats['difference'], 'low': stats['low'], 'high': stats['high']})
    return result

def fraction_preserved(labels):
    labels = list(labels)
    if len(labels) != 3 or any(x is None for x in labels):
        return None
    return sum(x == 'preserved' for x in labels) / 3

def paired_bootstrap(left, right, *, seed=1729, samples=10000):
    """Maps document IDs to values. Only complete pairs enter; returns pair count."""
    ids = sorted(k for k in left.keys() & right.keys() if left[k] is not None and right[k] is not None)
    if not ids:
        return {'n': 0, 'difference': None, 'low': None, 'high': None}
    differences = np.array([left[k] - right[k] for k in ids], dtype=float)
    rng = np.random.default_rng(seed)
    draws = rng.choice(differences, size=(samples, len(ids)), replace=True).mean(axis=1)
    low, high = np.quantile(draws, [0.025, 0.975])
    return {'n': len(ids), 'difference': float(differences.mean()), 'low': float(low), 'high': float(high)}

def cohen_kappa(pairs):
    """Unweighted Cohen's kappa for (rater_a, rater_b) label pairs; None if undefined."""
    if not pairs:
        return None
    n = len(pairs)
    labels = sorted({x for p in pairs for x in p})
    observed = sum(a == b for a, b in pairs) / n
    expected = sum((sum(a == l for a, _ in pairs) / n) * (sum(b == l for _, b in pairs) / n) for l in labels)
    return None if expected == 1 else (observed - expected) / (1 - expected)

def agreement(pairs):
    """Human-vs-AI agreement on item labels: 5-way and preserved-vs-not."""
    binary = [(a == 'preserved', b == 'preserved') for a, b in pairs]
    confusion = {}
    for a, b in pairs:
        confusion[f'{a}->{b}'] = confusion.get(f'{a}->{b}', 0) + 1
    return {'n_items': len(pairs),
            'percent_agreement': (sum(a == b for a, b in pairs) / len(pairs)) if pairs else None,
            'kappa_5_label': cohen_kappa(pairs),
            'percent_agreement_preserved_vs_not': (sum(a == b for a, b in binary) / len(binary)) if binary else None,
            'kappa_preserved_vs_not': cohen_kappa(binary),
            'confusion_human_to_ai': dict(sorted(confusion.items()))}
