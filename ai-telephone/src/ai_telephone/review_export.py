"""Export unreviewed drafts for human source and ground-truth review."""
import csv
import json
from pathlib import Path
from .models import Document

def main():
    paths = [Path('data/sources.jsonl'), *sorted(Path('data/drafts').glob('*.jsonl'))]
    docs = []
    for path in paths:
        docs.extend(Document.model_validate_json(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip())
    dest = Path('data/source-review.csv')
    if dest.exists():
        raise FileExistsError('review sheet exists; preserve edits and rename it before creating a new one')
    fields = ['document_id','split','category','word_count','source_text','item_id','item_type','quotation','intended_meaning','reviewer','decision','review_notes']
    with dest.open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for doc in docs:
            for item in doc.items:
                w.writerow({'document_id':doc.id, 'split':doc.split, 'category':doc.category,
                    'word_count':len(doc.text.split()), 'source_text':doc.text, 'item_id':item.id,
                    'item_type':item.type, 'quotation':item.quotation, 'intended_meaning':item.meaning})
    print(f'Exported {len(docs)} unreviewed documents to {dest}')

if __name__ == '__main__': main()
