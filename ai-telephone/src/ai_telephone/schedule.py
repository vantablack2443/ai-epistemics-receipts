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
