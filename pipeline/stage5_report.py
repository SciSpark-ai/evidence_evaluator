"""
Stage 5: Evidence Evaluation Report Synthesis

Deterministic components:
1. Score rule engine — collect deltas, de-duplicate, apply boundary matrix
2. Structured report assembly — format all stage outputs into plain-text report

The narrative summary (LLM) and Markdown export are agent tasks, not code.
"""

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCORE_LABELS = {
    5: ("Excellent", "\u2605\u2605\u2605\u2605\u2605"),
    4: ("Good", "\u2605\u2605\u2605\u2605\u2606"),
    3: ("Average", "\u2605\u2605\u2605\u2606\u2606"),
    2: ("Fair", "\u2605\u2605\u2606\u2606\u2606"),
    1: ("Very Low", "\u2605\u2606\u2606\u2606\u2606"),
}

# Boundary matrix: starting_grade → (base, max, min)
# LTFU hard rule can pierce the floor
BOUNDARY_MATRIX = {
    5: (5, 5, 3),
    4: (4, 4, 2),
    3: (3, 4, 2),
    2: (2, 3, 1),
    1: (1, 1, 1),
}

QUADAS2_CAP = -2
GRADE_UPGRADE_CAP = 1


# ---------------------------------------------------------------------------
# De-duplication (Stage 5 level — cross-stage)
# ---------------------------------------------------------------------------

def deduplicate_stage4_deltas(stage4_output, study_type, stage2_output=None):
    """Apply Stage 5 de-duplication rules to Stage 4 deltas.

    Rules:
    - QUADAS-2 cap: max −2 total across all domains
    - GRADE upgrade cap: max +1 total
    - Diagnostic case-control overlap: Stage 2 case-control deduction and
      QUADAS-2 patient selection are the same bias — apply only once

    Args:
        stage4_output: dict with "domains" list of {domain, delta, ...} and
                       optional "surrogate_endpoint_delta", "heterogeneity_delta"
        study_type: str
        stage2_output: dict with optional "case_control_deduction" flag

    Returns:
        dict with total_delta, domain_details, dedup_notes
    """
    domains = stage4_output.get("domains", [])
    surrogate_delta = stage4_output.get("surrogate_endpoint_delta", 0)
    heterogeneity_delta = stage4_output.get("heterogeneity_delta", 0)

    domain_sum = sum(d.get("delta", 0) for d in domains)
    dedup_notes = []

    # QUADAS-2 cap
    if study_type == "diagnostic" and domain_sum < QUADAS2_CAP:
        dedup_notes.append(
            f"QUADAS-2 cap applied: raw domain sum {domain_sum} capped to {QUADAS2_CAP}"
        )
        domain_sum = QUADAS2_CAP

    # GRADE upgrade cap
    if study_type == "observational" and domain_sum > GRADE_UPGRADE_CAP:
        dedup_notes.append(
            f"GRADE upgrade cap applied: raw sum +{domain_sum} capped to +{GRADE_UPGRADE_CAP}"
        )
        domain_sum = GRADE_UPGRADE_CAP

    # Diagnostic case-control overlap with Stage 2
    if study_type == "diagnostic" and stage2_output:
        s2_case_control = stage2_output.get("case_control_deduction", False)
        s4_patient_selection = any(
            d.get("domain") == "patient_selection" and d.get("delta", 0) < 0
            for d in domains
        )
        if s2_case_control and s4_patient_selection:
            dedup_notes.append(
                "Case-control spectrum bias: Stage 2 deduction suppressed "
                "(already counted in QUADAS-2 patient selection)"
            )

    total = domain_sum + surrogate_delta + heterogeneity_delta
    return {
        "domain_delta": domain_sum,
        "surrogate_delta": surrogate_delta,
        "heterogeneity_delta": heterogeneity_delta,
        "total_delta": total,
        "dedup_notes": dedup_notes,
    }


# ---------------------------------------------------------------------------
# Score Rule Engine
# ---------------------------------------------------------------------------

def compute_suggested_score(
    initial_grade,
    stage2_deltas=None,
    stage3_output=None,
    stage4_output=None,
    study_type="RCT_intervention",
    stage2_output=None,
    excluded=False,
):
    """Compute the optional heuristic 1–5 score.

    Args:
        initial_grade: int 1–5 from Stage 1
        stage2_deltas: dict with individual deltas from Stage 2, e.g.:
            {"effect_below_mcid": -1, "n_below_domain": -1, "nnt_exceeds": -1,
             "case_control_deduction": True/False, "auc_below": -1, ...}
            De-duplication of {effect_below_mcid, n_below_domain, nnt_exceeds}
            with Stage 3 statistical stability is handled here.
        stage3_output: dict from run_stage3() — contains metrics and total_delta
        stage4_output: dict with "domains" list and optional surrogate/heterogeneity
        study_type: str
        stage2_output: full Stage 2 output (for case-control dedup)
        excluded: bool — retracted/excluded paper

    Returns:
        dict with score, label, stars, score_path, disclaimer
    """
    if excluded:
        return {
            "enabled": False,
            "score": None,
            "label": "Excluded",
            "stars": None,
            "reason": "Paper excluded — no score computed.",
            "score_path": [],
            "disclaimer": None,
        }

    # Phase 0/I: lock score 1–2
    phase_0_1 = study_type == "phase_0_1"

    score_path = []
    score_path.append({
        "step": "Initial grade",
        "detail": f"Grade {initial_grade} from Stage 1",
        "delta": initial_grade,
    })

    running = float(initial_grade)

    # --- Stage 2 deltas ---
    s2_total = 0
    s2_details = []
    stage2_deltas = stage2_deltas or {}

    # Collect Stage 2 deductions that are in the statistical stability group
    s2_stat_stability = {}
    for key in ("n_below_domain", "nnt_exceeds"):
        val = stage2_deltas.get(key, 0)
        if val < 0:
            s2_stat_stability[key] = val

    # Non-stability Stage 2 deltas
    for key in ("effect_below_mcid", "auc_below", "lr_plus_below"):
        val = stage2_deltas.get(key, 0)
        if val != 0:
            s2_total += val
            s2_details.append(f"{key}: {val:+g}")

    # Stage 3 statistical stability dedup already handled in stage3,
    # but Stage 2's n_below_domain and nnt_exceeds overlap with it.
    # If Stage 3 already applied a dedup group delta, suppress Stage 2 overlaps.
    s3_output = stage3_output or {}
    s3_has_dedup = "deduplication" in s3_output.get("metrics", {})

    if s3_has_dedup:
        # Stage 3 already picked the most severe from {power, n_vs_domain, nnt_threshold}
        # Suppress any Stage 2 overlapping deductions
        for key, val in s2_stat_stability.items():
            s2_details.append(f"{key}: {val:+g} [SUPPRESSED — deduplicated with Stage 3]")
    else:
        # No Stage 3 dedup — apply Stage 2 stat stability deductions
        # But still deduplicate among themselves: only most severe
        if s2_stat_stability:
            most_severe_key = min(s2_stat_stability, key=s2_stat_stability.get)
            for key, val in s2_stat_stability.items():
                if key == most_severe_key:
                    s2_total += val
                    s2_details.append(f"{key}: {val:+g}")
                else:
                    s2_details.append(f"{key}: {val:+g} [SUPPRESSED — deduplicated]")

    if s2_details:
        score_path.append({
            "step": "Stage 2 deductions",
            "detail": "; ".join(s2_details),
            "delta": s2_total,
        })
        running += s2_total

    # --- Stage 3 deltas ---
    s3_total = s3_output.get("total_delta", 0)
    if not s3_output.get("skipped", False):
        s3_details = []
        metrics = s3_output.get("metrics", {})

        if "fragility_index" in metrics:
            fi_d = metrics["fragility_index"]["delta"]
            if fi_d != 0:
                s3_details.append(f"FI: {fi_d:+g}")

        if "ltfu_fi_rule" in metrics:
            ltfu_d = metrics["ltfu_fi_rule"]["delta"]
            if ltfu_d != 0:
                s3_details.append(f"LTFU>FI hard rule: {ltfu_d:+g}")

        if "fragility_quotient" in metrics:
            fq_d = metrics["fragility_quotient"]["delta"]
            if fq_d != 0:
                s3_details.append(f"FQ: {fq_d:+g}")

        if "nnt" in metrics:
            nnt_d = metrics["nnt"]["delta"]
            if nnt_d != 0:
                s3_details.append(f"NNT neutral: {nnt_d:+g}")

        # Dedup group — only non-suppressed entries
        if "deduplication" in metrics:
            for name, entry in metrics["deduplication"].items():
                if not entry.get("suppressed", False) and entry.get("delta", 0) != 0:
                    s3_details.append(f"{name}: {entry['delta']:+g}")
                elif entry.get("suppressed", False):
                    s3_details.append(f"{name}: suppressed")

        if "dor" in metrics:
            dor_d = metrics["dor"]["delta"]
            if dor_d != 0:
                s3_details.append(f"DOR: {dor_d:+g}")

        score_path.append({
            "step": "Stage 3 deductions",
            "detail": "; ".join(s3_details) if s3_details else "none",
            "delta": s3_total,
        })
        running += s3_total
    else:
        score_path.append({
            "step": "Stage 3",
            "detail": "Skipped",
            "delta": 0,
        })

    # --- Stage 4 deltas ---
    s4_result = deduplicate_stage4_deltas(
        stage4_output or {"domains": []}, study_type, stage2_output,
    )

    # Case-control dedup: if Stage 4 already covers it, remove from Stage 2
    if any("Case-control" in n for n in s4_result["dedup_notes"]):
        # Already suppressed in s4 logic — adjust s2_total if case_control was counted
        cc_delta = stage2_deltas.get("case_control_deduction_delta", 0)
        if cc_delta != 0:
            running -= cc_delta  # undo it
            score_path.append({
                "step": "De-duplication",
                "detail": "Case-control spectrum bias: Stage 2 deduction removed (counted in QUADAS-2)",
                "delta": -cc_delta,
            })

    s4_total = s4_result["total_delta"]
    s4_detail_parts = []
    if s4_result["domain_delta"] != 0:
        s4_detail_parts.append(f"domains: {s4_result['domain_delta']:+g}")
    if s4_result["surrogate_delta"] != 0:
        s4_detail_parts.append(f"surrogate: {s4_result['surrogate_delta']:+g}")
    if s4_result["heterogeneity_delta"] != 0:
        s4_detail_parts.append(f"I² heterogeneity: {s4_result['heterogeneity_delta']:+g}")
    for note in s4_result["dedup_notes"]:
        s4_detail_parts.append(note)

    score_path.append({
        "step": "Stage 4 deductions",
        "detail": "; ".join(s4_detail_parts) if s4_detail_parts else "none",
        "delta": s4_total,
    })
    running += s4_total

    # --- Boundary enforcement ---
    raw_score = running
    base, ceiling, floor = BOUNDARY_MATRIX.get(initial_grade, (initial_grade, 5, 1))

    # LTFU hard rule can pierce floor
    ltfu_triggered = False
    if not s3_output.get("skipped", False):
        metrics = s3_output.get("metrics", {})
        ltfu_triggered = metrics.get("ltfu_fi_rule", {}).get("triggered", False)

    if ltfu_triggered:
        # Floor is 1 (LTFU pierces)
        final = max(1, min(ceiling, round(running)))
    else:
        final = max(floor, min(ceiling, round(running)))

    # Phase 0/I: lock to 1–2
    if phase_0_1:
        final = max(1, min(2, final))

    boundary_detail = []
    if round(running) > ceiling:
        boundary_detail.append(f"ceiling {ceiling} applied (raw {running:.1f})")
    if not ltfu_triggered and round(running) < floor:
        boundary_detail.append(f"floor {floor} applied (raw {running:.1f})")
    if ltfu_triggered and round(running) < floor:
        boundary_detail.append(f"LTFU hard rule pierced floor {floor} (raw {running:.1f})")
    if phase_0_1:
        boundary_detail.append("Phase 0/I: score locked to 1–2")

    score_path.append({
        "step": "Boundary enforcement",
        "detail": "; ".join(boundary_detail) if boundary_detail else "none",
        "delta": final - raw_score,
    })

    label, stars = SCORE_LABELS.get(final, ("Unknown", "?"))

    return {
        "enabled": True,
        "score": final,
        "label": label,
        "stars": stars,
        "raw_score": round(running, 2),
        "score_path": score_path,
        "disclaimer": (
            "Suggested score \u2014 heuristic generated by rule engine. "
            "Design choices pending expert calibration."
        ),
    }


# ---------------------------------------------------------------------------
# Structured Report Assembly
# ---------------------------------------------------------------------------

def assemble_report(
    stage0_output,
    stage1_output,
    stage2_output=None,
    stage3_output=None,
    stage4_output=None,
    score_result=None,
    excluded=False,
    exclusion_reason=None,
):
    """Assemble the structured plain-text Evidence Evaluation Report.

    Args:
        stage0_output: dict with study_type, confidence, human_review_flag
        stage1_output: dict with extracted_variables, grading, pico, extraction_qa
        stage2_output: dict with mcid, source, tier, observed_effect, etc.
        stage3_output: dict from run_stage3()
        stage4_output: dict with domains, surrogate, heterogeneity, overall_concern
        score_result: dict from compute_suggested_score() or None
        excluded: bool
        exclusion_reason: str or None

    Returns:
        str — the full structured report as plain text
    """
    sep = "=" * 58
    lines = []

    # --- Exclusion block ---
    if excluded:
        lines.append(sep)
        lines.append("EVIDENCE EVALUATION REPORT")
        lines.append(sep)
        lines.append("")
        lines.append("*** PAPER EXCLUDED -- DATA INTEGRITY CONCERN ***")
        lines.append(f"Reason: {exclusion_reason or 'retraction'}")
        lines.append("No evidence evaluation is provided.")
        lines.append("")
        lines.append(sep)
        return "\n".join(lines)

    study_type = stage0_output.get("study_type", "unknown")
    confidence = stage0_output.get("confidence", 0)
    human_review = stage0_output.get("human_review_flag", False)

    ev = stage1_output.get("extracted_variables", {})
    grading = stage1_output.get("grading", {})
    pico = stage1_output.get("pico", {})

    # --- Header ---
    lines.append(sep)
    lines.append("EVIDENCE EVALUATION REPORT")
    lines.append(sep)
    lines.append(f"Study type: {study_type} | Routing confidence: {confidence:.0%}")

    if human_review:
        reason = stage0_output.get("human_review_reason") or stage1_output.get(
            "extraction_qa", {}
        ).get("human_review_reason", "low confidence fields")
        lines.append(f"!! HUMAN REVIEW REQUIRED: {reason}")

    if study_type == "phase_0_1":
        lines.append(
            "!! Phase 0/I Trial: report reflects methodology quality only. "
            "Stages 2+3 skipped. Score locked 1-2."
        )

    lines.append(sep)

    # --- Section 1: Study Design & Population ---
    lines.append("")
    lines.append("SECTION 1 -- STUDY DESIGN & POPULATION")
    lines.append(f"  Study type: {study_type}")
    phase = ev.get("trial_phase")
    if phase:
        lines.append(f"  Phase: {phase}")
    lines.append(
        f"  N: {ev.get('n_intervention', 'n/a')} intervention / "
        f"{ev.get('n_control', 'n/a')} control"
    )
    lines.append(f"  Blinding: {ev.get('blinding', 'n/a')}")
    lines.append(f"  Randomization: {ev.get('randomization', 'n/a')}")
    if ev.get("multicenter") is not None:
        lines.append(f"  Multicenter: {'yes' if ev['multicenter'] else 'no'}")
    lines.append(f"  PICO:")
    lines.append(f"    Population: {pico.get('population', 'n/a')}")
    lines.append(f"    Intervention: {pico.get('intervention', 'n/a')}")
    lines.append(f"    Comparator: {pico.get('comparator', 'n/a')}")
    lines.append(f"    Outcome: {pico.get('outcome', 'n/a')}")

    # --- Section 2: Statistical Robustness ---
    lines.append("")
    lines.append("SECTION 2 -- STATISTICAL ROBUSTNESS")

    s3 = stage3_output or {}
    if s3.get("skipped", False):
        lines.append(f"  *This stage was not run for {study_type} studies.*")
    else:
        metrics = s3.get("metrics", {})

        if "fragility_index" in metrics:
            fi = metrics["fragility_index"]
            lines.append(
                f"  Fragility Index (FI): {fi['fi']}  "
                f"[{fi['interpretation']}]"
            )

        if "fragility_quotient" in metrics:
            fq = metrics["fragility_quotient"]
            lines.append(
                f"  Fragility Quotient (FQ): {fq['fq']:.4f}  "
                f"[{'below 0.01 threshold' if fq['below_threshold'] else 'above threshold'}]"
            )

        if "posthoc_power" in metrics:
            pwr = metrics["posthoc_power"]
            lines.append(
                f"  Post-hoc Power: {pwr['power']:.1%}  "
                f"[{'adequate' if pwr['adequate'] else 'underpowered'}]"
            )
        elif study_type not in ("diagnostic", "phase_0_1"):
            lines.append("  Post-hoc Power: skipped (no MCID available)")

        if "ltfu_fi_rule" in metrics:
            ltfu = metrics["ltfu_fi_rule"]
            flag = "!! LTFU > FI -- HARD RULE -2" if ltfu["triggered"] else "safe"
            lines.append(
                f"  LTFU vs FI: LTFU={ltfu['ltfu']}, FI={ltfu['fi']}  [{flag}]"
            )

        if "nnt" in metrics:
            nnt = metrics["nnt"]
            nnt_str = f"{nnt['nnt']}" if nnt["nnt"] != float("inf") else "infinite"
            lines.append(f"  NNT: {nnt_str}  ({nnt['direction']})")
            if "nnt_threshold" in metrics:
                thr = metrics["nnt_threshold"]
                flag = "exceeds threshold" if thr["exceeds_threshold"] else "favorable"
                lines.append(
                    f"    Domain threshold: {thr['domain_threshold']}  [{flag}]"
                )

        if "dor" in metrics:
            dor = metrics["dor"]
            lines.append(
                f"  DOR: {dor['dor']}  [{dor['interpretation']}]  "
                f"(95% CI [{dor['ci_lower']}, {dor['ci_upper']}])"
            )

    # --- Section 3: Clinical Benchmarking ---
    lines.append("")
    lines.append("SECTION 3 -- CLINICAL BENCHMARKING")

    s2 = stage2_output or {}
    if study_type == "phase_0_1":
        lines.append(f"  *This stage was not run for {study_type} studies.*")
    elif not s2:
        lines.append("  No Stage 2 data available.")
    else:
        mcid = s2.get("mcid")
        mcid_unit = s2.get("mcid_unit", "")
        source = s2.get("source", "n/a")
        tier = s2.get("mcid_source_tier")
        lines.append(f"  MCID: {mcid} {mcid_unit}")
        lines.append(f"  Source: {source} (Tier {tier})")
        if tier == 4:
            lines.append(
                "  !! No specialty MCID found -- Cohen's d proxy used. "
                "Interpret with caution."
            )
        effect_vs = s2.get("effect_vs_mcid", "n/a")
        observed = s2.get("observed_effect", "n/a")
        lines.append(f"  Observed effect: {observed}  vs. MCID: {effect_vs}")

    # --- Section 4: Bias Risk Assessment ---
    lines.append("")
    lines.append("SECTION 4 -- BIAS RISK ASSESSMENT")

    s4 = stage4_output or {}
    if not s4:
        lines.append("  No Stage 4 data available.")
    else:
        tool = s4.get("tool", "n/a")
        lines.append(f"  Tool: {tool}")
        for domain in s4.get("domains", []):
            d_name = domain.get("domain", "?")
            d_judgment = domain.get("judgment", "?")
            d_delta = domain.get("delta", 0)
            delta_str = f"  ({d_delta:+g})" if d_delta != 0 else ""
            lines.append(f"    {d_name}: {d_judgment}{delta_str}")

        surr = s4.get("surrogate_endpoint")
        if surr is not None:
            lines.append(f"  Surrogate endpoint: {'yes' if surr else 'no'}")
        i2 = s4.get("heterogeneity_i2")
        if i2 is not None:
            lines.append(f"  Meta-analysis I²: {i2}%")
        overall = s4.get("overall_concern", "n/a")
        lines.append(f"  Overall concern: {overall}")

    # --- Optional Score ---
    if score_result and score_result.get("enabled"):
        lines.append("")
        lines.append(sep)
        lines.append(
            f"SUGGESTED SCORE: {score_result['score']} "
            f"{score_result['stars']}  \"{score_result['label']}\""
        )
        lines.append(f"  {score_result['disclaimer']}")
        lines.append("")
        lines.append("  Score path:")
        for step in score_result.get("score_path", []):
            delta_str = (
                f"{step['delta']:+g}" if isinstance(step["delta"], (int, float))
                and step["step"] != "Initial grade"
                else str(step["delta"])
            )
            lines.append(f"    {step['step']}: {step['detail']} [{delta_str}]")

    lines.append("")
    lines.append(sep)
    return "\n".join(lines)
