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
