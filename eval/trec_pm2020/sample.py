"""Build the stratified 500-PMID sample from qrels-expgains-phase2.txt.

For each unique PMID, compute its maximum grade across all topics it appears in.
Group by max-grade ∈ {8, 4, 2, 1} and sample 125 per bucket with seed=42 (or
configurable). Emit sample_500.csv with one row per sampled PMID.

CSV columns:
    pmid              str
    max_grade         int
    all_topic_grades  str (format "topic_a:grade_a,topic_b:grade_b")
"""

import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple

from eval.trec_pm2020.qrels import parse_qrels, QrelRow


BUCKETS = (8, 4, 2, 1)
DEFAULT_PER_BUCKET = 125
DEFAULT_SEED = 42


@dataclass(frozen=True)
class SampleRow:
    pmid: str
    max_grade: int
    all_topic_grades: str  # "1:8,3:4"


def compute_max_grades(
    qrels_pairs: Iterable[Tuple[int, str, int]]
) -> Tuple[Dict[str, int], Dict[str, List[Tuple[int, int]]]]:
    """Given (topic, pmid, grade) tuples, return (max_grade_per_pmid, all_topic_grades_per_pmid)."""
    max_grades: Dict[str, int] = {}
    topic_grades: Dict[str, List[Tuple[int, int]]] = defaultdict(list)
    for topic, pmid, grade in qrels_pairs:
        topic_grades[pmid].append((topic, grade))
        if pmid not in max_grades or grade > max_grades[pmid]:
            max_grades[pmid] = grade
    return max_grades, dict(topic_grades)


def stratified_sample(
    max_grades: Dict[str, int],
    per_bucket: int = DEFAULT_PER_BUCKET,
    seed: int = DEFAULT_SEED,
    topic_grades: Dict[str, List[Tuple[int, int]]] | None = None,
) -> List[SampleRow]:
    """Sample `per_bucket` PMIDs from each max-grade bucket in BUCKETS.

    Raises ValueError if any *non-empty* bucket has fewer than `per_bucket` PMIDs.
    Empty buckets are silently skipped (the dataset simply has no PMIDs at that grade).
    Returns a list in bucket order: all grade-8 first, then grade-4, then grade-2, then grade-1.
    """
    rng = random.Random(seed)
    buckets: Dict[int, List[str]] = {g: [] for g in BUCKETS}
    for pmid, g in max_grades.items():
        if g in buckets:
            buckets[g].append(pmid)

    out: List[SampleRow] = []
    for g in BUCKETS:
        pool = sorted(buckets[g])  # sort for determinism before sampling
        if len(pool) == 0:
            continue  # bucket absent in this dataset; skip it
        if len(pool) < per_bucket:
            raise ValueError(
                f"Bucket max_grade={g} has only {len(pool)} PMIDs, need {per_bucket}"
            )
        chosen = rng.sample(pool, per_bucket)
        for pmid in chosen:
            tg_str = ""
            if topic_grades and pmid in topic_grades:
                tg_str = ",".join(f"{t}:{gr}" for t, gr in sorted(topic_grades[pmid]))
            out.append(SampleRow(pmid=pmid, max_grade=g, all_topic_grades=tg_str))
    return out


def write_sample_csv(rows: List[SampleRow], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["pmid", "max_grade", "all_topic_grades"])
        for r in rows:
            w.writerow([r.pmid, r.max_grade, r.all_topic_grades])


def main():
    """Build sample_500.csv from the real qrels file."""
    import os
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
    qrels_path = os.path.join(repo_root, "data/trec_pm2020/qrels-expgains-phase2.txt")
    out_path = os.path.join(repo_root, "data/trec_pm2020/sample_500.csv")

    pairs = [(r.topic, r.pmid, r.grade) for r in parse_qrels(qrels_path)]
    max_grades, topic_grades = compute_max_grades(pairs)
    rows = stratified_sample(max_grades, per_bucket=DEFAULT_PER_BUCKET,
                              seed=DEFAULT_SEED, topic_grades=topic_grades)
    write_sample_csv(rows, out_path)
    print(f"Wrote {len(rows)} rows to {out_path}")
    print(f"Bucket sizes: " + ", ".join(
        f"{g}={sum(1 for r in rows if r.max_grade == g)}" for g in BUCKETS))


if __name__ == "__main__":
    main()
