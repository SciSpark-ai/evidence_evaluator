"""
Tests for pipeline/stage3_math.py

Validates all Stage 3 computations against the same synthetic data
used in acceptance_tests_T1_T8.py and experiment_3B_math_unit_tests.py.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pipeline.stage3_math import (
    compute_fragility_index,
    compute_ltfu_fi_rule,
    compute_fragility_quotient,
    compute_nnt,
    compute_nnt_threshold_delta,
    compute_posthoc_power_binary,
    compute_dor,
    deduplicate_statistical_stability,
    run_stage3,
)

PASS = 0
FAIL = 0

def check(name, got, expected, tol=0.001):
    global PASS, FAIL
    if isinstance(expected, float):
        ok = abs(got - expected) <= tol
    elif isinstance(expected, bool):
        ok = bool(got) == expected
    else:
        ok = got == expected
    status = "✅" if ok else "❌"
    if not ok:
        FAIL += 1
    else:
        PASS += 1
    print(f"  {status} {name}: got={got}, expected={expected}")


print("=" * 60)
print("STAGE 3 MODULE TESTS")
print("=" * 60)

# ── Fragility Index ──────────────────────────────────────────
print("\n[Fragility Index]")
r = compute_fragility_index(47, 500, 60, 500, 0.038)
check("FI_fragile_1", r["fi"], 1)
check("FI_fragile_interp", r["interpretation"], "extreme_fragile")
check("FI_fragile_delta", r["delta"], -1)

r = compute_fragility_index(48, 512, 89, 508, 0.0001)
check("FI_robust_19", r["fi"], 19)
check("FI_robust_interp", r["interpretation"], "robust")
check("FI_robust_delta", r["delta"], 0.5)

r = compute_fragility_index(55, 500, 60, 500, 0.41)
check("FI_nonsig", r["fi"], 0)
check("FI_nonsig_interp", r["interpretation"], "not_computable")
check("FI_nonsig_delta", r["delta"], 0)

# ── LTFU-FI Rule ─────────────────────────────────────────────
print("\n[LTFU-FI Rule]")
r = compute_ltfu_fi_rule(8, 1)
check("LTFU_triggers", r["triggered"], True)
check("LTFU_triggers_delta", r["delta"], -2)

r = compute_ltfu_fi_rule(5, 19)
check("LTFU_safe", r["triggered"], False)
check("LTFU_safe_delta", r["delta"], 0)

r = compute_ltfu_fi_rule(19, 19)
check("LTFU_boundary_eq", r["triggered"], False)

r = compute_ltfu_fi_rule(20, 19)
check("LTFU_pierces", r["triggered"], True)

# ── Fragility Quotient ───────────────────────────────────────
print("\n[Fragility Quotient]")
r = compute_fragility_quotient(1, 1000)
check("FQ_below_threshold", r["below_threshold"], True)
check("FQ_below_delta", r["delta"], -0.5)

r = compute_fragility_quotient(19, 1020)
check("FQ_above_threshold", r["below_threshold"], False)
check("FQ_above_delta", r["delta"], 0)
check("FQ_value", r["fq"], round(19 / 1020, 6), tol=0.0001)

# ── NNT ──────────────────────────────────────────────────────
print("\n[NNT / NNH]")
r = compute_nnt(48, 512, 89, 508)
check("NNT_benefit_dir", r["direction"], "benefit")
check("NNT_value", r["nnt"], 12.3, tol=0.3)

r = compute_nnt(70, 500, 50, 500)
check("NNH_harm_dir", r["direction"], "harm")
check("NNH_value", r["nnt"], 25.0, tol=0.5)

r = compute_nnt(50, 500, 50, 500)
check("NNT_neutral_dir", r["direction"], "neutral")
check("NNT_neutral_delta", r["delta"], -1)

# ── NNT Threshold ────────────────────────────────────────────
print("\n[NNT Threshold]")
r = compute_nnt_threshold_delta(150, 50)
check("NNT_exceeds", r["exceeds_threshold"], True)
check("NNT_exceeds_delta", r["delta"], -1)

r = compute_nnt_threshold_delta(12.3, 50)
check("NNT_within", r["exceeds_threshold"], False)
check("NNT_within_delta", r["delta"], 0)

# ── DOR ──────────────────────────────────────────────────────
print("\n[DOR]")
r = compute_dor(80, 70, 20, 30)
check("DOR_T4_value", r["dor"], 9.33, tol=0.05)
check("DOR_T4_interp", r["interpretation"], "adequate")

r = compute_dor(90, 85, 10, 15)
check("DOR_excellent", r["dor"] > 20, True)
check("DOR_excellent_interp", r["interpretation"], "high")
check("DOR_excellent_delta", r["delta"], 0.5)

r = compute_dor(60, 50, 40, 50)
check("DOR_poor_value", r["dor"] < 5, True)
# DOR=1.5, CI crosses 1 → "unstable" takes precedence over "poor"
check("DOR_poor_interp", r["interpretation"], "unstable")
check("DOR_poor_delta", r["delta"], -1)

# ── Post-hoc Power ───────────────────────────────────────────
print("\n[Post-hoc Power]")
p_control = 0.17
p_mcid = 0.17 - 0.08
r = compute_posthoc_power_binary(p_mcid, p_control, 512, 508)
check("Power_adequate", r["adequate"], True)
check("Power_adequate_val", r["power"] >= 0.80, True)

r = compute_posthoc_power_binary(p_mcid, p_control, 50, 50)
check("Power_inadequate", r["adequate"], False)

# ── De-duplication ───────────────────────────────────────────
print("\n[De-duplication]")
power_r = {"delta": -1, "reasoning": "underpowered"}
nnt_r = {"delta": -1, "reasoning": "NNT exceeds threshold"}
n_r = {"delta": -1, "reasoning": "N < domain"}
dedup = deduplicate_statistical_stability(power_r, n_r, nnt_r)
active_count = sum(1 for v in dedup.values() if not v["suppressed"])
check("Dedup_only_one_active", active_count, 1)
suppressed_count = sum(1 for v in dedup.values() if v["suppressed"])
check("Dedup_two_suppressed", suppressed_count, 2)

# ── run_stage3: phase_0_1 skip ───────────────────────────────
print("\n[run_stage3: phase_0_1]")
r = run_stage3({}, study_type="phase_0_1")
check("Phase01_skipped", r["skipped"], True)
check("Phase01_delta", r["total_delta"], 0)

# ── run_stage3: T1 scenario (Grade 5 RCT, FI=19, low bias) ──
print("\n[run_stage3: T1 — robust RCT]")
r = run_stage3(
    {
        "events_intervention": 48, "n_intervention": 512,
        "events_control": 89, "n_control": 508,
        "p_value": 0.0001, "ltfu_count": 12, "alpha": 0.05,
    },
    study_type="RCT_intervention",
)
check("T1_fi", r["metrics"]["fragility_index"]["fi"], 19)
check("T1_fi_delta", r["metrics"]["fragility_index"]["delta"], 0.5)
check("T1_ltfu_safe", r["metrics"]["ltfu_fi_rule"]["triggered"], False)

# ── run_stage3: T2 scenario (LTFU > FI) ─────────────────────
print("\n[run_stage3: T2 — LTFU > FI]")
r = run_stage3(
    {
        "events_intervention": 47, "n_intervention": 500,
        "events_control": 60, "n_control": 500,
        "p_value": 0.038, "ltfu_count": 8, "alpha": 0.05,
    },
    study_type="RCT_intervention",
)
check("T2_fi", r["metrics"]["fragility_index"]["fi"], 1)
check("T2_ltfu_triggered", r["metrics"]["ltfu_fi_rule"]["triggered"], True)
check("T2_ltfu_delta", r["metrics"]["ltfu_fi_rule"]["delta"], -2)

# ── run_stage3: T4 diagnostic ───────────────────────────────
print("\n[run_stage3: T4 — diagnostic]")
r = run_stage3(
    {"tp": 80, "tn": 70, "fp": 20, "fn": 30},
    study_type="diagnostic",
)
check("T4_dor", r["metrics"]["dor"]["dor"], 9.33, tol=0.05)
check("T4_no_fi", "fragility_index" not in r["metrics"], True)

# ── Summary ──────────────────────────────────────────────────
print("\n" + "=" * 60)
print(f"RESULTS: {PASS} passed, {FAIL} failed out of {PASS + FAIL} tests")
print("=" * 60)
if FAIL > 0:
    sys.exit(1)
