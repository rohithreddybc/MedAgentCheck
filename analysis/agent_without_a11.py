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
    (OUT / "agent_without_a11.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    for rule, r in out.items():
        print(rule, r["n_applicable_cells"], round(r["share_reported"], 4), r["reported_boot_lo"], r["reported_boot_hi"],
              round(r["share_full"], 4), r["full_boot_lo"], r["full_boot_hi"], round(r["mean_bench_fraction_of_max"], 3))


if __name__ == "__main__":
    main()
