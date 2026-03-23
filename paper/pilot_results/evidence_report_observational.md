# Evidence Evaluation Report

**Paper:** Smoking and Carcinoma of the Lung: Preliminary Report
**Authors:** Doll R, Hill AB
**Journal:** British Medical Journal · **Year:** 1950 · **DOI:** 10.1136/bmj.2.4682.739
**PMID:** 14772469
**Study type:** observational · **Routing confidence:** 98%
**Generated:** 2026-03-23 · **Pipeline:** SciSpark Evidence Evaluator

---

## Section 1 — Study Design & Population

| Field | Value |
|---|---|
| Study type | observational (case-control) |
| Phase | n/a |
| N (cases) | 649 |
| N (controls) | 649 |
| Blinding | not_applicable |
| Randomization | not_randomized |
| Multicenter | yes (20 London hospitals) |

**PICO**

| Element | Value |
|---|---|
| Population | Patients aged 25+ admitted to 20 London hospitals; 649 with histologically confirmed lung carcinoma and 649 age/sex-matched controls with other diagnoses |
| Intervention | Tobacco smoking exposure (self-reported smoking history via standardized almoner interview) |
| Comparator | Non-smokers |
| Outcome | Diagnosis of carcinoma of the lung |

---

## Section 2 — Statistical Robustness

| Metric | Value | Threshold | Flag |
|---|---|---|---|
| Fragility Index (FI) | 18 | ≤ 2 = extreme fragile; > 10 = robust | 🟢 robust |
| Fragility Quotient (FQ) | 0.0139 | < 0.01 | 🟢 above threshold |
| Post-hoc Power | — | ≥ 80% | — skipped (observational study) |
| LTFU count | 0 | Must be ≤ FI | 🟢 safe (LTFU 0 ≤ FI 18) |
| NNT | 25.96 | Domain threshold: 100 | 🟢 favorable |

### Computation Traces

**Fragility Index (FI):**
```
Inputs: events_cases=647, events_controls=622, n_cases=649, n_controls=649, initial_p=1.28e-06
Note: For case-control FI, the arm with fewer exposure events (controls) is incremented
      toward the case rate to assess how many flips erase significance.
Iteration 1:  events_ctrl=623 → Fisher P=0.000002
Iteration 2:  events_ctrl=624 → Fisher P=0.000005
Iteration 3:  events_ctrl=625 → Fisher P=0.000009
Iteration 4:  events_ctrl=626 → Fisher P=0.000016
Iteration 5:  events_ctrl=627 → Fisher P=0.000031
Iteration 6:  events_ctrl=628 → Fisher P=0.000058
Iteration 7:  events_ctrl=629 → Fisher P=0.000107
Iteration 8:  events_ctrl=630 → Fisher P=0.000199
Iteration 9:  events_ctrl=631 → Fisher P=0.000366
Iteration 10: events_ctrl=632 → Fisher P=0.000670
Iteration 11: events_ctrl=633 → Fisher P=0.001221
Iteration 12: events_ctrl=634 → Fisher P=0.002209
Iteration 13: events_ctrl=635 → Fisher P=0.003967
Iteration 14: events_ctrl=636 → Fisher P=0.007068
Iteration 15: events_ctrl=637 → Fisher P=0.012481
Iteration 16: events_ctrl=638 → Fisher P=0.021819
Iteration 17: events_ctrl=639 → Fisher P=0.037708
Iteration 18: events_ctrl=640 → Fisher P=0.064313 ✓ (crossed 0.05)
FI = 18 → ROBUST (FI > 10)
Delta: +0.5 grade
Reasoning: 18 outcome event changes required to render the result non-significant.
```

**LTFU-FI Attrition Rule:**
```
LTFU = 0, FI = 18 → LTFU (0) ≤ FI (18): safe. No attrition threat.
Delta: 0
```

**Fragility Quotient (FQ):**
```
FQ = 18 / 1298 = 0.0139 (≥ 0.01): acceptable.
Delta: 0
```

**NNT:**
```
CER (cases smoking rate) = 647/649 = 0.9969
IER (controls smoking rate) = 622/649 = 0.9584
ARR = CER − IER = 0.0385
NNT = 1 / 0.0385 = 25.96 (benefit direction)
Domain threshold: 100 → NNT (25.96) ≤ 100: favorable.
Delta: 0

Note: NNT interpretation in case-control studies is approximate. The 3.85% absolute
difference in smoking prevalence between cases and controls reflects exposure contrast,
not a treatment effect. OR = 14.04 is the primary effect measure.
```

**Post-hoc Power:** Skipped — not computed for observational studies per pipeline routing.

---

## Section 3 — Clinical Benchmarking

| Field | Value |
|---|---|
| MCID | OR > 2.0 (GRADE large-effect benchmark) |
| Source | GRADE framework — large effect upgrade criterion |
| Source tier | Tier 3 (major specialty guidelines) |
| Observed effect | OR = 14.04 |
| Effect vs. MCID | 🟢 exceeds (OR 14.04 >> 2.0) |

The GRADE framework specifies that observational studies may be upgraded when effect sizes are large (RR > 2.0 or equivalent OR threshold). The observed odds ratio of 14.04 vastly exceeds this benchmark, representing one of the strongest epidemiological associations in the medical literature.

---

## Section 4 — Bias Risk Assessment

**Tool:** GRADE upgrading
**Overall concern:** 🟢 low (with caveats noted below)

### GRADE Upgrade Factors

**Large effect size:** 🟢 met (delta +1)
- OR = 14.04 (95% CI well above 1.0); P = 1.28 × 10⁻⁶. Far exceeds RR > 2.0 threshold. CI does not cross 1.
- Negative criteria check: CI is NOT wide (precise estimate); N = 1,298 > 30 (not small-sample inflation). Upgrade valid.

**Dose-response gradient:** 🟢 met (delta +1)
- Graded increase in lung cancer risk across 6 cigarette consumption categories (none, 1–4, 5–14, 15–24, 25–49, 50+ per day). Monotonically increasing risk with significant trend.
- Negative criteria check: ≥ 3 dose groups (6 categories); relationship is monotonic (not J-shaped or U-shaped). Upgrade valid.

**Plausible confounding:** 🟢 met (delta +1)
- Known confounders (occupational exposures, urban air pollution, socioeconomic factors) would bias toward the null. Despite uncontrolled confounders favoring no association, OR remains 14.04.
- Negative criteria check: Confounding direction is clear (toward null), not solely based on authors' assertion — the listed confounders demonstrably co-associate with both smoking and lung cancer. Upgrade valid.

**GRADE upgrade cap applied:** Raw sum +3 capped to +1 (maximum allowed for observational studies).

### Observational-Specific Bias Considerations

| Bias Type | Assessment | Notes |
|---|---|---|
| Selection bias | 🟡 some_concerns | Hospital-based controls may not represent general population smoking rates. Matching on age/sex/hospital mitigates partially. |
| Recall bias | 🟡 some_concerns | Case-control design relies on self-reported smoking history. Cases aware of their diagnosis might recall differently. Standardized almoner interviews reduce but do not eliminate this. |
| Confounding | 🟡 some_concerns | No multivariable adjustment. Occupational exposures, air pollution, and socioeconomic factors not controlled. However, confounders would likely attenuate the effect, not inflate it. |

**Additional checks**

| Check | Finding | Delta |
|---|---|---|
| Surrogate endpoint | 🟢 No — lung carcinoma diagnosis is a hard clinical endpoint. Classification: **hard endpoint** | 0 |
| Meta-analysis I² | n/a | 0 |

---

## Narrative Summary

Doll and Hill's 1950 case-control study compared smoking histories between 649 patients with histologically confirmed lung carcinoma and 649 matched hospital controls across 20 London hospitals. This landmark observational study employed a retrospective design without randomization or blinding, consistent with its case-control methodology.

The statistical robustness analysis reveals a notably resilient association. The Fragility Index of 18 indicates that 18 control smoking status changes would be required to render the result non-significant — a strong showing for any study, and particularly impressive for an observational design. The Fragility Quotient of 0.0139 sits comfortably above the 0.01 concern threshold, confirming that robustness is not merely an artifact of sample size. No patients were lost to follow-up, so the LTFU-FI attrition rule does not threaten the finding.

The observed odds ratio of 14.04 vastly exceeds the GRADE framework's large-effect benchmark of OR > 2.0. This places the smoking-lung cancer association among the strongest epidemiological effects ever documented. The NNT of approximately 26 (reflecting the absolute exposure prevalence difference between cases and controls) falls well within the domain threshold, though clinicians should note that NNT has limited direct clinical interpretability in case-control studies — the odds ratio is the primary effect measure.

All three GRADE upgrade factors are met: a very large effect size (OR = 14.04, P = 1.28 x 10^-6), a clear dose-response gradient across multiple cigarette consumption categories, and the observation that all plausible confounders would bias toward the null rather than inflate the association. Per GRADE rules, the upgrade is capped at +1 despite meeting all three criteria, raising the study from its initial Grade 3 to Grade 4.

The study has inherent limitations of its case-control design. Selection bias from hospital-based sampling, recall bias from self-reported smoking histories, and residual confounding from unmeasured exposures all warrant consideration. The interviews were conducted by trained hospital almoners using a standardized protocol, which mitigates but does not eliminate information bias. The lack of multivariable adjustment means confounders such as occupational chemical exposures and urban air pollution were not formally controlled — though, as noted, these would be expected to attenuate rather than amplify the observed association.

Clinicians reviewing this evidence should weigh the extraordinary strength of the association and the coherent dose-response relationship against the methodological constraints inherent to a 1950-era case-control study. The findings from this preliminary report were subsequently confirmed by prospective cohort studies, randomized cessation trials, and decades of mechanistic research, but this evaluation assesses only the evidence presented within this single paper.

---

## Suggested Score *(optional — heuristic)*

> This score is generated by a deterministic rule engine. Design choices are pending expert calibration. Do not use as a validated clinical instrument.

**Score: 4 ★★★★☆ — Good**

### Score Path

| Step | Detail | Delta |
|---|---|---|
| Initial grade | Case-control observational study → Grade 3 | 3 (base) |
| Stage 2 | No deductions — observed OR (14.04) far exceeds GRADE benchmark (OR > 2.0) | 0 |
| Stage 3 | FI = 18 (robust): +0.5 | +0.5 |
| Stage 4 | GRADE upgrade: all 3 factors met (large effect, dose-response, confounders favor null); raw +3 capped to +1 | +1 |
| De-duplication | No overlapping deductions to suppress | — |
| Boundary enforcement | Ceiling 4 applied (raw 4.5 → 4); Grade 3 observational max = 4 | -0.5 |
| **Final score** | | **4** |

---

*Generated by SciSpark Evidence Evaluator · [scispark.ai](https://scispark.ai) · team@scispark.ai*
