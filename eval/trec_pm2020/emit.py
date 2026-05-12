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


PROGRESS_TSV_HEADER = [
    "timestamp", "pmid", "status", "score", "study_type",
    "runtime_s", "output_tokens", "completed", "failed", "total",
]


def append_progress_tsv(path: str, fields: Dict[str, Any]) -> None:
    """Append one paper's progress to a tail-friendly TSV.

    Creates the file with a header row on first write. `fields` should contain
    the keys in PROGRESS_TSV_HEADER; missing keys are written as empty cells.
    """
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    write_header = not os.path.exists(path)
    with open(path, "a") as f:
        if write_header:
            f.write("\t".join(PROGRESS_TSV_HEADER) + "\n")
        row = [str(fields.get(k, "")) for k in PROGRESS_TSV_HEADER]
        f.write("\t".join(row) + "\n")


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
