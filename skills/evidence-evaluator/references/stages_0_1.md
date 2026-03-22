# Stage 0: Study Type Pre-Routing

## Purpose
Classify the paper before running any other stage. The routing decision controls which tools, thresholds, and bias frameworks all downstream stages use.

## Input
Abstract (minimum). Full text preferred but not required.

## Classification Categories

| Label | Description |
|---|---|
| `RCT_intervention` | Randomized controlled trial testing a treatment intervention |
| `diagnostic` | Study evaluating sensitivity/specificity/AUC of a diagnostic test |
| `preventive` | RCT or observational study targeting disease prevention (vaccines, screening, prophylaxis) |
| `observational` | Cohort, case-control, or cross-sectional study (no randomization) |
| `meta_analysis` | Systematic review with pooled quantitative synthesis |
| `phase_0_1` | Phase 0 or Phase I trial (safety/pharmacokinetics, not efficacy) |

## Routing Decision Table

| Study Type | Stage 2 | Stage 3 | Stage 4 Tool | Score Range |
|---|---|---|---|---|
| `RCT_intervention` | Full MCID search | FI + NNT + power | RoB 2.0 | 1–5 |
| `meta_analysis` | Full MCID search | FI + NNT + power | RoB 2.0 | 1–5 |
| `preventive` | NNT threshold focus | FI + NNT + power | RoB 2.0 | 1–5 |
| `observational` | Effect benchmark | FI (if events available) + NNT | GRADE upgrading | 1–5 |
| `diagnostic` | AUC/Sn/Sp thresholds | DOR only | QUADAS-2 | 1–5 |
| `phase_0_1` | **SKIP** | **SKIP** | RoB 2.0 (2 domains only) | **LOCKED 1–2** |

## Output Schema

```json
{
  "study_type": "RCT_intervention | diagnostic | preventive | observational | meta_analysis | phase_0_1",
  "confidence": 0.0,
  "classification_rationale": "string — why this type was selected",
  "human_review_flag": false,
  "human_review_reason": null
}
```

**Confidence threshold:** ≥ 0.7 → proceed automatically. < 0.7 → flag `[needs_human_review]`, continue with best-guess type, mark result provisional.

---

# Stage 1: Variable Extraction & Initial Grading

## Purpose
Extract all quantitative variables needed for downstream math and grading. Assign an Initial Grade (1–5) based on study design metadata alone.

## LLM Strategy

**Two-pass approach (adapted from Quicker, Li et al., npj Digital Medicine 2025):**

1. **Self-reflection few-shot prompting** — show 3–5 labeled examples, generate answer, then critique and revise before finalizing. Validated to outperform basic prompting for PICO extraction (higher F1 + BERTScore).

2. **CoT majority vote (3× parallel)** — run extraction independently 3 times. Fields where all 3 agree = high confidence. Any disagreement = `low_confidence_fields`. Fires all 3 calls simultaneously (asyncio-style) so latency ≈ 1× a single call.

## Tiered Context

Always use **Tier 1** first: abstract + methods + conclusion. If an agent pass returns `{"needs_full_paper": true}`, escalate to full text. Study type, blinding, randomization, sample size, primary outcome — all typically available in Tier 1.

## Output Schema

```json
{
  "study_type": "same as Stage 0 output",

  "extracted_variables": {
    "n_intervention": null,
    "n_control": null,
    "events_intervention": null,
    "events_control": null,
    "ltfu_count": null,            // LTFU = exclusions + withdrawals + AE-related dropouts (all causes of attrition)
    "p_value": null,
    "effect_size": null,
    "effect_size_type": "binary | continuous | SMD | MD | null",  // binary = events in 2x2 table (use for FI/NNT); continuous = means+SDs (use for SMD power); SMD = standardized mean difference; MD = mean difference
    "ci_lower": null,
    "ci_upper": null,
    "multicenter": false,
    "blinding": "open | single_blind | double_blind | not_applicable",
    "randomization": "randomized | quasi_randomized | not_randomized | not_applicable",
    "trial_phase": "0 | I | II_a | II_b | III | IV | not_applicable | null",
    "alpha": null,
    "stated_power": null,
    "primary_outcome": "string"
  },

  "grading": {
    "initial_grade": 3,
    "grade_criteria_matched": "string — exact rule that triggered this grade",
    "initial_grade_rationale": "string — full plain-language explanation",
    "special_rules_triggered": []
  },

  "pico": {
    "population": "string — who was studied, key inclusion/exclusion criteria",
    "intervention": "string — what was done, dose/protocol details",
    "comparator": "string | null",
    "outcome": "string — primary outcome measure with scale and timepoint",
    "pico_search_string": "string — PubMed-ready query for Stage 2"
  },

  "extraction_qa": {
    "confidence": 0.0,
    "low_confidence_fields": [],
    "human_review_flag": false,
    "human_review_reason": null,
    "source_locations": {
      "n_intervention": "Methods, Table 1",
      "p_value": "Abstract"
    }
  }
}
```

## LTFU Definition (critical for LTFU-FI rule)

LTFU (lost to follow-up) includes ALL sources of attrition that remove patients from the analysis:
- **Exclusions** after randomization (protocol violations, found ineligible)
- **Withdrawals** (patient withdrew consent, withdrew for personal reasons)
- **Adverse-event-related dropouts** (discontinued due to side effects)
- **Administrative losses** (moved, unreachable, death from non-study cause if not counted as event)

**How to extract:** Look for the CONSORT flow diagram or the "Participants" section of Results. Sum all patients randomized minus all patients in the final ITT analysis. If the paper reports "vital status ascertained for X%", compute: `LTFU = N_total × (1 − X/100)`.

**Do NOT count** as LTFU: deaths that are part of the primary endpoint (these are events, not losses).

## Effect Size Type Classification

The `effect_size_type` field determines which power calculation method Stage 3 uses. Apply these rules:

| If the primary outcome is... | Set `effect_size_type` to | Stage 3 power method |
|---|---|---|
| Binary (events/no events, 2×2 table available) | `binary` | `proportion_effectsize` → `NormalIndPower` |
| Continuous (means ± SDs in each arm) | `continuous` | `TTestIndPower` with SMD |
| Reported as SMD/Cohen's d (meta-analysis) | `SMD` | `TTestIndPower` with reported SMD |
| Reported as mean difference (same units) | `MD` | Convert to SMD using pooled SD, then `TTestIndPower` |

**When the paper reports both HR and events:** Use `binary` (events are extractable from the 2×2 table). HR is the reported effect size, but FI/NNT computation uses the raw event counts.

**When the paper reports only HR without event counts:** Set `effect_size_type` to `binary` and flag `needs_full_paper: true` to extract the events table.

## Initial Grade Table (Intervention / Meta-Analysis Studies)

| Grade | Study Design Criteria | Decision Rule |
|---|---|---|
| 1 | Expert consensus, physiological theory, narrative review | No primary data |
| 2 | Case series, case reports, low-quality cross-sectional, Phase 0/I | Phase 0/I always = Grade 2 regardless of N |
| 3 | Small RCT (N < 100), retrospective cohort, case-control | N is the deciding factor for RCTs; phase label is secondary |
| 4 | Medium RCT (N 100–1000) or high-quality prospective cohort | "High-quality" = prospective + pre-registered + ≥1 year follow-up |
| 5 | Large multi-center double-blind RCT (Phase III, N > 1000), or high-quality meta-analysis | Must meet ALL: multi-center AND double-blind AND N > 1000 |

**Grade assignment priority:** N takes precedence over phase label. A Phase IIb trial with N = 50 is Grade 3 (N < 100), not Grade 4. A Phase IIa trial with N = 200 is Grade 4 (N 100–1000), not Grade 3. Single-center or open-label trials with N > 1000 are Grade 4 (not Grade 5 — missing multi-center or double-blind requirement).

## Diagnostic Study Grade Table

| Grade | Criteria |
|---|---|
| 2 | Single-center retrospective, N < 100, case-control (spectrum bias) |
| 3 | Prospective single-center, consecutive enrollment, N 100–500, blinded reference standard |
| 4 | Multi-center prospective, N > 500, independent blinded interpretation, external validation |
| 5 | Diagnostic SR / meta-analysis (QUADAS-2 assessed), or large multi-center prospective registry |

## Special Rules

- **Phase 0/I:** Auto-lock to Grade 2, fixed score of 2. Phase 2 MCID search not triggered. Phase 3 FI/NNT skipped. Stage 4 runs only randomization + selective reporting domains of RoB 2.0. Final score fixed between 1–2; cannot be upgraded to 3 under any circumstance. Output must include: *"This is a Phase 0/I safety trial. Score reflects study quality only."*
- **Retracted paper / data fabrication / serious COI:** Set `excluded: true`. No score. All sections suppressed. UI: *"Removed due to data integrity concerns."* This applies to confirmed retractions, significant data fabrication, or serious undisclosed conflicts of interest discovered at any stage.
- **Confidence < 0.7:** Flag `human_review_flag: true`. Continue pipeline but mark provisional.
