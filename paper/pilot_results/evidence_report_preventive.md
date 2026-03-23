# Evidence Evaluation Report

**Paper:** Rosuvastatin to Prevent Vascular Events in Men and Women with Elevated C-Reactive Protein
**Authors:** Ridker PM, Danielson E, Fonseca FAH, Genest J, Gotto AM Jr, Kastelein JJP, et al.
**Journal:** New England Journal of Medicine · **Year:** 2008 · **PMID:** 18997196
**Study type:** preventive · **Routing confidence:** 99%
**Generated:** 2026-03-23 · **Pipeline:** SciSpark Evidence Evaluator

---

## Section 1 — Study Design & Population

| Field | Value |
|---|---|
| Study type | preventive |
| Phase | III |
| N (intervention) | 8,901 |
| N (control) | 8,901 |
| Blinding | double_blind |
| Randomization | randomized |
| Multicenter | yes |

**PICO**

| Element | Value |
|---|---|
| Population | Apparently healthy men (>=50 y) and women (>=60 y) with LDL cholesterol <130 mg/dL and hsCRP >=2.0 mg/L |
| Intervention | Rosuvastatin 20 mg daily |
| Comparator | Matching placebo |
| Outcome | First major cardiovascular event (composite: MI, stroke, arterial revascularization, hospitalization for unstable angina, cardiovascular death) |

---

## Section 2 — Statistical Robustness

| Metric | Value | Threshold | Flag |
|---|---|---|---|
| Fragility Index (FI) | 67 | > 10 = robust | robust |
| Fragility Quotient (FQ) | 0.0038 | < 0.01 | below threshold |
| Post-hoc Power | 85.5% | >= 80% | adequate |
| LTFU count | 25 | Must be <= FI (67) | safe |
| NNT | 81.7 | Domain threshold: 200 | favorable |

**Stage 3 computation trace:**

```
Fragility Index (FI):
  Inputs: events_i=142, events_c=251, n_i=8901, n_c=8901, initial_p<0.00001
  67 iterations required to cross P >= 0.05 (final: events_i=209, Fisher P=0.0527)
  FI = 67 → ROBUST (FI > 10)
  Delta: +0.5 grade
  Reasoning: Result is robust to multiple outcome changes.

LTFU-FI Attrition Rule:
  LTFU (25) <= FI (67): attrition does not threaten significance.
  Delta: 0

Fragility Quotient (FQ):
  FQ = 67 / 17,802 = 0.0038 (< 0.01)
  Delta: -0.5 grade
  Reasoning: Low FI relative to sample size — in a trial of 17,802, even FI=67 represents
  a small proportion of the total sample.

NNT:
  CER = 251/8901 = 0.0282
  IER = 142/8901 = 0.0160
  ARR = 0.0282 - 0.0160 = 0.0122
  NNT = 1/0.0122 = 81.7 (benefit)
  Domain threshold (CV primary prevention, low-risk): 200
  NNT (81.7) <= threshold (200): acceptable
  Delta: 0

Post-hoc Power:
  MCID = 0.007 (ARR); p_control = 0.0282; p_intervention_at_mcid = 0.0282 - 0.007 = 0.0212
  Cohen's h = 0.0452
  Power = 85.46% (>= 80%): adequately powered at MCID
  Delta: 0
```

---

## Section 3 — Clinical Benchmarking

| Field | Value |
|---|---|
| MCID | 0.007 ARR (0.7%) |
| Source | Tier 3 — powering convention from the landmark trial itself (HR <= 0.75) |
| Source tier | Tier 3 |
| Observed effect | ARR = 0.0122 (HR 0.56, 95% CI 0.46–0.69) |
| Effect vs. MCID | exceeds (observed 1.22% vs. threshold 0.7%) |

**MCID derivation:**

No Tier 1 (anchor-based patient-reported) or Tier 2 (established published MCID) threshold exists for cardiovascular primary prevention composite endpoints. Using Tier 3 (powering convention from landmark trial):

1. **Powering convention:** JUPITER was powered to detect HR <= 0.75 (25% relative risk reduction). This aligns with AHA/ESC primary prevention guidelines, which use HR <= 0.75–0.80 as the threshold for clinical significance.
2. **Per rule 5:** use the powering convention from the landmark trial itself, so HR <= 0.75.
3. **CER from Stage 1:** events_control = 251, n_control = 8,901 → CER = 251/8901 = 0.0282.
4. **Convert HR threshold to ARR:** ARR = CER x (1 - HR) = 0.0282 x (1 - 0.75) = 0.0282 x 0.25 = 0.0071.
5. **MCID = ARR 0.007 (0.7%).**
6. **Cross-check with HR <= 0.80:** ARR = 0.0282 x 0.20 = 0.0056 (0.6%). The selected threshold (0.7%) is conservative relative to the alternative.
7. **Observed ARR (1.22%) exceeds MCID (0.7%) by a factor of 1.74.** The trial result is clinically meaningful.

---

## Section 4 — Bias Risk Assessment

**Tool:** RoB 2.0
**Overall concern:** some_concerns

### Per-Domain Findings

**Domain 1 — Randomization process:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Was the allocation sequence random? | Yes | Computer-generated randomization sequence |
| Q2: Was the allocation sequence concealed until enrollment? | Yes | Concealed allocation via interactive voice-response system; 1:1 ratio, stratified by center |

**Domain 2 — Deviations from intended interventions:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Were participants aware of their assigned intervention? | No | Double-blind with matched placebo |
| Q2: Were there significant crossovers or co-interventions? | No | Protocol adherence monitored centrally; low crossover rate |
| Q3: Was the analysis intention-to-treat? | Yes | ITT analysis |

**Domain 3 — Missing outcome data:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Were outcome data available for ≥ 95% of randomized participants? | Yes | Vital status known for >97%; ~25 patients with unknown primary endpoint status |
| Q2: Was there differential missingness between arms (> 5% difference)? | No | No differential missingness reported |
| Q3: Was an appropriate method used for missing data? | Yes | National registry linkage for endpoint ascertainment |

**Domain 4 — Measurement of outcome:** 🟢 low (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Was the outcome objective or subjective? | Objective | Hard clinical endpoints (MI, stroke, CV death, revascularization). Adjudicated events → classify as OBJECTIVE |
| Q2: Were outcome assessors blinded? | Yes | Blinded independent endpoint committee adjudication |

**Domain 5 — Selection of reported results:** 🟡 some_concerns (delta 0)

| Question | Answer | Evidence |
|---|---|---|
| Q1: Was the trial pre-registered? | Yes | NCT00239681 |
| Q2: Does the published primary endpoint match the registration? | Yes | Primary composite endpoint unchanged |
| Q3: Are all pre-specified secondary endpoints reported? | Yes | All pre-specified endpoints reported |

Early stopping concern: Trial stopped by independent DSMB after median 1.9 years of planned 5 years, upon exceeding the pre-specified Haybittle-Peto stopping boundary. Early stopping may overestimate treatment effects. Classified as "some_concerns" rather than "high" because the stopping rule was pre-specified and the primary endpoint was not changed. No deduction applied at the "some_concerns" level.

**Additional checks**

| Check | Finding | Delta |
|---|---|---|
| Surrogate endpoint | 🟢 No — hard clinical composite (MI, stroke, CV death, revascularization). Classification: **hard endpoint** | 0 |
| Meta-analysis I² | n/a (single trial) | 0 |

---

## Narrative Summary

The JUPITER trial (Justification for the Use of Statins in Prevention: an Intervention Trial Evaluating Rosuvastatin) was a large, multinational, double-blind, randomized, placebo-controlled Phase III trial enrolling 17,802 apparently healthy men and women with low LDL cholesterol but elevated high-sensitivity C-reactive protein. Participants were randomized 1:1 to rosuvastatin 20 mg daily or placebo, with the primary endpoint being a composite of first major cardiovascular event (myocardial infarction, stroke, arterial revascularization, hospitalization for unstable angina, or cardiovascular death). The trial was stopped early by an independent Data Safety Monitoring Board after a median follow-up of 1.9 years out of a planned 5 years, upon crossing a pre-specified Haybittle-Peto efficacy boundary.

The statistical robustness of this trial is notable. The Fragility Index of 67 indicates that 67 outcome events in the intervention group would need to change classification before the primary result would lose statistical significance at the two-sided alpha = 0.05 level. This places JUPITER among the most statistically resilient cardiovascular prevention trials. The LTFU-FI attrition check confirms that missing data does not threaten the primary finding: only approximately 25 patients had unknown primary endpoint status, well below the FI of 67. However, the Fragility Quotient (FQ = 67/17,802 = 0.0038) falls below the 0.01 threshold, reflecting that even an FI of 67 represents a small fraction of the total sample. The FI bonus (+0.5) and FQ penalty (-0.5) cancel to a net zero adjustment. Post-hoc power was 85.5% at the updated MCID of 0.7% ARR, confirming the trial was adequately powered to detect a clinically meaningful effect at the Tier 3 threshold.

A key update in this re-evaluation concerns the MCID derivation. No Tier 1 or Tier 2 MCID exists for cardiovascular primary prevention composite endpoints. The Tier 3 derivation uses the powering convention from JUPITER itself: HR <= 0.75, representing a 25% relative risk reduction. Converting to an absolute scale using the control event rate (CER = 251/8,901 = 0.0282), the formula ARR = CER x (1 - HR) yields ARR = 0.0282 x 0.25 = 0.0071, rounded to MCID = 0.007 (0.7%). This is more stringent than the prior MCID of 1.0% used in earlier versions of this report, and it better reflects the powering assumption of the trial and the AHA/ESC guideline range. The observed ARR of 1.22% exceeds this MCID by a factor of 1.74, and the NNT of 81.7 falls well within the domain threshold of 200 for low-risk primary prevention populations. Together, these metrics indicate clinically meaningful benefit at a population level.

The bias risk assessment using RoB 2.0 identified low risk across four of five domains. The single domain rated "some concerns" is selection of reported results, driven by the trial's early termination. While the stopping followed a pre-specified Haybittle-Peto boundary and the primary endpoint was registered (NCT00239681), early stopping is known to overestimate treatment effects. The magnitude of this potential overestimation is uncertain but should be weighed when interpreting the hazard ratio of 0.56. No deductions were applied because the stopping rule was pre-specified and the primary endpoint was not changed, meeting the threshold for "some concerns" rather than "high risk."

Key strengths of the trial include its large sample size, rigorous double-blind design, use of hard clinical endpoints adjudicated by an independent blinded committee, near-complete follow-up (vital status known for >97%), and highly significant results (P < 0.00001). Key limitations include early stopping with potential effect overestimation, the highly selected population (elevated CRP as an enrollment criterion limits generalizability to broader primary prevention), the relatively short follow-up that leaves long-term benefit-risk balance uncertain, and a higher incidence of physician-reported diabetes in the rosuvastatin group. Clinicians interpreting this evidence should weigh the strong statistical robustness and favorable NNT against the uncertainty introduced by early stopping, the selected population, and the updated but still favorable MCID comparison.

---

## Suggested Score *(optional — heuristic)*

> This score is generated by a deterministic rule engine. Design choices are pending expert calibration. Do not use as a validated clinical instrument.

**Score: 5 -- Excellent**

### Score Path

| Step | Detail | Delta |
|---|---|---|
| Initial grade | Large multi-center double-blind Phase III RCT (N > 1,000) | 5 (base) |
| Stage 2 | Effect exceeds MCID; N > domain standard; NNT within threshold | 0 |
| Stage 3 | FI: +0.5 (robust); FQ: -0.5 (below threshold); net zero | 0 |
| Stage 4 | All RoB 2.0 domains low or some_concerns (no deduction-level findings) | 0 |
| De-duplication | No overlapping deductions to resolve | -- |
| Boundary enforcement | None required (raw score = 5, within [3, 5] range) | -- |
| **Final score** | | **5** |

**Score 5 prerequisites check:**
- Initial grade = 5: yes
- FI > 10: yes (67)
- FI > LTFU: yes (67 > 25)
- P < 0.001: yes (P < 0.00001)
- Power >= 0.80: yes (85.5%)
- Low bias (no high/critical domains): yes
- Hard endpoints (not surrogate): yes

---

*Generated by SciSpark Evidence Evaluator · [scispark.ai](https://scispark.ai) · team@scispark.ai*
