"""Build a self-contained HTML page for human source review.

The page shows each draft with its ground-truth quotations highlighted, the mechanical
pre-check flags, and per-item decision fields. Decisions autosave in the browser and export
as a CSV in exactly the `data/source-review.csv` format that `review_import` accepts.
The page records human decisions only; it never approves anything by itself.
"""
import json
from pathlib import Path
from .review_checks import check, load_all

PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Source Review</title>
<style>
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1b;--muted:#6b6b66;--line:#e2e1dc;--find:#fde68a;--qual:#bfdbfe;
--ok:#15803d;--warn:#b45309;--bad:#b91c1c;--accent:#1d4ed8}
@media (prefers-color-scheme:dark){:root{--bg:#141413;--card:#1e1e1c;--ink:#ecebe6;--muted:#a3a29b;--line:#34332f;
--find:#6b5612;--qual:#1e3a66;--ok:#4ade80;--warn:#fbbf24;--bad:#f87171;--accent:#93b4ff}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,sans-serif}
header{position:sticky;top:0;z-index:2;background:var(--card);border-bottom:1px solid var(--line);padding:10px 16px;
display:flex;flex-wrap:wrap;gap:10px;align-items:center}
header h1{font-size:17px;margin:0 8px 0 0}input,select,textarea,button{font:inherit;color:inherit}
input,select,textarea{background:var(--bg);border:1px solid var(--line);border-radius:6px;padding:4px 8px}
button{background:var(--accent);color:#fff;border:0;border-radius:6px;padding:6px 12px;cursor:pointer}
button.secondary{background:transparent;color:var(--ink);border:1px solid var(--line)}
.progress{color:var(--muted);font-size:13px}main{max-width:980px;margin:0 auto;padding:16px}
.doc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px;margin-bottom:18px}
.doc.done{border-left:5px solid var(--ok)}.meta{display:flex;flex-wrap:wrap;gap:8px;font-size:13px;color:var(--muted)}
.tag{border:1px solid var(--line);border-radius:999px;padding:1px 8px}.text{margin:12px 0;white-space:pre-wrap}
mark.f{background:var(--find);color:inherit}mark.q{background:var(--qual);color:inherit}
mark sup{font-weight:700;padding:0 2px}.flags{margin:8px 0;padding:8px 12px;border-radius:8px;
border:1px solid var(--warn);color:var(--warn);font-size:13px}.flags ul{margin:4px 0 0 18px;padding:0}
table{width:100%;border-collapse:collapse;font-size:14px}td,th{border-top:1px solid var(--line);padding:8px 6px;
vertical-align:top;text-align:left}th{font-size:12px;color:var(--muted);font-weight:600}
td textarea{width:100%;min-height:38px}.small{font-size:12px;color:var(--muted)}
.docq{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px;font-size:14px}
.docq label{display:flex;gap:6px;align-items:flex-start}.docq textarea{width:100%;grid-column:1/-1}
.guide{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 16px;margin-bottom:18px;font-size:14px}
@media (max-width:700px){.docq{grid-template-columns:1fr}td,th{display:block}tr{display:block;border-top:1px solid var(--line)}}
</style></head><body>
<header><h1>Source Review</h1>
<label>Reviewer <input id="reviewer" placeholder="your name" size="14"></label>
<label>Show <select id="filter"><option value="all">all</option><option value="todo">not finished</option>
<option value="flagged">flagged</option><option value="development">development</option><option value="test">test</option>
</select></label>
<span class="progress" id="progress"></span>
<button id="export">Export CSV</button><button class="secondary" id="reset">Clear my decisions</button></header>
<main>
<div class="guide"><b>For each item:</b> does the quotation say what “intended meaning” claims, and is it really a
critical qualification (or the principal finding) an engineer must not lose? Choose <b>approve</b>, or <b>revise</b>/<b>reject</b>
with a note. <b>For each document:</b> does it fit its category, is the scenario realistic and distinct, and (test documents)
is the finding <i>clearly established</i> by the evidence? Exactly six test documents should be marked strong.
Decisions save in this browser; <b>Export CSV</b> writes <code>source-review.csv</code> for <code>review_import</code>.
Only rows marked approve with a reviewer name pass the import.</div>
<div id="docs"></div></main>
<script>
const DATA = __DATA__;
const KEY = 'ai-telephone-source-review-v1';
let state = {};
try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch (e) { state = {}; }
const save = () => { try { localStorage.setItem(KEY, JSON.stringify(state)); } catch (e) {} };
const $ = s => document.querySelector(s);
const esc = s => s.replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
state.reviewer = state.reviewer || ''; $('#reviewer').value = state.reviewer;
$('#reviewer').oninput = e => { state.reviewer = e.target.value; save(); };

function highlight(doc) {
  const spans = doc.items.map((it, i) => ({s: doc.text.indexOf(it.quotation), e: doc.text.indexOf(it.quotation) + it.quotation.length,
    cls: it.type === 'finding' ? 'f' : 'q', n: it.type === 'finding' ? 'F' : 'Q' + i})).filter(x => x.s >= 0).sort((a, b) => a.s - b.s);
  let out = '', pos = 0;
  for (const sp of spans) { if (sp.s < pos) continue; out += esc(doc.text.slice(pos, sp.s));
    out += `<mark class="${sp.cls}"><sup>${sp.n}</sup>${esc(doc.text.slice(sp.s, sp.e))}</mark>`; pos = sp.e; }
  return out + esc(doc.text.slice(pos));
}
const itemState = id => (state[id] = state[id] || {decision: '', notes: ''});
const docState = id => (state['doc:' + id] = state['doc:' + id] || {category_ok: false, distinct_ok: false, strong: false, notes: ''});
const docDone = d => d.items.every(it => itemState(it.id).decision) && docState(d.id).category_ok && docState(d.id).distinct_ok;

function render() {
  const f = $('#filter').value;
  $('#docs').innerHTML = DATA.filter(d => f === 'all' || (f === 'todo' && !docDone(d)) || (f === 'flagged' && d.flags.length) || d.split === f)
    .map(d => { const ds = docState(d.id); return `<section class="doc ${docDone(d) ? 'done' : ''}" id="${d.id}">
    <div class="meta"><b style="color:var(--ink)">${d.id}</b><span class="tag">${d.split}</span><span class="tag">${d.category}</span>
    <span class="tag">${d.words} words</span>${d.finding_hedged ? '<span class="tag">hedged finding</span>' : ''}</div>
    <div class="text">${highlight(d)}</div>
    ${d.flags.length ? `<div class="flags">Pre-check flags<ul>${d.flags.map(x => `<li>${esc(x)}</li>`).join('')}</ul></div>` : ''}
    <table><tr><th>Item</th><th>Quotation → intended meaning</th><th>Decision</th><th>Note</th></tr>
    ${d.items.map((it, i) => { const s = itemState(it.id); return `<tr><td>${it.type === 'finding' ? 'F' : 'Q' + i}<div class="small">${it.type}</div></td>
      <td>“${esc(it.quotation)}”<div class="small">→ ${esc(it.meaning)}</div>
      ${it.paraphrases.length ? `<div class="small">Paraphrases: ${it.paraphrases.map(esc).join(' · ')}</div>` : ''}</td>
      <td><select data-item="${it.id}" data-k="decision"><option value=""></option>
      ${['approve', 'revise', 'reject'].map(v => `<option ${s.decision === v ? 'selected' : ''}>${v}</option>`).join('')}</select></td>
      <td><textarea data-item="${it.id}" data-k="notes" placeholder="required unless approve">${esc(s.notes)}</textarea></td></tr>`; }).join('')}
    </table>
    <div class="docq">
      <label><input type="checkbox" data-doc="${d.id}" data-k="category_ok" ${ds.category_ok ? 'checked' : ''}> Fits “${d.category}” category</label>
      <label><input type="checkbox" data-doc="${d.id}" data-k="distinct_ok" ${ds.distinct_ok ? 'checked' : ''}> Realistic and distinct scenario</label>
      ${d.split === 'test' ? `<label><input type="checkbox" data-doc="${d.id}" data-k="strong" ${ds.strong ? 'checked' : ''}> Principal finding clearly established (strong)</label>` : ''}
      <textarea data-doc="${d.id}" data-k="notes" placeholder="Document-level notes (category mismatch, edits needed)">${esc(ds.notes)}</textarea>
    </div></section>`; }).join('');
  const done = DATA.filter(docDone).length, strong = DATA.filter(d => d.split === 'test' && docState(d.id).strong).length;
  const items = DATA.flatMap(d => d.items), approved = items.filter(it => itemState(it.id).decision === 'approve').length;
  $('#progress').textContent = `${done}/${DATA.length} documents finished · ${approved}/${items.length} items approved · ${strong}/6 strong`;
}
document.addEventListener('change', e => { const t = e.target, k = t.dataset.k; if (!k) return;
  const v = t.type === 'checkbox' ? t.checked : t.value;
  if (t.dataset.item) itemState(t.dataset.item)[k] = v; else if (t.dataset.doc) docState(t.dataset.doc)[k] = v; else return;
  save(); if (t.tagName !== 'TEXTAREA') render(); });
document.addEventListener('input', e => { const t = e.target, k = t.dataset.k; if (t.tagName !== 'TEXTAREA' || !k) return;
  if (t.dataset.item) itemState(t.dataset.item)[k] = t.value; else docState(t.dataset.doc)[k] = t.value; save(); });
$('#filter').onchange = render;
$('#reset').onclick = () => { if (confirm('Clear every decision saved in this browser?')) { const r = state.reviewer; state = {reviewer: r}; save(); render(); } };

const cell = v => '"' + String(v ?? '').replace(/"/g, '""') + '"';
$('#export').onclick = () => {
  if (!state.reviewer.trim()) { alert('Enter your name as reviewer first.'); return; }
  const missing = DATA.flatMap(d => d.items).filter(it => { const s = itemState(it.id); return s.decision && s.decision !== 'approve' && !s.notes.trim(); });
  if (missing.length) { alert('Add a note for every revise/reject item: ' + missing.map(x => x.id).join(', ')); return; }
  const fields = ['document_id','split','category','word_count','source_text','item_id','item_type','quotation','intended_meaning','reviewer','decision','review_notes'];
  const rows = [fields.join(',')];
  for (const d of DATA) { const ds = docState(d.id);
    const tags = [ds.category_ok ? '' : '[category not confirmed]', ds.distinct_ok ? '' : '[distinctness not confirmed]',
      d.split === 'test' && ds.strong ? '[strong-finding]' : '', ds.notes.trim() ? '[doc] ' + ds.notes.trim() : ''].filter(Boolean).join(' ');
    for (const it of d.items) { const s = itemState(it.id);
      const notes = [s.notes.trim(), it.type === 'finding' ? tags : ''].filter(Boolean).join(' ');
      rows.push([d.id, d.split, d.category, d.words, d.text, it.id, it.type, it.quotation, it.meaning,
        s.decision ? state.reviewer.trim() : '', s.decision, notes].map(cell).join(',')); } }
  const blob = new Blob(['﻿' + rows.join('\r\n') + '\r\n'], {type: 'text/csv;charset=utf-8'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'source-review-' + state.reviewer.trim().replace(/\W+/g, '_') + '.csv'; a.click(); URL.revokeObjectURL(a.href);
};
render();
</script></body></html>
"""

def main():
    docs = load_all()
    data = []
    for d in docs:
        c = check(d)
        data.append({'id': d.id, 'split': d.split, 'category': d.category, 'words': c['words'], 'text': d.text,
                     'finding_hedged': c['finding_hedged'], 'flags': c['flags'],
                     'items': [{'id': i.id, 'type': i.type, 'quotation': i.quotation, 'meaning': i.meaning,
                                'paraphrases': i.paraphrases} for i in d.items]})
    checks = Path('artifacts/review-checks.json')
    if checks.exists():  # add similarity flags computed across documents
        extra = json.loads(checks.read_text(encoding='utf-8'))['documents']
        for row in data:
            row['flags'] = extra.get(row['id'], {}).get('flags', row['flags'])
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    out = Path('artifacts/source-review.html'); out.parent.mkdir(exist_ok=True)
    out.write_text(PAGE.replace('__DATA__', payload), encoding='utf-8')
    print(f'Wrote {out} with {len(data)} documents')

def main_v2():
    """Review page for design-v2 long sources (6-10 items, fictional and paper documents)."""
    from .review_checks import load_v2, run_v2
    checks = run_v2()
    data = [{'id': d['id'], 'split': d['split'], 'category': d.get('kind', ''), 'words': checks[d['id']]['words'],
             'text': d['text'], 'finding_hedged': checks[d['id']]['finding_hedged'], 'flags': checks[d['id']]['flags'],
             'items': [{'id': i['id'], 'type': i['type'], 'quotation': i['quotation'], 'meaning': i['meaning'],
                        'paraphrases': i.get('paraphrases', [])} for i in d['items']]} for d in load_v2()]
    payload = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    page = (PAGE.replace('__DATA__', payload)
            .replace('ai-telephone-source-review-v1', 'ai-telephone-source-review-v2')
            .replace(' Exactly six test documents should be marked strong.', ' Mark strong when the evidence clearly establishes the finding.')
            .replace("${strong}/6 strong", "${strong} strong")
            .replace('Fits “${d.category}” category', 'Accurate, realistic “${d.category}” document'))
    out = Path('artifacts/source-review-v2.html'); out.parent.mkdir(exist_ok=True)
    out.write_text(page, encoding='utf-8')
    print(f'Wrote {out} with {len(data)} documents')

if __name__ == '__main__':
    import sys
    main_v2() if '--v2' in sys.argv else main()
