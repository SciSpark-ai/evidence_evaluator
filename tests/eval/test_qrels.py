"""Tests for eval/trec_pm2020/qrels.py"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020.qrels import parse_qrels, QrelRow

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


def write_qrels(content):
    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def test_parses_basic_row():
    path = write_qrels("1 0 12345 8\n")
    rows = list(parse_qrels(path))
    check("count", len(rows), 1)
    check("row", rows[0], QrelRow(topic=1, pmid="12345", grade=8))
    os.unlink(path)


def test_drops_grade_zero_by_default():
    path = write_qrels("1 0 12345 0\n1 0 99999 1\n")
    rows = list(parse_qrels(path))
    check("count", len(rows), 1)
    check("pmid", rows[0].pmid, "99999")
    os.unlink(path)


def test_include_grade_zero_when_requested():
    path = write_qrels("1 0 12345 0\n1 0 99999 1\n")
    rows = list(parse_qrels(path, include_zero=True))
    check("count", len(rows), 2)
    os.unlink(path)


def test_tolerates_multiple_whitespace():
    path = write_qrels("1   0   12345   8\n")
    rows = list(parse_qrels(path))
    check("pmid", rows[0].pmid, "12345")
    check("grade", rows[0].grade, 8)
    os.unlink(path)


def test_ignores_blank_lines():
    path = write_qrels("\n1 0 12345 8\n\n\n")
    rows = list(parse_qrels(path))
    check("count", len(rows), 1)
    os.unlink(path)


def test_real_qrels_loads():
    # Smoke-load the real file
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
    real = os.path.join(repo_root, "data/trec_pm2020/qrels-expgains-phase2.txt")
    rows = list(parse_qrels(real))
    check("real row count > 2000", len(rows) > 2000, True)
    grades = {r.grade for r in rows}
    check("grades only positive", grades, {1, 2, 4, 8})


if __name__ == "__main__":
    for fn in [test_parses_basic_row, test_drops_grade_zero_by_default,
               test_include_grade_zero_when_requested, test_tolerates_multiple_whitespace,
               test_ignores_blank_lines, test_real_qrels_loads]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
