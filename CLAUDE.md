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
```

Tests use a custom pass/fail counter (not pytest). They print results to stdout with checkmark/cross indicators.

## Architecture

The repo contains no application code — it is a **skill specification + reference library** that an LLM agent follows at runtime:

- `SKILL.md` — Entry point. Defines the full pipeline, stage execution order, de-duplication rules, and output format. This is what the agent reads to run an evaluation.
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
- Stages 1, 2, 4, 5 use LLM (Claude Sonnet via GMI Cloud OpenAI-compatible API)
- Tiered context strategy: abstract + methods + conclusion first (Tier 1); only escalate to full text on `needs_full_paper: true`
