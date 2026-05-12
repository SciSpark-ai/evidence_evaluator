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
        transcript, sdk_meta = _run_agent(prompt, model=model, max_turns=max_turns, cwd=cwd)
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

    usage = sdk_meta.get("usage") or {}
    try:
        data = extract_final_json(transcript)
    except ValueError as e:
        return RunResult(
            pmid=pmid, status="error",
            error_msg=f"Could not extract final JSON: {e}",
            runtime_s=time.monotonic() - t0,
            input_tokens=usage.get("input_tokens", 0) or 0,
            output_tokens=usage.get("output_tokens", 0) or 0,
        )

    # Augment data with runtime metadata
    data.setdefault("pmid", pmid)
    data["model"] = model
    data["started_at"] = started_at.isoformat()
    data["finished_at"] = datetime.now(timezone.utc).isoformat()
    data["runtime_s"] = round(time.monotonic() - t0, 2)
    # Flat back-compat fields (used by run_log.jsonl + master.csv).
    data["input_tokens"] = usage.get("input_tokens", 0) or 0
    data["output_tokens"] = usage.get("output_tokens", 0) or 0
    # Full per-paper SDK metadata: usage breakdown (cache_read/cache_creation),
    # total_cost_usd, num_turns, model_usage, error fields, etc.
    data["sdk_meta"] = sdk_meta
    data["total_cost_usd"] = sdk_meta.get("total_cost_usd")
    data["num_turns"] = sdk_meta.get("num_turns")
    data["report_path"] = os.path.join(
        os.path.basename(reports_dir.rstrip(os.sep)),
        f"evidence_report_{pmid}.md",
    )

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


def _run_agent(
    prompt: str, model: str, max_turns: int, cwd: Optional[str]
) -> tuple[str, Dict[str, Any]]:
    """Invoke the Claude SDK and return (full_transcript_text, sdk_meta).

    `sdk_meta` is a dict capturing every observable field from the
    `ResultMessage` — usage (cache_read/cache_creation/input/output tokens),
    total_cost_usd, num_turns, duration_ms, duration_api_ms, model_usage,
    is_error, api_error_status, subtype, stop_reason, session_id.

    Uses the `query()` function (ideal for one-shot batch automation).
    Isolated so unit tests don't need to mock the SDK.

    Raises _MaxTurnsExceeded if the agent hit the turn cap.
    """
    import asyncio
    from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

    options = ClaudeAgentOptions(
        model=model,
        max_turns=max_turns,
        cwd=cwd,
        allowed_tools=["Bash", "Read", "Write", "Glob", "Grep"],
        permission_mode="acceptEdits",
    )

    def _usage_to_dict(u: Any) -> Dict[str, Any]:
        if u is None:
            return {}
        if isinstance(u, dict):
            return dict(u)
        # Fall back to attribute scraping for typed Usage objects
        out: Dict[str, Any] = {}
        for k in ("input_tokens", "output_tokens",
                  "cache_creation_input_tokens", "cache_read_input_tokens",
                  "server_tool_use", "service_tier"):
            v = getattr(u, k, None)
            if v is not None:
                out[k] = v
        return out

    async def _go() -> tuple[str, Dict[str, Any]]:
        transcript_parts: list[str] = []
        sdk_meta: Dict[str, Any] = {}

        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, AssistantMessage):
                for block in msg.content or []:
                    text = getattr(block, "text", None)
                    if text:
                        transcript_parts.append(text)
                # Skip AssistantMessage.usage on purpose; ResultMessage carries
                # the canonical aggregate.

            elif isinstance(msg, ResultMessage):
                sdk_meta = {
                    "subtype": getattr(msg, "subtype", None),
                    "stop_reason": getattr(msg, "stop_reason", None),
                    "is_error": getattr(msg, "is_error", None),
                    "api_error_status": getattr(msg, "api_error_status", None),
                    "num_turns": getattr(msg, "num_turns", None),
                    "duration_ms": getattr(msg, "duration_ms", None),
                    "duration_api_ms": getattr(msg, "duration_api_ms", None),
                    "total_cost_usd": getattr(msg, "total_cost_usd", None),
                    "session_id": getattr(msg, "session_id", None),
                    "usage": _usage_to_dict(getattr(msg, "usage", None)),
                    "model_usage": getattr(msg, "model_usage", None) or {},
                }
                if sdk_meta["stop_reason"] == "max_turns":
                    raise _MaxTurnsExceeded(f"Agent stopped at max_turns={max_turns}")

        return "".join(transcript_parts), sdk_meta

    return asyncio.run(_go())
