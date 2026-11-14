"""Worked examples shown to the summarizer in the `one` and `few` prompt conditions.

All scenarios are fictional and original, and deliberately differ from every domain used in
the study sources and in the annotator's examples. Each example has one principal finding and
three qualifications. `good` keeps all four; `bad` reads fluently but loses or invents
information, and `why_bad` names exactly what. `point` says which half the example teaches.
"""

import json
from pathlib import Path

EXAMPLES = {
    'coupons': {
        'point': 'good',
        'source': (
            "Lap-shear coupons bonded with the new two-part epoxy reached a mean failure load of "
            "18.4 kN across 30 coupons, compared with 15.1 kN for the current adhesive on a matched "
            "set of 30. All coupons used 2 mm aluminium sheet with the same grit-blasted surface "
            "preparation and were cured for 24 hours at 23 degrees Celsius before testing on a "
            "single hydraulic frame. Testing was done at room temperature only; no coupons were "
            "tested hot, cold, or after humidity exposure. The spread was wide, with a standard "
            "deviation of 2.9 kN for the new epoxy, so the two distributions overlap and the "
            "advantage is clear only in the mean. Technicians reported that the new epoxy was "
            "slightly easier to mix and had a longer working time on the bench. The coupons were prepared over two days by the same two technicians, and the test frame was recalibrated before each batch. Do not specify the "
            "new epoxy for production brackets until the humidity-aging series, now scheduled for "
            "March, is finished."),
        'good': (
            "The new epoxy's mean lap-shear failure load was 18.4 kN versus 15.1 kN for the current "
            "adhesive (30 coupons each, aluminium, cured 24 hours). Tests were at room temperature "
            "only. The spread is wide (standard deviation 2.9 kN), so the distributions overlap and "
            "only the mean clearly favours the new epoxy. Do not specify it for production brackets "
            "until the humidity-aging series is finished."),
        'bad': (
            "The new epoxy is stronger than the current adhesive, with a mean failure load of "
            "18.4 kN against 15.1 kN across 30 coupons. It is also easier to mix and has a longer "
            "working time. It can now be specified for production brackets."),
        'why_bad': (
            "It drops the room-temperature-only limit and the overlapping distributions, "
            "strengthens a mean difference into plain superiority, and removes the condition that "
            "the humidity-aging series must finish before specifying the epoxy."),
    },
    'rover': {
        'point': 'bad',
        'source': (
            "During the dry-lakebed trial, the prototype rover's new wheel-slip controller reduced "
            "wasted drive energy by 22 percent over a 4 km loop, compared with the previous "
            "controller on the same loop and the same day. The loop was flat, hard-packed clay; "
            "performance on sand, gravel, or slopes was not tested. The comparison used a single "
            "run of each controller, so run-to-run variation is unknown. The team replaced two "
            "wheel encoders before the trial and logged battery temperature every ten seconds. "
            "Before the controller is used on the sand-dune route, a second trial on loose sand "
            "must show that the saving holds. The rover's top speed was capped at 0.4 metres per "
            "second throughout, to protect the instrument mast. The trial ran on a cool, overcast morning, and the support crew followed the rover in a utility vehicle to recover the data cards afterwards. Wind gusts of up to six metres per second were recorded but did not interrupt either run."),
        'good': (
            "On a flat, hard-packed clay loop of 4 km, the new wheel-slip controller reduced "
            "wasted drive energy by 22 percent against the previous controller, but each "
            "controller was run once, so run-to-run variation is unknown, and sand, gravel and "
            "slopes were not tested. A second trial on loose sand must confirm the saving before "
            "use on the dune route."),
        'bad': (
            "The new wheel-slip controller cuts wasted drive energy by 22 percent, as shown over "
            "a 4 km loop with the rover capped at 0.4 metres per second. It is ready for the "
            "sand-dune route."),
        'why_bad': (
            "It drops that the result comes from a flat clay surface and a single run of each "
            "controller, and it turns a result that must be confirmed on loose sand into "
            "readiness for the dune route."),
    },
    'filters': {
        'point': 'good',
        'source': (
            "A bench test of the new ceramic particulate filter in the exhaust of a test diesel "
            "generator showed that it captured 97 percent of particles by mass, measured over "
            "five steady-load runs of two hours each. Particle counts below 50 nanometres could "
            "not be measured with the available instrument, so the capture rate for the smallest "
            "particles is unknown. The generator ran at a constant 60 percent load; transient "
            "loads such as start-up were not part of the protocol. The filter housing was "
            "supplied pre-assembled by the vendor, and installation took about forty minutes. The generator was borrowed from the workshop for three weeks, and the test cell was cleaned between runs. Sampling lines were heated to avoid condensation, and the same operator ran all five tests. "
            "Back-pressure rose steadily across each run, and the team has not yet established "
            "how quickly it would reach the engine maker's limit in service. Do not fit the "
            "filter to field generators until a long-duration back-pressure test is finished."),
        'good': (
            "The ceramic filter captured 97 percent of particles by mass over five two-hour "
            "steady-load runs on a test diesel generator at 60 percent load. Capture of particles "
            "below 50 nanometres could not be measured, and start-up and other transients were not "
            "tested. Back-pressure rose during each run and its time to the engine maker's limit "
            "is unknown. Do not fit field generators until a long-duration back-pressure test is "
            "finished."),
        'bad': (
            "The new ceramic particulate filter captured 97 percent of particles in bench tests "
            "on a diesel generator and installs in about forty minutes. Back-pressure rose "
            "during the runs."),
        'why_bad': (
            "It drops the unmeasured sub-50-nanometre range, the steady-load-only protocol, "
            "that the back-pressure limit is unknown, and the condition to finish a "
            "long-duration back-pressure test before fitting field generators."),
    },
    'indexes': {
        'point': 'bad',
        'source': (
            "Adding a composite index on the orders table cut the median latency of the "
            "order-history query from 840 ms to 95 ms in the staging database, using a replayed "
            "sample of one hour of production queries. Staging holds about a tenth of the "
            "production row count, so the improvement at full size is likely to differ. Write "
            "latency for inserts rose by roughly 6 percent in the same replay, and storage use "
            "grew by 1.2 GB. The query planner chose the new index for every replayed query, but "
            "the sample contained no month-end reporting queries, which behave differently. The "
            "engineers also renamed several columns while preparing the test, and the replay was run overnight by the platform team using a script kept in the shared repository. The staging cluster has the same software version as production and was otherwise idle during the replay. Production should "
            "not receive the index until the month-end reporting queries have been replayed "
            "against it."),
        'good': (
            "A composite index on the orders table cut the median latency of the order-history "
            "query from 840 ms to 95 ms in a one-hour replay of production queries on staging. "
            "Staging has about a tenth of production's rows, so the gain at full size will "
            "differ, and the replay had no month-end reporting queries. Inserts became about 6 "
            "percent slower. Replay the month-end queries before adding the index to production."),
        'bad': (
            "A composite index on the orders table cut the median latency of the order-history "
            "query from 840 ms to 95 ms in staging, and tests on the full production database "
            "confirmed a similar speed-up. Insert latency rose by 6 percent and storage by "
            "1.2 GB, so the index is worth adding."),
        'why_bad': (
            "It invents a test on the full production database that never happened, and drops "
            "that staging is a tenth of production size, that month-end queries were not "
            "replayed, and the condition to replay them before adding the index to production."),
    },
    'molding': {
        'point': 'good',
        'source': (
            "Raising the mould temperature from 60 to 75 degrees Celsius reduced warpage in the "
            "polypropylene housing from a mean of 1.8 mm to 0.7 mm across 40 parts per setting, "
            "measured on a coordinate machine 24 hours after moulding. All parts came from a "
            "single production lot of resin, and a different lot or supplier may respond "
            "differently. The higher temperature lengthened the cycle time by about eight "
            "seconds, and the cost of this has not been calculated. Parts were measured at "
            "room temperature only, so their shape after exposure to heat in service is not "
            "known. The tooling vendor visited the site during the trial and suggested changes to "
            "the gate design, which were not tried. The press is a 120-tonne machine that was serviced the week before, and the operators changed shifts halfway through the trial without any change in procedure. Hold the new setting out of regular "
            "production until a second resin lot has been moulded and measured."),
        'good': (
            "Raising the mould temperature from 60 to 75 degrees Celsius cut mean warpage of the "
            "polypropylene housing from 1.8 mm to 0.7 mm (40 parts per setting, measured after 24 "
            "hours). Only one resin lot was used, parts were measured at room temperature only, "
            "and the cycle is about eight seconds longer at an uncalculated cost. Do not use the "
            "setting in regular production until a second resin lot is moulded and measured."),
        'bad': (
            "A mould temperature of 75 degrees Celsius reduced warpage in the polypropylene "
            "housing from 1.8 mm to 0.7 mm. The cycle takes about eight seconds longer. The "
            "tooling vendor also proposed changes to the gate design."),
        'why_bad': (
            "It drops that only one resin lot was used, that parts were measured at room "
            "temperature only, that the cycle-time cost is uncalculated, and the condition to "
            "mould a second lot before regular production."),
    },
}

ONE_SHOT = [EXAMPLES['coupons']]
FEW_SHOT = [EXAMPLES[k] for k in ('coupons', 'rover', 'filters', 'indexes', 'molding')]

SELECTED_PATH = 'data/v2/examples/selected.json'
_REQUIRED = ('source', 'good', 'bad', 'why_bad')

def _project_root():
    return Path(__file__).resolve().parents[2]

def _check_example(e, where):
    for key in _REQUIRED:
        if not isinstance(e.get(key), str) or not e[key].strip():
            raise ValueError(f'{where}: field {key!r} missing or empty')
    if not 150 <= len(e['source'].split()) <= 250:
        raise ValueError(f'{where}: source must be 150 to 250 words')
    if len(e['good'].split()) > 80:
        raise ValueError(f'{where}: good summary must be at most 80 words')
    if len(e['bad'].split()) > 60:
        raise ValueError(f'{where}: bad summary must be at most 60 words')
    if e['why_bad'].count('. ') != 0 or not e['why_bad'].endswith('.'):
        raise ValueError(f'{where}: why_bad must be one sentence')

def load_selected(path=SELECTED_PATH):
    """Examples selected by humans (docs/examples-brief.md, Step E3), or None if the file is absent.

    Relative paths resolve against the project root. The file holds either a list of five
    records or an object keyed by example ID (E1..E5, read in ID order). Each record needs
    ``source``, ``good``, ``bad`` and ``why_bad``; other fields (``good_from``, ``bad_from``)
    are provenance and are ignored here. E1 is the one-shot example; all five form the
    few-shot set. Returns (ONE_SHOT, FEW_SHOT).
    """
    p = Path(path)
    if not p.is_absolute():
        p = _project_root() / p
    if not p.is_file():
        return None
    data = json.loads(p.read_text(encoding='utf-8'))
    if isinstance(data, dict):
        records = [data[k] for k in sorted(data)]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError('selected examples must be a list or an object keyed by example ID')
    if len(records) != 5 or not all(isinstance(r, dict) for r in records):
        raise ValueError('selected examples must contain exactly five records (E1..E5)')
    for n, record in enumerate(records, 1):
        _check_example(record, f'example {n}')
    return [records[0]], records

def render_examples(prompt: str, path=SELECTED_PATH) -> str:
    if prompt not in {'one', 'few'}:
        raise ValueError('examples exist only for the one and few prompts')
    selected = load_selected(path)
    one, few = selected if selected is not None else (ONE_SHOT, FEW_SHOT)
    examples = one if prompt == 'one' else few
    return '\n\n'.join(
        f"Source:\n{e['source']}\n\nGood summary:\n{e['good']}\n\nBad summary:\n{e['bad']}\n\n"
        f"Why the bad summary is bad:\n{e['why_bad']}" for e in examples)
