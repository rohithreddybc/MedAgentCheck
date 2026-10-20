"""Agent-module prevalence without A11 (co-author review 4, finding 1).

A11 ("Environment-state provenance") was credited on dataset origin or licence in the known-groups check (Note 12),
so it does not isolate environment-state provenance. This script recomputes the agent-module shares on A1-A10 for
the current resolved rule and the union rule (the two ends of the reported range). Nothing is rescored; it reuses
revision_rq12.audit_levels and rq1_rq2.module_summary (2,000 benchmark bootstrap resamples, seed 20261004).

Run from the project root:  python analysis/agent_without_a11.py
From the public release:     python analysis/agent_without_a11.py --run results
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT  # noqa: E402

import revision_rq12 as V  # noqa: E402
import rq1_rq2 as R  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Agent-module prevalence without A11.")
    ap.add_argument("--run", type=Path, default=V.AUDIT, help="directory holding resolved/ (default: audit/)")
    resolved = R.load_resolved(ap.parse_args().run)
    resolved = {b: c for b, c in resolved.items() if c}  # HealthCraft has no cells (coder failure)
    assert len(resolved) == 44, len(resolved)
    levels = V.audit_levels(resolved)
    out = {}
    for rule in ("current", "union"):
        d = V.as_resolved(levels[rule])
        d = {b: {it: c for it, c in cells.items() if it != "A11"} for b, cells in d.items()}
        rows = {r["module"]: r for r in R.module_summary(d, "final", R.N_BOOT)}
        out[rule] = rows["agent"]
    # Same summary on the benchmarks that remain after excluding the rule-affected ones (the 30 of
    # paper/tables/rq1_modules_ruleexcl.tex; same exclusion as rq1_rq2.py --exclude-rule-affected).
    # Release note: the exclusion needs research/eligibility/overrides_final.csv (the first-pass versus final eligibility
    # decisions), which is not redistributed; frozen_list_v1.csv alone gives 37 benchmarks, not 30. Without it the key
    # is skipped (and the output then lacks "rule_excluded"); the released JSON has it from the authors' run.
    if not R.OVERRIDES.exists():
        print(f"SKIPPED rule_excluded: {R.OVERRIDES} is not in this checkout (not redistributed); "
              "the output lacks that key, every other value is unchanged.")
    else:
        hit, _ = R.rule_affected_benches(sorted(resolved))
        keep = sorted(b for b in resolved if b not in hit)
        assert len(keep) == 30, len(keep)
        rx = {"excluded_benchmarks": sorted(hit), "n_benchmarks_kept": len(keep)}
        for rule in ("current", "union"):
            d = V.as_resolved(levels[rule])
            d = {b: {it: c for it, c in d[b].items() if it != "A11"} for b in keep}
            rows = {r["module"]: r for r in R.module_summary(d, "final", R.N_BOOT)}
            rx[rule] = rows["agent"]
        out["rule_excluded"] = rx
    (OUT / "agent_without_a11.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for rule, r in out.items():
        if rule == "rule_excluded":
            for rr in ("current", "union"):
                x = r[rr]
                print("rule_excluded", rr, x["n_benchmarks"], x["n_applicable_cells"], round(x["share_reported"], 4),
                      x["reported_boot_lo"], x["reported_boot_hi"], round(x["share_full"], 4), x["full_boot_lo"],
                      x["full_boot_hi"], round(x["mean_bench_fraction_of_max"], 3))
            continue
        print(rule, r["n_applicable_cells"], round(r["share_reported"], 4), r["reported_boot_lo"], r["reported_boot_hi"],
              round(r["share_full"], 4), r["full_boot_lo"], r["full_boot_hi"], round(r["mean_bench_fraction_of_max"], 3))


if __name__ == "__main__":
    main()
