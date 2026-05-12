"""Tests for eval/trec_pm2020/emit.py"""

import json
import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020.emit import (
    write_report, write_json, append_log,
    read_checkpoint, write_checkpoint, Checkpoint,
)

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


def test_write_report_creates_file():
    tmpdir = tempfile.mkdtemp()
    try:
        path = write_report(tmpdir, "12345", "# Report\nbody")
        check("file created", os.path.exists(path), True)
        with open(path) as f:
            check("content", f.read(), "# Report\nbody")
        check("path basename", os.path.basename(path), "evidence_report_12345.md")
    finally:
        shutil.rmtree(tmpdir)


def test_write_json_pretty():
    tmpdir = tempfile.mkdtemp()
    try:
        path = write_json(tmpdir, "12345", {"pmid": "12345", "status": "ok"})
        with open(path) as f:
            data = json.load(f)
        check("parses back", data["status"], "ok")
        check("path basename", os.path.basename(path), "12345.json")
    finally:
        shutil.rmtree(tmpdir)


def test_append_log_appends():
    tmpdir = tempfile.mkdtemp()
    try:
        log = os.path.join(tmpdir, "run_log.jsonl")
        append_log(log, {"pmid": "1", "event": "started"})
        append_log(log, {"pmid": "1", "event": "completed"})
        with open(log) as f:
            lines = f.readlines()
        check("two lines", len(lines), 2)
        check("first parses", json.loads(lines[0])["event"], "started")
        check("second parses", json.loads(lines[1])["event"], "completed")
    finally:
        shutil.rmtree(tmpdir)


def test_checkpoint_roundtrip():
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "checkpoint.json")
        cp = Checkpoint(
            run_id="r1",
            config={"model": "claude-opus-4-7", "workers": 2},
            completed=["1", "2"],
            failed=[{"pmid": "3", "reason": "fetch_error", "attempts": 3}],
        )
        write_checkpoint(path, cp)
        loaded = read_checkpoint(path)
        check("run_id", loaded.run_id, "r1")
        check("completed", loaded.completed, ["1", "2"])
        check("failed pmid", loaded.failed[0]["pmid"], "3")
    finally:
        shutil.rmtree(tmpdir)


def test_checkpoint_missing_returns_empty():
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "nope.json")
        cp = read_checkpoint(path)
        check("empty completed", cp.completed, [])
        check("empty failed", cp.failed, [])
    finally:
        shutil.rmtree(tmpdir)


def test_checkpoint_atomic_replace():
    """Writing checkpoint twice does not corrupt the file."""
    tmpdir = tempfile.mkdtemp()
    try:
        path = os.path.join(tmpdir, "checkpoint.json")
        for i in range(5):
            write_checkpoint(path, Checkpoint(
                run_id="r", config={},
                completed=[str(j) for j in range(i)], failed=[]))
            loaded = read_checkpoint(path)
            check(f"iter {i} count", len(loaded.completed), i)
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    for fn in [test_write_report_creates_file, test_write_json_pretty,
               test_append_log_appends, test_checkpoint_roundtrip,
               test_checkpoint_missing_returns_empty, test_checkpoint_atomic_replace]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
