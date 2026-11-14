# Draft annotation guide

Compare every output with the original, including later rounds. Each source has one principal finding and three critical qualifications or action conditions. Assess each independently.

- **Preserved:** the same meaning survives, including a valid paraphrase.
- **Omitted:** the information disappears without an explicit incompatible replacement.
- **Strengthened:** certainty, scope, or readiness exceeds the source.
- **Weakened:** the output makes a claim less definite than the source warrants.
- **Contradicted:** the output states an incompatible claim.

Record unsupported new claims separately. For each non-preserved item record a supporting output quotation where possible and a short rationale; omissions may have no corresponding output quotation. “May reduce latency” to “reduces latency” is strengthened; “deploy after the load test passes” to “ready to deploy” is strengthened; removing deployment discussion is omitted. Omitting the main finding is a loss of usefulness. Record disagreements before adjudication and preserve both original labels. This rubric needs reviewer practice and review before freeze.

## AI annotation with human audit (team decision, 2026-11-14)

Primary labels are **AI annotations**, not human annotations, and must be reported as such. The annotator is `claude-opus-5-5`, which is not one of the summarizing models, run through Claude Code with tools disabled and effort `high` (`src/ai_telephone/annotate.py`). Its prompt (`src/ai_telephone/annotator_prompt.py`) contains this rubric and five fictional worked examples outside the study's scenarios: three chains that keep the source's information and two that lose it, together covering all five labels and unsupported claims. The annotator sees only the original source, the ground-truth items with their intended meanings, and one summary. It never sees the condition, round, model, or other labels; structured formatting (condition C) remains visible. Every label is validated: one label per item, verbatim summary quotations, a rationale for every label. Invalid output stops the run for inspection and is never silently relabelled.

Human validation: `annotate audit --model {terra,haiku}` exports a blinded, shuffled sample (default 60 summaries, balanced across rounds and the direct control) without model, condition, round, or AI labels. Team members label it independently using this guide. `annotate agree` then reports human–AI percent agreement and Cohen's kappa, both five-way and preserved-versus-not, with a confusion table. Report these figures with the results, and treat low agreement as a limitation of the AI labels, not as grounds for changing them after seeing outcomes.

Commands:

    uv run python -m ai_telephone.annotate label --model haiku
    uv run python -m ai_telephone.annotate audit --model haiku --n 60
    uv run python -m ai_telephone.annotate agree --model haiku
