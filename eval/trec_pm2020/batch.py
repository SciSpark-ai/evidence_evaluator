"""Parallel orchestrator for the TREC PM 2020 batch run.

Reads sample_500.csv, skips PMIDs already in checkpoint.completed (if --resume),
runs the remainder via ThreadPoolExecutor with `workers` threads, updates the
checkpoint atomically after each completion.

The runner is injected so tests can substitute a fake without touching the LLM.
"""

import csv
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List, Optional

from eval.trec_pm2020.emit import (
    Checkpoint, read_checkpoint, write_checkpoint, append_log,
)
from eval.trec_pm2020.runner import RunResult, run_one


RunnerFn = Callable[..., RunResult]


def _load_sample_pmids(sample_csv: str) -> List[str]:
    with open(sample_csv) as f:
        reader = csv.DictReader(f)
        return [row["pmid"] for row in reader]


def run_batch(
    sample_csv: str,
    results_dir: str,
    cache_dir: str,
    run_id: str,
    workers: int = 2,
    runner: Optional[RunnerFn] = None,
    resume: bool = True,
    limit: Optional[int] = None,
    model: str = "claude-opus-4-7",
    max_turns: int = 60,
    cwd: Optional[str] = None,
) -> Checkpoint:
    """Run the batch. Returns the final checkpoint."""
    runner = runner or run_one

    os.makedirs(results_dir, exist_ok=True)
    reports_dir = os.path.join(results_dir, "reports")
    json_dir = os.path.join(results_dir, "json")
    log_path = os.path.join(results_dir, "run_log.jsonl")
    cp_path = os.path.join(results_dir, "checkpoint.json")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(json_dir, exist_ok=True)

    cp = read_checkpoint(cp_path) if resume else Checkpoint(
        run_id=run_id, config={"model": model, "workers": workers, "max_turns": max_turns},
    )
    if not cp.run_id:
        cp.run_id = run_id
        cp.config = {"model": model, "workers": workers, "max_turns": max_turns}

    all_pmids = _load_sample_pmids(sample_csv)
    completed_set = set(cp.completed)
    failed_pmid_set = {f["pmid"] for f in cp.failed}
    todo = [p for p in all_pmids if p not in completed_set and p not in failed_pmid_set]
    if limit is not None:
        todo = todo[:limit]

    if not todo:
        print(f"Nothing to do — all {len(all_pmids)} PMIDs already accounted for.")
        return cp

    print(f"Running {len(todo)} PMIDs with {workers} workers (of {len(all_pmids)} total).")

    def _work(pmid: str) -> RunResult:
        append_log(log_path, {"pmid": pmid, "event": "started", "run_id": run_id})
        return runner(
            pmid=pmid, reports_dir=reports_dir, json_dir=json_dir,
            cache_dir=cache_dir, model=model, max_turns=max_turns, cwd=cwd,
        )

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_work, p): p for p in todo}
        for fut in as_completed(futures):
            pmid = futures[fut]
            try:
                result: RunResult = fut.result()
            except Exception as e:
                result = RunResult(pmid=pmid, status="error", error_msg=str(e))
            if result.status == "ok" or result.status.startswith("partial_"):
                cp.completed.append(result.pmid)
                append_log(log_path, {
                    "pmid": pmid, "event": "completed", "status": result.status,
                    "runtime_s": result.runtime_s,
                    "input_tokens": result.input_tokens,
                    "output_tokens": result.output_tokens,
                })
            else:
                cp.failed.append({
                    "pmid": pmid, "reason": result.status, "error_msg": result.error_msg,
                })
                append_log(log_path, {
                    "pmid": pmid, "event": "failed", "status": result.status,
                    "error_msg": result.error_msg,
                })
            write_checkpoint(cp_path, cp)
            n_done = len(cp.completed) + len(cp.failed)
            print(f"  [{n_done}/{len(all_pmids)}] {pmid} → {result.status} ({result.runtime_s:.1f}s)")

    return cp
