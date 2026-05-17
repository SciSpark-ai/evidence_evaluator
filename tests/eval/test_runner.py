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
