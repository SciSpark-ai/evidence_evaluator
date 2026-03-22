# Stage 4: Bias Risk & Evidence Certainty Audit

## Purpose
Structured assessment of bias risk and evidence certainty using the appropriate validated tool for the study type. The LLM reads the paper using tiered context strategy and produces per-domain judgments with explicit evidence citations.

## Tool Selection by Study Type

| Study Type | Tool |
|---|---|
| `RCT_intervention` / `meta_analysis` / `preventive` | **RoB 2.0** (5 domains) |
| `diagnostic` | **QUADAS-2** (4 domains, capped at −2 total) |
| `observational` | **GRADE upgrading** (3 factors, capped at +1 total) |
| `phase_0_1` | **RoB 2.0 — limited** (randomization + selective reporting domains only) |

## Tiered Context Strategy
Use Tier 1 (abstract + methods + conclusion) first. For most RoB 2.0 domains (randomisation, blinding, LTFU, selective reporting), Tier 1 is sufficient — the relevant information is in methods. Signal `needs_full_paper: true` if trial registration details or supplementary protocols are required.

---

## RoB 2.0 — for RCT / meta-analysis / preventive

### Per-Domain Signaling Questions

For each domain, answer the signaling questions below. If the paper does not report the information needed to answer a question, mark it as `some_concerns` (absence of reporting ≠ absence of bias).

**Domain 1 — Randomization process** (Deduction: high risk −1; critical −2)
- Q1: Was the allocation sequence random? (Look for: "computer-generated", "random number table", "coin toss". NOT acceptable: "alternation", "date of birth", "medical record number")
- Q2: Was the allocation sequence concealed until enrollment? (Look for: "central randomization", "IVRS/IWRS", "sequentially numbered sealed opaque envelopes". NOT acceptable: "open allocation list", no mention of concealment)
- **Low:** Both Q1 and Q2 answered yes with evidence. **Some concerns:** One answered yes, one unclear. **High:** Either answered no. **Critical:** No randomization AND subjective unblinded outcome.

**Domain 2 — Deviations from intervention** (Deduction: high risk −1)
- Q1: Were participants aware of their assigned intervention? (Double-blind = low risk)
- Q2: Were there significant crossovers or co-interventions? (Look for: crossover rate > 10%, unbalanced co-interventions)
- Q3: Was the analysis intention-to-treat? (Per-protocol only = some concerns)
- **Low:** Double-blind + ITT + no significant crossover. **Some concerns:** Open-label but ITT with low crossover. **High:** Open-label + per-protocol or significant crossover.

**Domain 3 — Missing outcome data** (Deduction: high risk −1)
- Q1: Were outcome data available for ≥ 95% of randomized participants?
- Q2: Was there differential missingness between arms (> 5% difference)?
- Q3: Was an appropriate method used for missing data (multiple imputation, sensitivity analysis)?
- **Low:** ≥ 95% complete + no differential missingness. **Some concerns:** 90–95% complete or minor differential. **High:** < 90% complete or large differential without sensitivity analysis.

**Domain 4 — Measurement of outcome** (Deduction: subjective + unblinded −2; high risk −1)
- Q1: Was the outcome objective or subjective?
  - **Objective:** Death, hospitalization, lab values, imaging with automated measurement — events that do not depend on assessor judgment
  - **Subjective:** Patient-reported scores (pain VAS, PHQ-9), clinician-rated scales (PANSS, CGI), physician global assessment
  - **Semi-objective:** Adjudicated events (e.g., blinded endpoint committee reviewing clinical events) — classify as OBJECTIVE
- Q2: Were outcome assessors blinded?
- **Low:** Objective outcome (blinding irrelevant) OR subjective + blinded assessors. **Some concerns:** Subjective + assessors not described. **High:** Subjective + confirmed unblinded assessors. **Critical:** Subjective + unblinded + no objective verification → −2.

**Domain 5 — Selection of reported results** (Deduction: high risk −1)
- Q1: Was the trial pre-registered (ClinicalTrials.gov, ISRCTN, etc.)?
- Q2: Does the published primary endpoint match the registration?
- Q3: Are all pre-specified secondary endpoints reported?
- **Low:** Pre-registered + primary matches + secondaries reported. **Some concerns:** Registered but minor discrepancies. **High:** Not registered, or primary endpoint changed without justification, or selective secondary endpoint reporting.

**For Phase 0/I:** Run ONLY Domain 1 (randomization) + Domain 5 (selection of reported results). Skip all others.

Judgment levels: `low | some_concerns | high | critical`

---

## QUADAS-2 — for diagnostic studies

| Domain | High-Risk Trigger | Deduction |
|---|---|---|
| Patient selection | Case-control design OR non-consecutive enrollment | −1 |
| Index test | Reference standard known during index test interpretation (verification bias) | −1 |
| Reference standard | Not independently validated as gold standard | −1 |
| Flow and timing | Long interval between index test and reference standard | −0.5 |

**QUADAS-2 cap:** Maximum −2 total regardless of raw sum.

**De-duplication with Stage 2:** Case-control spectrum bias deducted in Stage 2 + QUADAS-2 patient selection domain are the same bias — apply only once in Stage 5.

---

## GRADE Upgrading — for observational studies

| Factor | Trigger Conditions | Effect |
|---|---|---|
| Large effect size | RR > 2.0 or RR < 0.5; CI does not cross 1; P < 0.01 | +1 grade |
| Dose-response gradient | P_trend < 0.05; ≥ 3 dose levels; monotonic relationship | +1 grade |
| Plausible confounding | Bias direction favors null but result still significant | +1 grade |

**Upgrade cap:** Maximum +1 total even if multiple factors met.
**Grade ceiling:** Grade 3 → max 4; Grade 2 → max 3. Score 5 is reserved for Grade 5 starting studies only.

**When upgrades do NOT trigger:**
- **Large effect size:** Does NOT trigger if the CI is wide (imprecise estimate) or N < 30 (small sample inflates effect).
- **Dose-response gradient:** Does NOT trigger if only 2 dose groups (need ≥ 3) or if the dose-response curve is J-shaped or U-shaped (non-monotonic).
- **Plausible confounding:** Does NOT trigger if the confounding direction is unclear, or if the claim is based solely on authors' assertion without supporting data (unadjusted crude effect must be smaller than adjusted effect).

---

## Additional Checks (all study types)

### Surrogate Endpoint
If the primary outcome is a biomarker proxy rather than a hard clinical endpoint:
→ **−1 grade** (applied once; not duplicated)

**Classification rule:** Compare the primary outcome from Stage 1 against the domain's accepted hard clinical endpoints from Stage 2. If the primary outcome is NOT a hard clinical endpoint for that disease, it is a surrogate.

| Classification | Examples | Rule |
|---|---|---|
| **Hard endpoint** (not surrogate) | All-cause mortality, cardiovascular death, hospitalization, stroke, MI, fracture, disease-free survival | Directly measures patient-important outcomes |
| **Surrogate** (−1 applies) | HbA1c, blood pressure, cholesterol, PSA, tumor response (RECIST), CD4 count, viral load, bone mineral density | Biomarker proxy for a hard endpoint |
| **Validated surrogate** (−1 still applies, but flag) | Progression-free survival in some oncology settings, eGFR decline in nephrology | Has regulatory acceptance but is still a proxy — apply −1 but note validation status |

**Context does NOT change the classification.** A biomarker is a surrogate regardless of whether the trial's mechanism targets it directly. HbA1c is a surrogate even in an antihyperglycemic trial — the question is whether the *patient* benefits (CV events, mortality), not whether the *drug* works on the biomarker.

### Meta-Analysis Inconsistency
If I² > 50% with no subgroup explanation or pre-specified heterogeneity analysis:
→ **−1 grade**

---

## Output Schema

For each domain assessed, output:
```json
{
  "domain": "domain_name",
  "evidence_found": "string — text located in the paper with section attribution (e.g., 'Methods §2.3: allocation was...')",
  "judgment": "low | some_concerns | high | critical | unclear",
  "delta": 0,
  "reasoning": "string — full explanation linking evidence to judgment and delta"
}
```

Plus:
```json
{
  "tool_used": "RoB_2.0 | QUADAS-2 | GRADE_upgrade",
  "additional_checks": {
    "surrogate_endpoint": { "detected": false, "evidence": "", "delta": 0 },
    "meta_analysis_inconsistency": { "applicable": false, "i_squared": null, "delta": 0 }
  },
  "stage_score_delta": 0.0
}
```

---

## Quality Principles for This Stage

- **Always cite the paper text** that supports each domain judgment. Do not assert bias without showing evidence.
- **Distinguish between absence of reporting and confirmed absence.** "Not reported" ≠ "Not done." Flag as `some_concerns` when information is missing.
- **Phase 0/I hard constraint:** Only two domains. Do not run other RoB 2.0 domains even if the paper contains enough information.
- **QUADAS-2 cap is non-negotiable.** Even if raw domain deductions sum to −3 or −4, apply max −2.
