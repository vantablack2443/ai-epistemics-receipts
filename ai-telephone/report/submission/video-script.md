# Four minute narration script

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
