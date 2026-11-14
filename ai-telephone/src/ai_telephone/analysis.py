"""Small, explicit document-level analysis primitives. Missing values stay missing."""
import numpy as np

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
