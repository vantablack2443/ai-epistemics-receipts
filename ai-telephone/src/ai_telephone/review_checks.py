"""Mechanical pre-checks that support (never replace) human source review.

Flags problems a reviewer should look at: length, quotation placement, overlapping items,
hedged vs. strong findings, near-duplicate scenarios, and development/test leakage.
Writes JSON consumed by the review page; prints a short summary.
"""
import json
import re
from itertools import combinations
from pathlib import Path
from .models import Document

HEDGES = re.compile(r"\b(may|might|could|suggests?|appears?|possibly|likely|preliminary|tentative|"
                    r"early|initial|seems?|indicates?|not yet|unclear|unconfirmed|inconclusive)\b", re.I)
ACTION = re.compile(r"\b(deploy|ship|release|roll ?out|enable|merge|approve|before|until|only after|do not|must|should|"
                    r"repeat|rerun|confirm|verify|require)\b", re.I)
SENSITIVE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|https?://|\b(?:sk|pk|api|key|token|password)[-_:=]\w+", re.I)

def load_all():
    paths = [Path('data/sources.jsonl'), *sorted(Path('data/drafts').glob('*.jsonl'))]
    return [Document.model_validate_json(line) for p in paths
            for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]

def shingles(text, n=3):
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(w[i:i + n]) for i in range(len(w) - n + 1)}

def content_words(text):
    stop = set('the a an and or of to in on for with was were is are be been by at as that this it its from not '
               'after before during only than then which while into each per team'.split())
    return {w for w in re.findall(r"[a-z][a-z0-9-]+", text.lower()) if w not in stop and len(w) > 3}

def check(doc):
    flags = []
    n = len(doc.text.split())
    if not 180 <= n <= 240:
        flags.append(f'length {n} words (needs 180-240)')
    spans = []
    for item in doc.items:
        count = doc.text.count(item.quotation)
        if count != 1:
            flags.append(f'{item.id}: quotation occurs {count} times')
        start = doc.text.find(item.quotation)
        spans.append((start, start + len(item.quotation), item.id))
    spans.sort()
    for (s1, e1, a), (s2, e2, b) in zip(spans, spans[1:]):
        if s2 < e1:
            flags.append(f'{a} and {b}: quotations overlap')
    finding = next(i for i in doc.items if i.type == 'finding')
    hedged = bool(HEDGES.search(finding.quotation))
    quals = [i for i in doc.items if i.type == 'qualification']
    if doc.category == 'conditional' and not any(ACTION.search(q.quotation) for q in quals):
        flags.append('conditional category but no qualification reads as an action condition')
    if doc.category == 'tentative' and not hedged:
        flags.append('tentative category but the finding quotation has no hedge word; check it is actually tentative')
    if SENSITIVE.search(doc.text):
        flags.append('possible URL, email, or credential-like string')
    for q in quals:
        if not q.paraphrases:
            flags.append(f'{q.id}: no acceptable paraphrases listed')
    return {'id': doc.id, 'split': doc.split, 'category': doc.category, 'words': n,
            'finding_hedged': hedged, 'flags': flags}

def main():
    docs = load_all()
    results = {d.id: check(d) for d in docs}
    sh = {d.id: shingles(d.text) for d in docs}
    cw = {d.id: content_words(d.text) for d in docs}
    pairs = []
    for a, b in combinations(docs, 2):
        j3 = len(sh[a.id] & sh[b.id]) / max(1, len(sh[a.id] | sh[b.id]))
        jw = len(cw[a.id] & cw[b.id]) / max(1, len(cw[a.id] | cw[b.id]))
        pairs.append({'a': a.id, 'b': b.id, 'trigram_jaccard': round(j3, 3), 'word_jaccard': round(jw, 3),
                      'cross_split': a.split != b.split})
    pairs.sort(key=lambda p: -p['word_jaccard'])
    for p in pairs[:10]:
        if p['word_jaccard'] >= 0.2 or p['trigram_jaccard'] >= 0.05:
            for side, other in (('a', 'b'), ('b', 'a')):
                results[p[side]]['flags'].append(
                    f"similar to {p[other]} (word overlap {p['word_jaccard']}{', dev/test leakage risk' if p['cross_split'] else ''})")
    strong = sorted(d.id for d in docs if d.split == 'test' and not results[d.id]['finding_hedged'])
    summary = {'documents': len(docs), 'with_flags': sum(bool(r['flags']) for r in results.values()),
               'test_findings_without_hedge_words': strong, 'most_similar_pairs': pairs[:10]}
    out = Path('artifacts/review-checks.json'); out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'summary': summary, 'documents': results}, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    for r in results.values():
        for f in r['flags']:
            print(f"{r['id']}: {f}")

# --- design v2: long sources (plain JSON, independent of the evolving pydantic models) ---

V2_DRAFTS = ('data/v2/drafts/fictional.jsonl', 'data/v2/drafts/fictional-terra.jsonl', 'data/v2/drafts/papers.jsonl')

def load_v2(paths=V2_DRAFTS):
    docs = []
    for p in map(Path, paths):
        if p.exists():
            docs += [json.loads(l) for l in p.read_text(encoding='utf-8').splitlines() if l.strip()]
    return docs

def check_v2(doc):
    flags = []
    text, items = doc['text'], doc['items']
    n = len(text.split())
    if not 900 <= n <= 1500:
        flags.append(f'length {n} words (needs 900-1500)')
    if not 6 <= len(items) <= 10:
        flags.append(f'{len(items)} items (needs 6-10)')
    findings = sum(i['type'] == 'finding' for i in items)
    if findings not in (1, 2):
        flags.append(f'{findings} findings (needs 1-2)')
    ids = [i['id'] for i in items]
    if len(set(ids)) != len(ids) or any(not i.startswith(doc['id'] + '-') for i in ids):
        flags.append('item ids not unique or not prefixed by the document id')
    spans = []
    for i in items:
        c = text.count(i['quotation'])
        if c != 1:
            flags.append(f"{i['id']}: quotation occurs {c} times")
        s = text.find(i['quotation']); spans.append((s, s + len(i['quotation']), i['id']))
        if not i.get('meaning', '').strip():
            flags.append(f"{i['id']}: no intended meaning")
    spans.sort()
    for (s1, e1, a), (s2, e2, b) in zip(spans, spans[1:]):
        if s1 >= 0 and s2 < e1:
            flags.append(f'{a} and {b}: quotations overlap')
    if SENSITIVE.search(text):
        flags.append('possible URL, email, or credential-like string')
    finding_text = ' '.join(i['quotation'] for i in items if i['type'] == 'finding')
    return {'id': doc['id'], 'split': doc['split'], 'kind': doc.get('kind'), 'words': n,
            'finding_hedged': bool(HEDGES.search(finding_text)), 'flags': flags}

def run_v2():
    docs = load_v2()
    results = {d['id']: check_v2(d) for d in docs}
    cw = {d['id']: content_words(d['text']) for d in docs}
    pairs = []
    for a, b in combinations(docs, 2):
        jw = len(cw[a['id']] & cw[b['id']]) / max(1, len(cw[a['id']] | cw[b['id']]))
        pairs.append({'a': a['id'], 'b': b['id'], 'word_jaccard': round(jw, 3), 'cross_split': a['split'] != b['split']})
        if jw >= 0.2:
            for x, y in ((a, b), (b, a)):
                results[x['id']]['flags'].append(f"similar to {y['id']} (word overlap {jw:.2f})")
    pairs.sort(key=lambda p: -p['word_jaccard'])
    counts = {}
    for d in docs:
        counts[f"{d['split']}/{d.get('kind')}"] = counts.get(f"{d['split']}/{d.get('kind')}", 0) + 1
    summary = {'documents': len(docs), 'by_split_kind': counts,
               'with_flags': sum(bool(r['flags']) for r in results.values()),
               'tentative_findings': sorted(k for k, r in results.items() if r['finding_hedged']),
               'max_word_overlap': pairs[0] if pairs else None}
    out = Path('artifacts/review-checks-v2.json'); out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps({'summary': summary, 'documents': results}, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))
    for r in results.values():
        for f in r['flags']:
            print(f"{r['id']}: {f}")
    return results

if __name__ == '__main__':
    import sys
    run_v2() if '--v2' in sys.argv else main()
