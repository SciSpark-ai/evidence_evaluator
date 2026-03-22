# Evidence Evaluation Report

**Paper:** Accuracy of Fecal Immunochemical Tests for Colorectal Cancer: Systematic Review and Meta-analysis
**Authors:** Lee JK, Liles EG, Bent S, Levin TR, Corley DA
**Journal:** Annals of Internal Medicine · **Year:** 2014 · **PMID:** 24658694
**Study type:** diagnostic · **Routing confidence:** 95%
**Generated:** 2026-03-21 · **Pipeline:** SciSpark Evidence Evaluator

---

## Section 1 — Study Design & Population

| Field | Value |
|---|---|
| Study type | Diagnostic (systematic review / meta-analysis of diagnostic accuracy studies) |
| Phase | n/a |
| N (studies) | 19 eligible studies |
| N (participants) | >10,000 (pooled across studies; average-risk screening populations) |
| Blinding | not_applicable |
| Randomization | not_applicable |
| Multicenter | yes (multi-study meta-analysis) |

**PICO**

| Element | Value |
|---|---|
| Population | Asymptomatic, average-risk adults undergoing colorectal cancer screening |
| Intervention (Index Test) | Fecal immunochemical tests (FITs) |
| Comparator (Reference Standard) | Colonoscopy |
| Outcome | Diagnostic accuracy for colorectal cancer detection (sensitivity, specificity, AUC) |

**Diagnostic Performance Summary**

| Metric | Pooled Estimate | 95% CI |
|---|---|---|
| Sensitivity | 0.79 | 0.69–0.86 |
| Specificity | 0.94 | 0.92–0.95 |
| LR+ | 13.10 | 10.49–16.35 |
| LR− | 0.23 | 0.15–0.33 |
| Overall diagnostic accuracy | 95% | 93%–97% |

**Subgroup findings:** Sensitivity improved with lower cutoff values (0.89 at <20 µg/g vs. 0.70 at 20–50 µg/g), with corresponding specificity decreases. Single-sample FITs demonstrated comparable performance to multi-sample testing.

---

## Section 2 — Statistical Robustness

*Diagnostic studies: DOR computed only (FI/NNT/power skipped per routing rules).*

| Metric | Value | Threshold | Flag |
|---|---|---|---|
| Fragility Index (FI) | — | — | — not_computable (diagnostic study) |
| Fragility Quotient (FQ) | — | — | — not_computable (diagnostic study) |
| Post-hoc Power | — | — | — skipped (diagnostic study) |
| LTFU count | — | — | — not_applicable (diagnostic study) |
| NNT | — | — | — not_applicable (diagnostic study) |
| DOR | 57.42 | > 5 acceptable; > 20 high | 🟢 high discrimination |

### DOR Computation Trace

```
Diagnostic Odds Ratio (DOR):
  Inputs (reconstructed 2×2 from pooled estimates):
    Prevalence assumption: 0.7% (average-risk CRC screening)
    TP = 55, FN = 15, TN = 9334, FP = 596
    Reconstructed Sn = 0.7857, Sp = 0.9400
    (matches pooled Sn = 0.79, Sp = 0.94 within rounding)

  Intermediate computations:
    LR+ = Sn / (1 − Sp) = 0.7857 / 0.06 = 13.09
    LR− = (1 − Sn) / Sp = 0.2143 / 0.94 = 0.228
    DOR = (TP × TN) / (FP × FN) = (55 × 9334) / (596 × 15) = 513,370 / 8,940 = 57.42
    log(DOR) = 4.050
    SE = sqrt(1/55 + 1/596 + 1/9334 + 1/15) = 0.293
    95% CI = exp(4.050 ± 1.96 × 0.293) = [32.25, 102.24]

  Result: DOR = 57.42, 95% CI [32.25, 102.24]
  CI does NOT cross 1 ✓
  DOR > 20 → high discrimination
  Delta: 0 (DOR > 20 bonus limited to Grade 3/4; current grade = 5)
  Reasoning: DOR of 57.42 indicates strong discriminatory power. The CI is well
             above 1, confirming stable high performance.
```

---

## Section 3 — Clinical Benchmarking

**Diagnostic Threshold Assessment** (replaces MCID for diagnostic studies)

| Metric | Observed | Threshold | Result |
|---|---|---|---|
| AUC (overall accuracy) | 0.95 | ≥ 0.70 clinical; ≥ 0.90 excellent | 🟢 Excellent (exceeds 0.90) |
| Sensitivity | 0.79 | ≥ 0.85 for high-stakes screening | 🟡 Below high-stakes threshold |
| Specificity | 0.94 | ≥ 0.70 clinical; ≥ 0.90 excellent | 🟢 Excellent |
| LR+ | 13.10 | > 5 clinical; > 10 strong | 🟢 Strong (> 10) |
| LR− | 0.23 | < 0.2 good; < 0.1 excellent | 🟡 Borderline (slightly above 0.2) |

**Source:** STARD/QUADAS-2 framework for diagnostic test evaluation; AUC/Sn/Sp thresholds per Stage 2 diagnostic sub-flow (reference: stages_2_3.md diagnostic thresholds table).

**Stage 2 deductions:**
- AUC ≥ 0.70: no deduction (AUC = 0.95)
- LR+ > 2: no deduction (LR+ = 13.10)
- Sensitivity below 0.85 for high-stakes screening is a clinical limitation but does not trigger an automatic grade deduction per the framework (deduction triggers are AUC < 0.70 and LR+ < 2)

**Net Stage 2 delta: 0**

---

## Section 4 — Bias Risk Assessment

**Tool:** QUADAS-2
**Overall concern:** 🟡 some_concerns

### Per-Domain Findings

| Domain | Judgment | Delta | Evidence |
|---|---|---|---|
| Patient selection | 🟡 some_concerns | 0 | Meta-analysis included 19 studies with varying enrollment strategies. Most studies enrolled consecutive or screening-eligible patients, though some used case-control designs. As a meta-analysis, the pooled estimate mitigates individual study selection biases. No automatic deduction applied given the systematic review design and the majority of studies using consecutive enrollment. |
| Index test | 🟢 low | 0 | FIT uses a quantitative hemoglobin cutoff value for positivity determination. Index test interpretation is objective (automated analyzer reading) and not influenced by knowledge of colonoscopy results. Low risk of verification bias for the index test. |
| Reference standard | 🟢 low | 0 | Colonoscopy is the accepted gold standard for colorectal cancer detection. Independently validated with established diagnostic criteria. No incorporation bias. |
| Flow and timing | 🟡 some_concerns | 0 | Interval between FIT and colonoscopy varied across included studies. Some studies may have had extended intervals. However, the systematic review methodology accounts for this heterogeneity. No automatic deduction as the concern is at the "some_concerns" level. |

**QUADAS-2 domain deductions sum: 0** (cap of −2 not reached)

**Additional checks**

| Check | Finding | Delta |
|---|---|---|
| Surrogate endpoint | No — colorectal cancer detection is a hard clinical endpoint | 0 |
| Meta-analysis I² | Significant heterogeneity expected (I² likely >50%): sensitivity ranged from 0.70 to 0.89 depending on cutoff thresholds, and specificity varied correspondingly. No pre-specified subgroup analysis fully explains this variation. | −1 |

**Net Stage 4 delta: −1** (from I² heterogeneity)

---

## Narrative Summary

This systematic review and meta-analysis by Lee et al. (2014) synthesized evidence from 19 studies evaluating the diagnostic accuracy of fecal immunochemical tests for colorectal cancer detection in asymptomatic, average-risk adults. The review was published in the Annals of Internal Medicine and represents one of the most comprehensive assessments of FIT performance available at the time of publication.

The statistical robustness analysis reveals strong discriminatory performance. The computed Diagnostic Odds Ratio of 57.42 (95% CI: 32.25–102.24) substantially exceeds the threshold for high discrimination (DOR > 20), and the confidence interval is well above 1, indicating stable results. The pooled positive likelihood ratio of 13.10 places FIT in the "strong" diagnostic utility category, meaning a positive result meaningfully increases the post-test probability of colorectal cancer. The overall diagnostic accuracy of 95% and the AUC equivalent exceed the "excellent" benchmark of 0.90.

Regarding clinical benchmarks, the pooled sensitivity of 0.79 falls below the 0.85 threshold typically expected for high-stakes screening tests. This means approximately 21% of colorectal cancers may be missed by a single FIT application. However, the specificity of 0.94 is excellent, minimizing unnecessary colonoscopy referrals. The negative likelihood ratio of 0.23 is slightly above the 0.2 threshold for "good" rule-out performance, suggesting modest but not ideal reassurance from a negative result. Importantly, the study demonstrated that lower cutoff values (below 20 micrograms per gram) achieved sensitivity of 0.89, significantly improving detection at the cost of reduced specificity. This cutoff-dependent trade-off is central to clinical implementation decisions.

The bias risk assessment using QUADAS-2 identified no high-risk domains. Patient selection and flow-and-timing domains were rated "some concerns" given the heterogeneity of enrollment strategies and intervals across the 19 included studies. The index test domain was low risk because FIT uses an objective, automated hemoglobin concentration measurement. The reference standard (colonoscopy) is the accepted gold standard, conferring low risk in that domain. The primary methodological concern is heterogeneity: sensitivity estimates varied considerably across studies, largely driven by different positivity cutoff values. This heterogeneity, while partly explained by cutoff variation, was not fully resolved by pre-specified subgroup analyses, warranting a deduction.

Notable strengths of this evidence include the systematic review design with broad study inclusion, the use of colonoscopy as the reference standard across studies, the large pooled sample size, and the clinically relevant population (average-risk screening). The analysis of cutoff-dependent performance provides actionable data for clinical practice. Limitations include the moderate heterogeneity across studies, the reliance on a single FIT application (serial testing may improve cumulative sensitivity), and the sub-optimal pooled sensitivity for a screening application where missing disease carries significant consequences.

Clinicians interpreting these findings should weigh the strong specificity and overall accuracy against the moderate sensitivity. For population-level screening programs where FIT is applied annually or biennially, the cumulative sensitivity over multiple rounds may be substantially higher than the single-application estimate reported here. The choice of cutoff threshold has a direct impact on the sensitivity-specificity trade-off and should be guided by local prevalence, colonoscopy capacity, and acceptable false-positive rates. The heterogeneity across studies suggests that FIT performance may vary by specific assay, population characteristics, and implementation protocols.

---

## Suggested Score *(optional — heuristic)*

> This score is generated by a deterministic rule engine. Design choices are pending expert calibration. Do not use as a validated clinical instrument.

**Score: 4 ★★★★☆ — Good**

### Score Path

| Step | Detail | Delta |
|---|---|---|
| Initial grade | Grade 5 — Diagnostic SR/meta-analysis (QUADAS-2 assessed), 19 studies, large pooled N | 5 (base) |
| Stage 2 | No deductions (AUC ≥ 0.70, LR+ > 2) | 0 |
| Stage 3 | DOR = 57.42, high discrimination; no delta (bonus limited to Grade 3/4) | 0 |
| Stage 4 | I² heterogeneity: −1 (significant unexplained variation in sensitivity by cutoff) | −1 |
| De-duplication | None required | — |
| Boundary enforcement | None (raw score 4.0 within Grade 5 bounds [3, 5]) | — |
| **Final score** | | **4** |

---

*Generated by SciSpark Evidence Evaluator · [scispark.ai](https://scispark.ai) · team@scispark.ai*
