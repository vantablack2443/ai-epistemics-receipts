"""Export complete, adjudicated document-level qualification scores; never impute missing data."""
import argparse
import csv
import json
import sqlite3
from pathlib import Path
from .analysis import fraction_preserved, paired_bootstrap
from .models import Annotation
from .runner import load_documents

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', required=True)
    p.add_argument('--annotations', required=True, help='JSONL with one adjudicated label per item')
    p.add_argument('--db', required=True, help='SQLite database of the final run')
    p.add_argument('--out', required=True)
    args = p.parse_args()
    docs = [d for d in load_documents(args.data) if d.split == 'test']
    with sqlite3.connect(f'file:{Path(args.db).resolve().as_posix()}?mode=ro', uri=True) as db:
        completed = {row[0] for row in db.execute("SELECT generation_id FROM attempts WHERE status='success'")}
    labels = {}
    for line in Path(args.annotations).read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        a = Annotation.model_validate_json(line)
        key = (a.generation_id, a.item_id)
        if key in labels: raise ValueError(f'duplicate adjudicated annotation: {key}')
        labels[key] = a.label
    scores = {condition: {} for condition in 'ABC'}
    rows = []
    for doc in docs:
        for condition in 'ABC':
            gid = f'{doc.id}-{condition}-3'
            score = (fraction_preserved(labels.get((gid, item.id)) for item in doc.items if item.type == 'qualification')
                     if gid in completed else None)
            scores[condition][doc.id] = score
            rows.append({'document_id': doc.id, 'category': doc.category, 'condition': condition, 'round': 3, 'qualification_preservation': score})
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    with (out / 'round3_scores.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys() if rows else ['document_id','category','condition','round','qualification_preservation'])
        writer.writeheader(); writer.writerows(rows)
    comparisons = {f'{a}-{b}': paired_bootstrap(scores[a], scores[b]) for a,b in [('C','A'),('B','A'),('C','B')]}
    (out / 'paired_comparisons.json').write_text(json.dumps(comparisons, indent=2), encoding='utf-8')
    print(json.dumps(comparisons, indent=2))

if __name__ == '__main__': main()
