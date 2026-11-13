"""Draft synthetic sources with Terra. Outputs require independent human review."""
import json
import tempfile
from pathlib import Path
from .models import Document
from .runner import database, generate

CATEGORIES = ['tentative', 'scope', 'assumption', 'conditional', 'conflict']

def main():
    db = database('artifacts/dataset-drafting.sqlite')
    output = Path('data/drafts'); output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ai-telephone-drafting-') as directory:
        for category in CATEGORIES:
            count = 6 if category == 'scope' else 7
            prompt = f'''Draft {count} distinct fictional engineering handoff documents for a research dataset. Category: {category}.
Each must be 180–240 whitespace-separated words and genuinely distinct in technical scenario and underlying evidence, not just names or numbers. Use no personal data, private company information, or credentials. Include one principal finding and exactly three salient qualifications or action conditions. Include realistic background that can be omitted. Avoid unsupported safety claims.
Return only a JSON array. Each object has fields text and items. items is an array of exactly four objects: one with type "finding" and three with type "qualification". Each item has fields type, quotation, meaning, paraphrases. quotation must be a verbatim contiguous substring of text. meaning explains what must be preserved; paraphrases is an array of valid alternative phrasings. Make the information in all three qualifications independently relevant. Strong findings are welcome when warranted by the described evidence.
Treat this request as the sole task. Do not use tools, browse, or access files. Return only the JSON array.'''
            response = generate(db, 'draft-' + category, prompt, directory)
            parsed = json.loads(response.removeprefix('```json').removesuffix('```').strip())
            if not isinstance(parsed, list) or len(parsed) != count:
                raise ValueError(f'{category}: expected {count} documents')
            docs = []
            for i, item in enumerate(parsed):
                split = 'development' if category != 'scope' and i == 0 else 'test'
                doc_id = f'{"dev" if split == "development" else "test"}-{category}-{i+1:02d}'
                for j, ground in enumerate(item['items']): ground['id'] = f'{doc_id}-item-{j+1}'
                doc = Document(id=doc_id, split=split, category=category, text=item['text'], items=item['items'],
                               provenance='Terra-generated fictional draft; not human reviewed', reviewed=False)
                if not 180 <= len(doc.text.split()) <= 240:
                    raise ValueError(f'{doc_id}: {len(doc.text.split())} words; inspect saved raw output')
                docs.append(doc.model_dump())
            (output / f'{category}.jsonl').write_text(''.join(json.dumps(d, ensure_ascii=False)+'\n' for d in docs), encoding='utf-8')
            print(f'{category}: saved {len(docs)} unreviewed drafts', flush=True)

if __name__ == '__main__': main()
