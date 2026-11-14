"""Read-only explorer for saved v2 study artifacts."""
import csv
import json
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='AI Telephone', layout='wide')
st.title('AI Telephone')

def records(path):
    if not path.exists():
        return []
    try:
        return [json.loads(line) for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    except (ValueError, OSError) as exc:
        st.error(f'Cannot read {path.name}: {exc}')
        return []

sources = records(Path('data/v2/sources.jsonl'))
results = Path('results')
models = sorted(p.name for p in results.iterdir() if p.is_dir() and (p/'generations.jsonl').exists()) if results.exists() else []
model = st.sidebar.selectbox('Model', models) if models else None
generations = records(results/model/'generations.jsonl') if model else []
annotations = records(results/model/'ai-annotations.jsonl') if model else []
by_id = {row['generation_id']: row for row in generations}
annotations_by_id = {row['generation_id']: row for row in annotations}
test_docs = [doc for doc in sources if doc.get('split') == 'test']
success = sum(row.get('status') == 'success' and row.get('document_id') in {d['id'] for d in test_docs} for row in generations)
requested = next((r.get('model') for r in generations if r.get('model')), model or 'not available')
st.caption(f'Requested model: {requested} · Test documents: {len(test_docs)} · Successful generations: {success}')
expected = {f"{d['id']}-{prompt}-{length}-r{n}" for d in test_docs for prompt in ('zero','one','few') for length in ('limited','free') for n in range(1,6)}
if not expected or any(gid not in by_id or by_id[gid].get('status') != 'success' for gid in expected):
    st.warning('Results incomplete: no final study or measured results are established for missing or unsuccessful generations.')
if not annotations:
    st.info('No final-study annotations are available.')

selected = st.sidebar.selectbox('Document', [d['id'] for d in sources]) if sources else None
prompt = st.sidebar.selectbox('Prompt', ['zero','one','few'])
length = st.sidebar.selectbox('Length', ['limited','free'])
round_no = st.sidebar.selectbox('Round', [1,2,3,4,5], index=4)
doc = next((d for d in sources if d['id'] == selected), None)

def show(gid, length_mode):
    row = by_id.get(gid)
    if not row:
        st.info('Not available: no saved generation.')
        return
    count = row.get('word_count')
    st.caption(f"Status: {row.get('status', 'unknown')} · Words: {count if count is not None else 'not available'}")
    if length_mode == 'limited' and count is not None and count > 250:
        st.warning('Over 250 words; kept unchanged.')
    if row.get('status') == 'success' and row.get('output') is not None:
        st.write(row['output'])
    else:
        st.info('Output not available.')

tabs = st.tabs(['Chain explorer','Prompt comparison','Evidence review','Results'])
with tabs[0]:
    if doc:
        st.subheader('Original text'); st.write(doc.get('text','Not available'))
        for n in range(1,6):
            st.subheader(f'Round {n}'); show(f'{selected}-{prompt}-{length}-r{n}', length)
    else: st.info('No sources available.')
with tabs[1]:
    if doc:
        for col, name in zip(st.columns(3), ('zero','one','few')):
            with col:
                st.subheader(name); show(f'{selected}-{name}-{length}-r{round_no}', length)
    else: st.info('No sources available.')
with tabs[2]:
    if doc:
        gid=f'{selected}-{prompt}-{length}-r{round_no}'
        annotation=annotations_by_id.get(gid)
        labels={item['item_id']:item for item in annotation.get('labels',[])} if annotation else {}
        for item in doc.get('items',[]):
            label=labels.get(item['id'],{})
            with st.expander(f"{item.get('type','item')} · {item['id']} · {label.get('label','not annotated')}"):
                st.write('Source quotation:',item.get('quotation','Not available'))
                st.write('Meaning:',item.get('meaning','Not available'))
                st.write('Summary quotation:',label.get('quotation','Not available'))
                st.write('Rationale:',label.get('rationale','Not available'))
        st.subheader('Unsupported claims')
        if annotation:
            for claim in annotation.get('unsupported_claims',[]): st.write(claim)
            if not annotation.get('unsupported_claims'): st.write('None recorded.')
        else: st.info('No annotation available.')
    else: st.info('No sources available.')
with tabs[3]:
    folder=results/'analysis'/model if model else None
    files=sorted(folder.glob('*.csv')) if folder and folder.exists() else []
    figdir=results/'analysis'/'figures'
    figures=sorted(figdir.glob('*.png')) if figdir.exists() else []
    if not files and not figures: st.info('No analysis results yet.')
    for path in files:
        st.subheader(path.stem.replace('_',' ').title())
        data=path.read_bytes()
        st.dataframe(list(csv.DictReader(data.decode('utf-8-sig').splitlines())))
        st.download_button('Download '+path.name,data,file_name=path.name,mime='text/csv')
    for path in figures:
        if model and (model in path.stem or path.stem == 'primary_contrasts'):
            st.image(str(path),caption=path.stem)
            st.download_button('Download '+path.name,path.read_bytes(),file_name=path.name,mime='image/png')
