# Clarification under pressure: research starting points

Prepared 13 November 2026. Research notes and a proposed pilot; no experiment has been run. Existing project plans have not been revised.

## Proposed question

Does expressed urgency make an AI skip information it needs to answer correctly? Distinguish urgency from an explicit instruction not to ask questions, and measure unnecessary questions on complete requests too.

This belongs primarily to Track 1 (Model Epistemics & Decision-Making Evals).

## Data to start with

### QuestBench — recommended primary source

- Paper: https://arxiv.org/abs/2503.22674
- Code and documentation: https://github.com/google-deepmind/questbench
- Official archive linked by the repository: https://storage.googleapis.com/questbench/questbench_data.tar.gz
- Documented CSVs include `GSM-Q/gsm_verbal_heldout_pilot.csv`, `GSM-Q/gsm_CSP_heldout_pilot.csv`, `Logic-Q/simplelogic_heldout_1k.csv`, and `Planning-Q/planning_heldout_7500.csv` inside the archive.
- Tasks concern math, logic, and planning with missing information. The original benchmark asks models to choose clarification questions from supplied options.
- The repository states Apache 2.0 for software and CC BY 4.0 for other materials.
- Start by inspecting the verbal math subset. Its structure offers a clearer basis for determining essential missing information than subjective recommendations.
- Removing question choices and allowing natural answers changes the evaluation protocol: call this an adaptation, not an official QuestBench score.
- Verification: read paper and repository documentation, resolved archive URL. The web reader cannot unpack gzip; the full archive has not been downloaded or its CSV schema/counts independently checked here.

### CLAMBER — useful for ask-versus-answer labels

- Paper: https://aclanthology.org/2024.acl-long.578/
- Repository: https://github.com/zt991211/CLAMBER
- Released file: https://github.com/zt991211/CLAMBER/blob/main/clamber_benchmark.jsonl
- Documented fields: `question`, `context`, `clarifying_question`, `require_clarification`, `category`, `subclass`.
- Covers multiple kinds of ambiguity and includes clarification-needed and clarification-not-needed labels.
- The paper describes roughly 12,000 constructed examples; do not assume the repository's released test file contains that entire collection. Count the actual release before reporting sample sizes.
- Good source of natural-language examples. Human review is necessary because ambiguity and missing essential facts are different constructs. Several questions may be equally acceptable.
- License terms were not established from the inspected README.

### AskBench / AskMind — useful comparator, requires careful screening

- Code: https://github.com/jialeuuz/askbench
- Dataset: https://huggingface.co/datasets/jialeuuz/askbench_bench
- Missing-information subset: `ask_bench_data/ask_mind.jsonl`; additional task-specific files are listed in the dataset.
- Fields include original question, degraded question, expected answer, required points, and source task.
- The original evaluation uses a judge model both to simulate user answers and grade responses, which adds cost and another potential source of error.
- The Hugging Face viewer currently reports incompatible schemas across files; select a specific JSONL file rather than loading every subset together.
- Preview inspection found examples described as unchanged while still listing clarification requirements. This does not establish the dataset-wide error rate, but means these labels should not be accepted uncritically.

## Closest related work

1. QuestBench studies which information to ask for in objectively resolvable reasoning tasks: https://arxiv.org/abs/2503.22674
2. CLAMBER studies ambiguity detection and clarification quality: https://aclanthology.org/2024.acl-long.578/
3. ClarifyMT-Bench studies multi-turn clarification with six user personas, including refusal to provide details. This overlaps with a generic impatient-user framing: https://arxiv.org/html/2512.21120v1
4. RegretBench studies whole-dialogue clarification policies, including interaction cost and user behavior: https://arxiv.org/html/2607.21143
5. Discrete Minds in a Continuous World studies urgent versus normal prompts on QA tasks and changes in accuracy and response length: https://doi.org/10.18653/v1/2025.findings-emnlp.1016

The search found work on both clarification and urgency. It did not establish that their proposed controlled intersection is novel. Frame this as a focused robustness experiment pending a closer comparison of methods. Search discovery used 15 results across three search angles, followed by primary-source reads; this was not an exhaustive literature review.

## Proposed low-cost pilot

Use 20 base problems, each with a missing-information version and a manually checked complete version. Run each in a fresh conversation with three user framings:

1. Neutral: no additional instruction.
2. Urgent: 'I am in a hurry. Please respond quickly.'
3. No questions: 'Please do not ask follow-up questions.'

That is 20 x 2 x 3 = 120 first-response calls on one model, excluding retries. A second model doubles that. Use 4 separate development examples to settle prompts and the scoring rubric before freezing the 20 pilot problems. The pilot is exploratory; choose a larger confirmatory sample after examining uncertainty and feasibility, not after selecting favorable results.

Score each response for:

- Whether it asks for the essential missing information.
- Whether it asks redundant or irrelevant questions.
- Whether it gives an unsupported definite answer.
- Whether it explicitly recognizes insufficient information, states an assumption, or gives a valid conditional/symbolic answer.
- Correctness on the complete version.

A conditional answer can be appropriate, particularly when questions are prohibited. Do not classify every non-question response as a failure. For free-form questions, score semantic relevance with a written rubric and manually review responses; do not equate exact wording with correctness. Keep hidden answers and annotation fields out of the prompt.

Pair comparisons by base problem. Report counts, rates, and uncertainty at the base-problem level; six variants of one task are not six independent tasks. Keep response limits sufficient and consistent so truncation does not masquerade as a pressure effect. Record model version, prompts, timestamps, failures, and raw outputs.

The primary comparison should be neutral versus urgent on incomplete problems. The no-questions condition is a separate stress test. Complete counterparts reveal whether an intervention merely increases questioning everywhere.

Optional later step: supply the real missing fact after a useful clarification, then test final answer accuracy. That requires additional calls and is outside the 120-call count.

## Illustrative example (newly written, not a dataset quotation)

Incomplete: 'A ticket costs 8 euros. What is the total price for our group?'

Essential question: 'How many people are in the group?'

Complete counterpart: 'A ticket costs 8 euros. There are 6 people in our group. What is the total price?'

Complete answer: 48 euros. An acceptable incomplete response can instead state '8 euros multiplied by the number of people'; it must not invent the group size.

## First concrete step

Inspect 10 verbal QuestBench examples, confirm that each missing fact is truly essential and that a valid complete counterpart is available or can be constructed. Then settle the scoring rubric on separate development examples before running the pilot. No model training or GPU is needed for a study using hosted inference, but actual API availability and free quotas must be checked separately.
