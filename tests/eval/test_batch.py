"""Tests for eval/trec_pm2020/batch.py.

The runner is monkey-patched with a fake so we can test queueing,
checkpoint updates, and resume logic without hitting the LLM.
"""

import os
import sys
import tempfile
import shutil
import csv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020 import batch
from eval.trec_pm2020.runner import RunResult
from eval.trec_pm2020.emit import read_checkpoint

PASS = 0
FAIL = 0


def check(name, got, expected):
    global PASS, FAIL
    if got == expected:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}: got {got!r}, expected {expected!r}")


def write_sample_csv(path, pmids):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pmid", "max_grade", "all_topic_grades"])
        for p in pmids:
            w.writerow([p, 8, f"1:8"])


def test_runs_all_pmids_when_no_checkpoint():
    tmpdir = tempfile.mkdtemp()
    try:
        sample = os.path.join(tmpdir, "sample.csv")
        write_sample_csv(sample, ["A", "B", "C"])
        results_dir = os.path.join(tmpdir, "run1")

        called = []
        def fake_runner(pmid, reports_dir, json_dir, cache_dir, **kw):
            called.append(pmid)
            return RunResult(pmid=pmid, status="ok", runtime_s=0.1)

        batch.run_batch(
            sample_csv=sample, results_dir=results_dir,
            cache_dir=os.path.join(tmpdir, "cache"),
            run_id="run1", workers=2, runner=fake_runner,
        )
        check("ran all 3", sorted(called), ["A", "B", "C"])

        cp = read_checkpoint(os.path.join(results_dir, "checkpoint.json"))
        check("checkpoint has 3", sorted(cp.completed), ["A", "B", "C"])
    finally:
        shutil.rmtree(tmpdir)


def test_skips_already_completed_pmids():
    tmpdir = tempfile.mkdtemp()
    try:
        sample = os.path.join(tmpdir, "sample.csv")
        write_sample_csv(sample, ["A", "B", "C"])
        results_dir = os.path.join(tmpdir, "run1")
        os.makedirs(results_dir)

        from eval.trec_pm2020.emit import write_checkpoint, Checkpoint
        write_checkpoint(
            os.path.join(results_dir, "checkpoint.json"),
            Checkpoint(run_id="run1", config={}, completed=["A"], failed=[]),
        )

        called = []
        def fake_runner(pmid, **kw):
            called.append(pmid)
            return RunResult(pmid=pmid, status="ok", runtime_s=0.1)

        batch.run_batch(
            sample_csv=sample, results_dir=results_dir,
            cache_dir=os.path.join(tmpdir, "cache"),
            run_id="run1", workers=1, runner=fake_runner, resume=True,
        )
        check("only B and C ran", sorted(called), ["B", "C"])

        cp = read_checkpoint(os.path.join(results_dir, "checkpoint.json"))
        check("checkpoint has all 3", sorted(cp.completed), ["A", "B", "C"])
    finally:
        shutil.rmtree(tmpdir)


def test_records_failures_in_checkpoint():
    tmpdir = tempfile.mkdtemp()
    try:
        sample = os.path.join(tmpdir, "sample.csv")
        write_sample_csv(sample, ["A", "B"])
        results_dir = os.path.join(tmpdir, "run1")

        def fake_runner(pmid, **kw):
            if pmid == "B":
                return RunResult(pmid=pmid, status="fetch_error",
                                 error_msg="boom", runtime_s=0.01)
            return RunResult(pmid=pmid, status="ok", runtime_s=0.01)

        batch.run_batch(
            sample_csv=sample, results_dir=results_dir,
            cache_dir=os.path.join(tmpdir, "cache"),
            run_id="run1", workers=1, runner=fake_runner,
        )
        cp = read_checkpoint(os.path.join(results_dir, "checkpoint.json"))
        check("completed has A only", cp.completed, ["A"])
        check("failed has B", cp.failed[0]["pmid"], "B")
        check("failure reason", cp.failed[0]["reason"], "fetch_error")
    finally:
        shutil.rmtree(tmpdir)


def test_limit_caps_count():
    tmpdir = tempfile.mkdtemp()
    try:
        sample = os.path.join(tmpdir, "sample.csv")
        write_sample_csv(sample, ["A", "B", "C", "D", "E"])
        results_dir = os.path.join(tmpdir, "run1")

        called = []
        def fake_runner(pmid, **kw):
            called.append(pmid)
            return RunResult(pmid=pmid, status="ok", runtime_s=0.01)

        batch.run_batch(
            sample_csv=sample, results_dir=results_dir,
            cache_dir=os.path.join(tmpdir, "cache"),
            run_id="run1", workers=1, runner=fake_runner, limit=2,
        )
        check("only 2 ran", len(called), 2)
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    for fn in [test_runs_all_pmids_when_no_checkpoint,
               test_skips_already_completed_pmids,
               test_records_failures_in_checkpoint,
               test_limit_caps_count]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
