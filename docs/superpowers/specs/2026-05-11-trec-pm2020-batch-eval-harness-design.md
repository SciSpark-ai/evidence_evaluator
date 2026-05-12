# TREC PM 2020 Batch Evaluation Harness — Design Spec

**Date:** 2026-05-11
**Status:** Draft (pending user review)
**Author:** Tong Shan + Claude

---

## Overview

Build a batch harness that runs the Evidence Evaluator pipeline against a stratified 500-paper sample drawn from TREC Precision Medicine 2020's Phase 2 qrels (`qrels-expgains-phase2.txt`). The harness produces per-paper Markdown reports, structured JSON dumps of each stage, a joined master CSV, and a cost-accounting run log. A colleague performs the human comparison between Evidence Evaluator's automated 1–5 score and TREC's expert evidence tiers downstream.

## Goal

Generate Evidence Evaluator outputs for **500 unique PMIDs** sampled from TREC PM 2020's Phase 2 relevance judgments. Deliver the artifacts a colleague needs to do the comparison externally. Nothing in this harness performs the comparison itself.

## Non-Goals

- **No retrieval system.** We are not building an IR system that ranks documents per topic. TREC participants did that; we don't replicate it.
- **No comparison metrics.** No Spearman, Kendall, weighted kappa, nDCG, etc. in this codebase. Those live in the colleague's analysis.
- **No full-text escalation.** Abstract-only (Tier 1) for all 500 papers. Mirrors what TREC assessors saw.
- **No topic-conditional runs.** A PMID appearing under multiple topics gets one Evidence Evaluator run. Topic context does not enter the agent prompt.
- **No new pipeline logic.** Stages 0–5 are unchanged; the harness only orchestrates them.

## Locked Decisions

| Decision | Value | Rationale |
|---|---|---|
| Source dataset | `qrels-expgains-phase2.txt` (TREC PM 2020) | Phase 2 has per-(topic, PMID) evidence-tier judgments (graded 1/2/4/8 exponential gains), the natural comparator for our 1–5 score |
| Sample size | 500 unique PMIDs | Fits Pro/Max subscription usage budget over multi-day run; preserves statistical power across all four grade tiers |
| Stratification | 125 PMIDs per max-grade bucket {8, 4, 2, 1} | Balanced design oversamples scarce top tiers; gives colleague equal power across tiers |
| Sampling seed | `random.Random(seed=42)` | Reproducibility — anyone can re-derive the exact sample |
| Pipeline execution | Claude Agent SDK (headless `ClaudeSDKClient`) | Highest fidelity to the manually-produced pilot reports — agent reads SKILL.md, calls `pipeline/stage3_math.py` and `pipeline/stage5_report.py`, fetches data, writes report |
| Model | Claude Opus 4.7 | Matches the manual pilots; best reasoning quality for Stages 1/2/4 |
| Input modality | Abstract-only (Tier 1, no PMC escalation) | Matches what TREC assessors saw; keeps cost bounded; reproducible |
| Topic context | Not passed to agent | Pipeline is topic-agnostic by design; one run per unique PMID |
| Off-distribution papers | Stage 0 routes `other`; pipeline degrades gracefully; report records gaps | Honest handling rather than silent failures |
| Auth + billing | Claude Pro/Max subscription via SDK OAuth | Avoid out-of-pocket cost; harness reads `ANTHROPIC_API_KEY` if set, falls back to OAuth otherwise |
| Concurrency | 2 parallel workers on subscription | Low enough to avoid disrupting interactive Claude Code use during the run |
| Failure handling | Resilient + checkpointed; retries on transient errors; partial outputs preserved | Multi-day run cannot afford to lose progress |
| Output artifacts | Per-paper `.md` + per-paper `.json` + master `.csv` + run log JSONL | All four requested |
| Smoke gate | 5-paper smoke test diffed against existing pilots before full run | Confirms fidelity before committing several days of subscription usage |

---

## Sample Design

### Bucket math

| Max-grade bucket | Definition | Universe | Sample | Rate |
|---|---|---|---|---|
| 8 | PMID's highest TREC grade across all topics it appears in | 303 | 125 | 41% |
| 4 | ditto | 314 | 125 | 40% |
| 2 | ditto | 640 | 125 | 20% |
| 1 | ditto | 894 | 125 | 14% |
| **Total** | | **2,151** | **500** | **23%** |

### Sampling algorithm

```
1. Parse qrels-expgains-phase2.txt; drop grade=0 rows (Phase 1 irrelevant pool fillers).
2. For each unique PMID, compute max_grade = max(grade across (topic, grade) appearances).
3. Group PMIDs into four buckets by max_grade.
4. random.Random(seed=42).sample(bucket, 125) for each bucket.
5. Emit sample_500.csv with columns: pmid, max_grade, all_topic_grades.
   all_topic_grades format: "topic_a:grade_a,topic_b:grade_b" (semicolon-free)
```

The sample is computed once via `python -m eval.trec_pm2020.sample` and the resulting `sample_500.csv` is **committed to the repo** so anyone can reproduce it without re-running.

### Master CSV row count

With 246 of the 2,151 PMIDs appearing under 2+ topics (avg 1.16 topics/PMID), 500 sampled PMIDs yield ~578 master CSV rows after joining back to all (topic, grade) appearances. Each row represents one TREC judgment of one PMID — that's what the colleague compares against.

---

## Architecture

### Module layout

```
eval/trec_pm2020/
  __init__.py
  sample.py            # build sample_500.csv (run once, commit output)
  qrels.py             # parse qrels file → iterator of (topic, pmid, grade)
  pubmed.py            # E-utilities efetch w/ retry, rate-limit, on-disk cache
  runner.py            # single-PMID driver: ClaudeSDKClient, capture outputs
  batch.py             # parallel orchestrator: worker pool, checkpoint, resume
  emit.py              # write report.md, json, run_log.jsonl; build master.csv
  cli.py               # python -m eval.trec_pm2020 {sample,run,build-csv,...}

data/trec_pm2020/
  qrels-expgains-phase2.txt        # source (committed)
  sample_500.csv                   # the locked sample (committed)
  abstracts_cache/<pmid>.xml       # PubMed efetch responses (gitignored)

results/trec_pm2020/<run_id>/
  reports/evidence_report_<pmid>.md
  json/<pmid>.json
  master.csv                       # built post-run by emit.build_master_csv
  run_log.jsonl
  checkpoint.json                  # {completed: [...], failed: [{pmid, reason}]}
  config.json                      # locked params: model, max_turns, started_at
```

The installed skill at `skills/evidence-evaluator/` is **not** modified. The harness imports `pipeline/stage3_math.py` and `pipeline/stage5_report.py` via `sys.path` only for type-hinting and post-run validation; the agent itself imports them by running `cd skills/evidence-evaluator/ && python3 -c "..."` per SKILL.md.

### Data flow

```
sample_500.csv  ──┐
                  ▼
          batch.py (worker pool, N=2 default)
                  │
                  ▼  per PMID
            ┌─────────────┐
            │  pubmed.py  │  efetch → abstracts_cache/<pmid>.xml
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │  runner.py  │  ClaudeSDKClient
            │             │  - model: claude-opus-4-7
            │             │  - cwd: skills/evidence-evaluator/
            │             │  - allowed_tools: Bash, Read, Write, WebFetch
            │             │  - max_turns: 60
            │             │  - prompt template (see below)
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │   emit.py   │  → results/<run_id>/reports/<pmid>.md
            │             │  → results/<run_id>/json/<pmid>.json
            │             │  → results/<run_id>/run_log.jsonl (append)
            │             │  → results/<run_id>/checkpoint.json (update)
            └─────────────┘

After all 500 complete (or --resume converges):
    emit.build_master_csv(run_id):
        for each (topic, pmid, grade) in qrels:
            if pmid in sampled_set:
                join with json/<pmid>.json
                emit row to master.csv
```

### Agent prompt template (in `runner.py`)

```text
You are running the Evidence Evaluator skill at skills/evidence-evaluator/.

Read skills/evidence-evaluator/SKILL.md, then evaluate the paper whose PubMed
abstract XML is at data/trec_pm2020/abstracts_cache/{pmid}.xml.

Execute Stages 0 through 5 per SKILL.md. Use Tier 1 input (abstract + structured
abstract sections only) — do NOT attempt to fetch full text, even if you would
normally signal needs_full_paper. If the abstract lacks fields needed for any
stage, document the gap in the report and continue with the deterministic
math/scoring that the available fields support.

Save the final Markdown report to {results_dir}/reports/evidence_report_{pmid}.md
using the standard pilot template.

After saving the Markdown, emit one final assistant message containing ONLY a
fenced ```json block with the following schema:

{stage_outputs_schema}

Do not include any text outside the JSON block in that final message. The harness
parses it and writes it to {results_dir}/json/{pmid}.json.
```

`{stage_outputs_schema}` is the JSON Schema for the per-paper structured dump (Section: Output Schemas).

---

## Output Schemas

### `json/<pmid>.json`

```json
{
  "pmid": "23177514",
  "run_id": "20260512-1430",
  "model": "claude-opus-4-7",
  "started_at": "2026-05-12T14:30:00Z",
  "finished_at": "2026-05-12T14:32:22Z",
  "status": "ok",

  "stage0": {
    "study_type": "RCT_intervention",
    "confidence": 0.99,
    "skipped_stages": []
  },
  "stage1": {
    "initial_grade": 5,
    "n_intervention": 2373,
    "n_control": 2371,
    "events_intervention": 386,
    "events_control": 502,
    "p_value": 0.00001,
    "ltfu_count": 21,
    "alpha": 0.05,
    "effect_size_type": "binary",
    "blinding": "double",
    "randomization": "yes",
    "trial_phase": "III",
    "primary_outcome": "...",
    "pico": {"P": "...", "I": "...", "C": "...", "O": "..."},
    "low_confidence_fields": []
  },
  "stage2": {
    "mcid": 0.04,
    "mcid_unit": "ARR",
    "mcid_source": "ESC HF outcome trial convention via HR≤0.80 → ARR",
    "mcid_tier": 3,
    "effect_vs_mcid": "exceeds",
    "domain_n": 1000,
    "n_vs_domain": "above",
    "domain_nnt_threshold": 50,
    "nnt_vs_threshold": "favorable"
  },
  "stage3": {
    "fragility_index": 62,
    "fragility_quotient": 0.0261,
    "ltfu_exceeds_fi": false,
    "nnt": 20.4,
    "post_hoc_power": 0.939,
    "dor": null,
    "deltas": {"power_below_080": 0, "ltfu_gt_fi": 0}
  },
  "stage4": {
    "tool": "RoB 2.0",
    "overall_concern": "low",
    "domains": [
      {"domain": "randomization", "judgment": "low", "delta": 0},
      {"domain": "deviations", "judgment": "low", "delta": 0},
      {"domain": "missing_outcome", "judgment": "low", "delta": 0},
      {"domain": "measurement", "judgment": "low", "delta": 0},
      {"domain": "selective_reporting", "judgment": "low", "delta": 0}
    ],
    "surrogate_endpoint_delta": 0,
    "heterogeneity_delta": 0
  },
  "stage5": {
    "suggested_score": 5,
    "score_path": [
      {"step": "initial_grade", "value": 5},
      {"step": "stage2_deltas", "value": 0},
      {"step": "stage3_deltas", "value": 0},
      {"step": "stage4_deltas", "value": 0},
      {"step": "final", "value": 5}
    ],
    "deduplications_applied": []
  },

  "runtime_s": 142,
  "input_tokens": 18234,
  "output_tokens": 4912,
  "report_path": "reports/evidence_report_23177514.md"
}
```

For papers where a stage was skipped (`phase_0_1`) or partial (off-distribution, insufficient data), the corresponding stage field becomes `null` and `stage0.skipped_stages` lists what was skipped. `status` ∈ `{ok, partial_insufficient_data, partial_off_distribution, max_turns, fetch_error, invalid_pmid, error}`. For any non-`ok` status, the JSON additionally carries `error_msg` (one-line summary) and `error_trace` (optional, full traceback for `error`).

### `master.csv`

Columns:

| Column | Source | Type |
|---|---|---|
| `topic_id` | qrels file | int |
| `pmid` | qrels file | str |
| `trec_grade` | qrels file (per topic) | int (1/2/4/8) |
| `max_grade` | derived | int |
| `ee_score` | json.stage5.suggested_score | int (1–5) or null |
| `ee_study_type` | json.stage0.study_type | str |
| `ee_overall_concern` | json.stage4.overall_concern | str |
| `ee_fragility_index` | json.stage3.fragility_index | int or null |
| `ee_post_hoc_power` | json.stage3.post_hoc_power | float or null |
| `ee_dor` | json.stage3.dor | float or null |
| `report_path` | filesystem | str |
| `json_path` | filesystem | str |
| `run_status` | json.status | str |
| `runtime_s` | json.runtime_s | int |

### `run_log.jsonl`

One JSON object per line, append-only. Records: `{ts, pmid, event, model, tokens_in, tokens_out, attempt, error?}` where `event` ∈ `{started, retry, completed, failed, skipped_resume}`.

### `checkpoint.json`

```json
{
  "run_id": "20260512-1430",
  "config": {"model": "claude-opus-4-7", "workers": 2, "max_turns": 60},
  "completed": ["23177514", "23306912", ...],
  "failed": [{"pmid": "12345", "reason": "fetch_error", "attempts": 3}, ...]
}
```

---

## Failure Handling Matrix

| Failure | Detection | Action | Status field |
|---|---|---|---|
| PubMed efetch 5xx / timeout | HTTP / exception | Retry 3× exp backoff (1s, 4s, 16s); on final fail skip | `fetch_error` |
| PubMed efetch 4xx (retracted, invalid) | HTTP 400/404 | Skip, log | `invalid_pmid` |
| Anthropic 529 overloaded | SDK exception | Retry 5× exp backoff (2s → 60s) | (recover or `error`) |
| Subscription rate-limit window hit | SDK 429 / specific error | Pause whole pool until reset, then resume | (recover) |
| Agent exceeds `max_turns=60` | SDK signal | Save partial output, log | `max_turns` |
| Stage 0 outputs `study_type=other` | Agent JSON | Continue with degraded pipeline | `partial_off_distribution` |
| Stage 1 critical fields missing | Agent JSON `low_confidence_fields` non-empty | Continue; report flags it | `partial_insufficient_data` |
| Other agent crash | SDK exception | Log full trace, skip | `error` |

Failures get re-tried at the end of the run via `python -m eval.trec_pm2020 run --resume --retry-failed`.

---

## Run Topology

### Auth

```python
# runner.py picks auth in this order:
# 1. ANTHROPIC_API_KEY env var (if set) → API billing
# 2. Otherwise → OAuth from `claude` CLI login (subscription billing)
# This makes the same harness work for both modes without code change.
```

### Concurrency

- Default: `--workers 2`
- Configurable up to `--workers 8`
- Each worker holds one `ClaudeSDKClient` instance for its current paper
- PubMed efetch throttle: 3 req/s without `NCBI_API_KEY`, 10 req/s with — recommend setting one

### Checkpointing + resume

`checkpoint.json` is rewritten atomically after every PMID completes. `--resume` reads it and skips any PMID in `completed`. `--retry-failed` retries everything in `failed` once.

### Hosting + duration

- `tmux new -s trec_run` then `python -m eval.trec_pm2020 run --resume`
- Detach: `Ctrl-b d`; reattach: `tmux a -t trec_run`
- Expected wall clock: 3–10 days at 2 workers on subscription
- Each PMID: ~90–180 s pipeline time when not throttled

---

## Testing Strategy

### Unit tests

`tests/eval/test_trec_pm2020_*.py`:

- `test_sample.py` — reproducibility (seed=42 produces same `sample_500.csv`), bucket sizes (125/125/125/125), `all_topic_grades` formatting
- `test_qrels.py` — parser handles whitespace variations, ignores grade=0 rows
- `test_pubmed.py` — efetch retry/backoff (mock requests), cache hit short-circuits network call
- `test_emit.py` — master CSV column types, join correctness on a synthetic 3-PMID fixture

Target: ~30 unit tests, fully offline (no network), running in <5 s.

### Smoke gate (mandatory before full 500 run)

`python -m eval.trec_pm2020 run --limit 5 --workers 1 --run-id smoke`

Then visually diff the 5 generated reports against the existing pilots in `paper/pilot_results/`. Confirm:

1. Markdown structure matches pilot template (4 sections + traces + narrative + score)
2. Stage 3 computation traces present and numerically consistent with `pipeline/stage3_math.py` re-runs
3. Stage 5 score path is fully documented
4. JSON dump is well-formed and parseable

If anything drifts materially from pilot quality, stop and revise the agent prompt template before kicking off the 500 run.

### Post-run validation

`python -m eval.trec_pm2020 validate <run_id>`:

- All 500 PMIDs accounted for (completed ∪ failed)
- No silent partials (every report has a `status` field)
- Master CSV row count matches expected ~578 ± a few (some sampled PMIDs may map to >1 topic)
- Re-run `pipeline/stage3_math.run_stage3()` on the `stage1` numeric fields of each JSON and confirm Stage 3 outputs match (catches any agent transcription errors)

---

## Out of Scope

- Comparison metrics or analysis (colleague's work, separate codebase)
- Topic-conditional agent prompts (one run per unique PMID)
- PMC full-text fetching or escalation logic
- A second run on Sonnet or Haiku for cost comparison
- Re-running TREC participant systems
- Any UI / dashboard

---

## Open Items for Future Iterations

1. **Optional API-billed expansion run** — if the colleague's analysis on 500 papers shows promising agreement, a follow-up could expand to all 2,151 relevant PMIDs using `ANTHROPIC_API_KEY` for parallel API billing. The harness already supports this — same code, different auth.
2. **PMC full-text re-run** — for papers flagged `partial_insufficient_data`, an optional re-run with `--allow-pmc-fulltext` could escalate to PubMed Central where openly available. Out of scope for v1.
3. **Per-topic context experiment** — eventually, a variant run that passes the TREC topic (disease + variant + treatment) as context could quantify how much topic-awareness shifts the EE score. Decided against for v1 to keep the comparison clean.

---

## File Manifest

New:
- `eval/trec_pm2020/__init__.py`
- `eval/trec_pm2020/sample.py`
- `eval/trec_pm2020/qrels.py`
- `eval/trec_pm2020/pubmed.py`
- `eval/trec_pm2020/runner.py`
- `eval/trec_pm2020/batch.py`
- `eval/trec_pm2020/emit.py`
- `eval/trec_pm2020/cli.py`
- `tests/eval/test_sample.py`
- `tests/eval/test_qrels.py`
- `tests/eval/test_pubmed.py`
- `tests/eval/test_emit.py`
- `data/trec_pm2020/qrels-expgains-phase2.txt` (committed)
- `data/trec_pm2020/sample_500.csv` (committed after first sample run)
- `.gitignore` additions: `data/trec_pm2020/abstracts_cache/`, `results/trec_pm2020/`

Modified: none (the installed skill at `skills/evidence-evaluator/` is unchanged).

---

## Approvals

- 2026-05-11 — Goal scoped to "generate outputs, colleague does comparison externally."
- 2026-05-11 — Scope narrowed from all 2,151 relevant PMIDs to a stratified sample of 500 to fit subscription usage.
- 2026-05-11 — Stratification: balanced 125/125/125/125 across max-grade buckets {8, 4, 2, 1}.
- 2026-05-11 — Execution: Claude Agent SDK on Opus 4.7, abstract-only (Tier 1), topic-agnostic (one run per unique PMID).
- 2026-05-11 — Output artifacts: per-paper Markdown + per-paper JSON + master CSV + run log + cost accounting (all four).
- 2026-05-11 — Ops: resilient + checkpointed local run, 2 parallel workers default, tmux/nohup hosting.
- 2026-05-11 — Auth: subscription via SDK OAuth for v1; `ANTHROPIC_API_KEY` env var supported as a no-code-change toggle for any future API-billed re-run.
- 2026-05-11 — 5-paper smoke gate diffed against existing pilots before kicking off the full 500 — mandatory.
