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
eval/trec_pm2020/                   ← TREC PM 2020 batch evaluation harness
data/trec_pm2020/                   ← qrels + abstracts cache (cache gitignored)
results/trec_pm2020/                ← Harness output files (gitignored)
tests/                              ← Development only (not part of skill package)
paper/                              ← Claw4S conference research note + pilot results
```

## Running Tests

```bash
pip install scipy statsmodels numpy

python tests/test_stage3_math.py                 # 147/147 pass
python tests/test_stage5_report.py               # 70/70 pass
python tests/eval/test_qrels.py                  # eval harness: qrels parser
python tests/eval/test_sample.py                 # eval harness: stratified sampler (8/8 pass)
python tests/eval/test_pubmed.py                 # eval harness: PubMed efetch + cache (7/7 pass)
python tests/eval/test_emit.py                   # eval harness: emit writers + build_master_csv (24/24 pass)
python tests/eval/test_runner.py                 # eval harness: prompt builder + JSON extractor (9/9 pass)
python tests/eval/test_batch.py                  # eval harness: parallel orchestrator + checkpoint/resume (8/8 pass)
```

Tests use a custom pass/fail counter (not pytest). They print results to stdout.

## Architecture

- `skills/evidence-evaluator/SKILL.md` — Skill entry point. Defines pipeline, stage execution order, output format, and Python code usage.
- `skills/evidence-evaluator/pipeline/stage3_math.py` — Deterministic math audit. Exports `run_stage3()`, `compute_fragility_index`, `compute_nnt`, `compute_dor`, etc. Routes by study type.
- `skills/evidence-evaluator/pipeline/stage5_report.py` — Score rule engine + report assembly. Exports `compute_suggested_score()`, `assemble_report()`, `deduplicate_stage4_deltas()`.
- `skills/evidence-evaluator/references/` — Stage specs the agent reads before executing each stage.
- `eval/trec_pm2020/qrels.py` — Parses `qrels-expgains-phase2.txt`. Exports `parse_qrels()`, `QrelRow`.
- `eval/trec_pm2020/sample.py` — Stratified 500-PMID sampler. Exports `compute_max_grades()`, `stratified_sample()`, `SampleRow`, `write_sample_csv()`. Groups unique PMIDs by max-grade across topics, then `random.Random(seed=42).sample(bucket, 125)` per bucket {8, 4, 2, 1}.
- `eval/trec_pm2020/pubmed.py` — PubMed E-utilities efetch with retry + on-disk cache. Exports `fetch_abstract(pmid, cache_dir, ...)`, `PubMedError`. Caches to `data/trec_pm2020/abstracts_cache/<pmid>.xml`. Retries 5xx (exp backoff 1s/4s/16s); raises `PubMedError` on 4xx. Respects `NCBI_API_KEY` env var (10 req/s vs 3 req/s default).
- `eval/trec_pm2020/emit.py` — Output writers for the batch harness. Exports `write_report()`, `write_json()`, `append_log()`, `read_checkpoint()`, `write_checkpoint()`, `Checkpoint`, and `build_master_csv()`. `build_master_csv(qrels_path, sample_csv, json_dir, out_path)` joins per-paper JSON dumps with the qrels file to produce a flat master.csv (one row per topic×pmid pair, TREC fields + EE fields).
- `eval/trec_pm2020/PROMPT_TEMPLATE.md` — Agent prompt template for one-PMID runs. Uses Python `.format()` placeholders `{pmid}`, `{reports_dir}`, `{json_dir}`; JSON schema example uses `{{`/`}}` escapes. Instructs the agent to read `SKILL.md`, work abstract-only (no full-text fetch), run Stages 0→5, save the Markdown report, then emit a single fenced `\`\`\`json` block.
- `eval/trec_pm2020/runner.py` — Single-PMID SDK driver. Exports `RunResult` (dataclass), `build_prompt(pmid, reports_dir, json_dir)`, `extract_final_json(transcript)`, `run_one(pmid, ...)`. SDK call isolated in `_run_agent()` (uses `claude_agent_sdk.query()` — one-shot batch API). Status strings: `ok`, `partial_insufficient_data`, `partial_off_distribution`, `max_turns`, `fetch_error`, `invalid_pmid`, `error`.
- `eval/trec_pm2020/batch.py` — Parallel orchestrator. Exports `run_batch(sample_csv, results_dir, cache_dir, run_id, workers=2, runner=None, resume=True, limit=None, ...)`. Reads `sample_500.csv`, skips PMIDs already in `checkpoint.completed` (when `resume=True`), runs remainder via `ThreadPoolExecutor`, updates `checkpoint.json` atomically after each completion. Runner is injected for testability.
- `eval/trec_pm2020/cli.py` — argparse CLI entry point. Subcommands: `sample` (regenerate sample_500.csv), `run` (kick off batch), `build-csv` (emit master.csv from JSON), `validate` (sanity-check run).
- `eval/trec_pm2020/__main__.py` — Module entry for `python -m eval.trec_pm2020 <cmd>`.
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

## TREC PM 2020 Comparison (in progress)

Stratified sample of 500 PMIDs from `qrels-expgains-phase2.txt` (125 per max-grade
bucket, seed=42). Harness runs the full pipeline via `claude-agent-sdk` on Opus 4.7
with Tier 1 (abstract-only) input. Outputs land in `results/trec_pm2020/<run_id>/`
(gitignored). A colleague performs the human comparison against TREC Phase 2 evidence
tiers externally.

- **Run a smoke test (5 papers):** `tmux new -s trec_smoke "python3 -m eval.trec_pm2020 run --limit 5 --workers 1 --run-id smoke"`
- **Run the full 500:** `tmux new -s trec_run "python3 -m eval.trec_pm2020 run --workers 2"`
- **Build master CSV after:** `python3 -m eval.trec_pm2020 build-csv results/trec_pm2020/<run_id>`
- **Validate completion:** `python3 -m eval.trec_pm2020 validate results/trec_pm2020/<run_id>`

Auth: harness uses `ANTHROPIC_API_KEY` if set, else falls back to OAuth from `claude` CLI
(subscription billing). The 500-paper run is designed to fit within Max-tier subscription
limits over a few days; the user controls when LLM runs happen.

Design: `docs/superpowers/specs/2026-05-11-trec-pm2020-batch-eval-harness-design.md`.
Plan: `docs/superpowers/plans/2026-05-11-trec-pm2020-batch-eval-harness.md`.

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
- TREC PM 2020 batch harness additionally requires: `pip install claude-agent-sdk requests`
