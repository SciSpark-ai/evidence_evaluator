"""Tests for eval/trec_pm2020/sample.py"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020.sample import compute_max_grades, stratified_sample, SampleRow

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


def test_max_grades_simple():
    qrels_pairs = [
        (1, "A", 4), (2, "A", 8),
        (3, "B", 2),
    ]
    max_grades, topic_grades = compute_max_grades(qrels_pairs)
    check("A max_grade", max_grades["A"], 8)
    check("B max_grade", max_grades["B"], 2)
    check("A topics", sorted(topic_grades["A"]), [(1, 4), (2, 8)])


def test_stratified_sample_deterministic():
    max_grades = {}
    for g in (1, 2, 4, 8):
        for i in range(10):
            max_grades[f"P{g}_{i}"] = g
    s1 = stratified_sample(max_grades, per_bucket=3, seed=42)
    s2 = stratified_sample(max_grades, per_bucket=3, seed=42)
    check("deterministic", [r.pmid for r in s1], [r.pmid for r in s2])
    check("size", len(s1), 12)
    counts = {g: sum(1 for r in s1 if r.max_grade == g) for g in (1, 2, 4, 8)}
    check("bucket counts", counts, {1: 3, 2: 3, 4: 3, 8: 3})


def test_stratified_sample_different_seed_different_result():
    max_grades = {f"P_{i}": 8 for i in range(20)}
    s1 = [r.pmid for r in stratified_sample(max_grades, per_bucket=5, seed=42)]
    s2 = [r.pmid for r in stratified_sample(max_grades, per_bucket=5, seed=7)]
    check("different seeds differ", s1 != s2, True)


def test_stratified_sample_raises_if_bucket_too_small():
    max_grades = {"P1": 8, "P2": 8}
    try:
        stratified_sample(max_grades, per_bucket=10, seed=42)
        check("raises", False, True)
    except ValueError as e:
        check("raises ValueError", "8" in str(e), True)


if __name__ == "__main__":
    for fn in [test_max_grades_simple, test_stratified_sample_deterministic,
               test_stratified_sample_different_seed_different_result,
               test_stratified_sample_raises_if_bucket_too_small]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
