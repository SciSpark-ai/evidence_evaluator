# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Evidence Evaluator is an installable Claude Code plugin containing a 6-stage agentic pipeline that produces structured evidence quality reports for clinical/biomedical research papers. Distributed as an open-source skill via `npx skills add SciSpark-ai/evidence_evaluator`.

## Repo Structure

```
.claude-plugin/plugin.json          ← Plugin manifest
skills/evidence-evaluator/
  SKILL.md                          ← Skill entry point
  pipeline/stage3_math.py           ← Stage 3: deterministic math (no LLM)
  pipeline/stage5_report.py         ← Stage 5: score engine + report assembly
  references/                       ← Stage specs, formulas, eval framework
tests/                              ← Development only (not part of skill package)
paper/                              ← Claw4S conference research note + pilot results
```

## Running Tests

```bash
pip install scipy statsmodels numpy

python tests/test_stage3_math.py                 # 147/147 pass
python tests/test_stage5_report.py               # 70/70 pass
```

Tests use a custom pass/fail counter (not pytest). They print results to stdout.

## Architecture

- `skills/evidence-evaluator/SKILL.md` — Skill entry point. Defines pipeline, stage execution order, output format, and Python code usage.
- `skills/evidence-evaluator/pipeline/stage3_math.py` — Deterministic math audit. Exports `run_stage3()`, `compute_fragility_index`, `compute_nnt`, `compute_dor`, etc. Routes by study type.
- `skills/evidence-evaluator/pipeline/stage5_report.py` — Score rule engine + report assembly. Exports `compute_suggested_score()`, `assemble_report()`, `deduplicate_stage4_deltas()`.
- `skills/evidence-evaluator/references/` — Stage specs the agent reads before executing each stage.
- `tests/` — Dev-only validation tests (not part of installed skill).
- `paper/` — Claw4S 2026 conference submission (research note, pilot results, submission script).

## Key Domain Rules

- **LTFU definition**: Includes exclusions + withdrawals + AE-related dropouts (all attrition sources). Deaths counted as primary endpoint events are NOT LTFU.
- **LTFU > FI hard rule**: LTFU exceeds FI → −2 grades, no exceptions, never deduplicated
- **MCID derivation**: Follow tier hierarchy strictly (Tier 1→2→3→4, stop at first hit). For Tier 3 HR thresholds, convert to ARR via `CER × (1 − HR)` using Stage 1 CER. Document the full derivation chain.
- **Effect vs MCID**: Binary only (exceeds or below). No "borderline" category.
- **De-duplication**: {power < 0.80, N < domain standard, NNT > threshold} → apply only the one with largest absolute delta; if equal, apply any one. Document which were suppressed.
- **Domain N**: Agent-searched via PubMed/FDA, not a fixed table. If not found, skip deduction.
- **NNT threshold**: Agentic search takes priority over reference table. If domain not in table and search finds nothing, skip deduction.
- **Study type routing**: `phase_0_1` skips Stages 2+3, locks score 1–2; `diagnostic` uses QUADAS-2 + DOR
- **Initial grade**: N takes precedence over phase label. Grade 5 requires ALL of: multi-center + double-blind + N > 1000.
- **Score disclaimer**: 1–5 score is heuristic, pending expert calibration — always display disclaimer

## Pilot Results

5 pilot papers validated end-to-end, one per study type. All deterministic outputs (Stage 3 metrics, Stage 5 scores) confirmed reproducible across reruns after spec tightening.

| Paper | Type | Score | Key Metrics |
|---|---|---|---|
| DAPA-HF (McMurray 2019) | RCT | 5/5 | FI=62, NNT=20.4, Power=93.9% |
| FIT meta-analysis (Lee 2014) | Diagnostic | 4/5 | DOR=57.42 (CI: 32.25–102.24) |
| JUPITER (Ridker 2008) | Preventive | 5/5 | FI=67, NNT=81.7, Power=85.5% |
| Doll & Hill 1950 | Observational | 4/5 | FI=18, OR=14.04, GRADE +1 |
| Topalian 2012 (anti-PD-1) | Phase 0/I | 2/5 | Stages 2+3 skipped, score locked 1–2 |

Reports in `paper/pilot_results/`. Research note in `paper/research_note.md`.

## Claw4S 2026 Submission

- **clawRxiv post:** #272 (final) — http://18.118.210.52/api/posts/272
- **Claw agent name:** Cu's CCbot
- **Human author:** Tong Shan
- **API key:** `oc_a4196eaa6ecdf22ed15cd7ffeb3a3e72d04de0a41b86057e51dbed7c49a18643`
- **Submit script:** `bash paper/submission/submit.sh <API_KEY>`
- **Conference site:** https://claw4s.github.io/
- **Submission spec:** https://claw4s.github.io/Claw4S_conference.md
- **Deadline:** April 5, 2026
- **Note:** Posts #268, #269 are earlier drafts with missing fields — #272 is the correct submission

## Sibling Repos

- **Meta-Analyst:** https://github.com/SciSpark-ai/meta_analyst — end-to-end clinical meta-analysis of RCTs (clawRxiv #287). Composes with Evidence Evaluator for per-study RoB 2.0.
- **Planned:** Meta-Reviewer (inter-rater agreement benchmark), Systematic Screener (PRISMA screening)

## Tech Context

- Stage 3 and Stage 5 score engine are deterministic Python (scipy, statsmodels, numpy)
- Stages 0, 1, 2, 4 are agent reasoning tasks — no Python modules needed
- All Python commands must run from `skills/evidence-evaluator/` directory for imports to resolve
- Reference docs in `references/` contain explicit signaling questions (RoB 2.0), classification tables (effect size type, surrogate endpoint, objective/subjective outcome), and fallback hierarchies (NNT threshold, domain N) to minimize agent interpretation variance
