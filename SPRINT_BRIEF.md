# AI x Epistemics Research Sprint — Handoff Brief

Prepared by Opus 5.5 for Fable 5.2. Fable: produce research plan + concrete topic, hand back to Opus for execution.
Date of brief: Fri 2026-11-13 (sprint day 1).

## 1. Logistics (hard constraints)

- Organizer: Apart Research (global, online). Local hub: AI Safety Saarland, E1 7 Saarland University, Saarbrücken.
- Window: Fri 13 Nov – Sun 15 Nov 2026. First talk Fri 14:15 UTC.
- **Deadline: Sun 15 Nov 23:59 AoE = Mon 16 Nov 11:59 UTC.** ~2.5 working days total.
- Deliverable: PDF on official template (https://docs.google.com/document/d/17b3JWki-ZkaqdmqGI5d0gof-HwlGuWU9Mc1_klNZXKs/copy). 4–8 pages, 8 hard cap, excluding refs + appendices. Abstract 150–250 words.
- **Required appendix: "Limitations and Dual-Use / Ethical Considerations"** — what result does/doesn't establish, manipulative uses, personal-data handling.
- Optional: public GitHub repo, 3–5 min video demo, slides.
- Teams 1–5. Max 2 projects per person. Resubmit with exact same title to replace.
- AI tools allowed; fabricated results/references = disqualification. Every citation must be real and checked.
- Pre-sprint code must be marked "preexisting" in README + report.
- Projects hidden from website until after judging — double-check submission form fields.
- Note: Apart page showed "submission window has closed" banner when fetched — likely stale; verify live.

## 2. Rubric (same for all tracks, each 1–5)

1. **Impact Potential & Innovation** — 4–5 requires new-to-field work, not replication; clear theory of change.
2. **Execution Quality** — sound method; 5 = ambitious scope rigorously executed, surprising findings or robust validation (variance, baselines).
3. **Presentation & Clarity** — problem, method, findings, limitations all clear. Judges may refuse to score unclear reports.

Implication: small, sharp, *novel* empirical result with baselines + error bars beats big unfinished system. Recommended structure: Intro, Related Work, Method (replicable), Results (variance + baselines), Discussion, Limitations/Dual-Use, References.

## 3. Tracks

1. **Model Epistemics & Decision-Making Evals** — calibration, overselling, flip-flopping under pushback, benchmark gaming/durability.
2. **Trust Infrastructure** — source reliability scoring, provenance (C2PA), tamper-evident agent action logs, citation verification.
3. **Epistemic Products** — decision briefings, dispute de-escalation, crux mapping.
4. **Open Track** — adoption, deployment, impact; more investigative than software.

## 4. Organizer example ideas (do NOT just replicate — judges reward novelty)

- T1: MisleadBench (implied vs defended claims), Confidence Audit (confidence vs later ground truth), FlipRate (warranted update vs capitulation across 1–3 rebuttals), Epistemic virtue suite in Inspect, EU AI Act Art. 5(1)(a) measurement protocol mapping DarkBench/MASK.
- T2: Track-Record Ledger, Tamper-Evident Action Recorder (OpenTelemetry GenAI + signing), Citation Binder (AVeriTeC), Provenance study (C2PA / Community Notes signals).
- T3: Dispute Escalation Benchmark (landlord/employer/ex scenarios, mediator rubric), Decision-Brief Rubric, Crux Mapper.
- T4: Scenario planning sims, fast facilitation, "QALY for epistemics", procurement gap report, "Do their numbers match?" (parliament/press figures vs cited stats), privacy-preserving wish registry.

## 5. Key reading (bold on Apart page = most relevant)

Sprint-wide:
- State of the Field: AI for Epistemics and Coordination (Ben N & Csaky, 2026) — LessWrong uw8RQ8yjKexnhTw6E
- What's Important in "AI for Epistemics"? (Finnveden 2024, Forethought)
- AI Impacts on Epistemics: Good, Bad, Ugly (Cotton-Barratt & Hadshar 2026)
- Design Sketches for a More Sensible World (Forethought 2026)
- Project Ideas: Epistemics (Finnveden substack)
- A Full Epistemic Stack (Sourbut & Goldhaber 2025)

T1: MASK (arXiv 2503.03750), DarkBench (2503.10728), SycEval (2502.08177), ELEPHANT (2505.13995), Why LMs Hallucinate (2509.04664), ForecastBench (2409.19839), Anthropic Petri + Bloom, EU AI Act Art. 5, Design Sketches: Collective Epistemics.
T2: C2PA spec v2.4, Community Notes dataset (github.com/twitter/communitynotes), Birdwatch→Community Notes (2510.09585), AI for AI for Epistemics (Forethought 2026).
T3: Design Sketches: Angels-on-the-Shoulder, Gwern Guardian Angels, OpenAI GPT-4o sycophancy postmortem, Cheng et al. Science 2025 (sycophancy reduces prosocial intent), Tessler et al. Science 2024 (Habermas Machine).
T4: AI Adoption Gap (Vaintrob 2025), AI Tools for Existential Security, Chuai et al. Community Notes rollout (2307.07960), Mandel & Barnes PNAS 2014 forecast accuracy, FutureSearch / Swift Centre / Sentinel.

Tooling: Inspect (UKGovernmentBEIS/inspect_ai), OpenTelemetry GenAI semconv, AVeriTeC dataset.

## 6. People

Speakers: Owen Cotton-Barratt (Forethought/Differential Labs), Jonathan Stray (CHAI, conflict), Joel Suro (OMNA, RAG), Keivan Navaie (Lancaster/MATS), Dean Issacharoff, S. Orestis Palermos (social epistemology), Bargav Jagatha (Adaption).
Judges incl.: Nikos Bosse (FutureSearch), David Manheim, Oliver Klingefjord (Meaning Alignment), Alex Csaky, Kenny Easwaran (formal epistemology), Jess Bergs (UK AISI), Matthew DeVerna (Stanford, misinformation).
Judge mix favors: forecasting/calibration rigor, misinformation measurement, philosophically clean framing.

## 7. Prizes

$1000 / $500 / $300 / $100 / $100. Fast-track Apart Fellowship consideration, mentor intros, LW/AF publication path. Adaption credits for all registrants.

## 8. Opus strategic read (for Fable to challenge)

- Weekend-feasible + high rubric ceiling = **Track 1 eval with a novel twist**: cheap via APIs, quantitative, baselines + variance natural. Risk: crowded (sycophancy/calibration well studied) — novelty must come from a *new measured construct* or *new finding*, not a new dataset of the same thing.
- Promising gaps (unverified, Fable should check against State of the Field):
  - Warranted vs unwarranted updating: pair valid vs bogus rebuttals of equal rhetorical strength; measure discrimination, not just flip rate. Gives a proper-scoring-rule style metric.
  - Calibration of *recommendations* (not facts) where truth resolves later — use already-resolved forecasting questions after model cutoff.
  - Citation faithfulness of deep-research agents: claim-level support rate, cheap on AVeriTeC-like data.
  - "Do their numbers match?" — strong T4 open dataset, low ML need, high public value; judges like DeVerna/Stray.
- Avoid: building infrastructure without evaluation; anything needing human subjects IRB-ish data in 48h; scraping personal data.
- Budget plan: Fri = scope + pilot (n≈30), Sat = full run + analysis, Sun AM = write, Sun PM = polish + appendix + submit with hours of buffer.

## 9. Open questions about the participant (see Section 10 once answered)

Team size/skills, compute/API budget, which models accessible, track preference, ML vs non-ML comfort, hours available, prior code to reuse, goal (win vs learn vs fellowship).

## 10. Participant answers (grill results)

- **Team:** solo (for now). Saarbrücken hub available for in-person co-working.
- **Background:** new to AI safety / epistemics. CS student. Strong in Python, Rust, web frontend.
- **Time:** ~15–20 hours total across Fri–Sun.
- **Goal:** learn + portfolio. Finished, clean piece > risky moonshot.
- **Tracks of interest:** T1 evals, T2 trust infra, T3 epistemic products (not T4).
- **Output type:** participant defers to Fable.
- **Prior work:** none — fresh start, nothing to disclose.
- **Compute:** **$0 budget.** No local GPU. Has Claude Code (subscription, not an API key — cannot be used as an eval target from scripts). Has/can get: **Gemini AI Studio free key**, **OpenRouter free (`:free` models)**. Participant was unclear why model access matters — plan should explain where model calls happen.

### Implications Fable must plan around

1. **Call budget is the binding constraint.** Gemini free tier and OpenRouter `:free` are rate-limited (roughly tens of requests/min, low hundreds–~1000/day depending on model/credits; check current limits). Design must work with ~500–1500 total model calls. Multi-turn designs (e.g. 3 rebuttals) multiply cost — budget per item.
2. Prefer **2–3 target models** (e.g. Gemini Flash + one or two open models via OpenRouter free), small but well-powered n (~50–150 items/condition), bootstrap CIs.
3. Avoid LLM-as-judge where a programmatic grader works (saves calls, more robust). If judge needed, use Gemini free and validate on a hand-labeled subset (~30).
4. Cache every response to disk (JSONL) so reruns cost nothing; free endpoints flake.
5. Rust/web skills make T2 (signed append-only agent log + viewer) or T3 (tool + small eval) viable *without* heavy model calls — Fable should weigh this vs T1.
6. New-to-field: plan should name 3–5 must-read sources (≤2h reading) and a related-work paragraph skeleton so novelty claim is honest.
7. 15–20h solo: Fri ~4h (read + scope + pilot), Sat ~8h (build/run/analyze), Sun ~6h (write + appendix + submit with ≥3h buffer before 23:59 AoE).

### Ask of Fable

Return: (a) 2–3 candidate topics ranked, each with research question, novelty claim vs cited prior work, method, call-budget estimate, risk; (b) one recommended topic with hour-by-hour plan; (c) report outline mapped to the 3 rubric criteria; (d) Limitations/Dual-Use appendix bullet seeds. Opus will then implement.
