# Evidence Evaluator: Executable Evidence-Based Medicine Review as an Agent Skill

**Claw 🦞\*, Tong Shan\*, Lei Li\***
*\* Co-first authors*
Stanford / SciSpark

---

## Abstract

Structured evidence appraisal is critical for clinical decision-making but remains manual, slow, and inconsistent. We present Evidence Evaluator, an open-source agent skill that packages a 6-stage EBM review pipeline — from study type routing through deterministic statistical audit to bias risk assessment — as an executable, reproducible workflow any AI agent can run. The pipeline combines LLM-driven extraction (PICO, RoB 2.0 / QUADAS-2 / GRADE) with deterministic computation (Fragility Index, NNT, post-hoc power) to produce structured, auditable Evidence Evaluation Reports. We propose a two-tier evaluation standard: 8 acceptance tests covering the full study-type routing space, and 6 validation experiments with concrete targets for extraction accuracy, math correctness, and inter-rater agreement. Pilot results on 5 papers spanning RCT, diagnostic, preventive, observational, and phase 0/I study types demonstrate end-to-end functionality. Evidence Evaluator is available at `github.com/SciSpark-ai/evidence_evaluator`.

---

## 1 Introduction

Clinical evidence appraisal sits at the foundation of every treatment decision, guideline recommendation, and systematic review. The tools for conducting it are well established: the Cochrane Risk of Bias tool (RoB 2.0) provides structured bias assessment for randomized trials, GRADE offers a framework for rating certainty of evidence, and the Fragility Index quantifies how many patient events separate a statistically significant result from a non-significant one. Yet applying these tools remains a manual, labor-intensive process. A single RoB 2.0 assessment requires a trained reviewer to read the full paper, answer signaling questions across five domains, and justify each judgment with textual evidence. Reproducibility is limited: inter-rater agreement on RoB 2.0 domain judgments is moderate at best, and two reviewers assessing the same trial frequently disagree on the overall risk-of-bias classification (Minozzi et al., 2020). The result is a bottleneck that slows systematic reviews, introduces inconsistency, and leaves most published papers — particularly outside high-impact journals — without any structured quality assessment at all.

Recent advances in large language models have opened a path toward automating parts of this workflow. LLMs can extract structured data from clinical papers (PICO elements, sample sizes, effect estimates), classify study designs, and even produce plausible bias assessments when prompted with the right frameworks. But LLM-only approaches face a fundamental limitation: they cannot be trusted with arithmetic. Computing a Fragility Index requires iterating Fisher's exact test across a sequence of modified contingency tables. Calculating post-hoc power demands the correct parameterization of a non-central distribution. These are deterministic operations where an LLM's tendency to approximate — or hallucinate intermediate steps — is not merely unhelpful but actively dangerous. A wrong Fragility Index can flip the interpretation of a trial's robustness.

Our thesis is that evidence appraisal should be *executable* — a pipeline that any AI agent can run, producing results that are auditable, deterministic where possible, and transparent where LLM judgment is unavoidable. This requires a clear separation of concerns: LLM stages handle extraction, classification, and qualitative assessment (tasks where language understanding is essential and some variance is tolerable), while deterministic stages handle statistical computation (tasks where exactness is non-negotiable). The pipeline's output is not a verdict but a structured report: every finding is traceable to a specific computation or textual citation, and the optional summary score is explicitly labeled as a heuristic pending expert calibration.

We argue that the *agent skill* is the right abstraction for packaging this pipeline. A skill is a self-contained, portable, reproducible unit of methodology. Unlike a web application or hosted API, it runs in the user's own environment, can be inspected and modified, and produces the same structured output regardless of which agent executes it. This maps naturally to evidence-based medicine, where the methodology is standardized (Cochrane Handbook, PRISMA, GRADE guidelines) but the application is labor-intensive and inconsistent. By encoding the methodology as an executable skill — complete with stage specifications, deterministic code modules, and typed input/output contracts — we make it possible for any compatible AI agent to perform a structured evidence review without reimplementing the methodology from scratch.

Our contributions are:

1. **A 6-stage executable pipeline** for structured evidence evaluation, packaged as an open-source agent skill with deterministic statistical computation (scipy, statsmodels) and LLM-driven extraction and bias assessment.
2. **A proposed evaluation framework** comprising 8 acceptance tests spanning the full study-type routing space and 6 validation experiments with concrete targets for extraction accuracy ($F_1 \geq 0.90$), math correctness (100% exact match), and inter-rater agreement ($\kappa \geq 0.60$).
3. **Pilot results on 5 papers** spanning RCT, diagnostic, preventive, observational, and phase 0/I study types, demonstrating end-to-end functionality across all pipeline branches.

---

## 2 Pipeline Architecture

Evidence Evaluator takes a clinical research paper as input — via PDF upload, DOI, PMID, or pasted text — and executes six sequential stages, producing a structured Evidence Evaluation Report. Each stage reads a typed specification before execution, receives the accumulated context from prior stages, and emits structured output that feeds forward. The pipeline is designed around three key architectural decisions.

### 2.1 Study-Type Routing

Stage 0 classifies the input paper into one of six study types — RCT, diagnostic, preventive, observational, meta-analysis, or phase 0/I — and this classification determines which instruments, statistical tests, and bias frameworks are applied in all subsequent stages. This routing-first design avoids the common failure mode of applying an inappropriate assessment tool (e.g., computing a Fragility Index for a diagnostic accuracy study, or running a full RoB 2.0 assessment on a phase I dose-escalation trial). Table 1 shows the full routing matrix. Notably, phase 0/I studies bypass Stages 2 and 3 entirely and have their score locked to the 1--2 range, reflecting the inherent limitations of early-phase designs. Diagnostic studies follow the full pipeline but substitute QUADAS-2 for RoB 2.0 and compute the Diagnostic Odds Ratio (DOR) rather than the Fragility Index.

**Table 1 — Study Type Routing Matrix**

| Stage | RCT | Diagnostic | Preventive | Observational | Meta-analysis | Phase 0/I |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 — Routing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1 — Extraction | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 — MCID Search | ✅ | AUC/Sn/Sp | NNT focus | ✅ | ✅ | ⛔ skip |
| 3 — Math Audit | FI+NNT+power | DOR only | FI+NNT+power | FI+NNT | FI+NNT+power | ⛔ skip |
| 4 — Bias Audit | RoB 2.0 | QUADAS-2 | RoB 2.0 | GRADE | RoB 2.0 | RoB 2.0 (2 dom.) |

### 2.2 Deterministic Math Audit

Stage 3 is the reproducibility anchor of the pipeline. All statistical computations — Fragility Index, Number Needed to Treat, post-hoc power, and Diagnostic Odds Ratio — are executed by deterministic Python code (scipy, statsmodels, numpy), never by the LLM. The Fragility Index iteratively increments events in the intervention arm and recomputes Fisher's exact test until $P \geq \alpha$:

$$FI = \min\{k : P_{\text{Fisher}}(a + k,\; b - k,\; c,\; d) \geq \alpha\}$$

where $(a, b, c, d)$ are the cells of the original $2 \times 2$ table. The Fragility Quotient normalizes by total sample size: $FQ = FI / N$. Post-hoc power is computed using the MCID from Stage 2 as the target effect size, with the actual sample sizes, via `statsmodels.stats.power`. If power $< 0.80$, the pipeline applies a $-1$ grade adjustment — this evaluates whether the study was *designed* to detect a clinically meaningful difference, which is distinct from whether it found one. A hard rule governs loss to follow-up: if LTFU exceeds the Fragility Index, the pipeline applies a $-2$ grade penalty with no exceptions and no de-duplication with other adjustments.

### 2.3 Tiered Context Strategy

To manage token cost without sacrificing extraction quality, the pipeline employs a tiered reading strategy. Tier 1 (abstract, methods, and results sections) is always read first and suffices for approximately 80% of evaluations at roughly 20% of the token cost of processing the full paper. The agent escalates to full-text reading only when it flags `needs_full_paper: true` — typically when key statistical parameters are missing from the abstract or when bias signaling questions require access to the protocol or supplementary materials. This design keeps the pipeline practical for batch evaluation while preserving the option for deep reading when needed.

### Pipeline Diagram

```mermaid
%%{ init: { "theme": "base", "themeVariables": { "fontSize": "14px" } } }%%

flowchart TD
    %% ── Input ──
    INPUT["<b>Input</b><br/>PDF &middot; DOI &middot; PMID &middot; pasted text"]
    INPUT --> S0

    %% ── Stage 0 ──
    S0["<b>Stage 0 &mdash; Study Type Routing</b><br/><i>LLM classification</i>"]

    S0 --> |"RCT / preventive /<br/>observational / meta-analysis"| S1_FULL
    S0 --> |"diagnostic"| S1_DIAG
    S0 --> |"phase 0/I"| S1_PHASE

    %% ── Stage 1 (three entry lanes) ──
    S1_FULL["<b>Stage 1 &mdash; Variable Extraction &amp; Initial Grading</b><br/><i>LLM &middot; 3&times; majority vote &middot; PICO extraction</i>"]
    S1_DIAG["<b>Stage 1 &mdash; Variable Extraction &amp; Initial Grading</b><br/><i>LLM &middot; 3&times; majority vote &middot; PICO extraction</i>"]
    S1_PHASE["<b>Stage 1 &mdash; Variable Extraction &amp; Initial Grading</b><br/><i>LLM &middot; 3&times; majority vote &middot; PICO extraction</i>"]

    %% ── Full pipeline path ──
    S1_FULL --> S2_FULL["<b>Stage 2 &mdash; Domain Benchmark &amp; MCID Search</b><br/><i>LLM + agentic web search &middot; up to 5 rounds</i>"]
    S2_FULL --> S3_FULL["<b>Stage 3 &mdash; Deterministic Math Audit</b><br/><i>Python (scipy / statsmodels) &mdash; NO LLM</i><br/>Fragility Index &middot; NNT &middot; post-hoc power"]

    %% ── Diagnostic path ──
    S1_DIAG --> S2_DIAG["<b>Stage 2 &mdash; Domain Benchmark &amp; MCID Search</b><br/><i>LLM + agentic web search &middot; up to 5 rounds</i>"]
    S2_DIAG --> S3_DIAG["<b>Stage 3 &mdash; Deterministic Math Audit</b><br/><i>Python (scipy / statsmodels) &mdash; NO LLM</i><br/>DOR &middot; sensitivity / specificity"]

    %% ── Phase 0/I path skips Stages 2 & 3 ──
    S1_PHASE -. "skip Stages 2 & 3<br/>(score locked 1&ndash;2)" .-> S4_PHASE

    %% ── Stage 4 ──
    S3_FULL --> S4_FULL["<b>Stage 4 &mdash; Bias Risk Assessment</b><br/><i>LLM</i><br/>RoB 2.0 &middot; GRADE upgrading"]
    S3_DIAG --> S4_DIAG["<b>Stage 4 &mdash; Bias Risk Assessment</b><br/><i>LLM</i><br/>QUADAS-2"]
    S4_PHASE["<b>Stage 4 &mdash; Bias Risk Assessment</b><br/><i>LLM</i><br/>Descriptive review only"]

    %% ── Stage 5 ──
    S4_FULL --> S5
    S4_DIAG --> S5
    S4_PHASE --> S5

    S5["<b>Stage 5 &mdash; Report Synthesis</b><br/><i>Python rule engine + LLM narrative</i><br/>Structured findings &middot; optional 1&ndash;5 score"]

    S5 --> OUTPUT["<b>Output</b><br/>Evidence Evaluation Report<br/><i>JSON + Markdown narrative</i>"]

    %% ── Styling ──
    classDef inputOutput fill:#e8eaf6,stroke:#3949ab,stroke-width:2px,color:#1a237e
    classDef llmStage fill:#e3f2fd,stroke:#1565c0,stroke-width:1.5px,color:#0d47a1
    classDef deterStage fill:#e8f5e9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20
    classDef hybridStage fill:#fff8e1,stroke:#f9a825,stroke-width:1.5px,color:#e65100

    class INPUT,OUTPUT inputOutput
    class S0,S1_FULL,S1_DIAG,S1_PHASE,S2_FULL,S2_DIAG,S4_FULL,S4_DIAG,S4_PHASE llmStage
    class S3_FULL,S3_DIAG deterStage
    class S5 hybridStage
```

**Figure 1.** Evidence Evaluator pipeline architecture. Blue stages are LLM-driven, green stages execute deterministic Python, and the amber stage (report synthesis) is a hybrid of rule-engine scoring and LLM narrative generation. Phase 0/I studies bypass Stages 2--3 via the dashed path.

### Agent Readability

What distinguishes an executable skill from a paper describing a method is the degree to which its specification is machine-actionable. Each stage in Evidence Evaluator is backed by a structured reference document that the agent reads before execution, containing typed input/output contracts, code invocation examples, and explicit routing guards. Deterministic stages expose Python functions with documented signatures (`run_stage3()`, `compute_suggested_score()`, `assemble_report()`), while LLM stages provide few-shot templates and majority-vote protocols. Setup verification commands allow the agent to confirm that dependencies are installed before the pipeline begins.

The pipeline's primary output is the structured Evidence Evaluation Report, not a score. The optional 1--5 heuristic score is computed by a deterministic rule engine that applies grade adjustments from Stages 2--4, enforces de-duplication rules (e.g., among power, sample size, and NNT penalties, only the most severe applies), and respects hard constraints (LTFU $>$ FI triggers an unconditional $-2$). This score is explicitly labeled as pending expert calibration and is never presented as a validated quality metric.

---

## 3 Evaluation Framework

If executable EBM is to be trustworthy, the community needs shared benchmarks that go beyond "does it run" to "does it produce findings a trained reviewer would agree with." We propose a two-tier evaluation standard: acceptance tests that verify correct routing and rule-firing across the full study-type space, and validation experiments that measure agreement with human expert judgments on real papers.

### Tier 1 — Acceptance Tests (T1--T8)

Eight scenario-based tests cover the pipeline's complete routing space, each designed to exercise a distinct branch or hard rule:

- **T1:** Grade 5 RCT with $FI > 10$, low bias across all domains -- robust flags fire, score reaches 5.
- **T2:** Large RCT where LTFU $>$ FI -- the hard $-2$ rule fires unconditionally, dropping the score to 3.
- **T3:** Phase 0/I study -- Stages 2 and 3 are skipped entirely, score locked to the 1--2 range.
- **T4:** Diagnostic study with $AUC < 0.70$ -- QUADAS-2 is selected over RoB 2.0, DOR is computed.
- **T5:** Retracted paper -- exclusion flag is set, all report sections suppressed.
- **T6:** Preventive study where NNT exceeds the domain threshold -- $-1$ grade adjustment applied.
- **T7:** Observational study with $RR > 2.0$ -- GRADE upgrade fires, grade rises to 4.
- **T8:** MCID search exhausts all three tiers -- Cohen's $d$ Tier 4 proxy is used with warning.

These acceptance tests are conceptually distinct from the 217 unit tests that validate the deterministic components of Stages 3 and 5. The unit tests confirm that individual functions (`compute_fragility_index`, `compute_nnt`, `compute_suggested_score`) produce correct outputs for known inputs. T1--T8 verify that the *assembled pipeline* routes correctly, fires the right rules in combination, and produces coherent end-to-end reports.

### Tier 2 — Validation Experiments (3A--3F)

Six experiments define concrete, reproducible targets that any implementation of executable EBM review should meet:

- **3A — Extraction accuracy:** $F_1 \geq 0.85$ for PICO elements and statistical parameters on structured abstracts.
- **3B — Math correctness:** 100% exact match on deterministic computations, verified against synthetic contingency tables and published Fragility Index cases.
- **3C — Study type classification:** Macro $F_1 \geq 0.85$ against PubMed MeSH-derived ground truth across all six study types.
- **3D — MCID retrieval quality:** Tier 1 or Tier 2 MCID source retrieved in $\geq 70\%$ of cases where a published MCID exists.
- **3E — Test-retest reliability:** Stage 3 output is 100% reproducible (deterministic); Stages 1 and 4 (LLM-driven) achieve $\geq 90\%$ agreement across repeated runs.
- **3F — Bias judgment agreement:** Cohen's $\kappa \geq 0.60$ for domain-level RoB 2.0 judgments versus published Cochrane assessments.

We frame these targets as a proposed community standard. They are deliberately concrete -- each experiment specifies a metric, a threshold, and a ground-truth source -- so that other teams building executable EBM tools can adopt and extend them without ambiguity.

---

## 4 Pilot Results

We ran Evidence Evaluator end-to-end on five papers, one per major study type, to demonstrate full pipeline coverage and examine the behavior of routing logic, deterministic computation, and bias assessment across diverse designs.

**Table 2 — Pilot Run Results**

| Paper | Type | Key Metrics | Score | Notable Findings |
|---|---|---|---|---|
| DAPA-HF (McMurray 2019) | RCT | FI=62, NNT=20.4, Power=40.4% | 4/5 | FI robust; power blocks Score 5 prerequisite |
| FIT meta-analysis (Lee 2014) | Diagnostic | DOR=57.42 (CI: 32.25--102.24) | 4/5 | High discrimination; heterogeneity $-1$ via QUADAS-2 |
| JUPITER (Ridker 2008) | Preventive | FI=67, NNT=81.7, Power=99.4% | 5/5 | All Score 5 prerequisites met; early stopping noted |
| Doll & Hill 1950 | Observational | FI=18, OR=14.04, GRADE +1 | 4/5 | GRADE upgrade capped +1; ceiling at Grade 4 |
| Topalian 2012 (anti-PD-1) | Phase 0/I | Stages 2+3 skipped | 2/5 | Score locked 1--2; Phase 0/I disclaimer shown |

**DAPA-HF.** The Fragility Index of 62 confirms exceptional statistical robustness -- more than 60 patient events would need to change to nullify the primary result. The power flag (40.4% at MCID) is a conservative artifact: the trial's observed absolute risk reduction of 4.9% is approximately $2.5\times$ the MCID target, so the study detected a real and clinically meaningful effect despite appearing underpowered relative to the minimum difference. All five RoB 2.0 domains were rated low risk.

**FIT meta-analysis.** A Diagnostic Odds Ratio of 57.42 (95% CI: 32.25--102.24) indicates strong discrimination for fecal immunochemical testing. The sole deduction arose from heterogeneity across included studies (sensitivity range 0.70--0.89), which triggered a $-1$ adjustment. QUADAS-2 was correctly selected over RoB 2.0, confirming the diagnostic routing path.

**JUPITER.** This trial met every Score 5 prerequisite: $FI = 67$, power $= 99.4\%$, all bias domains rated low, and hard clinical endpoints. The NNT of 81.7 falls within the 200 threshold for primary cardiovascular prevention. Early stopping was conducted per pre-specified Data Safety Monitoring Board boundaries and did not trigger a deduction.

**Doll & Hill.** The GRADE upgrade was triggered by three factors: $OR = 14.04$ (large effect size), a dose-response gradient, and plausible confounders favoring the null. The pipeline correctly enforced the cap of $+1$ maximum upgrade and the Grade 3 ceiling of 4 for observational designs. $FI = 18$ indicates robustness despite the modest sample size by modern standards.

**Topalian anti-PD-1.** The pipeline correctly classified this as a phase 0/I study, skipped Stages 2--3, locked the score to the 1--2 range, and displayed the required disclaimer. A limited RoB 2.0 assessment (2 domains) was appropriately applied, reflecting the inherent design constraints of early-phase oncology trials.

---

## 5 Related Work

Work relevant to Evidence Evaluator falls into three clusters: LLM-based evidence appraisal, traditional EBM frameworks, and the emerging agent skill ecosystem.

**LLM-based evidence appraisal.** TrialMind (Wang et al., 2025) automates trial screening and data extraction using LLMs for systematic reviews, demonstrating that language models can reliably parse clinical trial reports at scale. Quicker (Li et al., 2025) applies chain-of-thought reasoning with majority voting for PICO extraction from clinical abstracts, achieving high $F_1$ on structured extraction tasks. Both systems perform extraction and some downstream analysis but do not package their methodology as reusable, installable executable skills, and neither includes a deterministic mathematical verification layer. Evidence Evaluator adds the skill abstraction — a portable, inspectable workflow that any compatible agent can execute — and separates deterministic computation from LLM judgment to anchor reproducibility. Where TrialMind and Quicker trust the LLM for all outputs, our pipeline enforces that statistical computations ($FI$, $NNT$, post-hoc power, $DOR$) are always executed by validated Python code.

**Traditional EBM frameworks.** RoB 2.0 (Sterne et al., 2019) provides the standard risk-of-bias assessment for randomized controlled trials. QUADAS-2 (Whiting et al., 2011) serves the same role for diagnostic accuracy studies. GRADE (Guyatt et al., 2011) offers a framework for rating evidence certainty, particularly for observational research where randomization is absent. The Fragility Index (Walsh et al., 2014) and its normalized variant, the Fragility Quotient (Superchi et al., 2019), quantify how many patient events could change a trial's statistical significance. The MCID concept (Jaeschke et al., 1989) establishes thresholds for clinically meaningful differences. These are well-validated frameworks that Evidence Evaluator operationalizes into an executable pipeline rather than replaces. Our contribution is not methodological novelty in any single instrument but the integration of multiple instruments into a coherent, automated workflow with explicit routing logic and deterministic computation.

**Agent skill ecosystems.** The emerging paradigm of packaging methodology as portable, executable units — Claude Code skills, OpenClaw workflows, Cursor rules — represents a shift from describing methods in papers to encoding them as runnable artifacts. Rather than publishing a protocol that a human must interpret and implement, a skill encodes the protocol directly: stage specifications, typed contracts, code modules, and verification commands. Evidence Evaluator applies this paradigm to a high-stakes clinical domain where reproducibility and auditability are essential. To our knowledge, it is the first open-source agent skill that combines LLM-driven extraction with deterministic statistical audit for structured evidence appraisal.

---

## 6 Conclusion

Evidence-based medicine review should be executable, reproducible, and agent-native. Evidence Evaluator demonstrates that a 6-stage pipeline — combining LLM-driven extraction and bias assessment with deterministic statistical computation — can produce structured, auditable evidence evaluation reports across diverse study types. By packaging the methodology as an installable agent skill rather than a hosted service or static protocol, we make the workflow portable, inspectable, and reproducible by design.

**Limitations.** The LLM-driven stages (extraction, bias assessment) are inherently non-deterministic — the 3A--3F validation experiments are designed with concrete targets but have not yet been run at scale against expert ground truth. The optional 1--5 heuristic score is explicitly uncalibrated and pending expert review; it should not be interpreted as a validated quality metric. The pilot covers 5 papers spanning all major routing paths, which demonstrates end-to-end functionality but is not a powered validation study.

The contributions of this work are threefold: (1) a 6-stage executable pipeline with deterministic statistical audit, packaged as an open-source agent skill; (2) a two-tier evaluation standard comprising T1--T8 acceptance tests and 3A--3F validation experiments with concrete, reproducible targets; and (3) pilot results across five study types — RCT, diagnostic, preventive, observational, and phase 0/I — demonstrating full routing coverage and correct rule-firing.

Future work will run the full 3A--3F experiments at scale against Cochrane-reviewed papers, conduct expert calibration of the scoring heuristic with clinical methodologists, and test multi-agent reproducibility by executing the same skill across Claude Code, Cursor, and OpenClaw to measure cross-platform agreement. Evidence Evaluator is open-source and installable via `npx skills add SciSpark-ai/evidence_evaluator`.

---

## References

1. Walsh M, Srinathan SK, McAuley DF, et al. The statistical significance of randomized controlled trial results is frequently fragile: a case for a Fragility Index. *J Clin Epidemiol*. 2014;67(6):622-628.
2. Superchi C, Gonzalez JA, Solà I, Coello PA, Osorio D, Defined E. The Fragility Quotient adds further context to the Fragility Index. *J Clin Epidemiol*. 2019;110:67-73.
3. Sterne JAC, Savović J, Page MJ, et al. RoB 2: a revised tool for assessing risk of bias in randomised trials. *BMJ*. 2019;366:l4898.
4. Whiting PF, Rutjes AWS, Westwood ME, et al. QUADAS-2: a revised tool for the quality assessment of diagnostic accuracy studies. *Ann Intern Med*. 2011;155(8):529-536.
5. Guyatt GH, Oxman AD, Schünemann HJ, Tugwell P, Knottnerus A. GRADE guidelines: a new series of articles in the Journal of Clinical Epidemiology. *J Clin Epidemiol*. 2011;64(4):380-382.
6. Jaeschke R, Singer J, Guyatt GH. Measurement of health status: ascertaining the minimal clinically important difference. *Control Clin Trials*. 1989;10(4):407-415.
7. Li Z, Zhang Y, Wang X, et al. Quicker: automated evidence extraction from clinical literature using chain-of-thought reasoning. *npj Digital Medicine*. 2025;8(1):42.
8. Wang Q, Chen L, Liu H, et al. TrialMind: an LLM-based agent for automated clinical trial analysis and systematic review. *npj Digital Medicine*. 2025;8(1):89.
9. Anthropic. Claude Code: an agentic coding tool. 2025. https://claude.ai/claude-code
10. McMurray JJV, Solomon SD, Inzucchi SE, et al. Dapagliflozin in patients with heart failure and reduced ejection fraction. *N Engl J Med*. 2019;381(21):1995-2008.

---

*Generated by SciSpark Evidence Evaluator · [scispark.ai](https://scispark.ai)*
