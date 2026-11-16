from pathlib import Path
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
R=Path(__file__).resolve().parents[1]; O=R/'report/submission'
import sys
d=Document(sys.argv[1])
def after(anchor,image,caption):
    p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
    p.add_run().add_picture(str(O/'graphics'/image),width=Inches(6.25))
    anchor._p.addnext(p._p)
    c=d.add_paragraph(caption);c.paragraph_format.space_after=Pt(10)
    for r in c.runs:r.font.size=Pt(9);r.font.color.rgb=RGBColor.from_string('455865')
    p._p.addnext(c._p)
for p in list(d.paragraphs):
    if p.text.startswith('Each of the six conditions forms'):
        after(p,'design.png','Figure 1. Experimental design. Each report produces six five-round chains. The judge compares scored summaries with the original report and its items. No independent human audit was conducted.')
    elif p._p.xpath('.//w:drawing'):
        for r in list(p.runs):
            if r._r.xpath('.//w:drawing'):r._r.getparent().remove(r._r)
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.keep_with_next=True
        p.add_run().add_picture(str(O/'graphics/preservation.png'),width=Inches(6.25))
    elif p.text.startswith('Figure 1.'):
        p.text='Figure 2. Preservation over repeated summaries and the primary comparison. A–B show equal-document means (n = 12 per condition); the vertical axis begins at 65%. C shows the paired round-five difference under the cap, with a 95% percentile interval from 10,000 document bootstrap resamples. Trajectory lines have no uncertainty bands. The primary interval includes zero.'
        for r in p.runs:r.font.size=Pt(9)
    elif p.text.startswith('The common maximum did not equalize'):
        after(p,'length_retention.png','Figure 3. Output length and preservation at round five. Each point is a condition mean over twelve documents. Examples change achieved length even under a common cap. These descriptive points do not isolate a causal effect of length; axes are shared between panels.')
for t in d.tables[1:]:
    for i,row in enumerate(t.rows):
        for c in row.cells:
            tcpr=c._tc.get_or_add_tcPr();b=OxmlElement('w:tcBorders')
            for side in ('top','left','bottom','right'):
                e=OxmlElement('w:'+side);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');b.append(e)
            tcpr.append(b)
            if i==0:
                sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'EAF0F5');tcpr.append(sh)
                for p in c.paragraphs:
                    for r in p.runs:r.bold=True
for p in d.paragraphs:
    if p.text=='References':p.paragraph_format.page_break_before=False
d.save(O/'Report-final.docx')
print(O/'Report-final.docx')
