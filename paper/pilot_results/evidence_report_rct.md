# Evidence Evaluation Report

**Paper:** Dapagliflozin in Patients with Heart Failure and Reduced Ejection Fraction
**Authors:** McMurray JJV, Solomon SD, Inzucchi SE, Kober L, Kosiborod MN, Martinez FA, Ponikowski P, Sabatine MS, et al.
**Journal:** New England Journal of Medicine · **Year:** 2019 · **DOI:** 10.1056/NEJMoa1911303
**PMID:** 31535829
**Study type:** RCT_intervention · **Routing confidence:** 99%
**Generated:** 2026-03-23 · **Pipeline:** SciSpark Evidence Evaluator

---

## Section 1 — Study Design & Population

| Field | Value |
|---|---|
| Study type | RCT_intervention |
| Phase | III |
| N (intervention) | 2,373 |
| N (control) | 2,371 |
| N (total) | 4,744 |
| Blinding | double_blind |
| Randomization | randomized (central IVRS/IWRS, stratified by diabetes status) |
| Multicenter | yes (410 sites, 20 countries) |
| Median follow-up | 18.2 months |
| Funding | AstraZeneca |

**PICO**

| Element | Value |
|---|---|
| Population | Adults with heart failure and reduced ejection fraction (LVEF ≤ 40%), NYHA class II–IV, with or without type 2 diabetes, on stable guideline-directed medical therapy |
| Intervention | Dapagliflozin 10 mg once daily |
| Comparator | Matching placebo |
| Outcome | Composite of worsening heart failure (hospitalization or urgent visit requiring IV therapy) or cardiovascular death, median follow-up 18.2 months |

### Primary and Secondary Outcomes

| Endpoint | Dapagliflozin (n=2,373) | Placebo (n=2,371) | HR (95% CI) | P-value |
|---|---|---|---|---|
| **Primary composite** (worsening HF or CV death) | 386 (16.3%) | 502 (21.2%) | 0.74 (0.65–0.85) | <0.001 |
| Worsening heart failure | 237 (10.0%) | 326 (13.7%) | 0.70 (0.59–0.83) | — |
| Cardiovascular death | 227 (9.6%) | 273 (11.5%) | 0.82 (0.69–0.98) | — |
| All-cause mortality | 276 (11.6%) | 329 (13.9%) | 0.83 (0.71–0.97) | — |

---

## Section 2 — Statistical Robustness

| Metric | Value | Threshold | Flag |
|---|---|---|---|
| Fragility Index (FI) | 62 | ≤ 2 = extreme fragile; > 10 = robust | 🟢 robust |
| Fragility Quotient (FQ) | 0.0131 | < 0.01 | 🟢 above threshold |
| Post-hoc Power | 93.9% | ≥ 80% | 🟢 adequate (at MCID = ARR 4%) |
| LTFU count | 14 | Must be ≤ FI | 🟢 safe (LTFU 14 ≤ FI 62) |
| NNT | 20.4 | Domain threshold: 50 (CV secondary prevention) | 🟢 favorable |

### Computation Traces

**Fragility Index (FI):**
```
Inputs: events_i=386, events_c=502, n_i=2373, n_c=2371, initial_p<0.00001
Iteration log (selected):
  Flip  1: events_i=387  → Fisher P=0.000019
  Flip 10: events_i=396  → Fisher P=0.000085
  Flip 20: events_i=406  → Fisher P=0.000393
  Flip 30: events_i=416  → Fisher P=0.001569
  Flip 40: events_i=426  → Fisher P=0.005401
  Flip 50: events_i=436  → Fisher P=0.016128
  Flip 55: events_i=441  → Fisher P=0.026475
  Flip 60: events_i=446  → Fisher P=0.042038
  Flip 61: events_i=447  → Fisher P=0.045931
  Flip 62: events_i=448  → Fisher P=0.050119 ✓ (crossed 0.05)
FI = 62 → ROBUST (FI > 10)
Delta: +0.5 grade
Reasoning: 62 outcome events in the intervention arm would need to switch
  before P crosses the 0.05 threshold. This result is highly robust to
  individual outcome perturbation.
```

**NNT Computation:**
```
CER = 502 / 2371 = 0.2117 (21.17%)
IER = 386 / 2373 = 0.1627 (16.27%)
ARR = CER − IER = 0.2117 − 0.1627 = 0.0491 (4.91%)
NNT = 1 / ARR = 1 / 0.0491 = 20.4
Direction: benefit
Domain threshold (CV secondary prevention, high-risk): 50
NNT (20.4) ≤ 50: FAVORABLE
Delta: 0
Interpretation: For every ~20 patients treated with dapagliflozin for the
  median 18.2 months, one additional patient avoids worsening HF or CV death.
```

**LTFU-FI Comparison:**
```
LTFU = 14 (estimated from 99.7% vital status ascertainment: ~14/4,744 unknown)
FI = 62
LTFU (14) ≤ FI (62): SAFE — attrition does not threaten significance.
Hard attrition rule NOT triggered.
Delta: 0
```

**Post-hoc Power:**
```
MCID (from Stage 2): ARR = 0.04 (4%)
Method: Binary — proportion_effectsize() → NormalIndPower().solve_power()
  p1 (control rate) = 0.2117
  p2 (p1 − MCID) = 0.2117 − 0.04 = 0.1717
  Cohen's h = 0.1017
  n1 = 2373, ratio = 2371/2373 = 0.999, alpha = 0.05
Power = 93.87% → ADEQUATE (≥ 80%)
Delta: 0
Reasoning: The study had >93% power to detect the MCID of ARR=4%, confirming
  it was well-designed to reliably detect clinically meaningful differences.
```

**Fragility Quotient (FQ):**
```
FQ = FI / N_total = 62 / 4744 = 0.0131
Threshold: < 0.01 triggers −0.5
FQ (0.0131) ≥ 0.01: ACCEPTABLE
Delta: 0
```

**De-duplication (Statistical Stability Dimension):**
```
Candidates: none — all metrics passed thresholds.
No deductions to de-duplicate.
```

---

## Section 3 — Clinical Benchmarking

| Field | Value |
|---|---|
| MCID | 0.04 (ARR, 4%) |
| Source | ESC/FDA HF trial design convention — HR ≤ 0.80 converted to ARR using CER |
| Source tier | Tier 3 (major specialty guideline convention) |
| Observed effect | ARR = 4.91% (HR 0.74, 95% CI 0.65–0.85) |
| Effect vs. MCID | 🟢 exceeds (observed ARR 4.91% > MCID 4.0%) |

### MCID Derivation

**Tier search sequence:**
1. **Tier 1 (COMET/OMERACT):** No registered MCID exists for HF composite endpoints (CV death + HF hospitalization). Not available.
2. **Tier 2 (dedicated MCID systematic review):** No published anchor-based or distribution-based MCID study for this composite outcome. Not available.
3. **Tier 3 (major specialty guideline convention):** The ESC/AHA heart failure trial design literature and FDA regulatory guidance consistently use HR ≤ 0.80 (20% relative risk reduction) as the threshold for powering Phase III heart failure outcome trials. This convention was used in PARADIGM-HF (powered for HR 0.80), EMPEROR-Reduced (powered for HR 0.80), and DAPA-HF itself (powered for HR 0.80 at 90% power).

**Conversion to ARR:**
```
HR threshold = 0.80  →  RRR = 1 − 0.80 = 0.20
CER (from Stage 1) = 502 / 2371 = 0.2117
ARR = CER × RRR = 0.2117 × 0.20 = 0.0423
Rounded conservatively: MCID = 0.04 (ARR 4%)
```

**Consistency check:** This 4% ARR threshold aligns with observed effects in prior landmark HF trials: PARADIGM-HF (ARR 4.7%), EMPEROR-Reduced (ARR 3.5%). The DAPA-HF observed ARR of 4.91% exceeds this benchmark.

**MCID locked per selection rule 4.**

**Domain N standard:** 4,000 patients. The DAPA-HF trial enrolled 4,744, exceeding the domain standard. No deduction for sample size.

**NNT vs. domain threshold:** NNT 20.4 is well within the acceptable range for cardiovascular secondary prevention (10–50). No deduction.

---

## Section 4 — Bias Risk Assessment

**Tool:** RoB 2.0
**Overall concern:** 🟢 low

### Per-Domain Findings

**Domain 1 — Randomization process:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Was the allocation sequence random? | Yes | Computer-generated via central IVRS/IWRS system |
| Q2: Was the allocation sequence concealed until enrollment? | Yes | Central randomization system with stratification by diabetes status; matching placebo maintained concealment |

Balanced baseline characteristics across arms confirm successful randomization.

**Domain 2 — Deviations from intended interventions:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Were participants aware of their assigned intervention? | No | Double-blind; drug and placebo identical in appearance |
| Q2: Were there significant crossovers or co-interventions? | No | No significant crossover or co-intervention imbalances reported |
| Q3: Was the analysis intention-to-treat? | Yes | ITT analysis with all randomized patients |

**Domain 3 — Missing outcome data:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Were outcome data available for ≥ 95% of randomized participants? | Yes | Vital status ascertained for 99.7% of patients (~14/4,744 unknown) |
| Q2: Was there differential missingness between arms (> 5% difference)? | No | No differential missingness between arms |
| Q3: Was an appropriate method used for missing data? | Yes | ITT analysis with all randomized patients included |

**Domain 4 — Measurement of outcome:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Was the outcome objective or subjective? | Objective | Hard clinical endpoints: hospitalization, urgent IV therapy visit, cardiovascular death. Adjudicated events by blinded committee → classify as OBJECTIVE |
| Q2: Were outcome assessors blinded? | Yes | Independent blinded clinical events committee adjudication |

**Domain 5 — Selection of reported results:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Was the trial pre-registered? | Yes | ClinicalTrials.gov NCT03036124 |
| Q2: Does the published primary endpoint match the registration? | Yes | Primary composite endpoint matches registration |
| Q3: Are all pre-specified secondary endpoints reported? | Yes | Statistical analysis plan finalized before database lock; all endpoints reported |

**Additional checks**

| Check | Finding | Delta |
|---|---|---|
| Surrogate endpoint | 🟢 No — hard clinical composite (worsening HF hospitalization/urgent visit + CV death). Classification: **hard endpoint** | 0 |
| Meta-analysis I² | n/a (single trial) | 0 |

---

## Narrative Summary

The DAPA-HF trial (McMurray et al., NEJM 2019) is a large, multinational, Phase III, double-blind, placebo-controlled randomized trial evaluating dapagliflozin 10 mg daily versus placebo in 4,744 patients with heart failure and reduced ejection fraction (NYHA class II–IV, LVEF ≤ 40%), regardless of diabetes status. The trial was conducted across 410 sites in 20 countries with a median follow-up of 18.2 months, sponsored by AstraZeneca.

The primary composite endpoint of worsening heart failure or cardiovascular death occurred in 386 of 2,373 patients (16.3%) in the dapagliflozin group versus 502 of 2,371 patients (21.2%) in the placebo group, yielding a hazard ratio of 0.74 (95% CI 0.65–0.85, P < 0.001). Both components of the composite endpoint individually favored dapagliflozin: worsening heart failure (HR 0.70, 95% CI 0.59–0.83) and cardiovascular death (HR 0.82, 95% CI 0.69–0.98). All-cause mortality was also lower in the dapagliflozin group (HR 0.83, 95% CI 0.71–0.97). The benefit was consistent across prespecified subgroups, including patients with and without type 2 diabetes, broadening the generalizability of these findings beyond prior SGLT2 inhibitor trials.

From a statistical robustness perspective, this trial demonstrates exceptional stability. The Fragility Index of 62 indicates that 62 outcome events in the dapagliflozin arm would need to be reclassified before the primary result would lose statistical significance — placing DAPA-HF among the most statistically robust cardiovascular trials in the literature. The Fragility Quotient of 0.0131 exceeds the 0.01 concern threshold, confirming that the high FI is not merely an artifact of the large sample size. The LTFU-to-FI comparison is strongly favorable: approximately 14 patients had unknown vital status (derived from 99.7% vital status ascertainment), far below the FI of 62, meaning that even in the worst-case scenario where every missing patient experienced an adverse outcome in the dapagliflozin arm, the finding would remain significant.

The MCID derivation follows the framework's tiered hierarchy. No Tier 1 (COMET/OMERACT) or Tier 2 (dedicated MCID study) value exists for HF composite endpoints. The Tier 3 value is derived from the ESC/FDA heart failure trial design convention, where HR ≤ 0.80 (20% relative risk reduction) is the standard powering threshold for Phase III HF outcome trials. Converting to an absolute risk reduction using the observed control event rate: ARR = CER x RRR = 0.2117 x 0.20 = 0.0423, conservatively rounded to 0.04 (4%). This same convention underpinned the design of PARADIGM-HF and EMPEROR-Reduced. Post-hoc power analysis confirms that the study had 93.9% power to detect this MCID — well above the 80% adequacy threshold — indicating the trial was reliably designed to detect clinically meaningful differences.

Clinically, the observed absolute risk reduction of 4.91% exceeds the MCID benchmark of 4.0%, confirming that the treatment effect is not only statistically significant but also clinically meaningful. The NNT of approximately 20 over the median 18.2-month follow-up falls well within the acceptable range for cardiovascular secondary prevention in high-risk populations (domain threshold: 10–50). For every 20 patients with HFrEF treated with dapagliflozin for approximately 18 months, one additional patient would avoid a worsening heart failure event or cardiovascular death compared to placebo.

Bias risk assessment using the RoB 2.0 framework reveals low risk across all five domains. The trial employed rigorous allocation concealment via central IVRS/IWRS, maintained double-blinding with matching placebo, achieved near-complete follow-up (99.7% vital status ascertainment), used blinded adjudication for objective clinical endpoints, and adhered to its pre-registered analysis plan. The primary outcome uses hard clinical endpoints, avoiding surrogate endpoint concerns.

Key strengths include the large multinational sample, inclusion of patients both with and without diabetes, use of hard clinical endpoints, rigorous blinding and adjudication, and consistency of results across subgroups and individual composite components. The trial was funded by AstraZeneca, which should be considered when interpreting results, though the methodological rigor and independent event adjudication mitigate potential influence. Clinicians should weigh these findings in the context of individual patient characteristics, comorbidities, and the evolving landscape of heart failure therapeutics.

---

## Suggested Score *(optional — heuristic)*

> This score is generated by a deterministic rule engine. Design choices are pending expert calibration. Do not use as a validated clinical instrument.

**Score: 5 ★★★★★ — Excellent**

### Score Path

| Step | Detail | Delta |
|---|---|---|
| Initial grade | Grade 5 — Large multicenter double-blind RCT, Phase III, N > 1,000 | 5 (base) |
| Stage 2 | Effect exceeds MCID; N exceeds domain standard; NNT within threshold | 0 |
| Stage 3 | FI = 62 (robust, +0.5); FQ above threshold (0); LTFU safe (0); Power 93.9% adequate (0); NNT favorable (0) | +0.5 |
| Stage 4 | All RoB 2.0 domains low; no surrogate endpoint; no heterogeneity concern | 0 |
| De-duplication | No competing deductions to de-duplicate | — |
| Boundary enforcement | Ceiling 5 applied (raw 5.5 capped to 5) | −0.5 |
| **Final score** | | **5** |

---

*Generated by SciSpark Evidence Evaluator · [scispark.ai](https://scispark.ai) · team@scispark.ai*
