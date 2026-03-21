# 🔬 Evidence Evaluator

**Automated structured evidence quality evaluation for clinical and biomedical research papers.**

Built on the [SciSpark](https://scispark.ai) EvidenceScore pipeline (v2) — a 6-stage agentic system that mirrors the reasoning of a trained Evidence-Based Medicine (EBM) reviewer. Drop in any paper; get a comprehensive, auditable evidence report back.

![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Acceptance%20Tests-8%2F8%20passing-brightgreen)
![Math Tests](https://img.shields.io/badge/Math%20Unit%20Tests-21%2F21%20passing-brightgreen)
![Status](https://img.shields.io/badge/Status-Pre--launch-orange)

---

## What It Does

Given a paper (PDF, pasted text, DOI, or PMID), the pipeline runs six sequential stages and produces:

- A **structured Evidence Evaluation Report** covering statistical robustness, clinical benchmarking, and bias risk — every finding traceable to its source
- A **500–800 word plain-language narrative summary** written for clinicians
- An **optional Markdown export** (`.md` file) for sharing or archiving
- An **optional heuristic 1–5 score** via a transparent rule engine (labeled as pending expert calibration)

> **Design philosophy:** This is not a black-box classifier. Every finding is auditable and citable — Fragility Index computed by Fisher exact test, MCID sourced from named clinical registries, bias domains assessed per RoB 2.0 protocol. The report is the contribution; the score is one possible way to summarize it.

---

## Pipeline

```
Input (PDF / text / DOI / PMID)
       │
       ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 0 │ Study Type Pre-Routing                       │
 │          │ RCT · diagnostic · preventive · observational│
 │          │ meta-analysis · phase 0/I                    │
 └──────────┼──────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 1 │ Variable Extraction & Initial Grading        │
 │          │ LLM · self-reflection few-shot · 3× CoT      │
 │          │ majority vote · PICO extraction              │
 └──────────┼──────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 2 │ Domain Benchmark & MCID Search               │
 │          │ Agentic search · up to 5 rounds              │
 │          │ COMET → PubMed SR → Guidelines → Cohen proxy │
 └──────────┼──────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 3 │ Deterministic Math Audit          [no LLM]   │
 │          │ Fragility Index · FQ · NNT/NNH               │
 │          │ Post-hoc power · DOR · LTFU-FI rule          │
 └──────────┼──────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 4 │ Bias Risk & Evidence Certainty Audit         │
 │          │ RoB 2.0 · QUADAS-2 · GRADE upgrading         │
 │          │ Surrogate endpoint · I² inconsistency        │
 └──────────┼──────────────────────────────────────────────┘
            │
            ▼
 ┌─────────────────────────────────────────────────────────┐
 │  Stage 5 │ Evidence Evaluation Report Synthesis         │
 │          │ Structured findings · LLM narrative          │
 │          │ Optional score · Optional Markdown export    │
 └─────────────────────────────────────────────────────────┘
            │
            ▼
     Evidence Evaluation Report
     (JSON · plain text · Markdown)
```

### Stage Routing by Study Type

| Stage | RCT | Diagnostic | Preventive | Observational | Meta-analysis | Phase 0/I |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 0 — Routing | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 1 — Extraction | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 2 — MCID Search | ✅ | AUC/Sn/Sp | NNT focus | ✅ | ✅ | ⛔ skip |
| 3 — Math Audit | FI+NNT+power | DOR only | FI+NNT+power | FI+NNT | FI+NNT+power | ⛔ skip |
| 4 — Bias Audit | RoB 2.0 | QUADAS-2 | RoB 2.0 | GRADE | RoB 2.0 | RoB 2.0 (2 domains) |
| Score range | 1–5 | 1–5 | 1–5 | 1–5 | 1–5 | 🔒 1–2 |

---

## Report Output

### Structured sections

| Section | Contents | Source stage |
|---|---|---|
| Study Design & Population | PICO, N, blinding, randomization, phase | Stage 0 + 1 |
| Statistical Robustness | FI, FQ, post-hoc power, LTFU-FI rule, NNT/NNH, DOR | Stage 3 |
| Clinical Benchmarking | MCID value + source tier, observed effect vs. MCID | Stage 2 |
| Bias Risk Assessment | Per-domain RoB 2.0 / QUADAS-2 / GRADE findings | Stage 4 |

### Key rules

- **LTFU > FI hard rule** — if lost-to-follow-up exceeds the Fragility Index → −2 grades, no exceptions, never deduplicated
- **De-duplication** — {power < 0.80, N < domain standard, NNT > threshold} share the same statistical stability dimension; only the most severe deduction is applied
- **QUADAS-2 cap** — maximum −2 total across all diagnostic domains
- **GRADE upgrade cap** — maximum +1 regardless of factors met

### Markdown export (optional)

Pass `output_format: markdown` to receive the full report as a shareable `.md` file. The markdown template uses 🟢/🟡/🔴 emoji status indicators in every metric table for at-a-glance scannability. Filename convention:

```
evidence_report_[first_author]_[year]_[pmid].md
```

### Optional suggested score

| Score | Label | Indicator |
|---|---|---|
| 5 | Excellent | ★★★★★ |
| 4 | Good | ★★★★☆ |
| 3 | Average | ★★★☆☆ |
| 2 | Fair | ★★☆☆☆ |
| 1 | Very Low | ★☆☆☆☆ |

> ⓘ The 1–5 score is generated by a deterministic rule engine. Design choices are pending expert calibration. Always displayed with this disclaimer — never presented as a validated clinical instrument.

---

## Repo Structure

```
evidence_evaluator/
├── SKILL.md                              ← Agent skill entry point
├── references/
│   ├── stages_0_1.md                     ← Stage 0: routing · Stage 1: extraction
│   ├── stages_2_3.md                     ← Stage 2: MCID search · Stage 3: math audit
│   ├── stage_4.md                        ← Stage 4: bias risk (RoB 2.0 / QUADAS-2 / GRADE)
│   ├── stage_5_report.md                 ← Stage 5: report synthesis + markdown export
│   ├── formulas.md                       ← All formulas (FI, FQ, NNT, DOR, power)
│   └── eval_framework.md                 ← Acceptance tests T1–T8 + Experiments 3A–3F
└── tests/
    ├── acceptance_tests_T1_T8.py         ← 8 scenario tests · all pass ✅
    └── experiment_3B_math_unit_tests.py  ← Stage 3 math unit tests · 21/21 correct ✅
```

---

## Running Tests

```bash
# Install dependencies
pip install scipy statsmodels numpy

# Acceptance tests T1–T8 (routing logic, deduction rules, special cases)
python tests/acceptance_tests_T1_T8.py

# Stage 3 math unit tests (FI, FQ, NNT, DOR, post-hoc power)
python tests/experiment_3B_math_unit_tests.py
```

### Acceptance test coverage

| Test | Scenario | Validates |
|---|---|---|
| T1 | Grade 5 RCT, FI > 10, low bias | FI robust flag, +0.5 delta, score = 5 |
| T2 | Large RCT, LTFU > FI | Hard −2 rule fires, score drops to 3 |
| T3 | Phase 0/I trial | Stages 2+3 skipped, score locked 1–2 |
| T4 | Diagnostic, AUC < 0.70, case-control | QUADAS-2 selected, DOR computed |
| T5 | Confirmed retracted paper | Exclusion flag, all sections suppressed |
| T6 | Preventive, NNT = 150 vs threshold 50 | NNT exceeds-threshold flag, −1 applied |
| T7 | Observational, RR > 2.0 | GRADE upgrade triggered, grade rises to 4 |
| T8 | MCID: all tiers exhausted | Cohen's d Tier 4 proxy + warning label |

---

## Validation Experiments (for publication)

| Experiment | Claim | Method | Target |
|---|---|---|---|
| **3A** — Extraction accuracy *(primary)* | Pipeline extracts quantitative fields accurately | Precision/recall on 50–100 papers vs. manual verification | F1 ≥ 0.85 |
| **3B** — Math correctness | FI, FQ, NNT, power computed correctly | Unit tests on synthetic + real cases with published FI values | 100% deterministic |
| **3C** — Study type classification | Stage 0 classifies all 6 types correctly | Validate against PubMed MeSH tags on 300 papers | Macro F1 ≥ 0.85 |
| **3D** — MCID retrieval quality | Stage 2 retrieves domain-appropriate MCID | Compare to COMET/OMERACT on 30 papers | Tier 1/2 hit ≥ 70% |
| **3E** — Test-retest reliability | Same paper → consistent report | Run 3× on 20 papers | Stage 3: 100%; Stage 1+4: ≥ 90% |
| **3F** — Bias judgment agreement | RoB 2.0 / QUADAS-2 agrees with Cochrane | Cohen's κ vs. published Cochrane assessments | κ ≥ 0.60 per domain |

Minimum viable paper: **3E + 3C + 3A + 3B**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| LLM (Stages 1, 2, 4, 5) | `anthropic/claude-sonnet-4-6` via GMI Cloud (OpenAI-compatible API) |
| Fallback LLM | `anthropic/claude-sonnet-4-5` |
| Math audit (Stage 3) | Python · `scipy.stats` · `statsmodels` · `numpy` |
| PDF parsing | GROBID (primary) · PyMuPDF (fallback) |
| Search APIs | PubMed E-utilities · Semantic Scholar · OpenAlex |
| Backend | FastAPI (Python 3.11+) |
| Frontend | React + Vite + TailwindCSS |
| Export | WeasyPrint (PDF) · stdlib json · Markdown |
| Deployment | Docker + docker-compose |

---

## References

| Method | Citation |
|---|---|
| PICO extraction · CoT majority vote | Li et al. (Quicker), *npj Digital Medicine* 2025 |
| Programmatic math audit pipeline | Wang et al. (TrialMind), *npj Digital Medicine* 2025 |
| Fragility Index | Walsh et al., *Journal of Clinical Epidemiology* 2014 |
| Fragility Quotient | Superchi et al., *Journal of Clinical Epidemiology* 2019 |
| RoB 2.0 | Sterne et al., *BMJ* 2019 |
| QUADAS-2 | Whiting et al., *Annals of Internal Medicine* 2011 |
| GRADE upgrading | Guyatt et al., *Journal of Clinical Epidemiology* 2011 |
| MCID concept | Jaeschke et al., *Controlled Clinical Trials* 1989 |
| Tiered document reading | DocAgent, *EMNLP* 2025; PaperGuide, arXiv 2026 |

---

## Publication Target

**Primary:** *npj Digital Medicine* (Quicker published here Dec 2025, vol. 8, art. 793 — same journal, same clinical informatics community)

**Secondary:** ML4H (NeurIPS Workshop) · CHIL · AMIA · JAMIA

**Proposed title:** *"Automated Structured Evidence Evaluation of Clinical Research Papers Using Multi-Agent LLMs"*

---

*Built by [SciSpark](https://scispark.ai) · [team@scispark.ai](mailto:team@scispark.ai)*
*Stanford Psychiatry Department · Pre-launch · March 2026*
