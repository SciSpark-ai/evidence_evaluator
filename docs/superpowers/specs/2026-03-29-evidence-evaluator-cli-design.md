# Evidence Evaluator CLI — Design Spec

**Date:** 2026-03-29
**Repo:** SciSpark-ai/evidence-evaluator-cli
**Package:** evidence-evaluator (PyPI)
**Status:** Approved — ready for implementation planning

---

## Overview

Convert the Evidence Evaluator Claude Code skill into a standalone Python package and CLI tool. The package provides a 6-stage agentic pipeline that produces structured evidence quality reports for clinical/biomedical research papers. Users bring their own LLM API key (Anthropic, OpenAI, or any provider supported by litellm).

### What stays the same

- The 6-stage pipeline logic, domain rules, and output format
- Stage 3 deterministic math (`stage3_math.py`) — ported as-is
- Stage 5 score engine (`stage5_report.py`) — ported as-is
- All domain rules (LTFU-FI hard rule, de-duplication, boundary matrix, MCID tier hierarchy, etc.)

### What changes

- LLM stages (0, 1, 2, 4) get their own prompt templates + orchestration (no longer rely on Claude Code agent)
- Stage 2 agentic search uses native LLM tool-use/function-calling instead of a coding agent
- New input layer (PDF, DOI, PMID, text)
- New CLI with rich progress display
- New config system for API keys and model selection

---

## Decisions Log

| Decision | Choice | Rationale |
|---|---|---|
| Architecture | Modular pipeline (Approach B) | Clean separation, testable, extensible |
| LLM abstraction | litellm | 100+ providers, unified API, no custom maintenance |
| CLI framework | Click | Mature, testable via CliRunner, clean subcommands |
| Stage 2 search | Native tool-use / function-calling | LLM drives search strategy naturally, extensible |
| Default model | claude-opus-4-20250514 | Strongest reasoning for evidence evaluation |
| Majority vote | 3x by default, `--no-vote` to disable | Accuracy first, cost escape hatch |
| Progress display | Rich stage-by-stage with spinners | Polished UX, plus `--quiet` / `--verbose` flags |
| Individual stages | `run-stage` subcommand supported | Useful for researchers and debugging |
| Output | Markdown + JSON files (no web server) | Keep focused, users preview however they like |
| Config | `config --init` interactive setup with API key prompts | Good first-run experience |
| PDF parsing | pymupdf | Fast, well-maintained, handles clinical PDFs |

---

## Package Structure

```
evidence-evaluator-cli/
├── pyproject.toml
├── README.md
├── CLAUDE.md
├── LICENSE
├── src/
│   └── evidence_evaluator/
│       ├── __init__.py                  # version + top-level evaluate() API
│       ├── __main__.py                  # python -m evidence_evaluator
│       ├── cli.py                       # Click CLI (evaluate, run-stage, config, version)
│       ├── config.py                    # Config loading: CLI > env > config.toml > defaults
│       ├── models.py                    # Pydantic v2 models for all inter-stage schemas
│       ├── exceptions.py               # Custom exception hierarchy
│       │
│       ├── pipeline/
│       │   ├── __init__.py
│       │   ├── orchestrator.py          # Sequential runner, checkpoints, resume
│       │   ├── stage0_routing.py        # Study type classification (LLM)
│       │   ├── stage1_extraction.py     # Variable extraction + 3x majority vote (LLM)
│       │   ├── stage2_benchmarks.py     # MCID/domain search via tool-use (LLM)
│       │   ├── stage3_math.py           # Deterministic math audit (ported as-is)
│       │   ├── stage4_bias.py           # Bias risk assessment (LLM)
│       │   └── stage5_report.py         # Score engine (ported) + LLM narrative
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py               # litellm wrapper, tool-use support
│       │   ├── prompts.py              # Template loader from prompts/
│       │   └── tools.py                # Tool definitions for Stage 2 search
│       │
│       ├── prompts/                     # External .txt prompt templates
│       │   ├── __init__.py              # Required for importlib.resources
│       │   ├── stage0_system.txt
│       │   ├── stage1_system.txt
│       │   ├── stage2_system.txt
│       │   ├── stage4_system.txt
│       │   └── stage5_narrative.txt
│       │
│       ├── search/
│       │   ├── __init__.py
│       │   ├── pubmed.py               # PubMed E-utilities client
│       │   └── crossref.py             # CrossRef API client
│       │
│       ├── input/
│       │   ├── __init__.py
│       │   ├── pdf.py                  # pymupdf text extraction + tiered sections
│       │   ├── doi.py                  # DOI resolution via CrossRef
│       │   ├── pmid.py                 # PMID resolution via PubMed
│       │   └── loader.py              # Unified input dispatcher
│       │
│       └── output/
│           ├── __init__.py
│           ├── markdown.py             # Markdown report renderer
│           ├── json_output.py          # JSON output formatter
│           └── naming.py              # Filename convention logic
│
├── tests/
│   ├── conftest.py                     # Fixtures, mock LLM responses
│   ├── test_stage3_math.py             # Ported 147 tests (pytest)
│   ├── test_stage5_report.py           # Ported 70 tests (pytest)
│   ├── test_cli.py                     # Click CliRunner tests
│   ├── test_orchestrator.py            # Pipeline with mocked LLM
│   ├── test_models.py                  # Pydantic validation
│   ├── test_input.py                   # PDF/DOI/PMID handling
│   └── fixtures/                       # Canned LLM responses, sample data
│
└── .github/
    └── workflows/
        ├── ci.yml                      # pytest + ruff on PR
        └── publish.yml                 # PyPI publish on tag
```

---

## LLM Layer

### Client (`llm/client.py`)

Thin wrapper around litellm with three calling patterns:

```python
class LLMClient:
    def complete(system, user) -> str
        # Simple text completion

    def complete_json(system, user, schema: PydanticModel) -> dict
        # Structured output with JSON validation
        # Uses response_format where supported, prompt-based fallback
        # Retries up to 2x if validation fails

    def complete_with_tools(system, user, tools, tool_executor) -> dict
        # Tool-use loop for Stage 2
        # Sends tool definitions, LLM responds with tool calls,
        # tool_executor runs them locally, results fed back
        # Repeats until LLM returns final_answer or max rounds hit
```

- **Temperature:** 0.0 for extraction stages (0, 1, 2, 4), 0.3 for narrative (Stage 5)
- **Default model:** `claude-opus-4-20250514`
- **Retry:** 2 retries with exponential backoff on rate limits / timeouts

### Tool Definitions (`llm/tools.py`)

Tools available to the LLM during Stage 2 search:

| Tool | Parameters | Returns |
|---|---|---|
| `search_pubmed` | `query: str, max_results: int` | List of {pmid, title, abstract} |
| `search_crossref` | `query: str, max_results: int` | List of {doi, title, abstract} |
| `fetch_abstract` | `pmid: str` | Full structured abstract text |

The LLM decides which tools to call and when. Capped at 5 tool-use rounds per Stage 2 run.

### Prompt Templates (`prompts/`)

Each LLM stage gets a system prompt file containing:
- Domain knowledge (extracted from current `references/` docs)
- Output JSON schema
- Specific instructions and rules

User prompts are constructed at runtime from pipeline context (paper text, previous stage outputs).

---

## Pipeline Orchestration

### PipelineContext

Accumulates all stage outputs. Fully serializable to JSON for checkpoints and resume.

```python
class PipelineContext(BaseModel):           # Pydantic v2 for serialization/checkpoints
    input_text: str
    input_metadata: dict
    stage0_output: Optional[Stage0Output] = None
    stage1_output: Optional[Stage1Output] = None
    stage2_output: Optional[Stage2Output] = None
    stage3_output: Optional[dict] = None    # deterministic, plain dict
    stage4_output: Optional[Stage4Output] = None
    stage5_output: Optional[Stage5Output] = None
    completed_stages: list[int] = []
```

### Execution flow

1. Stages run 0 → 5 sequentially
2. After each stage, checkpoint JSON saved to `~/.evidence-evaluator/checkpoints/`
3. `--resume checkpoint.json` loads context and skips completed stages
4. Skip logic: `phase_0_1` study type → stages 2+3 skipped automatically

### Error handling

- `--fail-fast` (default): Stop on first error, report which stage failed
- `--best-effort`: Continue past failures, produce partial report with warnings
- LLM errors: 2 retries with exponential backoff before failing

### Stage 1 majority vote

Runs 3 independent LLM calls using `concurrent.futures.ThreadPoolExecutor`. Fields where all 3 agree get high confidence; disagreements flagged in `low_confidence_fields`. Disabled with `--no-vote`.

---

## CLI Design

### Commands

```bash
# Primary: evaluate a paper
evidence-evaluator evaluate paper.pdf
evidence-evaluator evaluate --doi 10.1056/NEJMoa1911303
evidence-evaluator evaluate --pmid 31535829
evidence-evaluator evaluate --text "Abstract: ..."

# Run individual stage
evidence-evaluator run-stage 3 --input context.json
evidence-evaluator run-stage 5 --input context.json

# Configuration
evidence-evaluator config --init          # Interactive setup (prompts for API key + model)
evidence-evaluator config --show          # Print current config
evidence-evaluator config --set model claude-opus-4-20250514
evidence-evaluator config --set api_key sk-ant-...

# Version
evidence-evaluator version
```

### Evaluate flags

```
--output-format, -f    markdown | json | both    [default: markdown]
--output-dir, -o       Output directory           [default: ./]
--model, -m            LLM model override
--api-key, -k          API key override
--no-score             Disable suggested score
--no-vote              Single extraction (skip 3x majority vote)
--resume               Resume from checkpoint JSON
--fail-fast            Stop on first error         [default]
--best-effort          Continue on errors
--verbose, -v          Debug-level logging
--quiet, -q            Suppress all output except file path
```

### Progress display (Rich)

```
◼ Stage 0: Study Type Routing .............. done (3s)
◼ Stage 1: Variable Extraction (3x vote) ... done (12s)
◷ Stage 2: MCID & Benchmark Search ........ round 2/5
◻ Stage 3: Mathematical Audit
◻ Stage 4: Bias Risk Assessment
◻ Stage 5: Report Synthesis
```

---

## Config System

### First-run experience

```bash
$ evidence-evaluator config --init

Evidence Evaluator — First Time Setup
=====================================

1. Select your LLM provider:
   [1] Anthropic (Claude)
   [2] OpenAI (GPT)
   [3] Other (enter model string)
   > 1

2. Enter your Anthropic API key:
   (Get one at https://console.anthropic.com/settings/keys)
   > sk-ant-api03-...

3. Select model:
   [1] claude-opus-4-20250514 (recommended — best reasoning)
   [2] claude-sonnet-4-20250514 (faster, cheaper)
   [3] Custom model string
   > 1

Config saved to ~/.evidence-evaluator/config.toml
Run: evidence-evaluator evaluate <paper.pdf> to get started!
```

### Config file (`~/.evidence-evaluator/config.toml`)

```toml
[llm]
model = "claude-opus-4-20250514"
api_key = "sk-ant-api03-..."    # Your LLM API key

[pipeline]
majority_vote = true
max_search_rounds = 5
fail_fast = true

[output]
format = "markdown"
directory = "."
include_score = true
```

### Resolution order

CLI flags > environment variables > config.toml > defaults

Supported env vars:
- `EVIDENCE_EVALUATOR_API_KEY`
- `ANTHROPIC_API_KEY` (litellm reads natively)
- `OPENAI_API_KEY` (litellm reads natively)
- `EVIDENCE_EVALUATOR_MODEL`

---

## Input Handling

### Supported inputs

| Input | Method | What you get |
|---|---|---|
| PDF file | pymupdf text extraction | Full text + tiered sections |
| DOI | CrossRef API resolution | Abstract + metadata (warn: no full text) |
| PMID | PubMed E-utilities | Abstract + metadata (warn: no full text) |
| Raw text | `--text` flag | Whatever user provides |
| JSON | Pipeline context file | Resume or pre-extracted data |

### Tiered text extraction (PDF)

For PDFs, the loader detects section headings (Abstract, Methods, Results, Conclusion) via regex heuristics and returns:
- `tier1_text` — abstract + methods + conclusion (~20% of tokens)
- `full_text` — entire document

The pipeline starts with tier 1. If the LLM flags low confidence in Stage 1, it escalates to full text.

### DOI/PMID warning

When input is DOI or PMID, only the abstract is available. The CLI warns:
> "Only abstract available via DOI/PMID. For full evaluation, provide the PDF."

The pipeline still runs but extraction confidence will be lower.

---

## Output Handling

### Formats

- **Markdown** (default): Full evidence report with 4 sections, Stage 3 computation traces, optional score with path, narrative, disclaimer
- **JSON**: Complete pipeline context with all stage outputs, metadata, score path
- **Both**: `--output-format both` writes both files

### Filename convention

`evidence_report_[first_author]_[year]_[identifier].md`

Examples:
- `evidence_report_McMurray_2019_pmid31535829.md`
- `evidence_report_Ridker_2008_NEJMoa0807646.md`

### Output location

Current directory by default. `--output-dir ./reports` to override.

---

## Pydantic Models

All inter-stage data contracts are Pydantic v2 models. Key models:

- **`Stage0Output`**: study_type (enum), confidence, rationale, human_review_flag
- **`ExtractedVariables`**: n_intervention, n_control, events, ltfu_count, p_value, effect_size, blinding, randomization, etc.
- **`PICO`**: population, intervention, comparator, outcome, search_string
- **`Stage1Output`**: study_type, extracted_variables, grading, pico, extraction_qa
- **`Stage2Output`**: mcid, mcid_unit, source, tier, observed_effect, effect_vs_mcid, domain_n, domain_nnt_threshold
- **`Stage4Domain`**: domain, evidence_found, judgment, delta, reasoning
- **`Stage4Output`**: tool, domains[], surrogate_endpoint, heterogeneity, overall_concern
- **`PipelineContext`**: all stage outputs, metadata, completed_stages

These provide runtime validation, serialization for checkpoints, and documentation.

---

## Testing Strategy

### Ported tests (deterministic stages)

- **147 Stage 3 tests** — converted from custom pass/fail to pytest
- **70 Stage 5 tests** — converted from custom pass/fail to pytest
- These cover: FI, NNT, DOR, power, de-duplication, boundary matrix, LTFU floor pierce, score prerequisites, report assembly

### New tests

- **Mocked LLM tests** — Each LLM stage (0, 1, 2, 4, 5 narrative) tested with canned responses from `tests/fixtures/`. Mock `litellm.completion`.
- **CLI tests** — Click `CliRunner` for command parsing, flag handling, error messages, config init
- **Integration test** — Full pipeline with all LLM calls mocked, verifying stage chaining and correct output
- **Input tests** — PDF extraction (small test PDF), DOI/PMID resolution (mocked HTTP)
- **Model tests** — Pydantic validation (valid inputs pass, invalid raise ValidationError)

### CI

GitHub Actions:
- **ci.yml**: pytest + ruff on every PR
- **publish.yml**: Build + publish to PyPI on git tag (e.g., `v0.1.0`)

---

## Dependencies

### Runtime

```
litellm>=1.40          # LLM abstraction (Anthropic, OpenAI, 100+ providers)
click>=8.0             # CLI framework
pydantic>=2.0          # Data models + validation
httpx>=0.25            # HTTP client (PubMed, CrossRef, DOI resolution)
pymupdf>=1.24          # PDF text extraction
scipy>=1.10            # Fisher exact test (Stage 3)
statsmodels>=0.14      # Power analysis (Stage 3)
numpy>=1.24            # Numerical (Stage 3)
rich>=13.0             # Progress display + formatted output
tomli>=2.0;python_version<"3.11"  # TOML parsing for Python 3.10

Requires Python >= 3.10
```

### Dev

```
pytest>=8.0
pytest-cov
respx>=0.21            # HTTP mocking for httpx
ruff                   # Linting
```

---

## Top-Level Python API

For programmatic use (not just CLI):

```python
from evidence_evaluator import evaluate

result = evaluate(
    path="paper.pdf",           # or doi="10.1056/...", pmid="31535829", text="..."
    model="claude-opus-4-20250514",
    api_key="sk-ant-...",
    output_format="both",       # "markdown" | "json" | "both"
    include_score=True,
)

# result contains:
# - result["markdown"]       → report string
# - result["json"]           → full pipeline context dict
# - result["score"]          → score dict (if enabled)
# - result["output_paths"]   → list of written file paths
```

---

## README Content Plan

The new repo's README.md will cover:

1. **One-liner + badges** (PyPI, CI, license)
2. **What it does** — 6-stage pipeline summary with ASCII flow diagram
3. **Quick start** — pip install, config --init (with API key setup), evaluate paper.pdf
4. **Installation** — pip, from source
5. **Configuration** — API key setup (config --init prompts for key), model selection, env vars
6. **Usage examples** — PDF, DOI, PMID, JSON output, run-stage, programmatic API
7. **Pipeline stages** — brief description of each stage
8. **Output format** — example markdown report (truncated), example JSON
9. **Supported providers** — Anthropic, OpenAI, any litellm-supported provider
10. **Python API** — `from evidence_evaluator import evaluate`
11. **Configuration reference** — full config.toml reference
12. **Development** — contributing, running tests
13. **Domain rules** — key EBM rules summary
14. **Disclaimer** — "1-5 score is heuristic, pending expert calibration. Does not replace clinical judgment."
15. **Citation** — Claw4S 2026 paper reference
16. **License** — MIT

---

## CLAUDE.md Content Plan

The new repo's CLAUDE.md will cover:

1. **Project overview** — standalone Python package for clinical evidence evaluation
2. **Repo structure** — directory tree with descriptions
3. **Running tests** — `pytest tests/` (ported to pytest)
4. **Architecture** — pipeline stages, LLM vs deterministic, prompt templates
5. **Key domain rules** — LTFU definition, LTFU-FI hard rule, MCID tier hierarchy, de-duplication, boundary matrix, study type routing
6. **LLM configuration** — litellm, supported providers, tool-use in Stage 2
7. **Adding a new LLM stage** — where to add prompts, models, stage module
8. **Config system** — resolution order, env vars, config.toml location
9. **Pilot results** — same 5-paper validation table
10. **Tech context** — Python 3.10+, key dependencies

---

## Domain Rules (Unchanged)

All domain rules from the original skill carry over exactly:

- **LTFU definition**: Includes exclusions + withdrawals + AE-related dropouts. Deaths as primary endpoint events are NOT LTFU.
- **LTFU > FI hard rule**: LTFU exceeds FI → -2 grades, no exceptions, never deduplicated
- **MCID tier hierarchy**: Tier 1→2→3→4, stop at first hit. Tier 3 HR conversion via `CER x (1 - HR)`.
- **Effect vs MCID**: Binary only (exceeds or below). No "borderline."
- **De-duplication**: {power < 0.80, N < domain standard, NNT > threshold} → apply only largest absolute delta
- **Study type routing**: phase_0_1 skips stages 2+3, locks score 1-2; diagnostic uses QUADAS-2 + DOR
- **Initial grade**: N takes precedence over phase label. Grade 5 requires ALL of: multi-center + double-blind + N > 1000.
- **Boundary matrix**: Grade 5 base/max/min = 5/5/3; Grade 4 = 4/4/2; Grade 3 = 3/4/2; Grade 2 = 2/3/1; Grade 1 = 1/1/1
- **Score disclaimer**: Always displayed — "1-5 score is heuristic, pending expert calibration."
