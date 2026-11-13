from types import SimpleNamespace
from ai_telephone.schedule import CATEGORIES, balanced_schedule

def test_balanced_deterministic_schedule():
    docs = [SimpleNamespace(id=f'{c}-{n}', split='test', category=c) for c in CATEGORIES for n in range(6)]
    schedule = balanced_schedule(docs, 10)
    assert schedule == balanced_schedule(docs, 10)
    by_id = {d.id:d for d in docs}
    assert len({x['document_id'] for x in schedule}) == 10
    for block in (1,2):
        assert {by_id[x['document_id']].category for x in schedule if x['block'] == block} == set(CATEGORIES)
    assert all(set(x['conditions']) == set('ABC') for x in schedule)
