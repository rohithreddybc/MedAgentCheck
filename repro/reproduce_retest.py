"""Reproduce coder test-retest agreement (original versus retest, 10 seeded benchmarks, each coder and the resolved level).

Port of analysis/rq2_extras.py (retest) and of agentaudit/retest.py (_pair_stats; frozen, re-implemented here so that no
heavy dependency of that module is imported). Original scores: results/resolved/<bench>.json; retest scores:
results/retest/resolved/<bench>.json (raw coder score per cell, before quote verification, as the authors' script reads
from coding/); the drawn benchmarks and their packet slugs: results/retest/retest_agreement.json. Compared with
results/analysis_out/rq2_retest.csv, rq2_retest_per_benchmark.csv, rq2_retest.json, results/retest/retest_agreement.json
(resolved level) and the figures in analysis/out/RESULTS_SUMMARY.md section 3.3.

    python repro/reproduce_retest.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, RESULTS, SEED, SUMMARY_MD, Checker, load_resolved, read_json  # noqa: E402
from reproduce_audit import write_csv  # noqa: E402

from agentaudit.stats import alpha_ordinal, bootstrap_ci, cohen_kappa, raw_agreement, weighted_kappa, wilson  # noqa: E402


def pair_stats(pairs: list[tuple], groups: dict[str, list], n_boot: int, seed: int) -> dict:
    """Port of agentaudit.retest._pair_stats. pairs: [(orig, retest)] raw scores (0|1|2|'NA')."""
    n = len(pairs)
    appl = [(a, b) for a, b in pairs if a != "NA" and b != "NA"]
    na_mismatch = sum(1 for a, b in pairs if (a == "NA") != (b == "NA"))
    out = {"n_cells": n, "n_applicable_both": len(appl), "n_na_mismatch": na_mismatch,
           "raw_agreement": None, "raw_agreement_wilson95": None, "alpha_ordinal": None, "alpha_ci95": None,
           "weighted_kappa_quadratic": None, "cohen_kappa": None, "reported_split_agreement": None, "n_exact": 0}
    if not n:
        return out
    exact = sum(1 for a, b in pairs if a == b)
    out["n_exact"] = exact
    out["raw_agreement"] = exact / n
    w = wilson(exact, n)
    out["raw_agreement_wilson95"] = list(w) if w else None
    units = [[a, b] for a, b in pairs]
    out["alpha_ordinal"] = alpha_ordinal(units)
    if out["alpha_ordinal"] is not None and len(groups) >= 2:
        ci = bootstrap_ci(groups, alpha_ordinal, n_boot=n_boot, seed=seed)
        out["alpha_ci95"] = list(ci) if ci else None
    if appl:
        a, b = [x for x, _ in appl], [y for _, y in appl]
        out["weighted_kappa_quadratic"] = weighted_kappa(a, b, (0, 1, 2), "quadratic")
        out["cohen_kappa"] = cohen_kappa(a, b)
        out["reported_split_agreement"] = raw_agreement([int(x >= 1) for x in a], [int(y >= 1) for y in b])
    return out


def raw_cells(resolved: dict, benches: list[str]) -> tuple[dict, dict]:
    cells, fam = {}, {}
    for b in benches:
        for it, c in resolved[b].items():
            for coder, v in c["votes"].items():
                cells.setdefault((b, it), {})[coder] = v["raw"]
                fam[coder] = (c.get("coders", {}).get(coder) or {}).get("family") or coder  # retest cells hold votes only
    return cells, fam


def load_retest(drawn_dirs: list[str]) -> dict:
    """bench slug -> cells, from results/retest/resolved/ (file names differ from the slug only in case)."""
    by_lower = {p.stem.lower(): p for p in (RESULTS / "retest" / "resolved").glob("*.json") if p.stem != "summary"}
    return {b: read_json(by_lower[b.lower()])["cells"] for b in drawn_dirs}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    ck = Checker("coder test-retest")
    meta = read_json(RESULTS / "retest" / "retest_agreement.json")
    ref_json = read_json(ANALYSIS_OUT / "rq2_retest.json")
    benches = [d["packet_dir"] for d in meta["drawn"]]
    ck.eq("drawn benchmarks", benches, ref_json["packet_dirs"])
    original = load_resolved()
    retest = load_retest(benches)
    o_cells, o_fam = raw_cells(original, benches)
    r_cells, r_fam = raw_cells(retest, benches)

    rows, per_bench, js = [], [], {"coders": {}}
    for coder in sorted(set(o_fam) & set(r_fam)):
        pairs, groups = [], defaultdict(list)
        pb = defaultdict(lambda: [0, 0])
        per_item = defaultdict(lambda: [0, 0])
        for (b, it), votes in sorted(o_cells.items()):
            rv = r_cells.get((b, it), {})
            if coder in votes and coder in rv:
                p = (votes[coder], rv[coder])
                pairs.append(p)
                groups[b].append(list(p))
                pb[b][0] += 1
                pb[b][1] += p[0] == p[1]
                per_item[it][0] += 1
                per_item[it][1] += p[0] == p[1]
        st = pair_stats(pairs, dict(groups), N_BOOT, SEED)
        done = [b for b in benches if pb[b][0]]
        partial = len(done) < len(benches)
        js["coders"][coder] = {**st, "n_benchmarks": len(done), "partial": partial,
                               "per_item": {i: {"n": v[0], "agree": v[1]} for i, v in per_item.items()}}
        rows.append({"coder": coder, "partial": partial, "n_benchmarks": len(done),
                     **{k: st[k] for k in ("n_cells", "n_applicable_both", "n_na_mismatch", "n_exact", "raw_agreement",
                                           "alpha_ordinal", "weighted_kappa_quadratic", "cohen_kappa")},
                     "raw_lo": (st["raw_agreement_wilson95"] or [None, None])[0],
                     "raw_hi": (st["raw_agreement_wilson95"] or [None, None])[1],
                     "alpha_lo": (st["alpha_ci95"] or [None, None])[0], "alpha_hi": (st["alpha_ci95"] or [None, None])[1]})
        for b in benches:
            per_bench.append({"coder": coder, "bench": b, "n_cells": pb[b][0], "n_exact": pb[b][1],
                              "raw_agreement": pb[b][1] / pb[b][0] if pb[b][0] else None})

    write_csv(a.out / "rq2_retest.csv", rows)
    write_csv(a.out / "rq2_retest_per_benchmark.csv", per_bench)
    ck.csv_rows("rq2_retest.csv", rows, ANALYSIS_OUT / "rq2_retest.csv", ["coder"])
    ck.csv_rows("rq2_retest_per_benchmark.csv", per_bench, ANALYSIS_OUT / "rq2_retest_per_benchmark.csv", ["coder", "bench"])
    for coder, st in js["coders"].items():
        ref = ref_json["coders"][coder]
        for f in ("n_cells", "n_applicable_both", "n_na_mismatch", "n_exact", "n_benchmarks"):
            ck.eq(f"json {coder}/{f}", st[f], ref[f])
        for f in ("raw_agreement", "alpha_ordinal", "weighted_kappa_quadratic", "cohen_kappa", "reported_split_agreement"):
            ck.eq(f"json {coder}/{f}", st[f], ref[f], 1e-9)
        for f in ("raw_agreement_wilson95", "alpha_ci95"):
            ck.eq(f"json {coder}/{f}", st[f], ref[f], 1e-9)
        ck.eq(f"json {coder}/per_item", st["per_item"], ref["per_item"])

    # resolved level, original versus retest (the resolution rule applied to each run separately)
    pairs = []
    for b in benches:
        for it in sorted(original[b]):
            if it in retest[b]:
                pairs.append((original[b][it]["final"], retest[b][it]["final"]))
    res_alpha = alpha_ordinal([[x, y] for x, y in pairs])
    res_raw = sum(1 for x, y in pairs if x == y) / len(pairs)
    ref_res = meta["resolved"]
    ck.eq("resolved retest n_cells", len(pairs), ref_res["n_cells"])
    ck.eq("resolved retest raw agreement", res_raw, ref_res["raw_agreement"], 1e-9)
    ck.eq("resolved retest alpha", res_alpha, ref_res["alpha_ordinal"], 1e-9)

    txt = SUMMARY_MD.read_text(encoding="utf-8")
    for r in rows:
        ck.in_text(f"3.3 {r['coder']}",
                   f"| {r['coder']} | complete | {r['n_benchmarks']} | {r['n_cells']} | {r['n_exact']} | "
                   f"{r['raw_agreement']:.3f} [{r['raw_lo']:.3f}, {r['raw_hi']:.3f}] | "
                   f"{r['alpha_ordinal']:.3f} [{r['alpha_lo']:.3f}, {r['alpha_hi']:.3f}] | {r['weighted_kappa_quadratic']:.3f} |", txt)
    ck.in_text("3.3 resolved", f"{len(pairs)} cells, raw agreement {res_raw:.3f}, ordinal alpha {res_alpha:.3f}.", txt)
    ck.done()
    for r in rows:
        print(f"{r['coder']}: raw agreement {r['raw_agreement']:.3f}, alpha {r['alpha_ordinal']:.3f} "
              f"[{r['alpha_lo']:.3f}, {r['alpha_hi']:.3f}], {r['n_benchmarks']} benchmarks")
    print(f"resolved: raw agreement {res_raw:.3f}, alpha {res_alpha:.3f} ({len(pairs)} cells)")


if __name__ == "__main__":
    main()
