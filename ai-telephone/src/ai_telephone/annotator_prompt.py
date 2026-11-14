"""Frozen-candidate prompt for the AI annotator (LLM judge).

The five worked examples are fictional and deliberately outside the study's scenarios
(no caches, indexes, coupons, rovers, filters, molding, schedulers or heat sinks), so they
cannot leak ground truth. Three chains keep the source's information; two lose it.
Together they show every label: preserved, omitted, strengthened, weakened, contradicted.
The annotator never sees the condition, round, or model that produced a summary.
"""
import json

RUBRIC = """You are annotating summaries of engineering handoffs for a research study.
Compare the SUMMARY with the ORIGINAL handoff, never with any intermediate summary.
For each ground-truth ITEM, choose exactly one label:

- preserved: the item's meaning survives, possibly as a valid paraphrase or compressed notation.
- omitted: the information is missing and nothing incompatible replaces it.
- strengthened: certainty, scope, generality, or readiness to act exceeds the original
  (e.g. "may reduce" -> "reduces"; "in staging" -> "in production"; "deploy after X passes" -> "ready to deploy").
- weakened: the summary is less definite than the original warrants
  (e.g. "confirmed 30%" -> "might help somewhat").
- contradicted: the summary states something incompatible with the item
  (e.g. "eastbound span only" -> "both spans").

Rules:
- Judge meaning, not wording. Keyword overlap is not enough; a hedge, scope, or condition must survive.
- If a summary keeps a number but drops the context that limits it, label the limiting item, not the number.
- When strengthened and contradicted both seem to fit, prefer strengthened unless the summary asserts the opposite fact.
- For every label except omitted, "quotation" must be copied verbatim from the SUMMARY. For omitted use "".
- Give a one-sentence rationale for every label.
- Also list unsupported claims: statements in the summary that the original does not support.
  Quote them verbatim from the summary. Return an empty list if there are none.
- Use only the texts provided. Do not use tools, browse, or access files.

Return only JSON, no code fences, in this shape:
{"items": [{"item_id": "...", "label": "...", "quotation": "...", "rationale": "..."}],
 "unsupported_claims": [{"quotation": "...", "rationale": "..."}]}"""

EXAMPLES = [
    {   # KEEPS: compressed notation still preserves every item.
        'kind': 'keeps information',
        'original': ('The new charger firmware cut charge time from 95 to 71 minutes on four lab units at 22 °C. '
                     'Cold-weather charging was not tested. Release only after the thermal soak test passes.'),
        'items': [
            {'item_id': 'F', 'type': 'finding', 'quotation': 'The new charger firmware cut charge time from 95 to 71 minutes on four lab units at 22 °C.'},
            {'item_id': 'Q1', 'type': 'qualification', 'quotation': 'Cold-weather charging was not tested.'},
            {'item_id': 'Q2', 'type': 'qualification', 'quotation': 'Release only after the thermal soak test passes.'}],
        'round1': ('New charger firmware reduced charge time from 95 to 71 minutes on four lab units at 22 °C. '
                   'Cold-weather charging is untested. Release only after the thermal soak test passes.'),
        'round2': 'Firmware cut lab charge time 95→71 min (4 units, 22 °C); cold untested; release after thermal soak passes.',
        'answer': {'items': [
            {'item_id': 'F', 'label': 'preserved', 'quotation': 'Firmware cut lab charge time 95→71 min (4 units, 22 °C)',
             'rationale': 'Same measurement, sample, and temperature in compressed notation.'},
            {'item_id': 'Q1', 'label': 'preserved', 'quotation': 'cold untested',
             'rationale': 'States that cold-weather charging was not tested.'},
            {'item_id': 'Q2', 'label': 'preserved', 'quotation': 'release after thermal soak passes',
             'rationale': 'Keeps the release condition.'}],
            'unsupported_claims': []},
    },
    {   # KEEPS: paraphrase of an unknown cause and an untested platform.
        'kind': 'keeps information',
        'original': ('Retrying the network mock removed the flaky failure in 200 consecutive CI runs on the Linux runners. '
                     'Windows runners were not included. The root cause of the flake is still unknown.'),
        'items': [
            {'item_id': 'F', 'type': 'finding', 'quotation': 'Retrying the network mock removed the flaky failure in 200 consecutive CI runs on the Linux runners.'},
            {'item_id': 'Q1', 'type': 'qualification', 'quotation': 'Windows runners were not included.'},
            {'item_id': 'Q2', 'type': 'qualification', 'quotation': 'The root cause of the flake is still unknown.'}],
        'round1': ('A retry on the network mock eliminated the flaky failure over 200 consecutive Linux CI runs. '
                   'Windows runners were excluded, and the root cause is still unknown.'),
        'round2': 'Mock retry stopped the flake across 200 Linux CI runs; Windows was not checked and the cause remains unidentified.',
        'answer': {'items': [
            {'item_id': 'F', 'label': 'preserved', 'quotation': 'Mock retry stopped the flake across 200 Linux CI runs',
             'rationale': 'Keeps the effect, the run count, and the Linux scope.'},
            {'item_id': 'Q1', 'label': 'preserved', 'quotation': 'Windows was not checked',
             'rationale': 'Valid paraphrase of Windows runners being excluded.'},
            {'item_id': 'Q2', 'label': 'preserved', 'quotation': 'the cause remains unidentified',
             'rationale': '"Unidentified" preserves "still unknown".'}],
            'unsupported_claims': []},
    },
    {   # KEEPS: the hedge "may" survives as "possibly".
        'kind': 'keeps information',
        'original': ('The fine-tuned model may reduce terminology errors: reviewers marked 14 errors versus 22 on a '
                     '50-sentence sample from one product manual. The sample is too small to separate the effect from '
                     'reviewer variation. Do not switch production translation until a blinded comparison on three '
                     'manuals is complete.'),
        'items': [
            {'item_id': 'F', 'type': 'finding', 'quotation': 'The fine-tuned model may reduce terminology errors'},
            {'item_id': 'Q1', 'type': 'qualification', 'quotation': 'The sample is too small to separate the effect from reviewer variation.'},
            {'item_id': 'Q2', 'type': 'qualification', 'quotation': 'Do not switch production translation until a blinded comparison on three manuals is complete.'}],
        'round1': ('The fine-tuned model may reduce terminology errors (14 vs 22 on a 50-sentence sample from one manual), '
                   'but the sample is too small to rule out reviewer variation. Keep production translation unchanged '
                   'until a blinded three-manual comparison is done.'),
        'round2': ('Fine-tuned model possibly reduces terminology errors (14 vs 22, one small sample; reviewer variation '
                   'not ruled out). Keep production model until blinded three-manual comparison.'),
        'answer': {'items': [
            {'item_id': 'F', 'label': 'preserved', 'quotation': 'Fine-tuned model possibly reduces terminology errors',
             'rationale': '"Possibly" keeps the original hedge "may".'},
            {'item_id': 'Q1', 'label': 'preserved', 'quotation': 'one small sample; reviewer variation not ruled out',
             'rationale': 'Keeps that the sample cannot separate the effect from reviewer variation.'},
            {'item_id': 'Q2', 'label': 'preserved', 'quotation': 'Keep production model until blinded three-manual comparison',
             'rationale': 'Keeps the condition before switching production.'}],
            'unsupported_claims': []},
    },
    {   # LOSES: round 1 is fine; round 2 generalizes the result, drops a limit, and removes the rollout condition.
        'kind': 'loses information',
        'original': ('Replacing the valve actuator stabilized supply-air temperature within ±0.5 °C during one week of '
                     'mild spring weather in Building C. Performance under peak cooling load is unknown. Roll out to '
                     'other buildings only after the summer peak-load check.'),
        'items': [
            {'item_id': 'F', 'type': 'finding', 'quotation': 'Replacing the valve actuator stabilized supply-air temperature within ±0.5 °C during one week of mild spring weather in Building C.'},
            {'item_id': 'Q1', 'type': 'qualification', 'quotation': 'Performance under peak cooling load is unknown.'},
            {'item_id': 'Q2', 'type': 'qualification', 'quotation': 'Roll out to other buildings only after the summer peak-load check.'}],
        'round1': ('The new valve actuator kept Building C supply air within ±0.5 °C over one mild spring week; '
                   'peak-cooling performance is unknown. Roll out elsewhere only after the summer peak-load check.'),
        'round2': 'The new valve actuator stabilizes supply-air temperature within ±0.5 °C and is ready to roll out to other buildings.',
        'answer': {'items': [
            {'item_id': 'F', 'label': 'strengthened', 'quotation': 'The new valve actuator stabilizes supply-air temperature within ±0.5 °C',
             'rationale': 'One mild week in one building becomes a general, present-tense claim.'},
            {'item_id': 'Q1', 'label': 'omitted', 'quotation': '',
             'rationale': 'Unknown peak-load performance is no longer mentioned.'},
            {'item_id': 'Q2', 'label': 'strengthened', 'quotation': 'is ready to roll out to other buildings',
             'rationale': 'A rollout conditional on the peak-load check becomes unconditional readiness.'}],
            'unsupported_claims': [
            {'quotation': 'is ready to roll out to other buildings',
             'rationale': 'The original never states readiness for rollout.'}]},
    },
    {   # LOSES: strong evidence is weakened, the scope limit is contradicted, the action is dropped.
        'kind': 'loses information',
        'original': ('Strain gauges confirmed that the retrofit brace reduced peak deck strain by 30% across 1,200 truck '
                     'crossings over the full monitoring period. The results apply to the eastbound span only. Inspect '
                     'the brace welds after the first winter before removing the temporary load limit.'),
        'items': [
            {'item_id': 'F', 'type': 'finding', 'quotation': 'Strain gauges confirmed that the retrofit brace reduced peak deck strain by 30% across 1,200 truck crossings over the full monitoring period.'},
            {'item_id': 'Q1', 'type': 'qualification', 'quotation': 'The results apply to the eastbound span only.'},
            {'item_id': 'Q2', 'type': 'qualification', 'quotation': 'Inspect the brace welds after the first winter before removing the temporary load limit.'}],
        'round1': ('Monitoring of 1,200 truck crossings showed the retrofit brace cut peak deck strain by 30% on the bridge. '
                   'Weld inspection after the first winter is planned.'),
        'round2': 'Early monitoring suggests the retrofit brace might lower deck strain somewhat on both spans.',
        'answer': {'items': [
            {'item_id': 'F', 'label': 'weakened', 'quotation': 'Early monitoring suggests the retrofit brace might lower deck strain somewhat',
             'rationale': 'A confirmed 30% reduction over 1,200 crossings becomes a vague, tentative effect.'},
            {'item_id': 'Q1', 'label': 'contradicted', 'quotation': 'on both spans',
             'rationale': 'The original limits results to the eastbound span.'},
            {'item_id': 'Q2', 'label': 'omitted', 'quotation': '',
             'rationale': 'The weld inspection required before lifting the load limit is gone.'}],
            'unsupported_claims': [
            {'quotation': 'Early monitoring',
             'rationale': 'The original describes the full monitoring period, not early monitoring.'},
            {'quotation': 'on both spans',
             'rationale': 'The original covers the eastbound span only.'}]},
    },
]

def render_items(items):
    return '\n'.join(f"- {i['item_id']} ({i['type']}): \"{i['quotation']}\""
                     + (f" — must preserve: {i['meaning']}" if i.get('meaning') else '') for i in items)

def render_examples():
    parts = []
    for n, ex in enumerate(EXAMPLES, 1):
        parts.append(
            f"EXAMPLE {n} ({ex['kind']})\nORIGINAL:\n{ex['original']}\nITEMS:\n{render_items(ex['items'])}\n"
            f"Round-1 summary (context only, not annotated): {ex['round1']}\n"
            f"SUMMARY to annotate (round 2):\n{ex['round2']}\n"
            f"ANSWER:\n{json.dumps(ex['answer'], ensure_ascii=False)}")
    return '\n\n'.join(parts)

def make_annotation_prompt(original, items, summary):
    """Items: dicts with item_id, type, quotation, meaning. No condition, round or model is included."""
    return (f"{RUBRIC}\n\nWORKED EXAMPLES\n\n{render_examples()}\n\nNOW ANNOTATE\nORIGINAL:\n{original}\n"
            f"ITEMS:\n{render_items(items)}\nSUMMARY to annotate:\n{summary}\nANSWER:")
