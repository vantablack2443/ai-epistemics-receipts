"""Read-only integrity checks and independent descriptive summaries for submission."""
import csv, hashlib, json, statistics
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
def lines(p): return [json.loads(x) for x in p.read_text(encoding='utf-8-sig').splitlines() if x.strip()]
def main():
    sources=lines(ROOT/'data/v2/sources.jsonl'); docs={d['id']:d for d in sources if d['split']=='test'}
    gens=lines(ROOT/'results/haiku/generations.jsonl'); anns=lines(ROOT/'results/haiku/ai-annotations.jsonl')
    gm={g['generation_id']:g for g in gens}; am={a['generation_id']:a for a in anns}
    assert len(gm)==len(gens)==len(docs)*30
    assert len(am)==len(anns)==len(docs)*18
    assert all(g['status']=='success' and g['word_count']==len(g['output'].split()) for g in gens)
    for a in anns:
        g=gm[a['generation_id']]; d=docs[g['document_id']]
        assert g['round'] in (1,3,5)
        assert Counter(x['item_id'] for x in a['labels'])==Counter(x['id'] for x in d['items'])
        for label in a['labels']:
            assert label['label'] in ('preserved','omitted','strengthened','weakened','contradicted')
            assert label['rationale'].strip()
            quote=label['quotation']; pos=0
            for fragment in quote.split('...'):
                if fragment.strip():
                    pos=g['output'].index(fragment.strip(),pos)+len(fragment.strip())
        for claim in a['unsupported_claims']: assert claim['quotation'] in g['output']
    manifest=json.loads((ROOT/'freeze/haiku.json').read_text())
    checks={p:dict(raw=hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,lf_normalized=hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==h) for p,h in manifest['files'].items()}
    groups=[]
    for length in ('limited','free'):
        for prompt in ('zero','one','few'):
            for rnd in (1,3,5):
                group=[g for g in gens if (g['length'],g['prompt'],g['round'])==(length,prompt,rnd)]
                rates=[]; labels=Counter(); claims=0
                for g in group:
                    a=am[g['generation_id']]; c=Counter(x['label'] for x in a['labels']); labels.update(c)
                    rates.append(c['preserved']/len(a['labels'])); claims+=len(a['unsupported_claims'])
                groups.append(dict(length=length,prompt=prompt,round=rnd,n=len(group),mean_preservation=statistics.mean(rates),mean_words=statistics.mean(g['word_count'] for g in group),over_limit=sum(g['word_count']>250 for g in group) if length=='limited' else None,labels=dict(labels),unsupported_claims=claims))
    report=dict(test_documents=len(docs),development_documents=len(sources)-len(docs),test_items=sum(len(d['items']) for d in docs.values()),generations=len(gens),annotations=len(anns),item_labels=sum(len(a['labels']) for a in anns),source_words=[len(d['text'].split()) for d in docs.values()],statuses=dict(Counter(g['status'] for g in gens)),freeze_checks=checks,groups=groups,human_audit_present=any((ROOT/'results').rglob('audit-agreement.json')))
    out=ROOT/'results/analysis/submission-integrity.json'; out.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='groups'},indent=2))
if __name__=='__main__': main()
