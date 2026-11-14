"""Predefine balanced collection blocks without looking at model outputs."""
import random

CATEGORIES = ('tentative', 'scope', 'assumption', 'conditional', 'conflict')

def balanced_schedule(documents, count=30, seed=1729):
    if count not in (10, 15, 20, 25, 30):
        raise ValueError('sample must be a predetermined balanced size')
    rng = random.Random(seed)
    pools = {}
    for category in CATEGORIES:
        pool = sorted((d for d in documents if d.split == 'test' and d.category == category), key=lambda d: d.id)
        if len(pool) < count // 5:
            raise ValueError(f'insufficient {category} documents')
        rng.shuffle(pool)
        pools[category] = pool
    result = []
    for block in range(count // 5):
        categories = list(CATEGORIES); rng.shuffle(categories)
        for category in categories:
            conditions = list('ABC'); rng.shuffle(conditions)
            result.append({'block': block + 1, 'document_id': pools[category][block].id, 'conditions': conditions})
    return result

# --- Design v2 ---------------------------------------------------------------------

PROMPTS = ('zero', 'one', 'few')
LENGTHS = ('limited', 'free')

def all_chains():
    return [{'prompt': p, 'length': l} for p in PROMPTS for l in LENGTHS]

def shuffled_chains(seed=1729):
    """The six (prompt, length) chains of one document in a seeded random order."""
    chains = all_chains()
    random.Random(seed).shuffle(chains)
    return chains

def schedule_v2(docs, seed=1729):
    """Test documents in shuffled order; per document its six chains shuffled. Deterministic."""
    rng = random.Random(seed)
    tests = sorted((d for d in docs if d.split == 'test'), key=lambda d: d.id)
    rng.shuffle(tests)
    result = []
    for doc in tests:
        chains = all_chains()
        rng.shuffle(chains)
        result.append({'document_id': doc.id, 'chains': chains})
    return result
