import pytest
from ai_telephone.prompts import make_prompt, words
from ai_telephone.analysis import fraction_preserved, paired_bootstrap
from ai_telephone.models import Annotation

def test_matched_budgets_and_heading_count():
    for round_number, budget in [(1, 100), (2, 70), (3, 45)]:
        for condition in 'ABC':
            assert f'at most {budget} words' in make_prompt('source', condition, round_number)
    assert words('Finding: one Evidence: two') == 4

def test_metrics_keep_missing_and_pair_documents():
    assert fraction_preserved(['preserved', 'omitted', 'preserved']) == 2/3
    assert fraction_preserved(['preserved', None, 'preserved']) is None
    result = paired_bootstrap({'b': 1, 'a': 0}, {'a': 1, 'b': 0, 'missing': 1})
    assert result['n'] == 2 and result['difference'] == 0
    assert paired_bootstrap({'a': None}, {'a': 1})['n'] == 0

def test_non_preserved_requires_rationale():
    with pytest.raises(ValueError):
        Annotation(generation_id='g', item_id='i', reviewer_id='r', label='omitted')
