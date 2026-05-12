# TREC PM 2020 Batch Evaluation Harness — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python harness that runs the Evidence Evaluator pipeline (via Claude Agent SDK on Opus 4.7) against a stratified 500-PMID sample drawn from TREC PM 2020's `qrels-expgains-phase2.txt`, producing per-paper Markdown + JSON, a joined master CSV, and a checkpointed run log.

**Architecture:** New top-level package `eval/trec_pm2020/` with seven modules (sample, qrels, pubmed, runner, batch, emit, cli). The installed skill at `skills/evidence-evaluator/` is unchanged — the agent reads `SKILL.md` and calls `pipeline/stage3_math.py` / `pipeline/stage5_report.py` exactly as the manual pilot runs did. A `tmux` background run on the user's Pro/Max subscription is the production deployment.

**Tech Stack:** Python 3.11+, `claude-agent-sdk` (Python), stdlib `concurrent.futures` for the worker pool, `requests` for PubMed E-utilities, `xml.etree.ElementTree` for parsing efetch XML. No pytest — tests follow the existing project convention (manual `PASS/FAIL` counter, run with `python3 tests/eval/test_*.py`). Stages 0–5 of the pipeline are unchanged.

**Reference spec:** `docs/superpowers/specs/2026-05-11-trec-pm2020-batch-eval-harness-design.md`

---

## File Manifest

**Created:**
- `eval/__init__.py`
- `eval/trec_pm2020/__init__.py`
- `eval/trec_pm2020/qrels.py`
- `eval/trec_pm2020/sample.py`
- `eval/trec_pm2020/pubmed.py`
- `eval/trec_pm2020/runner.py`
- `eval/trec_pm2020/batch.py`
- `eval/trec_pm2020/emit.py`
- `eval/trec_pm2020/cli.py`
- `eval/trec_pm2020/PROMPT_TEMPLATE.md`
- `tests/eval/__init__.py`
- `tests/eval/test_qrels.py`
- `tests/eval/test_sample.py`
- `tests/eval/test_pubmed.py`
- `tests/eval/test_emit.py`
- `tests/eval/test_runner.py`
- `tests/eval/test_batch.py`
- `data/trec_pm2020/sample_500.csv` (generated, committed)

**Modified:**
- `.gitignore` (add `data/trec_pm2020/abstracts_cache/` and `results/trec_pm2020/`)
- `CLAUDE.md` (final task — add repo-structure entry for `eval/trec_pm2020/`)

**Untouched:** everything in `skills/evidence-evaluator/`, `paper/`, existing `tests/`.

---

## Task 1: Scaffolding (directories, gitignore, dependency)

**Files:**
- Create: `eval/__init__.py`
- Create: `eval/trec_pm2020/__init__.py`
- Create: `tests/eval/__init__.py`
- Modify: `.gitignore`
- Verify: `data/trec_pm2020/qrels-expgains-phase2.txt` (already committed in 8f27ed5)

- [ ] **Step 1: Create package directories**

```bash
mkdir -p eval/trec_pm2020 tests/eval data/trec_pm2020/abstracts_cache results/trec_pm2020
```

- [ ] **Step 2: Create `eval/__init__.py`**

```python
# eval/__init__.py
"""Evaluation harnesses for Evidence Evaluator.

Each subpackage targets one external benchmark or comparison dataset.
"""
```

- [ ] **Step 3: Create `eval/trec_pm2020/__init__.py`**

```python
# eval/trec_pm2020/__init__.py
"""TREC Precision Medicine 2020 batch evaluation harness.

Runs Evidence Evaluator against a stratified 500-PMID sample from
qrels-expgains-phase2.txt. See ../../docs/superpowers/specs/2026-05-11-
trec-pm2020-batch-eval-harness-design.md for the design.
"""
```

- [ ] **Step 4: Create `tests/eval/__init__.py`**

```python
# tests/eval/__init__.py
```

- [ ] **Step 5: Update `.gitignore`**

Append these lines to `.gitignore` (create the file if missing):

```
# TREC PM 2020 batch eval harness
data/trec_pm2020/abstracts_cache/
results/trec_pm2020/
```

- [ ] **Step 6: Install the Claude Agent SDK**

```bash
python3 -m pip install claude-agent-sdk requests
```

Verify import works:

```bash
python3 -c "import claude_agent_sdk; print(claude_agent_sdk.__version__)"
python3 -c "import requests; print(requests.__version__)"
```

Expected: both print version strings without error.

- [ ] **Step 7: Commit**

```bash
git add eval/__init__.py eval/trec_pm2020/__init__.py tests/eval/__init__.py .gitignore
git commit -m "Scaffold eval/trec_pm2020/ package for TREC PM 2020 batch harness"
```

---

## Task 2: `qrels.py` — parse qrels file

**Files:**
- Create: `eval/trec_pm2020/qrels.py`
- Test: `tests/eval/test_qrels.py`

The qrels format is `topic_id 0 pmid grade` separated by whitespace, one per line. We need an iterator that yields parsed rows, optionally filtering out `grade=0` (Phase 1 irrelevant pool fillers).

- [ ] **Step 1: Write failing tests in `tests/eval/test_qrels.py`**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/eval/test_qrels.py
```

Expected: `ModuleNotFoundError: No module named 'eval.trec_pm2020.qrels'`

- [ ] **Step 3: Implement `eval/trec_pm2020/qrels.py`**

```python
"""Parse TREC PM 2020 qrels-expgains-phase2.txt.

Format: one row per line, four whitespace-separated fields:
    topic_id (int)
    0        (literal, unused)
    pmid     (str)
    grade    (int; 0, 1, 2, 4, or 8)

grade=0 rows are Phase 1 irrelevant pool fillers; dropped by default.
grade in {1, 2, 4, 8} are exponential gains over the Phase 2 evidence tiers.
"""

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class QrelRow:
    topic: int
    pmid: str
    grade: int


def parse_qrels(path: str, include_zero: bool = False) -> Iterator[QrelRow]:
    """Yield QrelRow objects parsed from a qrels file.

    Args:
        path: filesystem path to the qrels file.
        include_zero: if True, yield grade=0 rows too. Default False.
    """
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 4:
                raise ValueError(f"Malformed qrels line: {line!r}")
            topic = int(parts[0])
            pmid = parts[2]
            grade = int(parts[3])
            if grade == 0 and not include_zero:
                continue
            yield QrelRow(topic=topic, pmid=pmid, grade=grade)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/eval/test_qrels.py
```

Expected: `PASS: 11  FAIL: 0` (each `check()` call counts as one).

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/qrels.py tests/eval/test_qrels.py
git commit -m "Add qrels.py: parse TREC PM 2020 qrels-expgains-phase2.txt"
```

---

## Task 3: `sample.py` — build the stratified 500 sample

**Files:**
- Create: `eval/trec_pm2020/sample.py`
- Test: `tests/eval/test_sample.py`

Algorithm: group unique PMIDs by max-grade across topics, then `random.Random(seed=42).sample(bucket, 125)` per bucket {8, 4, 2, 1} → 500 PMIDs.

- [ ] **Step 1: Write failing tests in `tests/eval/test_sample.py`**

```python
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
    # PMID "A" appears in topic 1 with grade 4 and topic 2 with grade 8
    # PMID "B" appears only with grade 2
    qrels_pairs = [
        (1, "A", 4), (2, "A", 8),
        (3, "B", 2),
    ]
    max_grades, topic_grades = compute_max_grades(qrels_pairs)
    check("A max_grade", max_grades["A"], 8)
    check("B max_grade", max_grades["B"], 2)
    check("A topics", sorted(topic_grades["A"]), [(1, 4), (2, 8)])


def test_stratified_sample_deterministic():
    # 10 PMIDs per max-grade bucket; sample 3 per bucket
    max_grades = {}
    for g in (1, 2, 4, 8):
        for i in range(10):
            max_grades[f"P{g}_{i}"] = g
    s1 = stratified_sample(max_grades, per_bucket=3, seed=42)
    s2 = stratified_sample(max_grades, per_bucket=3, seed=42)
    check("deterministic", [r.pmid for r in s1], [r.pmid for r in s2])
    check("size", len(s1), 12)
    # Bucket counts
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
        check("raises", False, True)  # should not reach
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/eval/test_sample.py
```

Expected: `ModuleNotFoundError: No module named 'eval.trec_pm2020.sample'`

- [ ] **Step 3: Implement `eval/trec_pm2020/sample.py`**

```python
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

    Raises ValueError if any bucket has fewer than `per_bucket` PMIDs.
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/eval/test_sample.py
```

Expected: `PASS: N  FAIL: 0`

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/sample.py tests/eval/test_sample.py
git commit -m "Add sample.py: stratified 500-PMID sampler with seed=42"
```

---

## Task 4: Generate and commit `sample_500.csv`

**Files:**
- Generated: `data/trec_pm2020/sample_500.csv`

- [ ] **Step 1: Run the sampler**

```bash
python3 -m eval.trec_pm2020.sample
```

Expected output:
```
Wrote 500 rows to .../data/trec_pm2020/sample_500.csv
Bucket sizes: 8=125, 4=125, 2=125, 1=125
```

- [ ] **Step 2: Inspect the file**

```bash
head -5 data/trec_pm2020/sample_500.csv
wc -l data/trec_pm2020/sample_500.csv
awk -F',' 'NR>1 {print $2}' data/trec_pm2020/sample_500.csv | sort | uniq -c
```

Expected:
- 501 total lines (1 header + 500 data rows)
- `125 1`, `125 2`, `125 4`, `125 8` from the uniq count

- [ ] **Step 3: Commit the sample file**

```bash
git add data/trec_pm2020/sample_500.csv
git commit -m "Generate sample_500.csv (125 PMIDs per max-grade bucket, seed=42)"
```

---

## Task 5: `pubmed.py` — E-utilities efetch with retry + on-disk cache

**Files:**
- Create: `eval/trec_pm2020/pubmed.py`
- Test: `tests/eval/test_pubmed.py`

The PubMed efetch endpoint is `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={pmid}&retmode=xml`. Optional `NCBI_API_KEY` env var bumps rate limit from 3 req/s to 10 req/s. Cache responses to `data/trec_pm2020/abstracts_cache/<pmid>.xml`.

- [ ] **Step 1: Write failing tests in `tests/eval/test_pubmed.py`**

```python
"""Tests for eval/trec_pm2020/pubmed.py"""

import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020.pubmed import fetch_abstract, PubMedError

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


def test_returns_cached_content_without_network():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "12345"
        cache_path = os.path.join(tmpdir, f"{pmid}.xml")
        with open(cache_path, "w") as f:
            f.write("<PubmedArticle>cached</PubmedArticle>")

        with patch("eval.trec_pm2020.pubmed.requests.get") as mock_get:
            content = fetch_abstract(pmid, cache_dir=tmpdir)
            check("returns cached content", content, "<PubmedArticle>cached</PubmedArticle>")
            check("network not called", mock_get.called, False)
    finally:
        shutil.rmtree(tmpdir)


def test_fetches_and_caches_on_miss():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "99999"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<PubmedArticle>fetched</PubmedArticle>"
        mock_response.raise_for_status = MagicMock()

        with patch("eval.trec_pm2020.pubmed.requests.get", return_value=mock_response) as mock_get:
            content = fetch_abstract(pmid, cache_dir=tmpdir, throttle=0.0)
            check("returns fetched content", content, "<PubmedArticle>fetched</PubmedArticle>")
            check("network called once", mock_get.call_count, 1)
            check("cached to disk", os.path.exists(os.path.join(tmpdir, f"{pmid}.xml")), True)
    finally:
        shutil.rmtree(tmpdir)


def test_retries_on_5xx_then_succeeds():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "77777"
        fail_resp = MagicMock(status_code=503)
        import requests
        fail_resp.raise_for_status = MagicMock(side_effect=requests.HTTPError("503"))
        ok_resp = MagicMock(status_code=200)
        ok_resp.text = "<PubmedArticle>ok</PubmedArticle>"
        ok_resp.raise_for_status = MagicMock()

        with patch("eval.trec_pm2020.pubmed.requests.get",
                   side_effect=[fail_resp, fail_resp, ok_resp]):
            with patch("eval.trec_pm2020.pubmed.time.sleep"):
                content = fetch_abstract(pmid, cache_dir=tmpdir, throttle=0.0, max_retries=3)
                check("succeeds after retry", content, "<PubmedArticle>ok</PubmedArticle>")
    finally:
        shutil.rmtree(tmpdir)


def test_raises_on_4xx_invalid_pmid():
    tmpdir = tempfile.mkdtemp()
    try:
        pmid = "00000"
        resp = MagicMock(status_code=400)
        import requests
        resp.raise_for_status = MagicMock(side_effect=requests.HTTPError("400 invalid"))

        with patch("eval.trec_pm2020.pubmed.requests.get", return_value=resp):
            try:
                fetch_abstract(pmid, cache_dir=tmpdir, throttle=0.0)
                check("raises PubMedError", False, True)
            except PubMedError as e:
                check("PubMedError raised", "400" in str(e) or "invalid" in str(e).lower(), True)
    finally:
        shutil.rmtree(tmpdir)


if __name__ == "__main__":
    for fn in [test_returns_cached_content_without_network,
               test_fetches_and_caches_on_miss,
               test_retries_on_5xx_then_succeeds,
               test_raises_on_4xx_invalid_pmid]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/eval/test_pubmed.py
```

Expected: `ModuleNotFoundError: No module named 'eval.trec_pm2020.pubmed'`

- [ ] **Step 3: Implement `eval/trec_pm2020/pubmed.py`**

```python
"""PubMed E-utilities efetch with retry + on-disk cache.

Fetches a single PMID's XML record (db=pubmed, retmode=xml). Caches to disk;
returns cached content on hit. Retries 5xx with exponential backoff (1s, 4s, 16s).
4xx responses raise PubMedError immediately.

Set NCBI_API_KEY env var to raise rate limit from 3 to 10 req/s (default throttle
is 0.34s between calls).
"""

import os
import time
from typing import Optional

import requests


EFETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
DEFAULT_THROTTLE_S = 0.34  # ~3 req/s without API key
WITH_KEY_THROTTLE_S = 0.10  # ~10 req/s with API key
DEFAULT_MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 4  # 1s, 4s, 16s


class PubMedError(Exception):
    """Raised on unrecoverable PubMed efetch errors (4xx or final 5xx retry)."""


def fetch_abstract(
    pmid: str,
    cache_dir: str,
    throttle: Optional[float] = None,
    max_retries: int = DEFAULT_MAX_RETRIES,
    api_key: Optional[str] = None,
) -> str:
    """Fetch a PubMed record's XML for the given pmid, with caching.

    Args:
        pmid: PubMed ID as string
        cache_dir: directory to cache responses (created if missing)
        throttle: seconds to sleep before request; default 0.34s (or 0.10s if API key)
        max_retries: number of retry attempts on 5xx errors (default 3)
        api_key: NCBI_API_KEY override; falls back to env var

    Returns:
        The XML string content (cached or freshly fetched).

    Raises:
        PubMedError on 4xx or after exhausting retries on 5xx.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"{pmid}.xml")
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            return f.read()

    key = api_key or os.environ.get("NCBI_API_KEY")
    if throttle is None:
        throttle = WITH_KEY_THROTTLE_S if key else DEFAULT_THROTTLE_S

    params = {"db": "pubmed", "id": pmid, "retmode": "xml"}
    if key:
        params["api_key"] = key

    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        if throttle > 0:
            time.sleep(throttle)
        try:
            resp = requests.get(EFETCH_URL, params=params, timeout=30)
            if 400 <= resp.status_code < 500:
                raise PubMedError(
                    f"PubMed efetch returned {resp.status_code} for pmid={pmid}: invalid pmid?"
                )
            resp.raise_for_status()
            content = resp.text
            with open(cache_path, "w") as f:
                f.write(content)
            return content
        except PubMedError:
            raise
        except (requests.HTTPError, requests.RequestException) as e:
            last_err = e
            if attempt < max_retries:
                backoff = RETRY_BACKOFF_BASE ** attempt  # 1, 4, 16
                time.sleep(backoff)
            else:
                raise PubMedError(
                    f"PubMed efetch failed for pmid={pmid} after {max_retries} retries: {e}"
                ) from e
    # Defensive: unreachable
    raise PubMedError(f"Unexpected end of retry loop for pmid={pmid}: {last_err}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/eval/test_pubmed.py
```

Expected: `PASS: N  FAIL: 0`

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/pubmed.py tests/eval/test_pubmed.py
git commit -m "Add pubmed.py: efetch with retry and on-disk cache"
```

---

## Task 6: `emit.py` — single-paper writers, run log, checkpoint

**Files:**
- Create: `eval/trec_pm2020/emit.py`
- Test: `tests/eval/test_emit.py`

This module owns all output I/O. Per-paper writers (Markdown, JSON), append-only `run_log.jsonl`, atomic checkpoint write.

- [ ] **Step 1: Write failing tests in `tests/eval/test_emit.py`**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/eval/test_emit.py
```

Expected: `ModuleNotFoundError: No module named 'eval.trec_pm2020.emit'`

- [ ] **Step 3: Implement `eval/trec_pm2020/emit.py` (single-paper writers + checkpoint)**

```python
"""Output writers for the TREC PM 2020 batch harness.

Handles per-paper Markdown + JSON, append-only run_log.jsonl, and atomic
checkpoint writes. The master CSV builder is in a separate function
(build_master_csv) — added in Task 7.
"""

import json
import os
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List


@dataclass
class Checkpoint:
    run_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    completed: List[str] = field(default_factory=list)
    failed: List[Dict[str, Any]] = field(default_factory=list)


def write_report(reports_dir: str, pmid: str, markdown: str) -> str:
    """Write the per-paper Markdown report. Returns the file path."""
    os.makedirs(reports_dir, exist_ok=True)
    path = os.path.join(reports_dir, f"evidence_report_{pmid}.md")
    with open(path, "w") as f:
        f.write(markdown)
    return path


def write_json(json_dir: str, pmid: str, data: Dict[str, Any]) -> str:
    """Write the per-paper structured JSON dump. Returns the file path."""
    os.makedirs(json_dir, exist_ok=True)
    path = os.path.join(json_dir, f"{pmid}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=False)
    return path


def append_log(log_path: str, entry: Dict[str, Any]) -> None:
    """Append one JSON line to the run_log.jsonl file."""
    os.makedirs(os.path.dirname(log_path) or ".", exist_ok=True)
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")


def read_checkpoint(path: str) -> Checkpoint:
    """Read the checkpoint file; return an empty Checkpoint if missing."""
    if not os.path.exists(path):
        return Checkpoint(run_id="", config={}, completed=[], failed=[])
    with open(path) as f:
        data = json.load(f)
    return Checkpoint(
        run_id=data.get("run_id", ""),
        config=data.get("config", {}),
        completed=list(data.get("completed", [])),
        failed=list(data.get("failed", [])),
    )


def write_checkpoint(path: str, cp: Checkpoint) -> None:
    """Atomically write the checkpoint (temp file + rename)."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".checkpoint.", suffix=".tmp",
        dir=os.path.dirname(path) or ".",
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(asdict(cp), f, indent=2)
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/eval/test_emit.py
```

Expected: `PASS: N  FAIL: 0`

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/emit.py tests/eval/test_emit.py
git commit -m "Add emit.py: per-paper writers, run log, atomic checkpoint"
```

---

## Task 7: `emit.py` — `build_master_csv`

**Files:**
- Modify: `eval/trec_pm2020/emit.py` (add `build_master_csv` function)
- Modify: `tests/eval/test_emit.py` (add tests)

After all 500 runs complete, join the per-paper JSON dumps with the qrels file to produce `master.csv`. One row per (topic, pmid, trec_grade) where pmid is in the sampled set.

- [ ] **Step 1: Add failing test to `tests/eval/test_emit.py`**

Append to the file before the `if __name__ == "__main__":` block:

```python

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
```

Then add `test_build_master_csv_basic` to the list at the bottom of the file.

- [ ] **Step 2: Run tests to verify the new test fails**

```bash
python3 tests/eval/test_emit.py
```

Expected: `ImportError: cannot import name 'build_master_csv'` (or similar).

- [ ] **Step 3: Append `build_master_csv` to `eval/trec_pm2020/emit.py`**

```python


def build_master_csv(
    qrels_path: str,
    sample_csv_path: str,
    json_dir: str,
    out_path: str,
) -> int:
    """Join per-paper JSON dumps with the qrels file → master.csv.

    For each (topic, pmid, grade) row in qrels where pmid is in the sampled set,
    emit one row to master.csv with both TREC fields and Evidence Evaluator fields.

    Returns the number of rows written (excluding header).
    """
    import csv as _csv
    from eval.trec_pm2020.qrels import parse_qrels

    # Build {pmid: max_grade} from the sample CSV
    sample_max: Dict[str, int] = {}
    with open(sample_csv_path) as f:
        reader = _csv.DictReader(f)
        for row in reader:
            sample_max[row["pmid"]] = int(row["max_grade"])

    columns = [
        "topic_id", "pmid", "trec_grade", "max_grade",
        "ee_score", "ee_study_type", "ee_overall_concern",
        "ee_fragility_index", "ee_post_hoc_power", "ee_dor",
        "report_path", "json_path", "run_status", "runtime_s",
    ]

    written = 0
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", newline="") as f_out:
        w = _csv.DictWriter(f_out, fieldnames=columns)
        w.writeheader()
        for r in parse_qrels(qrels_path):
            if r.pmid not in sample_max:
                continue
            json_path = os.path.join(json_dir, f"{r.pmid}.json")
            data: Dict[str, Any] = {}
            if os.path.exists(json_path):
                with open(json_path) as f:
                    data = json.load(f)
            row = {
                "topic_id": r.topic,
                "pmid": r.pmid,
                "trec_grade": r.grade,
                "max_grade": sample_max[r.pmid],
                "ee_score": _get(data, "stage5", "suggested_score"),
                "ee_study_type": _get(data, "stage0", "study_type"),
                "ee_overall_concern": _get(data, "stage4", "overall_concern"),
                "ee_fragility_index": _get(data, "stage3", "fragility_index"),
                "ee_post_hoc_power": _get(data, "stage3", "post_hoc_power"),
                "ee_dor": _get(data, "stage3", "dor"),
                "report_path": data.get("report_path", ""),
                "json_path": os.path.relpath(json_path, os.path.dirname(out_path)),
                "run_status": data.get("status", "missing"),
                "runtime_s": data.get("runtime_s", ""),
            }
            # Normalize None → "" for CSV
            for k, v in list(row.items()):
                if v is None:
                    row[k] = ""
            w.writerow(row)
            written += 1
    return written


def _get(data: Dict[str, Any], section: str, key: str) -> Any:
    """Safe nested lookup that tolerates missing sections."""
    sect = data.get(section)
    if not isinstance(sect, dict):
        return None
    return sect.get(key)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/eval/test_emit.py
```

Expected: `PASS: N  FAIL: 0` with the new test included.

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/emit.py tests/eval/test_emit.py
git commit -m "Add build_master_csv: join JSON dumps with qrels → master.csv"
```

---

## Task 8: `PROMPT_TEMPLATE.md` + `runner.py` — single-PMID SDK driver

**Files:**
- Create: `eval/trec_pm2020/PROMPT_TEMPLATE.md`
- Create: `eval/trec_pm2020/runner.py`
- Test: `tests/eval/test_runner.py`

`runner.py` orchestrates one paper end-to-end: fetch abstract → call `ClaudeSDKClient` → capture Markdown + JSON outputs → return a `RunResult`. The SDK call is isolated in one method so we can unit-test the surrounding logic (prompt building, JSON parsing) without hitting the LLM.

- [ ] **Step 1: Create the agent prompt template `eval/trec_pm2020/PROMPT_TEMPLATE.md`**

```markdown
You are running the Evidence Evaluator skill. The skill lives at `skills/evidence-evaluator/`
relative to the repo root (your current working directory).

## Inputs

- Paper to evaluate: PubMed PMID `{pmid}`
- Cached abstract XML: `data/trec_pm2020/abstracts_cache/{pmid}.xml`
- Output directory for the Markdown report: `{reports_dir}`
- Output directory for the JSON dump: `{json_dir}`

## Required workflow

1. Read `skills/evidence-evaluator/SKILL.md` in full. Follow its execution order strictly.
2. Read the cached abstract at `data/trec_pm2020/abstracts_cache/{pmid}.xml`. Treat this as
   Tier 1 input (abstract + structured abstract sections only). **Do NOT attempt to fetch
   full text under any circumstance**, even if you would normally signal `needs_full_paper`.
   If the abstract lacks fields you need for any stage, document the gap in the report and
   continue with whatever the available fields support.
3. Execute Stages 0 → 1 → 2 → 3 → 4 → 5 per `SKILL.md`. Use the Python modules
   `pipeline/stage3_math.py` and `pipeline/stage5_report.py` for the deterministic stages
   exactly as the pilot reports did. Run them via `cd skills/evidence-evaluator/ && python3 -c "..."`.
4. Save the full Markdown report to `{reports_dir}/evidence_report_{pmid}.md`.

## Final message (REQUIRED)

After saving the Markdown, emit ONE final assistant message containing ONLY a fenced
```json block with this exact schema. No prose, no explanation, no extra text outside
the fence.

```json
{{
  "pmid": "{pmid}",
  "status": "ok",
  "stage0": {{"study_type": "...", "confidence": 0.0, "skipped_stages": []}},
  "stage1": {{
    "initial_grade": null,
    "n_intervention": null, "n_control": null,
    "events_intervention": null, "events_control": null,
    "p_value": null, "ltfu_count": null, "alpha": 0.05,
    "effect_size_type": "...", "blinding": null, "randomization": null,
    "trial_phase": null, "primary_outcome": null,
    "pico": {{"P": "...", "I": "...", "C": "...", "O": "..."}},
    "low_confidence_fields": []
  }},
  "stage2": {{
    "mcid": null, "mcid_unit": null, "mcid_source": null, "mcid_tier": null,
    "effect_vs_mcid": null, "domain_n": null, "n_vs_domain": null,
    "domain_nnt_threshold": null, "nnt_vs_threshold": null
  }},
  "stage3": {{
    "fragility_index": null, "fragility_quotient": null,
    "ltfu_exceeds_fi": null, "nnt": null, "post_hoc_power": null,
    "dor": null, "deltas": {{}}
  }},
  "stage4": {{
    "tool": null, "overall_concern": null, "domains": [],
    "surrogate_endpoint_delta": 0, "heterogeneity_delta": 0
  }},
  "stage5": {{
    "suggested_score": null, "score_path": [], "deduplications_applied": []
  }}
}}
```

Use `null` for any field that did not apply or could not be extracted. Set `status` to
one of: `ok`, `partial_insufficient_data`, `partial_off_distribution`, or `max_turns`.
For partial statuses, additionally include `"error_msg": "<one-line summary>"`.
```

- [ ] **Step 2: Write failing tests in `tests/eval/test_runner.py`**

```python
"""Tests for eval/trec_pm2020/runner.py

The actual SDK call is not exercised here — it's isolated in one method that we
do not unit-test. We test prompt building and JSON extraction from agent transcripts.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from eval.trec_pm2020.runner import build_prompt, extract_final_json, RunResult

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


def test_build_prompt_substitutes_placeholders():
    p = build_prompt(pmid="12345", reports_dir="/r", json_dir="/j")
    check("contains pmid", "12345" in p, True)
    check("contains reports_dir", "/r" in p, True)
    check("contains json_dir", "/j" in p, True)
    check("no unresolved placeholders", "{pmid}" not in p, True)


def test_extract_final_json_simple_block():
    transcript = """
Some narrative text here.

```json
{"pmid": "12345", "status": "ok", "stage5": {"suggested_score": 4}}
```
"""
    data = extract_final_json(transcript)
    check("pmid", data["pmid"], "12345")
    check("score", data["stage5"]["suggested_score"], 4)


def test_extract_final_json_picks_last_block():
    """Agent might emit intermediate JSON blocks; we want the final one."""
    transcript = """
```json
{"pmid": "WRONG"}
```
later...
```json
{"pmid": "RIGHT", "status": "ok"}
```
"""
    data = extract_final_json(transcript)
    check("picks last", data["pmid"], "RIGHT")


def test_extract_final_json_raises_on_missing():
    try:
        extract_final_json("no json block here")
        check("raises", False, True)
    except ValueError as e:
        check("ValueError raised", "no JSON" in str(e) or "json" in str(e).lower(), True)


def test_extract_final_json_raises_on_malformed():
    try:
        extract_final_json("```json\n{not valid json}\n```")
        check("raises", False, True)
    except ValueError:
        check("ValueError raised", True, True)


if __name__ == "__main__":
    for fn in [test_build_prompt_substitutes_placeholders,
               test_extract_final_json_simple_block,
               test_extract_final_json_picks_last_block,
               test_extract_final_json_raises_on_missing,
               test_extract_final_json_raises_on_malformed]:
        print(f"\n{fn.__name__}")
        fn()
    print(f"\n{'='*50}\nPASS: {PASS}  FAIL: {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
python3 tests/eval/test_runner.py
```

Expected: `ModuleNotFoundError: No module named 'eval.trec_pm2020.runner'`

- [ ] **Step 4: Implement `eval/trec_pm2020/runner.py`**

```python
"""Single-PMID driver: build the agent prompt, call ClaudeSDKClient, parse outputs.

The SDK call is isolated in `_run_agent()` so the surrounding pure logic
(prompt building, JSON extraction) can be unit-tested without hitting the LLM.
"""

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from eval.trec_pm2020.pubmed import fetch_abstract, PubMedError


# Loaded once at import time
_PROMPT_TEMPLATE_PATH = os.path.join(
    os.path.dirname(__file__), "PROMPT_TEMPLATE.md"
)
with open(_PROMPT_TEMPLATE_PATH) as _f:
    PROMPT_TEMPLATE = _f.read()


@dataclass
class RunResult:
    pmid: str
    status: str  # ok, partial_*, max_turns, fetch_error, invalid_pmid, error
    json_data: Dict[str, Any] = field(default_factory=dict)
    runtime_s: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    error_msg: str = ""
    error_trace: str = ""


def build_prompt(pmid: str, reports_dir: str, json_dir: str) -> str:
    """Fill the prompt template with this run's paths."""
    return PROMPT_TEMPLATE.format(
        pmid=pmid, reports_dir=reports_dir, json_dir=json_dir
    )


_JSON_BLOCK_RE = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)


def extract_final_json(transcript: str) -> Dict[str, Any]:
    """Extract the last ```json fenced block from an agent transcript.

    Raises ValueError if no valid JSON block is found.
    """
    matches = _JSON_BLOCK_RE.findall(transcript)
    if not matches:
        raise ValueError("Transcript contains no fenced ```json block")
    last = matches[-1].strip()
    try:
        return json.loads(last)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON in final block: {e}") from e


def run_one(
    pmid: str,
    reports_dir: str,
    json_dir: str,
    cache_dir: str,
    model: str = "claude-opus-4-7",
    max_turns: int = 60,
    cwd: Optional[str] = None,
) -> RunResult:
    """Run the Evidence Evaluator pipeline on one PMID end-to-end.

    Steps:
      1. Fetch (or load cached) PubMed abstract XML.
      2. Build the agent prompt.
      3. Call _run_agent (ClaudeSDKClient).
      4. Extract the final ```json block, write report.md + json.
      5. Return a RunResult.
    """
    started_at = datetime.now(timezone.utc)
    t0 = time.monotonic()

    try:
        fetch_abstract(pmid, cache_dir=cache_dir)
    except PubMedError as e:
        return RunResult(
            pmid=pmid, status="invalid_pmid" if "400" in str(e) or "invalid" in str(e).lower()
            else "fetch_error",
            error_msg=str(e), runtime_s=time.monotonic() - t0,
        )

    prompt = build_prompt(pmid, reports_dir, json_dir)

    try:
        transcript, usage = _run_agent(prompt, model=model, max_turns=max_turns, cwd=cwd)
    except _MaxTurnsExceeded as e:
        return RunResult(
            pmid=pmid, status="max_turns", error_msg=str(e),
            runtime_s=time.monotonic() - t0,
        )
    except Exception as e:
        import traceback
        return RunResult(
            pmid=pmid, status="error",
            error_msg=str(e), error_trace=traceback.format_exc(),
            runtime_s=time.monotonic() - t0,
        )

    try:
        data = extract_final_json(transcript)
    except ValueError as e:
        return RunResult(
            pmid=pmid, status="error",
            error_msg=f"Could not extract final JSON: {e}",
            runtime_s=time.monotonic() - t0,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

    # Augment data with runtime metadata
    data.setdefault("pmid", pmid)
    data["model"] = model
    data["started_at"] = started_at.isoformat()
    data["finished_at"] = datetime.now(timezone.utc).isoformat()
    data["runtime_s"] = round(time.monotonic() - t0, 2)
    data["input_tokens"] = usage.get("input_tokens", 0)
    data["output_tokens"] = usage.get("output_tokens", 0)
    data["report_path"] = f"reports/evidence_report_{pmid}.md"

    # Persist JSON via emit (re-import to avoid circular issues if any)
    from eval.trec_pm2020.emit import write_json
    write_json(json_dir, pmid, data)

    return RunResult(
        pmid=pmid,
        status=data.get("status", "ok"),
        json_data=data,
        runtime_s=data["runtime_s"],
        input_tokens=data["input_tokens"],
        output_tokens=data["output_tokens"],
    )


class _MaxTurnsExceeded(Exception):
    pass


def _run_agent(prompt: str, model: str, max_turns: int, cwd: Optional[str]) -> tuple[str, Dict[str, int]]:
    """Invoke ClaudeSDKClient and return (full_transcript_text, usage_dict).

    Isolated so tests don't need to mock the SDK.
    """
    import asyncio
    from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

    options = ClaudeAgentOptions(
        model=model,
        max_turns=max_turns,
        cwd=cwd,
        allowed_tools=["Bash", "Read", "Write", "Glob", "Grep"],
        permission_mode="acceptEdits",
    )

    async def _go() -> tuple[str, Dict[str, int]]:
        transcript_parts: list[str] = []
        in_toks = 0
        out_toks = 0
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for msg in client.receive_response():
                kind = type(msg).__name__
                # Best-effort text accumulation across SDK message variants
                if hasattr(msg, "content"):
                    for block in getattr(msg, "content", []) or []:
                        text = getattr(block, "text", None)
                        if text:
                            transcript_parts.append(text)
                if hasattr(msg, "usage"):
                    u = getattr(msg, "usage", {}) or {}
                    in_toks += getattr(u, "input_tokens", 0) or u.get("input_tokens", 0) if u else 0
                    out_toks += getattr(u, "output_tokens", 0) or u.get("output_tokens", 0) if u else 0
                if kind == "ResultMessage":
                    # Some SDK versions expose stop_reason here
                    sr = getattr(msg, "stop_reason", None)
                    if sr == "max_turns":
                        raise _MaxTurnsExceeded(f"Agent stopped at max_turns={max_turns}")
        return "".join(transcript_parts), {"input_tokens": in_toks, "output_tokens": out_toks}

    return asyncio.run(_go())
```

> **Note for the implementer:** the SDK's exact message-class names and attributes shift between versions. The `_run_agent` body above is a defensive starting point; if `claude-agent-sdk` exposes a cleaner streaming API in the installed version, replace the `receive_response()` loop with that. The contract is: return `(transcript_str, {"input_tokens": int, "output_tokens": int})` and raise `_MaxTurnsExceeded` if the agent hit the turn cap. Verify against the docs at https://docs.claude.com/en/docs/agent-sdk/ during the smoke test (Task 11).

- [ ] **Step 5: Run unit tests to verify the pure-logic pieces pass**

```bash
python3 tests/eval/test_runner.py
```

Expected: `PASS: N  FAIL: 0`

The `_run_agent` function is NOT unit-tested here. It will be exercised end-to-end by the smoke test (Task 11).

- [ ] **Step 6: Commit**

```bash
git add eval/trec_pm2020/PROMPT_TEMPLATE.md eval/trec_pm2020/runner.py tests/eval/test_runner.py
git commit -m "Add runner.py + PROMPT_TEMPLATE.md: single-PMID SDK driver"
```

---

## Task 9: `batch.py` — parallel orchestrator with checkpoint/resume

**Files:**
- Create: `eval/trec_pm2020/batch.py`
- Test: `tests/eval/test_batch.py`

A worker-pool driver that reads `sample_500.csv`, skips PMIDs already in `checkpoint.completed`, runs the rest in parallel via `ThreadPoolExecutor`, updates the checkpoint after each completion. Worker count defaults to 2.

- [ ] **Step 1: Write failing tests in `tests/eval/test_batch.py`**

```python
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

        # Pre-populate checkpoint: A is already done
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
python3 tests/eval/test_batch.py
```

Expected: `ModuleNotFoundError: No module named 'eval.trec_pm2020.batch'`

- [ ] **Step 3: Implement `eval/trec_pm2020/batch.py`**

```python
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
        try:
            return runner(
                pmid=pmid, reports_dir=reports_dir, json_dir=json_dir,
                cache_dir=cache_dir, model=model, max_turns=max_turns, cwd=cwd,
            )
        except TypeError:
            # Fake runners in tests may not accept all kwargs
            return runner(pmid=pmid, reports_dir=reports_dir, json_dir=json_dir,
                          cache_dir=cache_dir)

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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 tests/eval/test_batch.py
```

Expected: `PASS: N  FAIL: 0`

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/batch.py tests/eval/test_batch.py
git commit -m "Add batch.py: parallel orchestrator with checkpoint/resume"
```

---

## Task 10: `cli.py` — argparse entry point

**Files:**
- Create: `eval/trec_pm2020/cli.py`
- Create: `eval/trec_pm2020/__main__.py`

Subcommands:
- `sample` — regenerate `sample_500.csv` (sanity check only — the file is already committed)
- `run` — invoke `batch.run_batch` with the given flags
- `build-csv` — invoke `emit.build_master_csv` after the run
- `validate` — sanity-check a completed run

- [ ] **Step 1: Implement `eval/trec_pm2020/cli.py`**

```python
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
```

- [ ] **Step 2: Implement `eval/trec_pm2020/__main__.py`**

```python
"""Make `python -m eval.trec_pm2020 <cmd>` work."""
from eval.trec_pm2020.cli import main
import sys

if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 3: Sanity-check the CLI surfaces**

```bash
python3 -m eval.trec_pm2020 --help
python3 -m eval.trec_pm2020 run --help
python3 -m eval.trec_pm2020 build-csv --help
python3 -m eval.trec_pm2020 validate --help
```

Expected: each prints argparse usage without error.

- [ ] **Step 4: Run all unit tests one more time to confirm nothing regressed**

```bash
for t in tests/eval/test_*.py; do
  echo "=== $t ==="
  python3 "$t" || exit 1
done
```

Expected: every file reports `FAIL: 0`.

- [ ] **Step 5: Commit**

```bash
git add eval/trec_pm2020/cli.py eval/trec_pm2020/__main__.py
git commit -m "Add CLI: python -m eval.trec_pm2020 {sample,run,build-csv,validate}"
```

---

## Task 11: Smoke test (5 papers) + visual diff against pilots

**Files:**
- Generated: `results/trec_pm2020/smoke/` (ignored by git)

This is the **gate** before the full 500 run. Do NOT skip.

- [ ] **Step 1: Pick 5 smoke PMIDs covering the design space**

Use these PMIDs from the sample (one per max-grade bucket, plus a diagnostic study so QUADAS-2 gets exercised):

```bash
head -1 data/trec_pm2020/sample_500.csv
awk -F',' '$2==8' data/trec_pm2020/sample_500.csv | head -1
awk -F',' '$2==4' data/trec_pm2020/sample_500.csv | head -1
awk -F',' '$2==2' data/trec_pm2020/sample_500.csv | head -1
awk -F',' '$2==1' data/trec_pm2020/sample_500.csv | head -1
```

Record the 4 PMIDs printed. Pick a 5th by hand from the diagnostic-flavored topics if you can identify one from `topics2020.xml` (optional — if you can't, just use 5 from the sample).

- [ ] **Step 2: Run the smoke batch**

Ensure you're logged into Claude Code (`claude` CLI) on a Pro/Max subscription. Then:

```bash
tmux new-session -d -s trec_smoke "python3 -m eval.trec_pm2020 run \
    --limit 5 --workers 1 --run-id smoke 2>&1 | tee /tmp/trec_smoke.log"
tmux attach -t trec_smoke
```

Detach with `Ctrl-b d` if you want to keep working. Reattach with `tmux attach -t trec_smoke`.

Expected: 5 papers complete in 10–30 minutes total (single worker).

- [ ] **Step 3: Inspect the outputs**

```bash
ls results/trec_pm2020/smoke/reports/
ls results/trec_pm2020/smoke/json/
cat results/trec_pm2020/smoke/checkpoint.json
```

Expected: 5 `evidence_report_<pmid>.md` files, 5 `<pmid>.json` files, checkpoint shows `completed: [5 PMIDs]` and `failed: []`.

- [ ] **Step 4: Build the master CSV for the smoke run**

```bash
python3 -m eval.trec_pm2020 build-csv results/trec_pm2020/smoke
head results/trec_pm2020/smoke/master.csv
```

Expected: 5+ rows (more if any of the 5 PMIDs appears under multiple topics).

- [ ] **Step 5: Visual diff against existing pilots**

Open one of the smoke reports side-by-side with a structurally similar pilot:

```bash
diff -u paper/pilot_results/evidence_report_rct.md \
        results/trec_pm2020/smoke/reports/evidence_report_<rct_pmid>.md | head -100
```

Check for:
- All 4 sections present (Study Design, Statistical Robustness, Clinical Benchmarking, Bias Risk)
- Stage 3 computation traces (FI iterations, NNT breakdown, LTFU-FI rule, power inputs)
- Score path with disclaimer
- ~500–800 word narrative summary

If anything is materially missing or garbled, stop and revise `PROMPT_TEMPLATE.md` before the full run.

- [ ] **Step 6: Validate the smoke run**

```bash
python3 -m eval.trec_pm2020 validate results/trec_pm2020/smoke
```

Expected exit code 0; "Missing: 0".

- [ ] **Step 7: Commit any prompt-template fixes (if needed)**

If you had to revise `PROMPT_TEMPLATE.md` to fix output quality, commit it:

```bash
git add eval/trec_pm2020/PROMPT_TEMPLATE.md
git commit -m "Tune PROMPT_TEMPLATE.md based on smoke-run observations"
```

If no changes were needed, skip.

---

## Task 12: Update CLAUDE.md to mention the new harness

**Files:**
- Modify: `CLAUDE.md`

Now that the code exists, CLAUDE.md should list the new top-level directory in the Repo Structure section.

- [ ] **Step 1: Read the current Repo Structure section**

```bash
grep -n "^## Repo Structure" CLAUDE.md
sed -n '/^## Repo Structure/,/^##/p' CLAUDE.md
```

- [ ] **Step 2: Add `eval/trec_pm2020/` entry**

Edit the Repo Structure code block in `CLAUDE.md` to include:

```
eval/trec_pm2020/                    ← Batch eval harness vs TREC PM 2020 (500 PMIDs)
data/trec_pm2020/                    ← TREC qrels + stratified sample
```

(Inserted alphabetically between the existing entries.)

- [ ] **Step 3: Add a short "TREC PM 2020 Comparison" subsection**

After the "Pilot Results" section in CLAUDE.md, add:

```markdown
## TREC PM 2020 Comparison (in progress)

Stratified sample of 500 PMIDs from `qrels-expgains-phase2.txt` (125 per max-grade
bucket, seed=42). Harness runs the full pipeline via `claude-agent-sdk` on Opus 4.7
with Tier 1 (abstract-only) input. Outputs land in `results/trec_pm2020/<run_id>/`
(gitignored). A colleague performs the human comparison against TREC Phase 2 evidence
tiers externally.

- **Run a smoke test (5 papers):** `python3 -m eval.trec_pm2020 run --limit 5 --workers 1 --run-id smoke`
- **Run the full 500:** `tmux new -s trec_run "python3 -m eval.trec_pm2020 run --workers 2"`
- **Build master CSV after:** `python3 -m eval.trec_pm2020 build-csv results/trec_pm2020/<run_id>`
- **Validate completion:** `python3 -m eval.trec_pm2020 validate results/trec_pm2020/<run_id>`

Design: `docs/superpowers/specs/2026-05-11-trec-pm2020-batch-eval-harness-design.md`.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "Document TREC PM 2020 batch eval harness in CLAUDE.md"
```

---

## Final Checklist Before the User Kicks Off the 500-Paper Run

After Tasks 1–12 are done and the smoke gate passed cleanly, the user can launch the full run themselves with:

```bash
tmux new -s trec_run
python3 -m eval.trec_pm2020 run --workers 2 --run-id $(date +%Y%m%d-%H%M)
# Ctrl-b d to detach
# tmux attach -t trec_run to reattach
```

Then, after completion (3–10 days on subscription):

```bash
python3 -m eval.trec_pm2020 validate results/trec_pm2020/<run_id>
python3 -m eval.trec_pm2020 build-csv results/trec_pm2020/<run_id>
```

Hand `results/trec_pm2020/<run_id>/master.csv` (+ the `reports/` and `json/` directories) to the colleague for analysis.

---

## Spec Coverage Check

Re-reading the spec section by section against the plan:

- ✅ **Sample design (125 × 4 buckets, seed=42, all_topic_grades)** → Tasks 2–4
- ✅ **Module layout (qrels, sample, pubmed, runner, batch, emit, cli)** → Tasks 2–10
- ✅ **Data flow diagram (sample → batch → pubmed → runner → emit)** → Tasks 5, 8, 9
- ✅ **Agent prompt template referenced by runner** → Task 8 (PROMPT_TEMPLATE.md)
- ✅ **Per-paper JSON schema** → Tasks 6–8 (template + extraction + persistence)
- ✅ **Master CSV columns** → Task 7
- ✅ **run_log.jsonl** → Task 6 (append_log), Task 9 (used by batch)
- ✅ **checkpoint.json atomic writes + resume** → Tasks 6 + 9
- ✅ **Failure handling matrix (fetch_error / invalid_pmid / max_turns / partial_*)** → Task 8 (status codes in runner) + Task 9 (recording in checkpoint)
- ✅ **Auth: ANTHROPIC_API_KEY env var fallback to OAuth** → Inherited from `claude-agent-sdk` defaults; no code branching needed
- ✅ **Concurrency default 2 workers** → Task 10 (`--workers 2` default)
- ✅ **5-paper smoke gate + diff vs pilots** → Task 11
- ✅ **`tmux` background hosting** → Task 11 + Final Checklist
- ✅ **Stages 0–5 unmodified** → Plan only adds `eval/`, doesn't touch `skills/`
- ✅ **Unit tests in custom PASS/FAIL counter style** → All test files in Tasks 2–9
