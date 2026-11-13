"""Import explicit human source-review decisions without fabricating approvals."""
import csv
import json
from pathlib import Path
from .models import Document

def main():
    paths = [Path('data/sources.jsonl'), *sorted(Path('data/drafts').glob('*.jsonl'))]
    docs = [Document.model_validate_json(line) for path in paths
            for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    with Path('data/source-review.csv').open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    indexed = {}
    for row in rows:
        key = (row['document_id'], row['item_id'])
        if key in indexed: raise ValueError(f'duplicate review row: {key}')
        indexed[key] = row
    reviewed = []
    for doc in docs:
        for item in doc.items:
            row = indexed.get((doc.id, item.id))
            if not row or row['decision'].strip().lower() != 'approve' or not row['reviewer'].strip():
                raise ValueError(f'{doc.id}/{item.id}: requires named reviewer and approve decision')
            if row['source_text'] != doc.text or row['quotation'] != item.quotation or row['intended_meaning'] != item.meaning:
                raise ValueError(f'{doc.id}/{item.id}: content changed in review sheet; edit draft and re-export for review')
        reviewed.append(doc.model_copy(update={'reviewed': True}).model_dump())
    if len(indexed) != sum(len(d.items) for d in docs): raise ValueError('unexpected review rows')
    dest = Path('data/reviewed-sources.jsonl')
    with dest.open('x', encoding='utf-8') as f:
        for doc in reviewed: f.write(json.dumps(doc, ensure_ascii=False) + '\n')
    print(f'Saved {len(reviewed)} explicitly reviewed records to {dest}; this is not a protocol freeze.')

if __name__ == '__main__': main()
