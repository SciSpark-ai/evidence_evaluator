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


def test_build_master_csv_basic():
    """Synthetic test: 2 sampled PMIDs, one appears under 2 topics."""
    tmpdir = tempfile.mkdtemp()
    try:
        json_dir = os.path.join(tmpdir, "json")
        os.makedirs(json_dir)

        # PMID A: topic 1 grade 8, topic 2 grade 4 — sampled, max_grade=8
        # PMID B: topic 3 grade 2 — sampled, max_grade=2
        # PMID C: topic 4 grade 1 — NOT sampled
        write_json(json_dir, "A", {
            "pmid": "A", "status": "ok",
            "stage0": {"study_type": "RCT_intervention"},
            "stage3": {"fragility_index": 62, "post_hoc_power": 0.94, "dor": None},
            "stage4": {"overall_concern": "low"},
            "stage5": {"suggested_score": 5},
            "runtime_s": 142, "report_path": "reports/evidence_report_A.md",
        })
        write_json(json_dir, "B", {
            "pmid": "B", "status": "partial_insufficient_data",
            "stage0": {"study_type": "observational"},
            "stage3": {"fragility_index": 18, "post_hoc_power": None, "dor": None},
            "stage4": {"overall_concern": "some_concerns"},
            "stage5": {"suggested_score": 3},
            "runtime_s": 95, "report_path": "reports/evidence_report_B.md",
        })

        qrels_path = os.path.join(tmpdir, "qrels.txt")
        with open(qrels_path, "w") as f:
            f.write("1 0 A 8\n2 0 A 4\n3 0 B 2\n4 0 C 1\n")

        sample_csv = os.path.join(tmpdir, "sample.csv")
        with open(sample_csv, "w") as f:
            f.write("pmid,max_grade,all_topic_grades\n")
            f.write("A,8,1:8,2:4\n")
            f.write("B,2,3:2\n")

        master_path = os.path.join(tmpdir, "master.csv")
        from eval.trec_pm2020.emit import build_master_csv
        build_master_csv(qrels_path, sample_csv, json_dir, master_path)

        import csv
        with open(master_path) as f:
            rows = list(csv.DictReader(f))
        check("row count", len(rows), 3)  # A x 2 topics + B x 1 topic
        a_rows = [r for r in rows if r["pmid"] == "A"]
        check("A appears twice", len(a_rows), 2)
        check("A ee_score", a_rows[0]["ee_score"], "5")
        check("A study type", a_rows[0]["ee_study_type"], "RCT_intervention")
        b_row = next(r for r in rows if r["pmid"] == "B")
        check("B power is empty", b_row["ee_post_hoc_power"], "")
        check("B status", b_row["run_status"], "partial_insufficient_data")
    finally:
        shutil.rmtree(tmpdir)


def test_build_master_csv_nested_layout():
    """JSON dumps live under per-status subdirs (e.g. json/ok/A.json) — builder must still find them."""
    tmpdir = tempfile.mkdtemp()
    try:
        json_dir = os.path.join(tmpdir, "json")
        # Flat-layout JSON for old runs (B) and nested-layout JSON for reorganized runs (A under ok/, C under partial_off_distribution/)
        os.makedirs(os.path.join(json_dir, "ok"))
        os.makedirs(os.path.join(json_dir, "partial_off_distribution"))

        # A: nested under ok/
        with open(os.path.join(json_dir, "ok", "A.json"), "w") as f:
            json.dump({
                "pmid": "A", "status": "ok",
                "stage0": {"study_type": "RCT_intervention"},
                "stage5": {"suggested_score": 5},
                "runtime_s": 100,
            }, f)
        # B: flat (back-compat — old layout, file at root)
        with open(os.path.join(json_dir, "B.json"), "w") as f:
            json.dump({
                "pmid": "B", "status": "partial_insufficient_data",
                "stage0": {"study_type": "observational"},
                "stage5": {"suggested_score": 2},
                "runtime_s": 50,
            }, f)
        # C: nested under partial_off_distribution/
        with open(os.path.join(json_dir, "partial_off_distribution", "C.json"), "w") as f:
            json.dump({
                "pmid": "C", "status": "partial_off_distribution",
                "stage0": {"study_type": "narrative_review"},
                "stage5": {"suggested_score": 1},
                "runtime_s": 30,
            }, f)

        qrels_path = os.path.join(tmpdir, "qrels.txt")
        with open(qrels_path, "w") as f:
            f.write("1 0 A 8\n2 0 B 4\n3 0 C 2\n")

        sample_csv = os.path.join(tmpdir, "sample.csv")
        with open(sample_csv, "w") as f:
            f.write("pmid,max_grade,all_topic_grades\n")
            f.write("A,8,1:8\n")
            f.write("B,4,2:4\n")
            f.write("C,2,3:2\n")

        master_path = os.path.join(tmpdir, "master.csv")
        from eval.trec_pm2020.emit import build_master_csv
        n = build_master_csv(qrels_path, sample_csv, json_dir, master_path)
        check("rows written", n, 3)

        import csv
        with open(master_path) as f:
            rows = list(csv.DictReader(f))
        by_pmid = {r["pmid"]: r for r in rows}
        # Nested JSONs were read successfully (status would be "missing" otherwise)
        check("A (nested) status", by_pmid["A"]["run_status"], "ok")
        check("A ee_score from nested JSON", by_pmid["A"]["ee_score"], "5")
        check("B (flat) status", by_pmid["B"]["run_status"], "partial_insufficient_data")
        check("C (nested) status", by_pmid["C"]["run_status"], "partial_off_distribution")
        check("C ee_study_type from nested JSON", by_pmid["C"]["ee_study_type"], "narrative_review")
        # report_path reflects the status subdir when JSON was nested
        check("A report_path nested", by_pmid["A"]["report_path"], "reports/ok/evidence_report_A.md")
        check("C report_path nested", by_pmid["C"]["report_path"],
              "reports/partial_off_distribution/evidence_report_C.md")
        # For flat layout, report_path falls back to whatever's in the JSON (or "reports/evidence_report_B.md" if computed)
        check("B report_path flat", by_pmid["B"]["report_path"], "reports/evidence_report_B.md")
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    for fn in [test_write_report_creates_file, test_write_json_pretty,
               test_append_log_appends, test_checkpoint_roundtrip,
               test_checkpoint_missing_returns_empty, test_checkpoint_atomic_replace,
               test_build_master_csv_basic,
               test_build_master_csv_nested_layout]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
