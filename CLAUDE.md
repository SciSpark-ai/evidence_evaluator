# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Evidence Evaluator is a 6-stage agentic pipeline (SciSpark EvidenceScore v2) that produces structured evidence quality reports for clinical/biomedical research papers. It is an **LLM skill** (defined in `SKILL.md`), not a standalone application — the pipeline is executed by an AI agent following the stage reference documents.

## Running Tests

```bash
# Dependencies
pip install scipy statsmodels numpy

# Acceptance tests (T1–T8): routing logic, deduction rules, special cases
python tests/acceptance_tests_T1_T8.py

# Stage 3 math unit tests (FI, FQ, NNT, DOR, post-hoc power) — 21 cases
python tests/experiment_3B_math_unit_tests.py

# Stage 3 module tests — 147 tests: core metrics, edge cases, acceptance
# scenarios, study type routing, de-duplication, test-retest, total delta
# end-to-end, and published FI validation (Walsh et al. 2014)
python tests/test_stage3_math.py

# Stage 5 module tests — 60 tests: score rule engine, boundary matrix,
# de-duplication caps (QUADAS-2, GRADE), LTFU floor pierce, phase_0_1 lock,
# report assembly, exclusion handling, special case formatting
python tests/test_stage5_report.py
```

Tests use a custom pass/fail counter (not pytest). They print results to stdout with checkmark/cross indicators.

## Architecture

The repo is a **skill specification + reference library + Stage 3 & 5 implementations**:

- `SKILL.md` — Entry point. Defines the full pipeline, stage execution order, de-duplication rules, and output format. This is what the agent reads to run an evaluation.
- `pipeline/stage3_math.py` — **Implemented.** Deterministic math audit module (no LLM). Exports `run_stage3()` as the top-level entry point, plus individual functions: `compute_fragility_index`, `compute_ltfu_fi_rule`, `compute_fragility_quotient`, `compute_nnt`, `compute_nnt_threshold_delta`, `compute_posthoc_power_binary`, `compute_posthoc_power_continuous`, `compute_dor`, `deduplicate_statistical_stability`. Routes by study type (diagnostic → DOR only; observational → no power; phase_0_1 → skip).
- `pipeline/stage5_report.py` — **Implemented.** Score rule engine + structured report assembly. Exports `compute_suggested_score()` (collects deltas, applies cross-stage de-duplication, enforces boundary matrix with LTFU floor pierce and phase_0_1 lock) and `assemble_report()` (formats all stage outputs into plain-text report with exclusion/disclaimer handling). Also exports `deduplicate_stage4_deltas()` for QUADAS-2 cap, GRADE upgrade cap, and case-control overlap de-duplication.
- `references/` — Stage-specific specifications the agent reads before executing each stage:
  - `stages_0_1.md` — Stage 0 (study type routing) + Stage 1 (variable extraction with 3× CoT majority vote)
  - `stages_2_3.md` — Stage 2 (agentic MCID search, up to 5 rounds) + Stage 3 (deterministic math audit)
  - `stage_4.md` — Stage 4 (bias risk: RoB 2.0 / QUADAS-2 / GRADE, selected by study type)
  - `stage_5_report.md` — Stage 5 (report synthesis, narrative, optional score, optional markdown export)
  - `formulas.md` — All math formulas (Fragility Index, FQ, NNT/NNH, DOR, post-hoc power)
  - `eval_framework.md` — Validation experiments (3A–3F) and acceptance test definitions (T1–T8)
- `tests/` — Python test scripts that validate the deterministic math (Stage 3) and pipeline routing logic

## Key Domain Rules

- **LTFU > FI hard rule**: If lost-to-follow-up exceeds Fragility Index → −2 grades, no exceptions, never deduplicated with other rules
- **De-duplication**: {power < 0.80, N < domain standard, NNT > threshold} share one statistical stability dimension — only the most severe deduction applies
- **Study type routing**: `phase_0_1` skips Stages 2+3 and locks score to 1–2; `diagnostic` uses QUADAS-2 instead of RoB 2.0 and computes DOR instead of FI/NNT
- **Score disclaimer**: The 1–5 score is heuristic, pending expert calibration — always display the disclaimer

## Tech Context

- Stage 3 math is deterministic Python (scipy, statsmodels, numpy) — no LLM involvement
- Stage 5 score engine and report assembly are deterministic Python — no LLM involvement (the narrative summary is an agent task)
- Stages 0, 1, 2, 4 are agent reasoning tasks — the agent follows reference docs, no Python modules needed
- Tiered context strategy: abstract + methods + conclusion first (Tier 1); only escalate to full text on `needs_full_paper: true`
