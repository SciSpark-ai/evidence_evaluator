"""CLI for the TREC PM 2020 batch evaluation harness.

Run with: python -m eval.trec_pm2020 <command> [...]
"""

import argparse
import os
import sys
from datetime import datetime

from eval.trec_pm2020 import sample as sample_mod
from eval.trec_pm2020 import batch as batch_mod
from eval.trec_pm2020 import emit as emit_mod


REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def cmd_sample(args: argparse.Namespace) -> int:
    """Regenerate sample_500.csv (already committed; this re-derives for sanity)."""
    sample_mod.main()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    """Kick off the batch run."""
    run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M")
    sample_csv = args.sample or os.path.join(REPO_ROOT, "data/trec_pm2020/sample_500.csv")
    results_dir = args.results_dir or os.path.join(REPO_ROOT, "results/trec_pm2020", run_id)
    cache_dir = args.cache_dir or os.path.join(REPO_ROOT, "data/trec_pm2020/abstracts_cache")

    cp = batch_mod.run_batch(
        sample_csv=sample_csv, results_dir=results_dir, cache_dir=cache_dir,
        run_id=run_id, workers=args.workers, resume=args.resume,
        retry_failed=args.retry_failed,
        limit=args.limit, model=args.model, max_turns=args.max_turns,
        cwd=REPO_ROOT,
    )
    print(f"\nRun complete. Completed: {len(cp.completed)}, Failed: {len(cp.failed)}")
    return 0 if not cp.failed else 1


def cmd_build_csv(args: argparse.Namespace) -> int:
    """Build the master.csv from a completed run."""
    qrels_path = os.path.join(REPO_ROOT, "data/trec_pm2020/qrels-expgains-phase2.txt")
    sample_csv = os.path.join(REPO_ROOT, "data/trec_pm2020/sample_500.csv")
    json_dir = os.path.join(args.results_dir, "json")
    out_path = os.path.join(args.results_dir, "master.csv")
    n = emit_mod.build_master_csv(qrels_path, sample_csv, json_dir, out_path)
    print(f"Wrote {n} rows to {out_path}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Sanity-check a completed run."""
    cp_path = os.path.join(args.results_dir, "checkpoint.json")
    cp = emit_mod.read_checkpoint(cp_path)
    sample_csv = os.path.join(REPO_ROOT, "data/trec_pm2020/sample_500.csv")
    import csv
    with open(sample_csv) as f:
        all_pmids = {row["pmid"] for row in csv.DictReader(f)}
    accounted = set(cp.completed) | {f["pmid"] for f in cp.failed}
    missing = all_pmids - accounted
    print(f"Sample size:      {len(all_pmids)}")
    print(f"Completed:        {len(cp.completed)}")
    print(f"Failed:           {len(cp.failed)}")
    print(f"Missing (unrun):  {len(missing)}")
    if missing:
        print("First 10 missing PMIDs: " + ", ".join(sorted(missing)[:10]))
        return 1
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.trec_pm2020")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sample = sub.add_parser("sample", help="Regenerate sample_500.csv")
    p_sample.set_defaults(func=cmd_sample)

    p_run = sub.add_parser("run", help="Kick off the batch run")
    p_run.add_argument("--run-id", type=str, default=None)
    p_run.add_argument("--sample", type=str, default=None)
    p_run.add_argument("--results-dir", type=str, default=None)
    p_run.add_argument("--cache-dir", type=str, default=None)
    p_run.add_argument("--workers", type=int, default=2)
    p_run.add_argument("--limit", type=int, default=None,
                       help="Cap number of PMIDs (for smoke tests)")
    p_run.add_argument("--resume", action="store_true", default=True)
    p_run.add_argument("--no-resume", dest="resume", action="store_false")
    p_run.add_argument("--retry-failed", action="store_true", default=False,
                       help="Re-attempt PMIDs in checkpoint.failed (e.g. after a rate-limit-induced batch of errors).")
    p_run.add_argument("--model", type=str, default="claude-opus-4-7")
    p_run.add_argument("--max-turns", type=int, default=60)
    p_run.set_defaults(func=cmd_run)

    p_csv = sub.add_parser("build-csv", help="Build master.csv from a completed run")
    p_csv.add_argument("results_dir", type=str)
    p_csv.set_defaults(func=cmd_build_csv)

    p_val = sub.add_parser("validate", help="Sanity-check a completed run")
    p_val.add_argument("results_dir", type=str)
    p_val.set_defaults(func=cmd_validate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
