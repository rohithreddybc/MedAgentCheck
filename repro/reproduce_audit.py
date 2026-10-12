"""Reproduce the audit-population results (RQ1 prevalence and bounds, RQ2 cross-family alpha) from results/resolved/.

Port of analysis/postfreeze/rq1_rq2.py (prevalence, module_summary, resolution_summary, contradictions, alpha_table) and of
the union-rule bounds of analysis/revision_rq12.py (bounds_block). The authors' scripts read audit/resolved, audit/coding
and audit/verified of the working tree; this one reads results/resolved/<bench>.json only, which holds the same
information per cell (resolved level, status, both coders' raw and effective scores, contradiction flags, family).
Statistics come from the frozen agentaudit/stats.py (alpha_ordinal, bootstrap_ci, wilson), read from this checkout.

Reproduced and compared with the released analysis outputs (results/analysis_out/, written by the authors' scripts):
  rq1_prevalence.csv  rq1_modules.csv  rq1_resolution.csv  rq1_contradictions.csv  rq1_contradictions_by_bench.csv
  rq2_alpha.csv       (cross-family ordinal Krippendorff alpha, bootstrap CI over benchmarks, 2,000 resamples, seed 20261004)
  rev_bounds_items.csv  rev_bounds_modules.csv   (prevalence as the interval [resolved rule, union rule])
and with the figures printed in analysis/out/RESULTS_SUMMARY.md (overall alpha, module shares).

    python repro/reproduce_audit.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import csv
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, SEED, SUMMARY_MD, Checker, load_resolved  # noqa: E402

from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402
from agentaudit.stats import alpha_ordinal, bootstrap_ci, wilson  # noqa: E402


# ------------------------------------------------------------------ RQ1 (port of analysis/postfreeze/rq1_rq2.py)
def level_of(v):
    return None if v == "NA" else int(v)


def _share(k: int, n: int):
    if n <= 0:
        return None, None, None
    ci = wilson(k, n)
    return k / n, ci[0], ci[1]


def prevalence(resolved: dict, rule: str = "final") -> list[dict]:
    items = load_items()
    rows = []
    for it in ITEM_ORDER:
        cells = [(b, c[it]) for b, c in resolved.items() if it in c]
        if not cells:
            continue
        lv = [level_of(c[rule]) for _, c in cells]
        app = [x for x in lv if x is not None]
        n_rep = sum(x >= 1 for x in app)
        n_full = sum(x == 2 for x in app)
        r = _share(n_rep, len(app))
        f = _share(n_full, len(app))
        rows.append({
            "item": it, "module": items[it].module, "title": items[it].title,
            "rule": "resolved" if rule == "final" else "majority",
            "n_cells": len(cells), "n_na": len(lv) - len(app), "n_applicable": len(app),
            "n_reported": n_rep, "share_reported": r[0], "reported_lo": r[1], "reported_hi": r[2],
            "n_full": n_full, "share_full": f[0], "full_lo": f[1], "full_hi": f[2],
            "n_fallback": sum(1 for _, c in cells if c.get("fallback")) if rule == "final" else None})
    return rows


def module_summary(resolved: dict, rule: str = "final", n_boot: int = N_BOOT) -> list[dict]:
    items = load_items()
    rows = []
    for mod in ("core", "agent"):
        ids = [i for i in ITEM_ORDER if items[i].module == mod]
        groups: dict[str, list] = {}
        frac: list[float] = []
        for b, cells in resolved.items():
            units = []
            for i in ids:
                if i in cells and level_of(cells[i][rule]) is not None:
                    x = level_of(cells[i][rule])
                    units.append((x >= 1, x == 2, x))
            if units:
                groups[b] = units
                frac.append(sum(u[2] for u in units) / (2 * len(units)))
        units = [u for g in groups.values() for u in g]
        n = len(units)
        if not n:
            continue
        k_rep, k_full = sum(u[0] for u in units), sum(u[1] for u in units)
        wr, wf = wilson(k_rep, n), wilson(k_full, n)
        br = bootstrap_ci(groups, lambda us: sum(u[0] for u in us) / len(us) if us else None, n_boot=n_boot)
        bf = bootstrap_ci(groups, lambda us: sum(u[1] for u in us) / len(us) if us else None, n_boot=n_boot)
        rows.append({
            "module": mod, "rule": "resolved" if rule == "final" else "majority", "n_items": len(ids),
            "n_benchmarks": len(groups), "n_applicable_cells": n,
            "share_reported": k_rep / n, "reported_wilson_lo": wr[0], "reported_wilson_hi": wr[1],
            "reported_boot_lo": br[0] if br else None, "reported_boot_hi": br[1] if br else None,
            "share_full": k_full / n, "full_wilson_lo": wf[0], "full_wilson_hi": wf[1],
            "full_boot_lo": bf[0] if bf else None, "full_boot_hi": bf[1] if bf else None,
            "mean_bench_fraction_of_max": float(np.mean(frac)), "median_bench_fraction_of_max": float(np.median(frac))})
    return rows


def resolution_summary(resolved: dict) -> list[dict]:
    counts: dict[str, int] = {}
    total = fb = same = 0
    for cells in resolved.values():
        for c in cells.values():
            counts[c["status"]] = counts.get(c["status"], 0) + 1
            total += 1
            fb += bool(c.get("fallback"))
            same += c["final"] == c["majority_final"]
    rows = [{"status": k, "n_cells": v, "share": v / total} for k, v in sorted(counts.items())]
    rows.append({"status": "ALL_FALLBACK", "n_cells": fb, "share": fb / total if total else None})
    rows.append({"status": "PRIMARY_EQUALS_MAJORITY", "n_cells": same, "share": same / total if total else None})
    rows.append({"status": "TOTAL_CELLS", "n_cells": total, "share": 1.0 if total else None})
    return rows


def contradictions(resolved: dict) -> tuple[list[dict], list[dict]]:
    """Per item and per benchmark counts of coder-raised contradiction flags. The released resolved cells hold the
    fields of verified/<bench>/<item>/<coder>.json that the original function reads (contradicted,
    contradiction_verified, family)."""
    per_item = {i: {"item": i, "cells_with_flag": 0, "cells_flag_verified_quote": 0,
                    "cells_flag_two_families": 0, "coder_flags": 0} for i in ITEM_ORDER}
    per_bench: dict[str, dict] = {}
    for b in sorted(resolved):
        pb = per_bench.setdefault(b, {"bench": b, "cells_with_flag": 0, "cells_flag_verified_quote": 0,
                                      "cells_flag_two_families": 0, "items": []})
        for it in sorted(resolved[b]):  # the original iterates sorted((bench, item)) keys
            votes = resolved[b][it]["coders"]
            fl = {c: v for c, v in votes.items() if v.get("contradicted")}
            if not fl:
                continue
            ver = any(v.get("contradiction_verified") for v in fl.values())
            fams = {v.get("family") or c for c, v in fl.items()}
            d = per_item[it]
            d["cells_with_flag"] += 1
            d["cells_flag_verified_quote"] += ver
            d["cells_flag_two_families"] += len(fams) >= 2
            d["coder_flags"] += len(fl)
            pb["cells_with_flag"] += 1
            pb["cells_flag_verified_quote"] += ver
            pb["cells_flag_two_families"] += len(fams) >= 2
            pb["items"].append(it)
    for d in per_bench.values():
        d["items"] = ";".join(d["items"])
    items = list(per_item.values())
    note = "candidate flags only until checked against the benchmark's documentation and offered right of reply"
    for d in items:
        d["status"] = note
    return items, list(per_bench.values())


# ------------------------------------------------------------------ RQ2: cross-family alpha
def raw_scores(resolved: dict) -> tuple[dict, dict]:
    """({(bench, item): {coder: raw score}}, {coder: family}) from the released resolved cells
    (the raw coder score before quote verification, which the original reads from coding/<bench>/<item>/<coder>.json)."""
    cells, fam = {}, {}
    for b, cs in resolved.items():
        for it, c in cs.items():
            for coder, v in c["votes"].items():
                cells.setdefault((b, it), {})[coder] = v["raw"]
                fam[coder] = c["coders"][coder].get("family") or coder
    return cells, fam


def alpha_table(resolved: dict, n_boot: int = N_BOOT, seed: int = SEED) -> list[dict]:
    benches = sorted(resolved)
    cells, fam = raw_scores(resolved)
    coders = sorted(fam)
    sets: dict[str, list[str]] = {}
    if len(coders) >= 2:
        sets["all:" + "+".join(coders)] = coders
    for a, b in combinations(coders, 2):
        if fam[a] != fam[b]:
            sets[f"cross-family:{a}|{b}"] = [a, b]

    def one(cs: list[str], item: str | None) -> dict:
        groups: dict[str, list] = {b: [] for b in benches}
        for (b, it), votes in sorted(cells.items()):
            if (item is not None and it != item) or not all(c in votes for c in cs):
                continue
            groups[b].append([votes[c] for c in cs])
        groups = {b: u for b, u in groups.items() if u}
        units = [u for us in groups.values() for u in us]
        a = alpha_ordinal(units)
        ci = bootstrap_ci(groups, alpha_ordinal, n_boot=n_boot, seed=seed) if a is not None else None
        return {"alpha": a, "ci_lo": ci[0] if ci else None, "ci_hi": ci[1] if ci else None,
                "units": len(units), "benchmarks": len(groups)}

    rows = []
    for name, cs in sets.items():
        kind = "all_coders" if name.startswith("all:") else "cross_family_pair"
        for item in [None] + ITEM_ORDER:
            r = one(cs, item)
            if item is not None and not r["units"]:
                continue
            rows.append({"set": name, "kind": kind, "scope": "overall" if item is None else "item",
                         "item": item or "", **r, "n_boot": n_boot, "seed": seed})
    return rows


# ------------------------------------------------------------------ bounds (port of analysis/revision_rq12.py)
def _union(votes: dict, key: str):
    nums = [v[key] for v in votes.values() if v[key] != "NA"]
    return max(nums) if nums else "NA"


def bounds(resolved: dict, n_boot: int = N_BOOT) -> dict:
    """Prevalence under the resolved rule (the stored final level) and under the union rule (higher of the two verified
    scores; 'union_raw' = higher of the two raw scores), as in revision_rq12.rq1_block and bounds_block."""
    def lv(rule):
        out = {}
        for b, cells in resolved.items():
            out[b] = {}
            for it, c in cells.items():
                if rule == "current":
                    out[b][it] = {"final": c["final"]}
                else:
                    out[b][it] = {"final": _union(c["votes"], "effective" if rule == "union" else "raw")}
        return out
    mods = {r: {m["module"]: m for m in module_summary(lv(r), "final", n_boot)} for r in ("current", "union", "union_raw")}
    its = {r: {m["item"]: m for m in prevalence(lv(r), "final")} for r in ("current", "union", "union_raw")}
    titles = load_items()
    irows = []
    for it in ITEM_ORDER:
        c, u, ur = its["current"][it], its["union"][it], its["union_raw"][it]
        irows.append({"item": it, "module": titles[it].module, "title": titles[it].title,
                      "n_applicable": c["n_applicable"], "n_applicable_union": u["n_applicable"],
                      "reported_current": c["share_reported"], "reported_union": u["share_reported"],
                      "reported_union_raw": ur["share_reported"],
                      "reported_lo_ci": c["reported_lo"], "reported_hi_ci": u["reported_hi"],
                      "full_current": c["share_full"], "full_union": u["share_full"], "full_union_raw": ur["share_full"],
                      "full_lo_ci": c["full_lo"], "full_hi_ci": u["full_hi"]})
    mrows = []
    for m in ("core", "agent"):
        c, u, ur = mods["current"][m], mods["union"][m], mods["union_raw"][m]
        mrows.append({"module": m, "n_cells": c["n_applicable_cells"], "n_cells_union": u["n_applicable_cells"],
                      "reported_current": c["share_reported"], "reported_union": u["share_reported"],
                      "reported_union_raw": ur["share_reported"],
                      "reported_lo_ci": c["reported_boot_lo"], "reported_hi_ci": u["reported_boot_hi"],
                      "full_current": c["share_full"], "full_union": u["share_full"], "full_union_raw": ur["share_full"],
                      "full_lo_ci": c["full_boot_lo"], "full_hi_ci": u["full_boot_hi"]})
    return {"items": irows, "modules": mrows}


# ------------------------------------------------------------------ main
def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)

    def cell(v):
        return "" if v is None else (round(v, 6) if isinstance(v, float) else v)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: cell(r.get(k)) for k in fields})


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    resolved = load_resolved()
    assert len(resolved) == 44, len(resolved)
    ck = Checker("audit population (RQ1 prevalence, bounds; RQ2 cross-family alpha)")

    prev = prevalence(resolved, "final") + prevalence(resolved, "majority_final")
    mods = module_summary(resolved, "final") + module_summary(resolved, "majority_final")
    res = resolution_summary(resolved)
    ci_item, ci_bench = contradictions(resolved)
    alpha = alpha_table(resolved)
    bnd = bounds(resolved)
    for name, rows in (("rq1_prevalence", prev), ("rq1_modules", mods), ("rq1_resolution", res),
                       ("rq1_contradictions", ci_item), ("rq1_contradictions_by_bench", ci_bench),
                       ("rq2_alpha", alpha), ("rev_bounds_items", bnd["items"]), ("rev_bounds_modules", bnd["modules"])):
        write_csv(a.out / f"{name}.csv", rows)
    ck.csv_rows("rq1_prevalence.csv", prev, ANALYSIS_OUT / "rq1_prevalence.csv", ["item", "rule"])
    ck.csv_rows("rq1_modules.csv", mods, ANALYSIS_OUT / "rq1_modules.csv", ["module", "rule"])
    ck.csv_rows("rq1_resolution.csv", res, ANALYSIS_OUT / "rq1_resolution.csv", ["status"])
    ck.csv_rows("rq1_contradictions.csv", ci_item, ANALYSIS_OUT / "rq1_contradictions.csv", ["item"])
    ck.csv_rows("rq1_contradictions_by_bench.csv", ci_bench, ANALYSIS_OUT / "rq1_contradictions_by_bench.csv", ["bench"])
    ck.csv_rows("rq2_alpha.csv", alpha, ANALYSIS_OUT / "rq2_alpha.csv", ["set", "scope", "item"])
    ck.csv_rows("rev_bounds_items.csv", bnd["items"], ANALYSIS_OUT / "rev_bounds_items.csv", ["item"])
    ck.csv_rows("rev_bounds_modules.csv", bnd["modules"], ANALYSIS_OUT / "rev_bounds_modules.csv", ["module"])

    # printed values in RESULTS_SUMMARY.md
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    ov = [r for r in alpha if r["scope"] == "overall" and r["kind"] == "all_coders"][0]
    ck.in_text("overall alpha", f"alpha = {ov['alpha']:.3f} (95% CI [{ov['ci_lo']:.3f}, {ov['ci_hi']:.3f}]), "
                                f"{ov['units']} cells, {ov['benchmarks']} benchmarks", txt)
    for r in (x for x in alpha if x["scope"] == "item" and x["kind"] == "all_coders"):
        ck.in_text(f"alpha {r['item']}", f"| {r['item']} | {r['alpha']:.3f} | [{r['ci_lo']:.3f}, {r['ci_hi']:.3f}] | {r['units']} |", txt)
    core = [m for m in mods if m["module"] == "core" and m["rule"] == "resolved"][0]
    agent = [m for m in mods if m["module"] == "agent" and m["rule"] == "resolved"][0]
    ck.in_text("module shares", f"reported share core {100 * core['share_reported']:.1f}%, agent {100 * agent['share_reported']:.1f}%; "
                                f"fully reported core {100 * core['share_full']:.1f}%, agent {100 * agent['share_full']:.1f}%", txt)
    ck.done()
    print(f"overall cross-family alpha {ov['alpha']:.3f} [{ov['ci_lo']:.3f}, {ov['ci_hi']:.3f}] over {ov['units']} cells; "
          f"reported share core {100 * core['share_reported']:.1f}%, agent {100 * agent['share_reported']:.1f}%")


if __name__ == "__main__":
    main()
