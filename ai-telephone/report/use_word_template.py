from pathlib import Path
from copy import deepcopy
from docx import Document
from docx.shared import Inches
import hashlib
root=Path(__file__).resolve().parents[1]
import sys
ref=Path(sys.argv[1])
out=root/'report/submission/report-template.docx'
d=Document(ref)
body=d._element.body
normal=deepcopy(d.paragraphs[3]._p)
heading=deepcopy(d.paragraphs[2]._p)
first=d.tables[0]
for node in list(body):
    if node is first._tbl or node.tag.endswith('sectPr'): continue
    body.remove(node)
for t in first._tbl.xpath('.//w:t'):
    if t.text=='PROJECT TITLE':t.text='AI Telephone and Information Preservation Across Repeated Technical Summaries'
    elif t.text and t.text.startswith('Author name '):
        n=int(t.text.rsplit(' ',1)[1]);t.text={1:'Bilal Amin Dipu',2:'Thejitha'}.get(n,'')
    elif t.text=='Affiliation':t.text=''
authorparas=first._tbl.xpath('.//w:p')
for par in authorparas:
    ts=par.xpath('.//w:t')
    if ts and ts[0].text=='Bilal Amin Dipu' and len(ts)>1:ts[1].text='Saarland University'
for tbl in first._tbl.xpath('.//w:tbl'):
    if 'Bilal Amin Dipu' in ''.join(tbl.xpath('.//w:t/text()')) and not tbl.xpath('.//w:tbl'):
        cp=deepcopy(tbl.xpath('.//w:p')[0])
        for child in list(cp):
            if not child.tag.endswith('pPr'):cp.remove(child)
        tbl.addprevious(cp)
        from docx.text.paragraph import Paragraph
        Paragraph(cp,first.cell(1,0)).add_run('Bilal Amin Dipu and Thejitha\nSaarland University (Bilal Amin Dipu)\nbiam00002@stud.uni-saarland.de')
        tbl.getparent().remove(tbl)
abstract=(root/'report/submission/abstract.txt').read_text(encoding='utf-8')
cell=first.cell(1,0)
for par in list(cell._tc):
    if par.tag.endswith('p') and ''.join(par.xpath('.//w:t/text()')).strip()=='Abstract':
        from docx.text.paragraph import Paragraph
        cp=deepcopy(normal)
        for child in list(cp):
            if not child.tag.endswith('pPr'):cp.remove(child)
        par.addnext(cp);Paragraph(cp,cell).add_run(abstract)
for par in first._tbl.xpath('.//w:p'):
    if ''.join(par.xpath('.//w:t/text()')).strip().startswith('Summarize your project in'):
        par.getparent().remove(par)
md=(root/'report/submission/report.md').read_text(encoding='utf-8')
start=md.index('## 1 Introduction')
for block in md[start:].split('\n\n'):
    block=block.strip()
    if not block: continue
    if block.startswith('!['):
        p=d.add_paragraph();p.add_run().add_picture(str(root/'results/analysis/figures/trajectory_haiku.png'),width=Inches(6))
        d.add_paragraph(block[2:block.index(']')]);continue
    if ' | ' in block and block.startswith('Prompt'):
        lines=block.splitlines();t=d.add_table(rows=0,cols=5)
        for line in lines[:4]:
            for c,v in zip(t.add_row().cells,line.split(' | ')): c.text=v
        d.add_paragraph('\n'.join(lines[4:]));continue
    ishead=block.startswith('## ')
    node=deepcopy(heading if ishead else normal)
    for child in list(node):
        if not child.tag.endswith('pPr'):node.remove(child)
    body.insert(len(body)-1,node)
    from docx.text.paragraph import Paragraph
    p=Paragraph(node,d);p.add_run(block.removeprefix('## '))
    if ishead and block.startswith('## References'):p.paragraph_format.page_break_before=True
from docx.oxml import OxmlElement
for tc in d._element.xpath('.//w:tc'):
    if not tc[-1].tag.endswith('p'):tc.append(OxmlElement('w:p'))
d.save(out)
(root/'report/qa/artifact.md').write_text('Reference: '+str(ref)+'\nSHA256: '+hashlib.sha256(ref.read_bytes()).hexdigest()+'\nContract: retain template sections, page geometry, styles, header/footer and opening title/abstract table. Replace guidance with verified report content; remove unused author slots.\n')
print(out)
