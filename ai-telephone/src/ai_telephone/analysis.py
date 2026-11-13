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
