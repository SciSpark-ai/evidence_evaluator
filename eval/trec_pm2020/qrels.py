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
