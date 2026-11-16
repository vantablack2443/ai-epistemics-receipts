"""Build the PDF report, slide deck and supporting text from saved analysis.

Run with the bundled document Python runtime (reportlab and Pillow required).
No model calls, network calls or changes to experimental data.
"""
import csv, hashlib, json, shutil, zipfile
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'report/submission'; OUT.mkdir(parents=True,exist_ok=True)
AN=ROOT/'results/analysis'
audit=json.loads((AN/'submission-integrity.json').read_text())
def csvrows(name):
    with (AN/name).open() as f: return list(csv.DictReader(f))
primary=csvrows('primary.csv')[0]
groups=audit['groups']
def g(p,l,r=5): return next(x for x in groups if (x['prompt'],x['length'],x['round'])==(p,l,r))
def pct(v): return f'{100*float(v):.2f}'
TITLE='AI Telephone and Information Preservation Across Repeated Technical Summaries'
AUTHORS='Bilal Amin Dipu and Thejitha'
CONTACT='Saarland University (Bilal Amin Dipu) | biam00002@stud.uni-saarland.de'
abstract=(
'Repeated AI summaries can retain a headline while losing the qualifications needed to interpret it. '
'We study whether examples of good and bad summaries preserve source information over five successive summaries. '
'The completed experiment uses Claude Haiku 5.5 through Claude Code on twelve fictional technical reports, '
'with zero, one, or five example pairs, under a 250-word cap or without a length cap. '
'All 360 scheduled summaries completed; Claude Opus 5.5 annotated 216 summaries at rounds one, three, and five '
'against 86 source items. At round five under the cap, mean document-level preservation was 84.72% without '
'examples and 84.92% with five pairs: a paired difference of +0.20 percentage points '
'(95% document-bootstrap interval -8.33 to +8.93; n = 12). Without a cap, preservation was '
'97.92% and 81.60%, respectively, while mean output length was 615.58 and 210.83 words. '
'The primary comparison provides no clear evidence of a lasting preservation advantage from examples. '
'The uncapped comparison shows that example prompts also change compression behavior, complicating interpretation '
'of preservation differences. These are exploratory measurements from one model and harness, synthetic sources, '
'and an AI judge without a human audit; they do not establish effects on real engineering decisions.')
assert 150<=len(abstract.split())<=250

pages=[]
def page(*blocks): pages.append(list(blocks))
def h(s):return ('h',s)
def p(s):return ('p',s)
def fig(file,caption):return ('fig',file,caption)
def table(rows,caption):return ('table',rows,caption)
page(('title',TITLE),p(AUTHORS),p(CONTACT),p('Research conducted at the AI x Epistemics Research Sprint, November 2026'),
h('Abstract'),p(abstract),h('1 Introduction'),
p('An engineering summary can be factually plausible yet omit the condition that makes action justified. Repeated handoffs create additional opportunities to lose uncertainty, scope restrictions, conflicting evidence, and prerequisites. Evaluating only the claims a summary contains can miss the qualifications it leaves behind.'),
p('We ask whether contrastive examples of faithful and unfaithful summaries improve retention over repeated summarization. Our contribution is a reproducible chain experiment, item-level annotations against the original source, and a comparison of capped and uncapped output lengths. The completed evidence concerns one summarizer and its CLI harness. It does not test downstream decisions.'),
h('2 Related Work'),
p('Kolagar and Zarcone (2024) study uncertainty transfer from source texts to generated summaries, using a taxonomy of uncertainty expressions and expert-informed annotation. Nnamdi et al. (2026) characterize epistemic erosion in professional text, including omission and shifts in certainty. These are close antecedents: our study does not claim to discover uncertainty loss. It examines repeated chains with contrastive examples under capped and uncapped length settings.'),
p('Maynez et al. (2020) examine faithfulness and factuality in abstractive summarization using human evaluation. Min et al. (2023) introduce FActScore, which evaluates support for atomic facts in long-form generated text. Our source-item measure instead asks whether specified findings and qualifications survive; it is a retention measure rather than an implementation of FActScore. We additionally record unsupported claims.'))
page(h('3 Methods'),
p('Completed design. Twelve held-out fictional engineering reports and three development reports were drafted with Claude Haiku 5.5. The test reports contain 909–1,191 whitespace-delimited words and 86 ground-truth items in total. Items identify one or two findings plus qualifications, each linked to a verbatim source quotation and intended meaning. Source review and example selection were performed by AI agents and checked by the orchestrator. No human review or human annotation audit is recorded.'),
p('Each test report receives three prompt variants crossed with two length settings. Zero supplies the shared instruction only. One adds one source with a good summary, a bad summary, and an explanation of the bad example. Few adds all five selected examples in that same paired format. Thus the implemented few condition contains five good/bad pairs, rather than the three-good/two-bad shorthand in the early design. Example sources are distinct from the test reports. Limited requests at most 250 words in every round; free specifies no word limit. All variants request plain prose, source-faithful summarization with no tools.'),
p('Each of the six conditions forms a five-round chain. Round one receives the original report; subsequent rounds receive only the preceding summary as their task text, alongside the same instruction and, where applicable, examples. Source items never enter the summarizer prompt. There is one chain per document and condition: 12 × 3 × 2 × 5 = 360 outputs. The manifest records randomized scheduling with seed 1729. Overlength outputs are retained and passed forward, rather than regenerated or truncated.'),
p('The recorded summarizer is claude-haiku-5-5 through Claude Code 2.1.325, low effort, with a fresh process and isolated working directory per call, tools disabled, strict MCP configuration, empty setting sources, and no session persistence. This is a model-plus-harness evaluation. Terra was planned but no final Terra export is available, so it contributes no results. Optional real-paper sources and Gemini runs are absent.'),
h('Annotation and analysis'),
p('Claude Opus 5.5 through Claude Code, at high effort, judges rounds 1, 3, and 5 against the original source and its item meanings. It receives one summary without the generating condition, round, or model metadata. The rubric assigns preserved, omitted, strengthened, weakened, or contradicted to each item and separately lists unsupported claims. Five worked annotation examples cover the labels. Outputs include evidence quotations and rationales. There are 216 scored summaries and 1,548 item labels.'),
p('The primary outcome is the proportion of items labeled preserved, first computed within each summary and then averaged equally over documents. The primary contrast is few minus zero at round five in the limited condition. We resample paired document differences 10,000 times using NumPy default_rng, seed 1729, and report the 2.5th and 97.5th percentiles. The document is the statistical unit (n = 12), not individual labels or rounds. Intervals condition on the saved labels and do not capture judge uncertainty. Other contrasts and trajectories are exploratory; no multiplicity correction is applied.'),
p('The repository contains a pre-collection frozen manifest and AI-only sign-off, not an external preregistration. After collection, the annotation validator was amended to accept ellipsis-joined fragments only when each fragment occurs verbatim in order. This amendment is documented in docs/annotation.md; it did not intentionally change labels. The current annotate.py therefore differs from its frozen hash. Other frozen files match after LF line-ending normalization.'))
rows=[['Prompt','Limited preservation','Free preservation','Limited words','Free words']]
for prompt in ('zero','one','few'):
    a,b=g(prompt,'limited'),g(prompt,'free')
    rows.append([prompt,pct(a['mean_preservation'])+'%',pct(b['mean_preservation'])+'%',f"{a['mean_words']:.2f}",f"{b['mean_words']:.2f}"])
page(h('4 Results'),
p('All 360 scheduled generations have success status; all 216 scheduled scored summaries have complete annotations. Table 1 reports round-five means over the same twelve documents. Label coverage and word counts were independently checked against the saved exports. No missing outputs were imputed.'),
table(rows,'Table 1. Round-five preservation and output length. Preservation is the mean of document-level fractions, with equal weight per document (n = 12 per cell). Words use whitespace splitting.'),
p('Primary contrast. Few-shot minus zero-shot preservation under the cap is +0.20 percentage points (95% paired bootstrap interval −8.33 to +8.93). The interval includes both loss and gain; this result is inconclusive about a lasting benefit. One-shot minus zero-shot is −5.16 points (−13.99 to +2.88).'),
fig('trajectory_haiku.png','Figure 1. Mean document-level item preservation at scored rounds. Lines describe the twelve observed documents in each prompt and length condition; they are not independent replications across rounds. No uncertainty bands are shown.'),
p('At round one under the cap, the few-minus-zero contrast is +7.19 points (1.19 to 14.73); by round three it is +1.24 (−8.13 to +10.96). This exploratory trajectory suggests the early advantage was not sustained in these chains. In the free condition at round five, few minus zero is −16.32 points (−27.08 to −6.55), alongside a large difference in generated length. We cannot attribute that difference to example content independently of compression.'))
page(h('Output length and error patterns'),
p('The common maximum did not equalize actual length. At round five, capped zero-shot outputs averaged 232.92 words versus 179.75 for few-shot. Across all five limited rounds, zero exceeded 250 words in 19/60 outputs; one and few each did so in 1/60. All overlength outputs remain in the analysis. Without a cap, round-five zero-shot outputs averaged 615.58 words, versus 247.83 for one and 210.83 for few. Short example summaries may have influenced compression behavior, but this is an interpretation rather than an isolated causal mechanism.'),
p('At round five under the cap, zero-shot labels were 73 preserved, 7 omitted, 5 strengthened, 1 weakened, and 0 contradicted out of 86 items. These pooled counts differ slightly from the equal-document percentages because reports have different numbers of items. The judge listed 9 unsupported claims across the twelve zero-shot summaries and 8 across the twelve few-shot summaries. Unsupported-claim counts can overlap conceptually with strengthening labels; they are not unique downstream incidents.'),
h('5 Discussion and Limitations'),
p('Examples can change how much a model writes as well as what it keeps. The capped comparison offers no clear evidence that five example pairs improve final preservation, while the uncapped comparison illustrates the difficulty of interpreting retention without measuring output length. Even a fixed maximum allows systematic differences in achieved length. A useful follow-up would match target lengths, add an instruction-only preservation baseline, and include direct summaries from the original as controls for repeated transformation.'),
p('The evidence is limited by twelve synthetic test documents, one realization per condition, a single summarizer and harness, and AI-generated sources, examples, and labels. The judge was not validated against an independent human audit. Shared model-family preferences and rubric errors may affect results. Item preservation equally weights findings and qualifications, and may not track decision importance. The current results do not establish that example prompting generally helps or harms, nor that observed omissions would change an engineer’s decision. Secondary comparisons are exploratory.'),
h('6 Conclusion'),
p('For this model, harness, and synthetic dataset, five example pairs yielded almost the same round-five preservation as zero-shot prompting under a 250-word maximum. Uncapped example prompts produced shorter summaries with lower retention. The practical lesson supported by this pilot is to measure both retained information and achieved output length when evaluating repeated summaries, and to validate AI judgments before treating them as reliable evidence of decision quality.'),
h('Code and Data'),
p('Repository: https://github.com/vantablack2443/ai-epistemics-receipts. Submission package: ai-telephone/report/submission. Data: ai-telephone/data/v2 and results/haiku. Analysis tables and figures: results/analysis. This report uses the Haiku exports introduced in commits e320dbb and bff9988. The separate receipts-study directory is outside this study. Repository history places the AI Telephone work within the sprint; no pre-sprint study code reuse is recorded.'))
page(h('References'),
p('Kolagar, Zahra, and Alessandra Zarcone. 2024. Aligning Uncertainty: Leveraging LLMs to Analyze Uncertainty Transfer in Text Summarization. Proceedings of UncertaiNLP, pp. 41–61. https://aclanthology.org/2024.uncertainlp-1.5/'),
p('Nnamdi, Micky C., Shaunna Wang, Chinaza Nnamdi, Jieru Li, Benoit Louis Marteau, J. Ben Tamo, Yining Yuan, and May Dongmei Wang. 2026. Epistemic Erosion: An Error Class Beyond Hallucination in LLM Text Generation. Proceedings of AACL-IJCNLP, pp. 4998–5026. https://aclanthology.org/2026.aacl-long.223/'),
p('Maynez, Joshua, Shashi Narayan, Bernd Bohnet, and Ryan McDonald. 2020. On Faithfulness and Factuality in Abstractive Summarization. Proceedings of ACL, pp. 1906–1919. https://aclanthology.org/2020.acl-main.173/'),
p('Min, Sewon, Kalpesh Krishna, Xinxi Lyu, Mike Lewis, Wen-tau Yih, Pang Wei Koh, Mohit Iyyer, Luke Zettlemoyer, and Hannaneh Hajishirzi. 2023. FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation. Proceedings of EMNLP, pp. 12076–12100. https://aclanthology.org/2023.emnlp-main.741/'),
h('Appendix A Limitations and Dual-Use / Ethical Considerations'),
p('Scope. All included reports are fictional. The proposed real-paper excerpt extension was not included. Source drafting, source review, example selection, and annotation used AI assistance. This design cannot establish performance on real operational documents, confidential reports, other domains, other model releases, or other harnesses. One sampled chain per condition leaves decoding variability unmeasured. No human agreement statistic is available; this report makes no claim of human validation.'),
p('Measurement limits. The bootstrap captures document variation within a small constructed sample, conditional on one set of generated outputs and judge labels. It does not account for source construction, example choice, model sampling, or judge error. The item list is selective and equally weighted. A qualification can be judged omitted even when an engineer could infer it, and implicit statements can be rated preserved too generously. Unsupported claims are judge judgments rather than externally verified falsehoods. Prompt length, examples, and achieved compression vary together.'),
p('Dual use. Polished summaries could make weak evidence appear authoritative, selectively suppress inconvenient qualifications, or support premature operational decisions. The benchmark and examples should be used to inspect those failure modes, rather than to optimize persuasive omission. A high aggregate preservation score is not a deployment approval. Practical use requires access to original documents and domain review of consequential recommendations.'),
p('Personal data. Experimental sources are synthetic and contain fictional organizations and scenarios. No real customer records or private operational documents were deliberately used. Publication exports omit raw CLI events, authentication data, and runtime databases. Author names and the supplied contact email are included for attribution. The study did not recruit human participants or measure their decisions.'),
h('LLM Usage Statement'),
p('Project records document Claude Haiku 5.5 and GPT 6.1 Terra assistance with implementation, draft sources, and example candidates; the final dataset and selected examples used here were Haiku-generated. Claude Opus 5.5 supplied the research labels. Codex assisted with analysis and report preparation. Automated checks recomputed reported statistics and validated export coverage and quotations. Human independent verification of labels and final author approval are not claimed. The named authors remain responsible for reviewing and approving the submission.'))
page(h('Appendix B Prompts and Reproduction'),
p('Shared summarizer instruction, verbatim: '+__import__('re').search(r'BASE = \((.*?)\)\nLIMIT', (ROOT/'src/ai_telephone/prompts.py').read_text(),__import__('re').S).group(1).replace('"\n        "','').strip('"')),
p('Limited suffix, verbatim: Use at most 250 words. This is a hard limit: count your words and stay under it.'),
p('Example introduction, verbatim: Examples of good and bad summaries follow. Learn what to keep and what to avoid; do not copy their content.'),
p('Each selected example is rendered as Source, Good summary, Bad summary, and Why the bad summary is bad. Zero uses none; one uses E1; few uses E1–E5. The full selected texts and provenance are in data/v2/examples/selected.json. The original task text or preceding output follows Text to summarize. Exact judge rubric and five worked examples are in src/ai_telephone/annotator_prompt.py.'),
h('Reproduction from saved outputs'),
p('From ai-telephone with its locked Python 3.11 environment: run uv sync, then uv run pytest. Run uv run python -m ai_telephone.analyze_cli --results results --sources data/v2/sources.jsonl --out results/analysis. Then run uv run python -m ai_telephone.figures --analysis results/analysis --out results/analysis/figures and uv run python report/audit_submission.py. These commands read saved outputs and make no model calls. The report builder requires reportlab and the bundled document runtime; its command is recorded in the package README.'),
h('Appendix C Provenance and Verification'),
p('Frozen settings are in freeze/haiku.json; AI-only review statements are in freeze/signoff.json. The frozen source set is twelve test plus three development reports, superseding the early plan for fifteen test reports including papers. The selected examples render five pairs; the implemented prompt is the authority for the reported condition. Terra candidates exist in repository history but do not contribute to the frozen final source set.'),
p('Integrity checks confirm unique generation and annotation IDs, complete item coverage, recorded word counts, valid labels, ordered verbatim evidence fragments, and verbatim unsupported-claim quotations. Seven of eight frozen files match their recorded SHA-256 after CRLF-to-LF normalization; annotate.py differs because of the disclosed validator amendment. Raw checkout hashes differ due to Windows line endings. Analysis and figure files are derived from saved exports, not test fixtures.'),
p('The current combined code passes 136 tests using a workspace-local temporary directory. The initial run encountered Windows temporary-directory cleanup permission failures; rerunning with a writable local temporary directory passed. These tests validate software mechanics, not the correctness of the AI judge. Full numerical tables, the integrity report, exact prompts, selected examples, sources, and labels accompany the report.'))

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='Body',fontName='Times-Roman',fontSize=10.5,leading=13.3,spaceAfter=8))
styles.add(ParagraphStyle(name='Head',fontName='Helvetica-Bold',fontSize=12,leading=15,spaceBefore=9,spaceAfter=7))
styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=18,leading=21,spaceAfter=13))
styles.add(ParagraphStyle(name='CaptionSmall',fontName='Times-Italic',fontSize=9,leading=11,spaceAfter=8))
def text(s,style='Body'): return Paragraph(escape(s.replace('−','-')),styles[style])
def footer(c,d):
    c.setFont('Helvetica',8);c.drawString(45,27,'AI Telephone | AI x Epistemics Research Sprint 2026');c.drawRightString(A4[0]-45,27,str(d.page))
story=[]; markdown=[]
for index,blocks in enumerate(pages):
    if index:story.append(PageBreak())
    for b in blocks:
        if b[0] in ('p','h','title'):
            story.append(text(b[1],{'p':'Body','h':'Head','title':'ReportTitle'}[b[0]])); markdown.append(('# ' if b[0]=='title' else '## ' if b[0]=='h' else '')+b[1]+'\n')
        elif b[0]=='fig':
            story.append(Image(str(AN/'figures'/b[1]),width=500,height=200));story.append(text(b[2],'CaptionSmall'));markdown.append(f'![{b[2]}](../../results/analysis/figures/{b[1]})\n')
        else:
            t=Table([[text(v,'CaptionSmall') for v in row] for row in b[1]],colWidths=[48,125,120,105,105]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e8edf2')),('GRID',(0,0),(-1,-1),.4,colors.HexColor('#d9d9d9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,6),text(b[2],'CaptionSmall')]);markdown.append('\n'.join(' | '.join(row) for row in b[1])+'\n'+b[2]+'\n')
SimpleDocTemplate(str(OUT/'report.pdf'),pagesize=A4,rightMargin=45,leftMargin=45,topMargin=37,bottomMargin=44,title=TITLE,author=AUTHORS).build(story,onFirstPage=footer,onLaterPages=footer)
(OUT/'report.md').write_text('\n'.join(markdown),encoding='utf-8')
(OUT/'abstract.txt').write_text(abstract+'\n',encoding='utf-8')

slides=[
('AI Telephone','Do examples preserve information across repeated summaries?', ['Bilal Amin Dipu and Thejitha','12 fictional reports | Haiku 5.5 via Claude Code','Primary result: +0.20 percentage points; interval includes loss and gain']),
('The experiment','Follow the information back to the original', ['3 prompts: zero, one, or five good/bad example pairs','2 length settings: at most 250 words or uncapped','5 rounds per chain; only preceding output passed forward','360 outputs; Opus judges rounds 1, 3 and 5; no human audit']),
('The primary result','No clear lasting preservation advantage', ['Round five, capped: zero 84.72% | few 84.92%','Paired difference +0.20 pp; 95% interval -8.33 to +8.93','12 paired documents; 10,000 bootstrap resamples']),
('Length changes the comparison','Examples also change compression', ['Uncapped round five: zero 615.58 words | few 210.83','Preservation: zero 97.92% | few 81.60%','Even capped outputs differ: 232.92 vs 179.75 words','A common maximum does not equalize achieved length']),
('What the evidence supports','A small experiment with explicit limits', ['One model and CLI harness; one chain per condition','Synthetic sources and AI-only labels, no human audit','No downstream decision measurement','Next: matched lengths, human validation, direct-summary controls']),
('Inspect and reproduce','Saved evidence and open analysis', ['Sources, examples, generations, and labels in the repository','Recompute tables and figures without making model calls','Read the required limitations and dual-use appendix','github.com/vantablack2443/ai-epistemics-receipts'])]
from reportlab.pdfgen import canvas
c=canvas.Canvas(str(OUT/'slides.pdf'),pagesize=landscape(A4));w,ht=landscape(A4)
for n,(title,sub,bullets) in enumerate(slides,1):
    c.setFillColor(colors.HexColor('#f6f8fa'));c.rect(0,0,w,ht,fill=1,stroke=0);c.setFillColor(colors.HexColor('#111827'))
    c.setFont('Helvetica-Bold',30);c.drawString(48,ht-72,title)
    c.setFont('Helvetica',19);c.drawString(48,ht-115,sub)
    for j,line in enumerate(bullets):
        para=text(line,'Head');para.wrap(w-110,100);para.drawOn(c,55,ht-190-j*61)
    c.setFont('Helvetica',10);c.drawString(48,28,'AI Telephone | AI x Epistemics Research Sprint 2026');c.drawRightString(w-48,28,f'{n} / 6');c.showPage()
c.save()
script='''# Four minute narration script

## Slide 1 0:00–0:35
An engineering handoff can preserve the headline while losing a condition that changes what a reader should do. We asked whether examples of good and bad summaries help preserve information when summaries are repeatedly summarized. Our completed experiment is small: twelve fictional reports and one summarizer, Claude Haiku 5.5 through Claude Code. The main result is that five example pairs gave almost the same final preservation as zero examples under a word cap.

## Slide 2 0:35–1:20
We crossed zero, one, and five good and bad example pairs with two length settings: at most two hundred and fifty words, or no cap. Every condition ran for five rounds. Each later round received only the preceding summary as the task text. That produced three hundred and sixty outputs. Claude Opus evaluated rounds one, three, and five against the original source and its findings and qualifications. The labels distinguish preservation, omission, strengthening, weakening, and contradiction. These are AI judgments without an independent human audit.

## Slide 3 1:20–2:00
Under the cap at round five, zero-shot preservation averaged eighty-four point seven two percent, and few-shot preservation averaged eighty-four point nine two percent. The paired difference was positive zero point two zero percentage points. Its ninety-five percent bootstrap interval ran from negative eight point three three to positive eight point nine three. We resampled documents, not individual labels, because twelve documents are the independent units. The interval includes meaningful loss and gain, so we cannot claim a lasting benefit. An early advantage at round one was not sustained in these chains.

## Slide 4 2:00–2:45
Without a cap, zero-shot summaries retained more information, but were much longer. At round five, zero-shot outputs averaged about six hundred and sixteen words, compared with about two hundred and eleven for five example pairs. Preservation was about ninety-eight versus eighty-two percent. The examples therefore changed compression behavior as well as the prompt content. Even under the common cap, the actual lengths differed. This means we cannot isolate an effect of example content independent of length. Overlength outputs were kept unchanged, rather than regenerated.

## Slide 5 2:45–3:25
Our conclusions are limited to one model, one CLI harness, synthetic reports, and a single chain per condition. Sources and labels were produced with AI assistance. We have not measured human agreement or engineering decisions. A high preservation score is not a deployment approval, and polished summaries could still conceal qualifications. The next experiment should match actual lengths, validate labels with human reviewers, and compare chains with direct summaries of the original source.

## Slide 6 3:25–4:00
The repository contains the sources, selected examples, all saved generations, labels, analysis tables, and figures. The analysis can be rerun without making new model calls. The report documents a validator amendment and includes limitations and dual-use considerations. The takeaway is modest: in this experiment, examples did not give a clear final preservation advantage under a cap. Measure both what information survives and how much text is produced when evaluating repeated AI summaries.
'''
(OUT/'video-script.md').write_text(script,encoding='utf-8')
(OUT/'submission-fields.md').write_text(f'''# Submission form text

Project title: {TITLE}

Project summary:

{abstract}

Suggested team name: AI Telephone

Authors: {AUTHORS}

Contact: biam00002@stud.uni-saarland.de

Affiliation: Saarland University (Bilal Amin Dipu); Thejitha affiliation not supplied.

Suggested track: Track 1 Model Epistemics & Decision-Making Evals

Code: https://github.com/vantablack2443/ai-epistemics-receipts/tree/codex/ai-telephone-analysis/ai-telephone

Report: report.pdf

Slides: slides.pdf

Recording URL: leave blank until a video is recorded and uploaded.

User decisions still required: confirm team name, team location, author spelling and affiliation; provide Thejitha contact details if required by form; select publication preference; review submission terms and final report. No form has been submitted.

Verified organizer deadline: 16 November 2026 at 12:59 Europe/Berlin (11:59 UTC). This package does not assert the deadline is still in the future or that a late submission will be accepted.
''',encoding='utf-8')
(OUT/'README.md').write_text('''# AI Telephone submission package

The report follows the official template section structure, adapted to a compact single-column PDF. It contains four body pages plus references and appendices. Review author details and scientific claims before submission. The project has not been submitted.

Files: report.pdf, editable report.md, abstract.txt, six-page slides.pdf, video-script.md, submission-fields.md, and research-artifacts.zip. Video recording remains deferred.

## Reproduce

From ai-telephone, install the locked Python 3.11 environment with uv sync. Run uv run pytest, then the analyze_cli and figures commands in Appendix B and uv run python report/audit_submission.py. Run report/build_submission.py with the bundled document Python runtime, which supplies reportlab and Pillow. No report-building command makes model calls. For tests on this Windows sandbox, point TEMP and TMP to a writable workspace directory.

The audit JSON records coverage and frozen-file checks. Windows checkout CRLF differs from manifest LF bytes; seven files match after normalization. annotate.py has the documented post-freeze quotation-validator amendment. Human annotation audit is absent. Test fixtures and runtime SQLite databases are excluded from the artifact archive.

## Sources verified on 16 November 2026

Organizer requirements: https://apartresearch.com/sprints/ai-x-epistemics-research-sprint-2026-11-13-to-2026-11-15

Official template text: https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs/edit

References: https://aclanthology.org/2020.acl-main.173/ and https://aclanthology.org/2023.emnlp-main.741/
''',encoding='utf-8')
with zipfile.ZipFile(OUT/'research-artifacts.zip','w',zipfile.ZIP_DEFLATED) as z:
    for folder in ('data/v2','freeze','results/haiku','results/analysis','src','tests'):
        for f in sorted((ROOT/folder).rglob('*')):
            if f.is_file() and '__pycache__' not in f.parts and f.suffix not in ('.sqlite','.pyc'):
                z.write(f,'ai-telephone/'+f.relative_to(ROOT).as_posix())
    for f in (ROOT/'pyproject.toml',ROOT/'uv.lock',ROOT/'report/audit_submission.py',ROOT/'report/build_submission.py'):
        z.write(f,'ai-telephone/'+f.relative_to(ROOT).as_posix())
shutil.copyfile(AN/'figures/trajectory_haiku.png',OUT/'project-image.png')
(OUT/'checksums.json').write_text(json.dumps({f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(OUT.iterdir()) if f.is_file() and f.name not in ('checksums.json','final-submission.zip')},indent=2)+'\n')
with zipfile.ZipFile(OUT/'final-submission.zip','w',zipfile.ZIP_DEFLATED) as z:
    for f in sorted(OUT.iterdir()):
        if f.is_file() and f.name!='final-submission.zip': z.write(f,f.name)
print(f'Built {OUT}; abstract {len(abstract.split())} words')
