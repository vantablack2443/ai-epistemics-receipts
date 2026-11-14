"""Calculate v2 tables from saved generations and annotations."""
import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from .analysis import LABELS, LENGTHS, SCORED_ROUNDS, load_jsonl, test_documents, summary_rates, contrasts

def write(path, rows, fields):
    with path.open('w', encoding='utf-8', newline='') as stream:
        w = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--results', required=True); p.add_argument('--sources', required=True); p.add_argument('--out', required=True)
    args=p.parse_args(); sources=load_jsonl(args.sources); docs=test_documents(sources)
    source_map={x['id']:x for x in sources}; dest=Path(args.out); dest.mkdir(parents=True,exist_ok=True); primary=[]
    for folder in sorted(Path(args.results).iterdir()):
        if not folder.is_dir() or folder.resolve()==dest.resolve(): continue
        genfile=folder/'generations.jsonl'; annfile=folder/'ai-annotations.jsonl'
        if not genfile.exists() or not annfile.exists(): print(f'Skipping {folder.name}: missing input'); continue
        generations=load_jsonl(genfile); annotations=load_jsonl(annfile); rows=summary_rates(generations,annotations,docs)
        out=dest/folder.name; out.mkdir(parents=True,exist_ok=True)
        flat=[{**r, **(r['labels'] or {k:None for k in LABELS})} for r in rows]
        write(out/'summary_rates.csv',flat,['document_id','prompt','length','round','status','n_items','n_preserved','rate','n_unsupported',*LABELS])
        comp=[x for length in LENGTHS for rnd in SCORED_ROUNDS for x in contrasts(rows,length,rnd)]
        write(out/'contrasts.csv',comp,['contrast','length','round','n_pairs','difference','low','high'])
        primary.extend({'model':folder.name,**x} for x in comp if x['contrast']=='few-zero' and x['length']=='limited' and x['round']==5)
        groups=defaultdict(list)
        for r in rows:
            if r['rate'] is not None: groups[(r['prompt'],r['length'],r['round'])].append(r)
        errors=[]; claims=[]
        for (prompt,length,rnd),group in sorted(groups.items()):
            counts=Counter(); [counts.update(r['labels']) for r in group]; total=sum(counts.values())
            errors.extend({'prompt':prompt,'length':length,'round':rnd,'label':label,'count':counts[label],'share':counts[label]/total if total else None} for label in LABELS)
            claims.append({'prompt':prompt,'length':length,'round':rnd,'n_summaries':len(group),'mean_unsupported':statistics.mean(r['n_unsupported'] for r in group)})
        write(out/'errors.csv',errors,['prompt','length','round','label','count','share']); write(out/'claims.csv',claims,['prompt','length','round','n_summaries','mean_unsupported'])
        buckets=defaultdict(list); failures=Counter()
        for g in generations:
            if g['document_id'] not in docs: continue
            if g['status']!='success': failures[g['status']]+=1; continue
            if g.get('word_count') is not None: buckets[(g['prompt'],g['length'],g['round'])].append(g['word_count'])
        lengths=[{'prompt':k[0],'length':k[1],'round':k[2],'n_success':len(v),'mean_words':statistics.mean(v),'median_words':statistics.median(v),'share_over_250':sum(x>250 for x in v)/len(v) if k[1]=='limited' else None} for k,v in sorted(buckets.items())]
        write(out/'lengths.csv',lengths,['prompt','length','round','n_success','mean_words','median_words','share_over_250']); write(out/'failures.csv',[{'status':k,'count':v} for k,v in failures.items()],['status','count'])
        by=defaultdict(list)
        for r in rows:
            if r['round']==5 and r['rate'] is not None:
                provenance=source_map[r['document_id']].get('provenance',''); drafter='haiku' if 'claude-haiku-5-5' in provenance else 'terra' if 'gpt-6.1-terra' in provenance else 'other'; by[(drafter,r['prompt'],r['length'])].append(r['rate'])
        write(out/'by_drafter.csv',[{'drafter':k[0],'prompt':k[1],'length':k[2],'n_documents':len(v),'mean_rate':statistics.mean(v)} for k,v in by.items()],['drafter','prompt','length','n_documents','mean_rate'])
    write(dest/'primary.csv',primary,['model','contrast','length','round','n_pairs','difference','low','high']); print(primary)

if __name__=='__main__': main()
