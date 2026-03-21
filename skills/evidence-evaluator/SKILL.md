---
name: evidence-evaluator
description: >
  Automated structured evidence evaluation of clinical/biomedical research papers via a
  6-stage agentic pipeline: (0) study type routing, (1) variable + PICO extraction with
  majority-vote confidence, (2) agentic MCID/domain benchmark retrieval, (3) deterministic
  math audit (Fragility Index, NNT, post-hoc power), (4) bias risk assessment (RoB 2.0 /
  QUADAS-2 / GRADE), (5) Evidence Evaluation Report synthesis. Outputs structured JSON +
  plain-language narrative. Optional heuristic 1-5 suggested score via rule engine.
  USE THIS SKILL when the user asks to evaluate, grade, or appraise a clinical paper;
  uploads a paper and wants evidence quality analyzed; asks about statistical robustness
  or bias risk; requests Fragility Index, NNT, post-hoc power, RoB 2.0, QUADAS-2, or
  MCID analysis; asks "is this paper good evidence?"; wants a structured EBM review;
  or asks about PICO extraction or study type classification.
---

# Evidence Evaluator Skill

A 6-stage agentic pipeline that produces a **structured Evidence Evaluation Report** for any clinical or biomedical research paper. Designed to match the reasoning of a trained EBM reviewer.

## Setup

Before running the pipeline, ensure Python dependencies are installed:

```bash
python3 -m pip install scipy statsmodels numpy
```

Verify the pipeline modules load correctly (run from the skill directory):

```bash
cd ${CLAUDE_SKILL_DIR} && python3 -c "from pipeline.stage3_math import run_stage3; from pipeline.stage5_report import compute_suggested_score, assemble_report; print('OK')"
```

**Important:** All Python code in Stages 3 and 5 must be run from the skill directory (`skills/evidence-evaluator/`) so that `from pipeline.stage3_math import ...` resolves correctly. Use `cd ${CLAUDE_SKILL_DIR} &&` before any `python3` commands, or add the skill directory to `sys.path`.

## Quick Start

1. **Receive paper** — PDF upload, pasted abstract/text, DOI, or PMID
2. **Run stages 0–5 sequentially** — each stage feeds the next via a shared `PipelineContext`
3. **Export full report** — save as Markdown file (`evidence_report_[author]_[year]_[pmid].md`)
4. **Reply with brief summary** — score + key findings + path to the exported file

Read the stage references before running each stage:
- `references/stages_0_1.md` — Study type routing + variable extraction
- `references/stages_2_3.md` — MCID search + math audit
- `references/stage_4.md` — Bias risk assessment
- `references/stage_5_report.md` — Report synthesis + scoring
- `references/formulas.md` — All formulas (FI, FQ, NNT, DOR, power)
- `references/eval_framework.md` — Evaluation experiments + acceptance test cases

---

## Pipeline Architecture

```
Input (PDF / text / DOI / PMID)
  → Stage 0: Study Type Pre-Routing
  → Stage 1: Variable Extraction & Initial Grading  [LLM, 3× majority vote]
  → Stage 2: Domain Benchmark & MCID Search          [LLM + web search, agentic]
  → Stage 3: Deterministic Math Audit                [Python / formula walkthrough]
  → Stage 4: Bias Risk Audit                         [LLM]
  → Stage 5: Evidence Evaluation Report Synthesis    [LLM + rule engine]
  → Output: Structured JSON Report + Narrative
```

**Tiered context strategy** — always use abstract + methods + conclusion first (Tier 1). Only escalate to full text if agent signals `needs_full_paper: true`. This covers ~80% of cases at ~20% of token cost.

---

## Stage Execution Order

### Stage 0: Study Type Pre-Routing
Read `references/stages_0_1.md → Stage 0`.

Classify the paper into one of:
`RCT_intervention | diagnostic | preventive | observational | meta_analysis | phase_0_1`

Output a confidence score (0–1). If confidence < 0.7, flag for human review but continue.

**Routing consequences:**
- `phase_0_1` → skip Stage 2 + Stage 3 entirely; lock score range 1–2
- `diagnostic` → Stage 2 uses diagnostic thresholds (not MCID); Stage 3 computes DOR (not FI/NNT); Stage 4 uses QUADAS-2 (not RoB 2.0)
- All others → full pipeline

---

### Stage 1: Variable Extraction & Initial Grading
Read `references/stages_0_1.md → Stage 1`.

**LLM Strategy:** Self-reflection few-shot + 3× CoT majority vote.
Run extraction 3 times independently. Fields where all 3 agree = high confidence. Disagreements → `low_confidence_fields` flag.

Extract: N (intervention/control), events, LTFU count, p-value, effect size + type, CI, blinding, randomization, trial phase, alpha, stated power, primary outcome, PICO.

Assign **Initial Grade (1–5)** based on study design hierarchy. See grade table in `references/stages_0_1.md`.

Special rules: Phase 0/I → auto-lock Grade 2. Retracted paper → Excluded (no score).

---

### Stage 2: Domain Benchmark & MCID Search
Read `references/stages_2_3.md → Stage 2`.

**Skip if:** `study_type = phase_0_1`

Agentic search (up to 5 rounds) using Stage 1's PICO + `pico_search_string`.
Source priority: COMET/OMERACT → PubMed SRs → Society guidelines → Cohen's d proxy (Tier 4, flag with warning).

For diagnostic studies: retrieve AUC/Sn/Sp thresholds instead of MCID.

Evaluate: effect vs. MCID, N vs. domain standard, NNT vs. domain threshold.

**Paper retrieval tips:**
- For DOIs: use CrossRef API (`https://api.crossref.org/works/{doi}`) for metadata.
- For PMIDs: use PubMed E-utilities (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml`) for structured abstracts.
- For MCID searches: use PubMed E-utilities search (`https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={query}&retmax=10`) then fetch results. Do NOT scrape PubMed HTML pages.
- If a journal blocks direct access (403), fall back to PubMed/CrossRef for abstract and metadata. Most evaluations can be completed from abstract + methods data alone (Tier 1).

**MCID selection rules (critical for reproducibility):**
The MCID value directly affects post-hoc power and the effect-vs-MCID comparison. To ensure consistent results across runs:

1. **For binary outcomes, express MCID as ARR (not HR).** HR depends on follow-up duration and baseline hazard, making it ambiguous. ARR is directly computable from the 2×2 table and feeds cleanly into the power formula. If you find a guideline MCID expressed as HR, convert it to ARR using the control group event rate: `ARR = CER × (1 − HR)`.
2. **Document the MCID derivation explicitly.** In the report, state: the MCID value, its unit (ARR/SMD/MD), the source (with citation), the tier, and how it was converted if applicable. This makes the score path auditable.
3. **Always compute post-hoc power using the MCID from Stage 2.** Per the framework: use the MCID as the target effect size, recalculate power with actual sample sizes via `statsmodels.stats.power`. If Power < 0.80 → apply −1 grade. This applies regardless of whether the observed effect exceeds the MCID — the power check evaluates whether the study was *designed* to reliably detect the MCID, which is a separate question from what it actually found.
4. **When Tier 3/4 MCID is used, lock the value to avoid variability.** If no Tier 1/2 MCID exists, search for the most commonly cited guideline threshold for this disease-outcome pair. Prefer explicit numeric thresholds (e.g., "ARR ≥ 3%" or "HR ≤ 0.80") over vague descriptions. If multiple Tier 3 values are found, use the most conservative (smallest ARR). Document the exact source and rationale for the chosen value.

---

### Stage 3: Deterministic Math Audit
Read `references/stages_2_3.md → Stage 3` and `references/formulas.md`.

**Skip if:** `study_type = phase_0_1`
**Diagnostic studies:** compute DOR only (skip FI/NNT)

**Run via Python module** — do NOT compute these by hand. Call `pipeline/stage3_math.py`:

```python
from pipeline.stage3_math import run_stage3

result = run_stage3(
    stage1_output={
        "events_intervention": 386,    # from Stage 1 extraction
        "n_intervention": 2373,
        "events_control": 502,
        "n_control": 2371,
        "p_value": 0.00001,
        "ltfu_count": 21,
        "alpha": 0.05,
        "effect_size_type": "binary",  # or "SMD", "MD", "continuous"
    },
    stage2_output={                     # from Stage 2 (optional)
        "mcid": 0.05,                  # as ARR for binary outcomes
        "domain_n": 1000,              # typical N for this domain
        "domain_nnt_threshold": 50,    # NNT threshold for this domain
    },
    study_type="RCT_intervention",     # from Stage 0
)
# result contains: metrics (FI, FQ, LTFU rule, NNT, power), total_delta
```

For **diagnostic studies**, pass `tp`, `tn`, `fp`, `fn` and `initial_grade` instead:

```python
result = run_stage3(
    stage1_output={"tp": 80, "tn": 70, "fp": 20, "fn": 30, "initial_grade": 3},
    study_type="diagnostic",
)
# result contains: metrics.dor (with CI, interpretation, delta)
```

The output includes full computation traces for every metric. Display these in the report.

---

### Stage 4: Bias Risk & Evidence Certainty Audit
Read `references/stage_4.md`.

Select tool based on study type:
- `RCT_intervention / meta_analysis / preventive` → **RoB 2.0** (5 domains)
- `diagnostic` → **QUADAS-2** (4 domains, capped at −2)
- `observational` → **GRADE upgrading** (3 factors, capped at +1)

Also check: surrogate endpoint (−1), meta-analysis I² > 50% (−1).

For Phase 0/I: run only randomization + selective reporting domains of RoB 2.0.

---

### Stage 5: Evidence Evaluation Report Synthesis
Read `references/stage_5_report.md`.

**Part 1 — Structured Findings + Score:** Run via Python module:

```python
from pipeline.stage5_report import compute_suggested_score, assemble_report

# Optional score (rule engine)
score = compute_suggested_score(
    initial_grade=5,                    # from Stage 1
    stage2_deltas={                     # from Stage 2 (optional)
        "effect_below_mcid": 0,         # -1 if effect < MCID
        "n_below_domain": 0,            # -1 if N < domain standard
        "nnt_exceeds": 0,               # -1 if NNT > threshold
    },
    stage3_output=stage3_result,        # from run_stage3()
    stage4_output={                     # from Stage 4
        "tool": "RoB 2.0",
        "domains": [
            {"domain": "randomization", "judgment": "low", "delta": 0},
            # ... one entry per domain
        ],
        "surrogate_endpoint_delta": 0,
        "heterogeneity_delta": 0,
        "overall_concern": "low",
    },
    study_type="RCT_intervention",
    excluded=False,
)

# Structured plain-text report
report = assemble_report(
    stage0_output={"study_type": "RCT_intervention", "confidence": 0.99},
    stage1_output={...},                # full Stage 1 output
    stage2_output={...},                # full Stage 2 output
    stage3_output=stage3_result,
    stage4_output={...},
    score_result=score,
)
print(report)
```

**Part 2 — Markdown Export (default, MUST be comprehensive):** Always export the full report as a `.md` file using the template in `references/stage_5_report.md → Part 5`. The Markdown file is the primary deliverable and must include ALL of the following:
- All 4 structured sections with full detail
- **Stage 3 computation traces** — show the FI iteration log (inputs, key iterations, final P), NNT computation (CER, IER, ARR breakdown), LTFU-FI comparison, power computation inputs/output, and DOR if applicable. These traces are what make the report auditable.
- **Primary and secondary outcomes table** — include all reported endpoints with event counts, rates, and effect sizes (HR/RR/OR with CI)
- 500–800 word narrative summary (findings only, no verdict)
- Score with full score path and disclaimer
- Save to: `evidence_report_[first_author]_[year]_[pmid].md`

**Do NOT abbreviate the Markdown file.** The full computation traces, outcome tables, and per-domain evidence citations are what distinguish this from a summary — they make every finding auditable and citable.

**Part 3 — Chat summary:** After saving the Markdown file, respond to the user with a **brief summary** (not the full report). Include:
- Paper title and study type
- Score (if enabled) with one-line rationale
- 2–3 key findings (e.g., "FI = 62 (robust)", "NNT = 20 (favorable)", "All RoB 2.0 domains low")
- Any flags or concerns (LTFU > FI, low confidence fields, Tier 4 MCID proxy)
- Path to the exported Markdown file

Do NOT paste the full report into the chat. The Markdown file is the deliverable; the chat message is a summary pointing to it.

---

## Output Format

Default output is plain text (structured sections + narrative). Pass `output_format: markdown` to also receive a fully-rendered `.md` file. See `references/stage_5_report.md → Part 5` for the full markdown template.

```
══════════════════════════════════════════════════════════
EVIDENCE EVALUATION REPORT
══════════════════════════════════════════════════════════
Paper: [title] | [journal] | [year]
Study type: [type] · Routing confidence: [X]%
══════════════════════════════════════════════════════════

SECTION 1 — STUDY DESIGN & POPULATION
  [PICO summary, N, phase, blinding, randomization]

SECTION 2 — STATISTICAL ROBUSTNESS
  Fragility Index (FI): [value]  [robust | fragile | extreme_fragile]
  Fragility Quotient (FQ): [value]  [below 0.01 threshold: yes/no]
  Post-hoc Power: [value]%  [≥ 0.80: yes/no]
  LTFU vs FI: LTFU=[X], FI=[Y]  [safe | ⚠ LTFU > FI — attrition concern]
  NNT: [value]  (domain threshold: [value])  [favorable | exceeds threshold]

SECTION 3 — CLINICAL BENCHMARKING
  MCID: [value] [units]  (source: [COMET | PubMed SR | Guidelines | Cohen proxy])
  Observed effect: [value]  vs. MCID: [exceeds | below | borderline]
  MCID source tier: [1–4]

SECTION 4 — BIAS RISK ASSESSMENT
  Tool: [RoB 2.0 | QUADAS-2 | GRADE]
  [Per-domain findings]
  Surrogate endpoint: [yes | no]
  Overall concern: [low | some_concerns | high | critical]

══════════════════════════════════════════════════════════
NARRATIVE SUMMARY
[500–800 words — findings, not verdict]
══════════════════════════════════════════════════════════

[OPTIONAL] SUGGESTED SCORE: [1–5] [★★★★☆]
  ⓘ Heuristic score — design choices pending expert calibration
══════════════════════════════════════════════════════════
```

---

## De-duplication Rules (apply in Stage 5)

1. **Statistical stability dimension:** Among {post-hoc power < 0.8, N < domain standard, NNT > threshold} → apply only the most severe deduction. Suppress others.
2. **Case-control spectrum bias (diagnostic):** Stage 2 case-control deduction vs. QUADAS-2 patient selection domain → apply only once.
3. **QUADAS-2 cap:** Max −2 total across all QUADAS-2 domains.
4. **GRADE upgrade cap:** Max +1 total regardless of how many factors are met.
5. **LTFU-FI hard rule:** −2 grade, highest priority. Not deduplicated with any other rule.

---

## Running Evaluations

To run the full PRD validation suite, see `references/eval_framework.md`.

Acceptance test cases (T1–T8) are defined there with expected outputs and pass criteria.

Validation experiments (3A–3F) follow the same file.

---

## Key Design Principles

- **Not a black-box classifier.** Every finding is auditable and citable.
- **Report is the contribution; score is optional.** The 1–5 score is a heuristic pending expert calibration — never present it as validated.
- **Findings only, no verdict.** The narrative summary surfaces what was found; the clinician judges what it means.
- **Tiered reading saves tokens.** Always Tier 1 first; only escalate on `needs_full_paper` signal.
- **LTFU > FI is the hardest rule.** −2 grade, not negotiable, not deduplicated.
