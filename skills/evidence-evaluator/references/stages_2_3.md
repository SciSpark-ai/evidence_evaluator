# Stage 2: Domain Benchmark & MCID Search

## Purpose
Retrieve the Minimum Clinically Important Difference (MCID) for the primary outcome, domain-standard effect size, and typical sample size. These benchmarks determine whether results are clinically meaningful — not just statistically significant.

**Skip entirely if:** `study_type = phase_0_1`

## LLM Strategy
Agentic iterative retrieval (up to 5 rounds). Start from Stage 1's `pico_search_string` as the first-round query. The LLM expands each PICO concept into comprehensive search terms and database-specific Boolean syntax before querying — this dramatically outperforms naive queries (Quicker: recall 0.782 vs 0.073 for naive GPT).

## Study Type Routing

| Study Type | Action |
|---|---|
| `RCT_intervention` / `meta_analysis` | Full Stage 2: MCID + expected effect size + domain N |
| `observational` | Full Stage 2: focus on domain benchmark effect sizes |
| `preventive` | Full Stage 2: focus on NNT threshold tables for the indication |
| `diagnostic` | Diagnostic sub-flow: retrieve AUC / Sn / Sp thresholds (STARD, QUADAS-2) |
| `phase_0_1` | **SKIP Stage 2 entirely** |

## MCID Source Priority (Tiers)

| Tier | Source | Action if found |
|---|---|---|
| 1 | COMET Initiative, OMERACT, IMMPACT, FDA CDER/EMA CHMP | Direct citation — no inference |
| 2 | PubMed systematic reviews — query: `"minimum clinically important difference"[Title] AND [disease]` | Use with citation |
| 3 | Major specialty guidelines: ASCO/ESMO, AHA/ESC, ACR/EULAR, AAN/EAN, KDIGO, IASP | Use with citation. If expressed as HR, convert to ARR: `ARR = CER × (1 − HR)` using Stage 1 CER. |
| 4 | Statistical proxy: Cohen's d = 0.5 | **Must label:** *"MCID not found in specialty literature; using Cohen's d = 0.5 as conservative estimate. Interpret with caution."* |

**Tier 3 conversion example (cardiovascular):** ESC/FDA convention for HF outcome trials uses HR ≤ 0.80 as the powering threshold. If CER = 21.2%, then MCID = 0.212 × 0.20 = 0.042 → ARR ≈ 4%. Do NOT invent arbitrary thresholds (e.g., "ARR 2%") without a documented guideline source. The conversion must use the actual CER from Stage 1 to produce a study-specific ARR.

## Domain Standard N — Search Instruction

The "domain standard N" is NOT a fixed lookup — it is determined by agentic search during Stage 2. Search for the typical sample size of trials at the same phase and indication:

**Search strategy:** Query PubMed for recent systematic reviews or meta-analyses in the same disease-outcome pair. Look for the median or typical sample size of included trials. Alternatively, check FDA guidance documents for the indication, which often specify minimum enrollment expectations.

**If no domain standard is found:** Do not apply the N < domain deduction. Document: "No domain standard N found for [indication]; N deduction not applied."

**Always document:** The domain N value, its source, and how it was derived.

## Deductions from Stage 2

| Finding | Deduction | Rationale |
|---|---|---|
| Observed effect < MCID | −1 grade | Statistically significant but clinically meaningless |
| N < domain standard N | −1 grade | Underpowered relative to field norms |
| NNT > domain threshold | −1 grade | Benefit rate too low for clinical justification |

**Effect vs. MCID is binary:** If observed effect ≥ MCID → "exceeds" (no deduction). If observed effect < MCID → "below" (−1 deduction). There is no "borderline" category — this eliminates agent interpretation variance at the threshold.

**De-duplication:** {power < 0.8, N < domain standard, NNT > threshold} share the same statistical stability dimension. In Stage 5, apply ONLY the single deduction with the largest absolute value. If all three are −1, apply any one and suppress the other two (they are equivalent). Document which was applied and which were suppressed.

## Preventive Study NNT Reference Thresholds

| Prevention Domain | Acceptable NNT Range |
|---|---|
| Cardiovascular primary prevention (low-risk) | 50–200 |
| Cardiovascular secondary prevention (high-risk) | 10–50 |
| Oncology adjuvant chemotherapy | 5–20 |
| Infectious disease prevention (vaccines) | 20–100 |
| Stroke secondary prevention | 15–50 |
| Osteoporosis fracture prevention | 30–100 |

**NNT threshold priority:** (1) Use the evidence-based NNT consensus value found during agentic search — if found, the table above is void. (2) If no evidence-based value is found, use the table above as a conservative fallback. (3) If the indication is not in the table, do NOT apply the NNT threshold deduction — document: "No NNT threshold available for [indication]; NNT deduction not applied." **Always state the source of the NNT threshold used in the report.**

## Diagnostic Thresholds (replaces MCID for diagnostic studies)

| Metric | Clinical Value | Excellent | Deduction Trigger |
|---|---|---|---|
| AUC | ≥ 0.70 | ≥ 0.90 | AUC < 0.70 → −1 |
| Sensitivity | ≥ 0.85 (high-stakes) | ≥ 0.95 | — |
| Specificity | ≥ 0.70 | ≥ 0.90 | — |
| LR+ | > 5 | > 10 | LR+ < 2 → −1 |
| LR− | < 0.2 | < 0.1 | — |

Additional diagnostic rules:
- Case-control design (not consecutive enrollment) → −1 (spectrum bias)
- Same-technology reference standard → −1 (incorporation bias)
- AUC-only reporting (no cutoff points) → −0.5 + flag *"Insufficient clinical utility"*

---

# Stage 3: Deterministic Mathematical Audit

## Purpose
Pure computation. No LLM. Calculates objective, reproducible statistical metrics that anchor the qualitative LLM reasoning from other stages.

**Skip if:** `study_type = phase_0_1`
**Diagnostic studies:** compute DOR only (skip FI/NNT)
**Observational studies:** compute FI (if events available) and NNT; skip post-hoc power

## Computations

### 1. Fragility Index (FI)
**Method:** Iteratively increment `events_intervention` by 1 and recompute Fisher exact test P-value until P ≥ 0.05. The number of increments = FI.

**Thresholds:**
- FI ≤ 2 → extreme fragility → **−1 grade**
- FI > 10 (AND other conditions met) → highly robust → **+0.5 grade**

**Special case:** If initial P ≥ 0.05, FI = 0 by definition. Flag: *"Result not statistically significant; FI not computable."*

### 2. LTFU-FI Attrition Rule (HIGHEST PRIORITY)
```
If LTFU_count > FI → apply −2 grade (hard rule, cannot be deduplicated or overridden)
```
This means: the number of patients lost to follow-up exceeds the number of outcome switches that would make the result non-significant. The finding is fragile in the face of its own dropout.

**Floor interaction:** LTFU > FI can penetrate TO the boundary floor but not below it. For Grade 5 studies, the floor is 3 — LTFU can reduce the score to 3 but not below. When LTFU triggers, do not re-penalize for near-threshold P-values or low FI (the −2 already accounts for these).

### 3. Fragility Quotient (FQ)
```
FQ = FI / N_total
```
**Threshold:** FQ < 0.01 → **−0.5 grade**

### 4. Post-hoc Power
**Method:** Use MCID from Stage 2 as the target effect size. Compute post-hoc power with actual sample sizes.

| Effect size type | Computation method |
|---|---|
| Binary (RR/OR) | Convert ARR to Cohen's h via `proportion_effectsize()`, then `NormalIndPower().solve_power()` |
| Continuous (SMD/MD) | `TTestIndPower().solve_power()` with SMD as effect size |
| HR (time-to-event) | `NormalIndPower().solve_power()` approximating via log-HR / SE |

**Threshold:** Power < 0.80 → **−1 grade**

### 5. NNT / NNH
```
CER = events_control / n_control
IER = events_intervention / n_intervention
ARR = CER − IER

If ARR > 0:  NNT = 1 / ARR  (benefit)
If ARR < 0:  NNH = 1 / |ARR|  (harm — informational only, no auto-deduction)
If ARR = 0:  NNT = ∞  → −1 grade (equivalent to exceeding any domain threshold)
```

**NNT 95% CI:** Derive Wilson CI on ARR → `NNT_CI = [1/ARR_upper, 1/ARR_lower]`

**Deduction:** If NNT exceeds domain threshold → **−1 grade**

### 6. Diagnostic Odds Ratio (DOR) — diagnostic studies only
```
DOR = (TP × TN) / (FP × FN) = LR+ / LR−
LR+ = Sensitivity / (1 − Specificity)
LR− = (1 − Sensitivity) / Specificity
```

**Thresholds:**
- DOR < 5 → poor discrimination → **−1 grade**
- DOR > 20 (Grade 3/4 only) → high discrimination → **+0.5 grade**
- If CI crosses 1 → flag *"Result unstable"* → **−1 grade**

## De-duplication (applied in Stage 5)
Among these three candidates:
- Post-hoc power < 0.80 → −1
- N < domain standard N (from Stage 2) → −1
- NNT > domain threshold → −1

**Apply only the most severe single deduction. Suppress the other two.**

## Output: Show Full Trace
Always display:
- Inputs used (with source stage attribution)
- Intermediate computation values
- Final metric, threshold comparison, delta applied
- Reasoning string explaining the judgment

Example output format:
```
Fragility Index (FI):
  Inputs: events_i=47, events_c=60, n_i=312, n_c=308, initial_p=0.038
  Iteration 1: events_i=48 → Fisher P=0.054 ✓ (crossed 0.05)
  FI = 1 → EXTREME FRAGILITY (FI ≤ 2)
  Delta: −1 grade
  Reasoning: One outcome event change would render the result non-significant.
```
