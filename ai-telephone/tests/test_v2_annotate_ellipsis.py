"""Ellipsis-joined quotations in judge output: every fragment verbatim and in order; no model calls."""
import json
import pytest
from ai_telephone.annotate import parse_judgement

SUMMARY = 'A closed-lane trial ran. Lighting was 220 lux lighting in the depot. The result was not tested.'
QUOTE = 'A closed-lane trial ... 220 lux lighting ... not tested.'

def judgement(quote, claims=(), label='preserved'):
    items = [{'item_id': 'a', 'label': label, 'quotation': quote, 'rationale': 'r'},
             {'item_id': 'b', 'label': 'omitted', 'quotation': '', 'rationale': 'r'}]
    return json.dumps({'items': items, 'unsupported_claims': list(claims)})

def check(quote, summary=SUMMARY):
    return parse_judgement(judgement(quote), ['a', 'b'], summary)

def test_ellipsis_quote_passes_when_fragments_in_order():
    items, _ = check(QUOTE)
    assert items[0]['quotation'] == QUOTE

@pytest.mark.parametrize('quote', [
    '220 lux lighting ... A closed-lane trial',          # out of order
    'not tested. ... A closed-lane trial',                 # reversed
])
def test_ellipsis_quote_fails_when_fragments_out_of_order(quote):
    with pytest.raises(ValueError, match='verbatim'):
        check(quote)

def test_ellipsis_quote_fails_when_a_fragment_is_missing():
    with pytest.raises(ValueError, match='verbatim'):
        check('A closed-lane trial ... 330 lux lighting ... not tested.')

def test_ellipsis_quote_fails_when_a_fragment_appears_only_before_previous_match():
    # 'lux' occurs once, but only before the first fragment's match ends, so order is violated
    with pytest.raises(ValueError, match='verbatim'):
        check('not tested. ... The result')

@pytest.mark.parametrize('quote', ['...', '…', ' ... ', '… …'])
def test_ellipsis_only_quote_fails(quote):
    with pytest.raises(ValueError, match='verbatim'):
        check(quote)

def test_unicode_ellipsis_is_split_too():
    items, _ = check('A closed-lane trial … not tested.')
    assert items[0]['label'] == 'preserved'

def test_plain_verbatim_passes_and_non_verbatim_fails():
    check('Lighting was 220 lux lighting in the depot.')
    with pytest.raises(ValueError, match='verbatim'):
        check('lighting was 220 lux lighting in the depot.')  # case is not normalised
    with pytest.raises(ValueError, match='verbatim'):
        check('closed-lane trial, lighting')

def claims_payload(quote):
    items = [{'item_id': 'a', 'label': 'omitted', 'quotation': '', 'rationale': 'r'},
             {'item_id': 'b', 'label': 'omitted', 'quotation': '', 'rationale': 'r'}]
    return json.dumps({'items': items, 'unsupported_claims': [{'quotation': quote, 'reason': 'new claim'}]})

def test_unsupported_claims_accept_ordered_ellipsis_quotes():
    _, claims = parse_judgement(claims_payload('closed-lane trial ... not tested'), ['a', 'b'], SUMMARY)
    assert claims[0]['quotation'] == 'closed-lane trial ... not tested'

@pytest.mark.parametrize('quote', [
    'not tested ... closed-lane trial',   # out of order
    'closed-lane trial ... never seen',   # missing fragment
    '...',                                # ellipsis only
    'a plain claim not in the summary',   # plain, non-verbatim
])
def test_unsupported_claims_reject_bad_quotes(quote):
    with pytest.raises(ValueError, match='verbatim'):
        parse_judgement(claims_payload(quote), ['a', 'b'], SUMMARY)
