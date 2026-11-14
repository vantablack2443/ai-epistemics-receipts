"""Inspect saved local records; this application never starts a model call."""
import json
import sqlite3
from pathlib import Path
import streamlit as st

st.set_page_config(page_title='AI Telephone', layout='wide')
st.title('AI Telephone')
# Each model is a separate run with its own database; results are never pooled.
RUNS = {'gpt-6.1-terra (Codex CLI)': ('gpt-6.1-terra', 'artifacts/development.sqlite'),
        'claude-haiku-5-5 (Claude Code CLI)': ('claude-haiku-5-5', 'artifacts/development-haiku.sqlite')}
run_label = st.sidebar.radio('Model run', list(RUNS))
model, db_file = RUNS[run_label]
st.caption(f'Requested model: {model} · Local saved records · No model calls from this app')
source_path = Path('data/sources.jsonl')
docs = [json.loads(line) for line in source_path.read_text(encoding='utf-8').splitlines() if line.strip()] if source_path.exists() else []
db_path = Path(db_file)
rows = []
if db_path.exists():
    with sqlite3.connect(f'file:{db_path.resolve().as_posix()}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute('SELECT generation_id, attempt, status, output, word_count FROM attempts')]
st.warning('Development work in progress. Sources are unreviewed; no final study or measured results are available.')
st.caption(f'Development database ({db_path}) · {len(docs)} draft document(s) · {len(rows)} recorded attempt(s)')
tabs = st.tabs(['Chain explorer', 'Method comparison', 'Evidence review', 'Results'])
if docs:
    selected = st.sidebar.selectbox('Document', [d['id'] for d in docs])
    doc = next(d for d in docs if d['id'] == selected)
    def show(gid, limit):
        matches = [r for r in rows if r['generation_id'] == gid]
        if not matches:
            st.info('Missing or not yet run.')
            return
        r = matches[-1]
        st.caption(f"Status: {r['status']} · words: {r['word_count']} · budget: {limit}")
        if r['word_count'] is not None and r['word_count'] > limit:
            st.warning('Over budget; output retained unchanged.')
        st.write(r['output'] if r['output'] is not None else 'No successful output.')
    with tabs[0]:
        st.subheader('Original handoff'); st.write(doc['text'])
        condition = st.radio('Condition', ['A', 'B', 'C'], horizontal=True)
        for n, limit in [(1,100),(2,70),(3,45)]:
            st.subheader(f'Round {n}'); show(f'{selected}-{condition}-{n}', limit)
        st.subheader('Direct ordinary control'); show(f'{selected}-direct-3', 45)
    with tabs[1]:
        st.write('Round-three comparison')
        for col, condition in zip(st.columns(3), 'ABC'):
            with col:
                st.subheader(condition); show(f'{selected}-{condition}-3', 45)
    with tabs[2]:
        st.write('Draft source items — not human-reviewed annotations')
        for item in doc['items']:
            with st.expander(f"{item['type']}: {item['id']}"):
                st.write(item['quotation']); st.caption(item['meaning'])
        st.info('No independent annotations or adjudications are available.')
else:
    st.info('No source documents are available.')
with tabs[3]:
    st.info('No final-study annotations, aggregate results, confidence intervals, or reviewer agreement are available.')
