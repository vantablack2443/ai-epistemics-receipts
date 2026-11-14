import pytest
from pydantic import ValidationError
from ai_telephone.models import DocumentV2

QUOTES = ['Finding sentence one stands.', 'Limit alpha applies here.', 'Limit beta applies here.',
          'Limit gamma applies here.', 'Limit delta applies here.', 'Limit epsilon applies here.']

def v2_document(doc_id='long-01', split='test', kind='fictional', words=1000, quotes=QUOTES, findings=1, reviewed=True):
    filler = ' '.join(['background'] * words)
    text = filler + ' ' + ' '.join(quotes)
    items = [{'id': f'{doc_id}-{"f" if n < findings else "q"}{n + 1}', 'type': 'finding' if n < findings else 'qualification',
              'quotation': q, 'meaning': f'SECRET GROUND TRUTH {n}'} for n, q in enumerate(quotes)]
    return DocumentV2(id=doc_id, split=split, kind=kind, text=text, provenance='fixture', licence='CC0', items=items,
                      reviewed=reviewed)

def test_valid_document():
    d = v2_document()
    assert len(d.items) == 6 and DocumentV2.model_validate_json(d.model_dump_json()) == d

@pytest.mark.parametrize('kwargs', [
    {'quotes': QUOTES[:5]},                      # too few items
    {'words': 500},                              # too short
    {'words': 1600},                             # too long
    {'findings': 0}, {'findings': 3},
    {'quotes': QUOTES[:5] + ['Finding sentence one stands.']},  # duplicate quotation text -> occurs twice
])
def test_invalid_documents(kwargs):
    with pytest.raises(ValidationError):
        v2_document(**kwargs)

def test_item_ids_must_be_prefixed_and_unique():
    d = v2_document().model_dump()
    d['items'][1]['id'] = 'other-q2'
    with pytest.raises(ValidationError, match='must start with'):
        DocumentV2(**d)
    d = v2_document().model_dump()
    d['items'][1]['id'] = d['items'][2]['id']
    with pytest.raises(ValidationError, match='unique'):
        DocumentV2(**d)

def test_quotation_missing_from_text():
    d = v2_document().model_dump()
    d['items'][0]['quotation'] = 'not in the text anywhere'
    with pytest.raises(ValidationError, match='exactly once'):
        DocumentV2(**d)
