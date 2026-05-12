"""Parallel orchestrator for the TREC PM 2020 batch run.

Reads sample_500.csv, skips PMIDs already in checkpoint.completed (if --resume),
runs the remainder via ThreadPoolExecutor with `workers` threads, updates the
checkpoint atomically after each completion.

The runner is injected so tests can substitute a fake without touching the LLM.
"""

import csv
import os
import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from typing import Callable, List, Optional

from eval.trec_pm2020.emit import (
    Checkpoint, read_checkpoint, write_checkpoint, append_log,
    append_progress_tsv,
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
    retry_failed: bool = False,
    limit: Optional[int] = None,
    model: str = "claude-opus-4-7",
    max_turns: int = 60,
    cwd: Optional[str] = None,
    stop_after_consecutive_errors: Optional[int] = None,
) -> Checkpoint:
    """Run the batch. Returns the final checkpoint.

    With `retry_failed=True`, PMIDs previously in `cp.failed` are re-attempted
    and their prior failure entries are cleared from the checkpoint before retry.

    With `stop_after_consecutive_errors=N`, halts the batch after N back-to-back
    error results (typical rate-limit signature). Sets `cp.last_stop_reason` to
    "circuit_breaker" and `cp.first_error_at_iso` to the UTC ISO timestamp of
    the first error in the failing cluster. Remaining futures are cancelled
    where possible; any that complete after the break are still recorded.
    """
    runner = runner or run_one

    os.makedirs(results_dir, exist_ok=True)
    reports_dir = os.path.join(results_dir, "reports")
    json_dir = os.path.join(results_dir, "json")
    log_path = os.path.join(results_dir, "run_log.jsonl")
    cp_path = os.path.join(results_dir, "checkpoint.json")
    progress_path = os.path.join(results_dir, "progress.tsv")
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
    if retry_failed:
        # Clear previously-failed entries so they get re-attempted in this run.
        cp.failed = []
        failed_pmid_set: set[str] = set()
    else:
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

    consecutive_errors = 0
    first_error_at: Optional[datetime] = None
    stop_reason = "completed"

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
                consecutive_errors = 0
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
                if result.status == "error":
                    if first_error_at is None:
                        first_error_at = datetime.now(timezone.utc)
                    consecutive_errors += 1
                append_log(log_path, {
                    "pmid": pmid, "event": "failed", "status": result.status,
                    "error_msg": result.error_msg,
                })
            write_checkpoint(cp_path, cp)
            n_done = len(cp.completed) + len(cp.failed)
            # Pull score + study type out of result.json_data for the progress row
            jd = result.json_data or {}
            score = (jd.get("stage5") or {}).get("suggested_score")
            study_type = (jd.get("stage0") or {}).get("study_type")
            append_progress_tsv(progress_path, {
                "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "pmid": pmid,
                "status": result.status,
                "score": "" if score is None else score,
                "study_type": study_type or "",
                "runtime_s": f"{result.runtime_s:.1f}",
                "output_tokens": result.output_tokens,
                "completed": len(cp.completed),
                "failed": len(cp.failed),
                "total": len(all_pmids),
            })
            print(f"  [{n_done}/{len(all_pmids)}] {pmid} → {result.status} ({result.runtime_s:.1f}s)")

            # Circuit breaker: bail out if a sustained cluster of errors hits.
            if (stop_after_consecutive_errors is not None
                    and consecutive_errors >= stop_after_consecutive_errors):
                stop_reason = "circuit_breaker"
                print(f"\n  [circuit breaker] {consecutive_errors} consecutive errors — halting batch.")
                for f in futures:
                    if not f.done():
                        f.cancel()
                break

    cp.last_stop_reason = stop_reason
    cp.first_error_at_iso = first_error_at.isoformat() if first_error_at else ""
    write_checkpoint(cp_path, cp)
    return cp


def run_loop(
    sample_csv: str,
    results_dir: str,
    cache_dir: str,
    run_id: str,
    workers: int = 1,
    stop_after_consecutive_errors: int = 3,
    cooldown_buffer_minutes: int = 5,
    model: str = "claude-opus-4-7",
    max_turns: int = 60,
    cwd: Optional[str] = None,
    max_iterations: Optional[int] = None,
) -> Checkpoint:
    """Run batches in a loop with auto-resume after rate-limit cooldowns.

    Strategy: call run_batch with retry_failed=True and the given circuit-breaker
    threshold. On "circuit_breaker" stop, sleep until 5h + buffer after the first
    failing call (which clears the rolling subscription cap), then re-enter the loop.
    Exits when run_batch returns "completed" or `max_iterations` is reached.
    """
    cp_path = os.path.join(results_dir, "checkpoint.json")
    iteration = 0
    while True:
        iteration += 1
        if max_iterations is not None and iteration > max_iterations:
            print(f"\n[loop] reached max_iterations={max_iterations}; exiting.")
            return read_checkpoint(cp_path)

        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"\n========================================================")
        print(f"[loop] iteration {iteration} starting at {ts}")
        print(f"========================================================")
        cp = run_batch(
            sample_csv=sample_csv, results_dir=results_dir, cache_dir=cache_dir,
            run_id=run_id, workers=workers,
            resume=True, retry_failed=True,
            limit=None, model=model, max_turns=max_turns, cwd=cwd,
            stop_after_consecutive_errors=stop_after_consecutive_errors,
        )
        print(f"\n[loop] iteration {iteration} stop_reason={cp.last_stop_reason} "
              f"completed={len(cp.completed)} failed={len(cp.failed)}")

        if cp.last_stop_reason == "completed":
            if cp.failed:
                print(f"[loop] batch ended without circuit-breaker but {len(cp.failed)} "
                      f"PMIDs remain in failed — exiting (unrecoverable).")
            else:
                print(f"[loop] all papers complete — exiting.")
            return cp

        if cp.last_stop_reason != "circuit_breaker":
            print(f"[loop] unexpected stop_reason={cp.last_stop_reason!r}; exiting.")
            return cp

        if not cp.first_error_at_iso:
            print(f"[loop] circuit_breaker but no first_error_at recorded; exiting.")
            return cp
        first_err = datetime.fromisoformat(cp.first_error_at_iso)
        wake_at = first_err + timedelta(hours=5, minutes=cooldown_buffer_minutes)
        now = datetime.now(timezone.utc)
        sleep_s = (wake_at - now).total_seconds()
        if sleep_s > 0:
            print(f"[loop] sleeping {sleep_s/3600:.2f}h until {wake_at.isoformat()} "
                  f"(5h after first error + {cooldown_buffer_minutes}min buffer)")
            _time.sleep(sleep_s)
        else:
            print(f"[loop] cooldown already elapsed; resuming immediately.")
