"""
Stage 3: Deterministic Mathematical Audit

Pure Python — no LLM calls. Given the same inputs, produces the same outputs always.

Computes: Fragility Index (FI), LTFU-FI attrition rule, Fragility Quotient (FQ),
NNT/NNH, post-hoc power, and DOR (diagnostic only).

Skip entirely if study_type == "phase_0_1".
Diagnostic studies: compute DOR only (skip FI/NNT/power).
Observational studies: compute FI, FQ, NNT; skip post-hoc power.
"""

import math
import numpy as np
from scipy.stats import fisher_exact
from statsmodels.stats.proportion import proportion_effectsize
from statsmodels.stats.power import NormalIndPower, TTestIndPower

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FI_EXTREME_THRESHOLD = 2       # FI <= 2 → extreme fragility
FI_ROBUST_THRESHOLD = 10       # FI > 10 → robust
FQ_THRESHOLD = 0.01            # FQ < 0.01 → −0.5
POWER_THRESHOLD = 0.80         # power < 0.80 → −1
DOR_POOR_THRESHOLD = 5         # DOR < 5 → −1
DOR_HIGH_THRESHOLD = 20        # DOR > 20 → +0.5
FI_SAFETY_CAP = 500            # max iterations for FI computation


# ---------------------------------------------------------------------------
# Core computations
# ---------------------------------------------------------------------------

def compute_fragility_index(ei, ni, ec, nc, initial_p):
    """Iteratively increment events_intervention until Fisher P >= 0.05.

    Returns:
        dict with keys: fi, iteration_log, final_p, interpretation, delta, reasoning
    """
    if initial_p >= 0.05:
        return {
            "fi": 0,
            "iteration_log": [],
            "final_p": initial_p,
            "interpretation": "not_computable",
            "delta": 0,
            "reasoning": "Result not statistically significant; FI not computable.",
        }

    fi = 0
    curr_ei = ei
    iteration_log = []

    while fi < FI_SAFETY_CAP:
        curr_ei += 1
        fi += 1
        table = [[curr_ei, ni - curr_ei], [ec, nc - ec]]
        _, p = fisher_exact(table)
        iteration_log.append({"flip": fi, "events_i": curr_ei, "fisher_p": round(p, 6)})
        if p >= 0.05:
            break

    if fi <= FI_EXTREME_THRESHOLD:
        interpretation = "extreme_fragile"
        delta = -1
        reasoning = (
            f"FI = {fi} (≤ {FI_EXTREME_THRESHOLD}): "
            f"{'One outcome event change' if fi == 1 else f'{fi} outcome event changes'} "
            "would render the result non-significant."
        )
    elif fi > FI_ROBUST_THRESHOLD:
        interpretation = "robust"
        delta = 0.5
        reasoning = (
            f"FI = {fi} (> {FI_ROBUST_THRESHOLD}): "
            "Result is robust to multiple outcome changes."
        )
    else:
        interpretation = "moderate"
        delta = 0
        reasoning = (
            f"FI = {fi} (3–10 range): "
            "Moderate fragility — neither extreme nor robust."
        )

    return {
        "fi": fi,
        "iteration_log": iteration_log,
        "final_p": round(iteration_log[-1]["fisher_p"], 6),
        "interpretation": interpretation,
        "delta": delta,
        "reasoning": reasoning,
    }


def compute_ltfu_fi_rule(ltfu_count, fi):
    """LTFU-FI attrition rule: if LTFU > FI → −2 (hard rule, never deduplicated).

    Returns:
        dict with keys: triggered, ltfu, fi, delta, reasoning
    """
    triggered = ltfu_count > fi
    return {
        "triggered": triggered,
        "ltfu": ltfu_count,
        "fi": fi,
        "delta": -2 if triggered else 0,
        "reasoning": (
            f"LTFU ({ltfu_count}) > FI ({fi}): more patients dropped out than it takes "
            "to flip the result. Hard −2 applied."
            if triggered
            else f"LTFU ({ltfu_count}) ≤ FI ({fi}): attrition does not threaten significance."
        ),
    }


def compute_fragility_quotient(fi, n_total):
    """FQ = FI / N_total. FQ < 0.01 → −0.5.

    Returns:
        dict with keys: fq, n_total, below_threshold, delta, reasoning
    """
    fq = fi / n_total if n_total > 0 else 0.0
    below = fq < FQ_THRESHOLD
    return {
        "fq": round(fq, 6),
        "n_total": n_total,
        "below_threshold": below,
        "delta": -0.5 if below else 0,
        "reasoning": (
            f"FQ = {fi}/{n_total} = {fq:.4f} (< {FQ_THRESHOLD}): "
            "low FI relative to sample size."
            if below
            else f"FQ = {fi}/{n_total} = {fq:.4f} (≥ {FQ_THRESHOLD}): acceptable."
        ),
    }


def compute_nnt(ei, ni, ec, nc):
    """NNT/NNH from absolute risk reduction.

    Returns:
        dict with keys: cer, ier, arr, nnt, direction, delta, reasoning
    """
    cer = ec / nc
    ier = ei / ni
    arr = cer - ier

    if arr == 0:
        return {
            "cer": round(cer, 6),
            "ier": round(ier, 6),
            "arr": 0.0,
            "nnt": float("inf"),
            "direction": "neutral",
            "delta": -1,
            "reasoning": "ARR = 0: no difference between arms. NNT = ∞.",
        }

    nnt_val = 1.0 / abs(arr)
    direction = "benefit" if arr > 0 else "harm"

    if direction == "harm":
        delta = 0  # NNH is informational only
        reasoning = (
            f"NNH = {nnt_val:.1f}: intervention arm had higher event rate. "
            "Informational — no automatic deduction for harm direction."
        )
    else:
        delta = 0  # deduction depends on domain threshold, applied externally
        reasoning = f"NNT = {nnt_val:.1f}: {nnt_val:.1f} patients treated per additional benefit."

    return {
        "cer": round(cer, 6),
        "ier": round(ier, 6),
        "arr": round(arr, 6),
        "nnt": round(nnt_val, 2),
        "direction": direction,
        "delta": delta,
        "reasoning": reasoning,
    }


def compute_nnt_threshold_delta(nnt_val, domain_threshold):
    """Check NNT against domain threshold. Returns delta and reasoning."""
    if nnt_val == float("inf") or nnt_val > domain_threshold:
        return {
            "exceeds_threshold": True,
            "nnt": nnt_val,
            "domain_threshold": domain_threshold,
            "delta": -1,
            "reasoning": (
                f"NNT ({nnt_val}) exceeds domain threshold ({domain_threshold}): "
                "benefit rate too low for clinical justification."
            ),
        }
    return {
        "exceeds_threshold": False,
        "nnt": nnt_val,
        "domain_threshold": domain_threshold,
        "delta": 0,
        "reasoning": (
            f"NNT ({nnt_val}) ≤ domain threshold ({domain_threshold}): acceptable."
        ),
    }


def compute_posthoc_power_binary(p_intervention_at_mcid, p_control, n_intervention,
                                  n_control, alpha=0.05):
    """Post-hoc power for binary outcomes using proportion effect size (Cohen's h).

    Returns:
        dict with keys: effect_size_h, power, adequate, delta, reasoning
    """
    h = proportion_effectsize(p_intervention_at_mcid, p_control)
    ratio = n_control / n_intervention if n_intervention > 0 else 1.0
    power = NormalIndPower().solve_power(
        effect_size=abs(h), nobs1=n_intervention, ratio=ratio, alpha=alpha,
    )
    adequate = power >= POWER_THRESHOLD
    return {
        "effect_size_h": round(abs(h), 4),
        "power": round(power, 4),
        "adequate": adequate,
        "delta": 0 if adequate else -1,
        "reasoning": (
            f"Post-hoc power = {power:.2%} (≥ 80%): study adequately powered at MCID."
            if adequate
            else f"Post-hoc power = {power:.2%} (< 80%): underpowered to detect MCID."
        ),
    }


def compute_posthoc_power_continuous(smd, n_intervention, n_control, alpha=0.05):
    """Post-hoc power for continuous outcomes using SMD (Cohen's d).

    Returns:
        dict with keys: effect_size_smd, power, adequate, delta, reasoning
    """
    ratio = n_control / n_intervention if n_intervention > 0 else 1.0
    power = TTestIndPower().solve_power(
        effect_size=abs(smd), nobs1=n_intervention, ratio=ratio, alpha=alpha,
    )
    adequate = power >= POWER_THRESHOLD
    return {
        "effect_size_smd": round(abs(smd), 4),
        "power": round(power, 4),
        "adequate": adequate,
        "delta": 0 if adequate else -1,
        "reasoning": (
            f"Post-hoc power = {power:.2%} (≥ 80%): study adequately powered at MCID."
            if adequate
            else f"Post-hoc power = {power:.2%} (< 80%): underpowered to detect MCID."
        ),
    }


def compute_dor(tp, tn, fp, fn):
    """Diagnostic Odds Ratio with 95% CI.

    Returns:
        dict with keys: dor, lr_plus, lr_minus, ci_lower, ci_upper,
                        interpretation, delta, reasoning
    """
    sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0

    lr_plus = sensitivity / (1 - specificity) if specificity < 1.0 else float("inf")
    lr_minus = (1 - sensitivity) / specificity if specificity > 0 else float("inf")

    if fp * fn == 0:
        dor = float("inf")
        ci_lower = float("inf")
        ci_upper = float("inf")
    else:
        dor = (tp * tn) / (fp * fn)
        log_dor = math.log(dor)
        se = math.sqrt(1/tp + 1/fp + 1/tn + 1/fn)
        ci_lower = math.exp(log_dor - 1.96 * se)
        ci_upper = math.exp(log_dor + 1.96 * se)

    ci_crosses_1 = ci_lower <= 1.0 if dor != float("inf") else False

    if ci_crosses_1:
        interpretation = "unstable"
        delta = -1
        reasoning = f"DOR = {dor:.2f}, 95% CI [{ci_lower:.2f}, {ci_upper:.2f}] crosses 1: result unstable."
    elif dor < DOR_POOR_THRESHOLD:
        interpretation = "poor"
        delta = -1
        reasoning = f"DOR = {dor:.2f} (< {DOR_POOR_THRESHOLD}): poor discrimination."
    elif dor > DOR_HIGH_THRESHOLD:
        interpretation = "high"
        delta = 0.5
        reasoning = f"DOR = {dor:.2f} (> {DOR_HIGH_THRESHOLD}): high discrimination."
    else:
        interpretation = "adequate"
        delta = 0
        reasoning = f"DOR = {dor:.2f}: adequate discrimination."

    return {
        "dor": round(dor, 2),
        "sensitivity": round(sensitivity, 4),
        "specificity": round(specificity, 4),
        "lr_plus": round(lr_plus, 4),
        "lr_minus": round(lr_minus, 4),
        "ci_lower": round(ci_lower, 2),
        "ci_upper": round(ci_upper, 2),
        "ci_crosses_1": ci_crosses_1,
        "interpretation": interpretation,
        "delta": delta,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# De-duplication logic (statistical stability dimension)
# ---------------------------------------------------------------------------

def deduplicate_statistical_stability(power_result=None, n_vs_domain=None,
                                       nnt_threshold_result=None):
    """Among {power < 0.80, N < domain_N, NNT > threshold}, apply only the most severe.

    Each argument is a dict with a "delta" key, or None if not applicable.
    Returns the list of results with 'suppressed' flags set.
    """
    candidates = []
    if power_result and power_result.get("delta", 0) < 0:
        candidates.append(("power", power_result))
    if n_vs_domain and n_vs_domain.get("delta", 0) < 0:
        candidates.append(("n_vs_domain", n_vs_domain))
    if nnt_threshold_result and nnt_threshold_result.get("delta", 0) < 0:
        candidates.append(("nnt_threshold", nnt_threshold_result))

    if len(candidates) <= 1:
        return {name: {**result, "suppressed": False} for name, result in candidates}

    # Most severe = most negative delta (all are −1 in current spec, so pick first)
    most_severe = min(candidates, key=lambda c: c[1]["delta"])
    output = {}
    for name, result in candidates:
        suppressed = name != most_severe[0]
        output[name] = {**result, "suppressed": suppressed}
        if suppressed:
            output[name]["delta"] = 0
            output[name]["reasoning"] += " [SUPPRESSED — deduplicated with more severe finding]"
    return output


# ---------------------------------------------------------------------------
# Top-level audit runner
# ---------------------------------------------------------------------------

def run_stage3(stage1_output, stage2_output=None, study_type="RCT_intervention"):
    """Run the full Stage 3 math audit.

    Args:
        stage1_output: dict with keys from Stage 1 extraction (n_i, n_c, e_i, e_c,
                       ltfu_count, p_value, alpha, etc.). For diagnostic studies,
                       must include tp, tn, fp, fn.
        stage2_output: dict from Stage 2 with mcid, domain_n, domain_nnt_threshold, etc.
                       None if Stage 2 was skipped.
        study_type: one of RCT_intervention, diagnostic, preventive, observational,
                    meta_analysis, phase_0_1.

    Returns:
        dict with all computation results, deltas, and trace information.
    """
    if study_type == "phase_0_1":
        return {
            "skipped": True,
            "reason": "Stage 3 skipped for phase_0_1 studies.",
            "metrics": {},
            "total_delta": 0,
        }

    metrics = {}
    stage2_output = stage2_output or {}
    alpha = stage1_output.get("alpha", 0.05)

    # --- Diagnostic path: DOR only ---
    if study_type == "diagnostic":
        tp = stage1_output["tp"]
        tn = stage1_output["tn"]
        fp = stage1_output["fp"]
        fn = stage1_output["fn"]
        initial_grade = stage1_output.get("initial_grade")

        dor_result = compute_dor(tp, tn, fp, fn)
        # DOR > 20 bonus only applies at Grade 3/4
        if dor_result["delta"] == 0.5 and initial_grade not in (3, 4):
            dor_result["delta"] = 0
            dor_result["reasoning"] += f" (bonus limited to Grade 3/4; current grade = {initial_grade})"

        metrics["dor"] = dor_result
        return {
            "skipped": False,
            "study_type": study_type,
            "metrics": metrics,
            "total_delta": dor_result["delta"],
        }

    # --- Standard path: FI, LTFU, FQ, NNT, Power ---
    ei = stage1_output["events_intervention"]
    ni = stage1_output["n_intervention"]
    ec = stage1_output["events_control"]
    nc = stage1_output["n_control"]
    p_value = stage1_output["p_value"]
    ltfu = stage1_output.get("ltfu_count", 0)

    # Fragility Index
    fi_result = compute_fragility_index(ei, ni, ec, nc, p_value)
    metrics["fragility_index"] = fi_result

    # LTFU-FI Rule
    ltfu_result = compute_ltfu_fi_rule(ltfu, fi_result["fi"])
    metrics["ltfu_fi_rule"] = ltfu_result

    # Fragility Quotient
    n_total = ni + nc
    fq_result = compute_fragility_quotient(fi_result["fi"], n_total)
    metrics["fragility_quotient"] = fq_result

    # NNT
    nnt_result = compute_nnt(ei, ni, ec, nc)
    metrics["nnt"] = nnt_result

    # NNT vs domain threshold (if available from Stage 2)
    nnt_threshold_result = None
    domain_threshold = stage2_output.get("domain_nnt_threshold")
    if domain_threshold is not None and nnt_result["direction"] == "benefit":
        nnt_threshold_result = compute_nnt_threshold_delta(
            nnt_result["nnt"], domain_threshold,
        )
        metrics["nnt_threshold"] = nnt_threshold_result

    # Post-hoc power (skip for observational)
    power_result = None
    if study_type != "observational":
        mcid = stage2_output.get("mcid")
        effect_type = stage1_output.get("effect_size_type", "binary")
        if mcid is not None:
            if effect_type in ("RR", "OR", "binary"):
                # Derive p_intervention_at_mcid from control rate and MCID as ARR
                p_control = ec / nc
                p_intervention_at_mcid = p_control - mcid
                if 0 < p_intervention_at_mcid < 1:
                    power_result = compute_posthoc_power_binary(
                        p_intervention_at_mcid, p_control, ni, nc, alpha,
                    )
                    metrics["posthoc_power"] = power_result
            elif effect_type in ("SMD", "MD", "continuous"):
                power_result = compute_posthoc_power_continuous(
                    mcid, ni, nc, alpha,
                )
                metrics["posthoc_power"] = power_result

    # N vs domain standard (from Stage 2)
    n_vs_domain = None
    domain_n = stage2_output.get("domain_n")
    if domain_n is not None and n_total < domain_n:
        n_vs_domain = {
            "n_total": n_total,
            "domain_n": domain_n,
            "delta": -1,
            "reasoning": f"N ({n_total}) < domain standard ({domain_n}): underpowered relative to field norms.",
        }
        metrics["n_vs_domain"] = n_vs_domain

    # De-duplication of statistical stability dimension
    dedup = deduplicate_statistical_stability(power_result, n_vs_domain, nnt_threshold_result)
    if dedup:
        metrics["deduplication"] = dedup

    # --- Total delta ---
    # LTFU hard rule is never deduplicated — always add it
    total_delta = ltfu_result["delta"]
    # FI delta
    total_delta += fi_result["delta"]
    # FQ delta
    total_delta += fq_result["delta"]
    # From dedup group: only non-suppressed deltas
    if dedup:
        for entry in dedup.values():
            if not entry.get("suppressed", False):
                total_delta += entry["delta"]
    else:
        # No dedup needed — add individual deltas
        if nnt_threshold_result:
            total_delta += nnt_threshold_result["delta"]
        if power_result:
            total_delta += power_result["delta"]
        if n_vs_domain:
            total_delta += n_vs_domain["delta"]

    # NNT neutral case (arr=0 → −1) is in nnt_result, not in dedup group
    total_delta += nnt_result["delta"]

    return {
        "skipped": False,
        "study_type": study_type,
        "metrics": metrics,
        "total_delta": total_delta,
    }
