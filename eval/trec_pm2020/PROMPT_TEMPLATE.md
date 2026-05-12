You are running the Evidence Evaluator skill. The skill lives at `skills/evidence-evaluator/`
relative to the repo root (your current working directory).

## Inputs

- Paper to evaluate: PubMed PMID `{pmid}`
- Cached abstract XML: `data/trec_pm2020/abstracts_cache/{pmid}.xml`
- Output directory for the Markdown report: `{reports_dir}`
- Output directory for the JSON dump: `{json_dir}`

## Required workflow

1. Read `skills/evidence-evaluator/SKILL.md` in full. Follow its execution order strictly.
2. Read the cached abstract at `data/trec_pm2020/abstracts_cache/{pmid}.xml`. Treat this as
   Tier 1 input (abstract + structured abstract sections only). **Do NOT attempt to fetch
   full text under any circumstance**, even if you would normally signal `needs_full_paper`.
   If the abstract lacks fields you need for any stage, document the gap in the report and
   continue with whatever the available fields support.
3. Execute Stages 0 → 1 → 2 → 3 → 4 → 5 per `SKILL.md`. Use the Python modules
   `pipeline/stage3_math.py` and `pipeline/stage5_report.py` for the deterministic stages
   exactly as the pilot reports did. Run them via `cd skills/evidence-evaluator/ && python3 -c "..."`.
4. Save the full Markdown report to `{reports_dir}/evidence_report_{pmid}.md`.

## Final message (REQUIRED)

After saving the Markdown, emit ONE final assistant message containing ONLY a fenced
```json block with this exact schema. No prose, no explanation, no extra text outside
the fence.

```json
{{
  "pmid": "{pmid}",
  "status": "ok",
  "stage0": {{"study_type": "...", "confidence": 0.0, "skipped_stages": []}},
  "stage1": {{
    "initial_grade": null,
    "n_intervention": null, "n_control": null,
    "events_intervention": null, "events_control": null,
    "p_value": null, "ltfu_count": null, "alpha": 0.05,
    "effect_size_type": "...", "blinding": null, "randomization": null,
    "trial_phase": null, "primary_outcome": null,
    "pico": {{"P": "...", "I": "...", "C": "...", "O": "..."}},
    "low_confidence_fields": []
  }},
  "stage2": {{
    "mcid": null, "mcid_unit": null, "mcid_source": null, "mcid_tier": null,
    "effect_vs_mcid": null, "domain_n": null, "n_vs_domain": null,
    "domain_nnt_threshold": null, "nnt_vs_threshold": null
  }},
  "stage3": {{
    "fragility_index": null, "fragility_quotient": null,
    "ltfu_exceeds_fi": null, "nnt": null, "post_hoc_power": null,
    "dor": null, "deltas": {{}}
  }},
  "stage4": {{
    "tool": null, "overall_concern": null, "domains": [],
    "surrogate_endpoint_delta": 0, "heterogeneity_delta": 0
  }},
  "stage5": {{
    "suggested_score": null, "score_path": [], "deduplications_applied": []
  }}
}}
```

Use `null` for any field that did not apply or could not be extracted. Set `status` to
one of: `ok`, `partial_insufficient_data`, `partial_off_distribution`, or `max_turns`.
For partial statuses, additionally include `"error_msg": "<one-line summary>"`.
