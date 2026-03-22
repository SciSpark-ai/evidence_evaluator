# Figure 1 — Evidence Evaluator Pipeline Architecture

```mermaid
flowchart TD
    INPUT[/"Input: PDF / DOI / PMID / Text"/]
    INPUT --> S0

    S0["Stage 0 — Study Type Routing\n(LLM classification)"]

    S0 -->|"RCT / preventive /\nobservational / meta-analysis"| S1_FULL
    S0 -->|diagnostic| S1_DIAG
    S0 -->|"phase 0/I"| S1_PHASE

    S1_FULL["Stage 1 — Variable Extraction\n(LLM · 3x majority vote · PICO)"]
    S1_DIAG["Stage 1 — Variable Extraction\n(LLM · 3x majority vote · PICO)"]
    S1_PHASE["Stage 1 — Variable Extraction\n(LLM · 3x majority vote · PICO)"]

    S1_FULL --> S2_FULL["Stage 2 — MCID Search\n(LLM + agentic web search)"]
    S2_FULL --> S3_FULL["Stage 3 — Math Audit\n(Python · NO LLM)\nFI · NNT · post-hoc power"]:::deter

    S1_DIAG --> S2_DIAG["Stage 2 — MCID Search\n(LLM + agentic web search)"]
    S2_DIAG --> S3_DIAG["Stage 3 — Math Audit\n(Python · NO LLM)\nDOR · sensitivity · specificity"]:::deter

    S1_PHASE -.->|"skip Stages 2-3\n(score locked 1-2)"| S4_PHASE

    S3_FULL --> S4_FULL["Stage 4 — Bias Risk\n(LLM)\nRoB 2.0 · GRADE"]
    S3_DIAG --> S4_DIAG["Stage 4 — Bias Risk\n(LLM)\nQUADAS-2"]
    S4_PHASE["Stage 4 — Bias Risk\n(LLM)\nDescriptive review only"]

    S4_FULL --> S5
    S4_DIAG --> S5
    S4_PHASE --> S5

    S5["Stage 5 — Report Synthesis\n(Python rule engine + LLM narrative)\nStructured findings · optional 1-5 score"]:::hybrid

    S5 --> OUTPUT[/"Evidence Evaluation Report\n(JSON + Markdown)"/]

    classDef default fill:#e3f2fd,stroke:#1565c0,stroke-width:1.5px,color:#0d47a1
    classDef deter fill:#e8f5e9,stroke:#2e7d32,stroke-width:1.5px,color:#1b5e20
    classDef hybrid fill:#fff8e1,stroke:#f9a825,stroke-width:1.5px,color:#e65100
    classDef io fill:#e8eaf6,stroke:#3949ab,stroke-width:2px,color:#1a237e

    class INPUT,OUTPUT io
```

**Legend**

| Color | Meaning |
|-------|---------|
| Blue | LLM-driven stage |
| Green | Deterministic Python (no LLM) |
| Amber | Hybrid (Python rule engine + LLM narrative) |
| Indigo | Pipeline input / output |

> **Note:** Phase 0/I studies bypass Stages 2 and 3 entirely (dashed arrow) and have their score locked to 1--2. Diagnostic studies follow the full pipeline but use QUADAS-2 for bias assessment and DOR instead of Fragility Index / NNT in the math audit.
