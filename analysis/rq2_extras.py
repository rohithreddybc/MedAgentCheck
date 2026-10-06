"""RQ2 pieces that rq1_rq2.py does not produce (final run, 2026-10-06). Analysis side only; the frozen package is
imported read-only and nothing under audit/ is written.

1. Gold agreement by item and error direction (over-credit: coder level above the published expert level; under-credit:
   below), per coder and RESOLVED, for ABC and BetterBench. Per-cell predictions come from the frozen
   ``agentaudit.gold.gold_agreement(...)["_cells"]`` (the same cells as the scorer's agreement files). ABC gold is
   unlicensed: only per-item aggregates are written, never per-cell gold values. -> rq2_gold_by_item.csv,
   rq2_gold_direction.csv
2. Coder test-retest on the 10 drawn benchmarks for each coder. ANALYSIS-SIDE FIX 6: the frozen
   ``agentaudit retest --compare-only`` maps ids to packet directories with ``bench_dir_candidates`` (underscore slugs) and
   so drops diaggym-diagbench and synthetic-hospital; ids are mapped here through audit/manifests/*.yaml instead
   (as analysis/provisional_retest_all10.py did). Raw scores, original versus retest, as in the frozen statistics.
   A coder whose retest exists for fewer than 10 benchmarks is marked PARTIAL. -> rq2_retest.csv, rq2_retest.json,
   rq2_retest_per_benchmark.csv
"""
from __future__ import annotations

import json
from collections import defaultdict

from common import OUT, ROOT, SEED, write_csv

from agentaudit.agree import load_scores  # noqa: E402
from agentaudit.gold import gold_agreement, find_research_dir, load_instrument  # noqa: E402
from agentaudit.retest import _pair_stats  # noqa: E402
from agentaudit.sampling import draw_retest_benchmarks, load_frozen_list  # noqa: E402
from agentaudit.stats import wilson  # noqa: E402
from rq1_rq2 import manifest_slugs  # noqa: E402

AUDIT = ROOT / "audit"
RDIR = find_research_dir(str(ROOT / "research"))
GOLD_RUNS = {"abc": AUDIT / "gold_abc", "betterbench": AUDIT / "gold_bb"}
LABEL = {"abc": "ABC", "betterbench": "BetterBench"}


def _lv(x):
    return None if x == "NA" else int(x)


def gold_direction() -> tuple[list[dict], list[dict]]:
    by_item, direction = [], []
    for s, run in GOLD_RUNS.items():
        res = gold_agreement(run, s, RDIR, n_boot=2)
        instr = load_instrument(s, RDIR)
        cells = res["_cells"]
        for coder in sorted({c["coder"] for c in cells}, key=lambda c: (c == "RESOLVED", c)):
            cs = [c for c in cells if c["coder"] == coder]
            used = [(c["bench"], c["item"], _lv(c["gold"]), _lv(c["pred"])) for c in cs]
            n_na = sum(1 for _, _, g, p in used if g is None or p is None)
            used = [u for u in used if u[2] is not None and u[3] is not None]

            def stats(sel):
                n = len(sel)
                ag = sum(g == p for _, _, g, p in sel)
                ov = sum(p > g for _, _, g, p in sel)
                un = sum(p < g for _, _, g, p in sel)
                w1 = sum(abs(p - g) <= 1 for _, _, g, p in sel)
                dis = ov + un
                lo, hi = wilson(ag, n) if n else (None, None)
                wl, wh = wilson(ov, dis) if dis else (None, None)
                return {"n": n, "agree": ag, "agreement": ag / n if n else None, "agree_lo": lo, "agree_hi": hi,
                        "within_one": w1 / n if n else None, "n_over": ov, "n_under": un,
                        "share_over_of_disagree": ov / dis if dis else None, "over_lo": wl, "over_hi": wh}

            tot = stats(used)
            direction.append({"set": LABEL[s], "coder": coder, "n_na_left_out": n_na, **tot})
            for it in sorted({u[1] for u in used}, key=lambda i: [int(t) if t.isdigit() else t for t in
                                                                   i.replace("-", ".").split(".")]):
                st = stats([u for u in used if u[1] == it])
                by_item.append({"set": LABEL[s], "coder": coder, "item": it,
                                "title": (instr[it].title or instr[it].text)[:70] if it in instr else "",
                                "flag_agreement_lt_0.5": "FLAG" if st["agreement"] < 0.5 else "", **st})
    return by_item, direction


def retest() -> tuple[list[dict], dict, list[dict]]:
    frozen = load_frozen_list(ROOT / "research" / "eligibility" / "frozen_list_v1.csv")
    drawn = draw_retest_benchmarks([r["id"] for r in frozen], 10, SEED)
    slug = manifest_slugs()
    benches = [slug[i] for i in drawn]
    o_cells, o_fam = load_scores(AUDIT, benches)
    r_cells, r_fam = load_scores(AUDIT / "retest", benches)
    rows, js, per_bench = [], {"seed": SEED, "drawn": drawn, "packet_dirs": benches, "coders": {}}, []
    for coder in sorted(set(o_fam) & set(r_fam)):
        pairs, groups, pb, per_item = [], defaultdict(list), defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
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
        st = _pair_stats(pairs, dict(groups), 2000, SEED)
        done = [b for b in benches if pb[b][0]]
        partial = len(done) < len(benches)
        st.update({"n_benchmarks": len(done), "benchmarks_with_retest": done,
                   "benchmarks_missing": [b for b in benches if not pb[b][0]], "partial": partial,
                   "family": o_fam[coder]})
        js["coders"][coder] = {**st, "per_item": {i: {"n": v[0], "agree": v[1]} for i, v in per_item.items()}}
        rows.append({"coder": coder, "partial": partial, "n_benchmarks": len(done),
                     **{k: st[k] for k in ("n_cells", "n_applicable_both", "n_na_mismatch", "n_exact", "raw_agreement",
                                           "alpha_ordinal", "weighted_kappa_quadratic", "cohen_kappa")},
                     "raw_lo": (st["raw_agreement_wilson95"] or [None, None])[0],
                     "raw_hi": (st["raw_agreement_wilson95"] or [None, None])[1],
                     "alpha_lo": (st["alpha_ci95"] or [None, None])[0], "alpha_hi": (st["alpha_ci95"] or [None, None])[1]})
        for b in benches:
            per_bench.append({"coder": coder, "bench": b, "n_cells": pb[b][0], "n_exact": pb[b][1],
                              "raw_agreement": pb[b][1] / pb[b][0] if pb[b][0] else None})
    return rows, js, per_bench


def main() -> None:
    by_item, direction = gold_direction()
    write_csv(OUT / "rq2_gold_by_item.csv", by_item)
    write_csv(OUT / "rq2_gold_direction.csv", direction)
    rows, js, per_bench = retest()
    write_csv(OUT / "rq2_retest.csv", rows)
    write_csv(OUT / "rq2_retest_per_benchmark.csv", per_bench)
    (OUT / "rq2_retest.json").write_text(json.dumps(js, indent=2), encoding="utf-8", newline="\n")
    for r in direction:
        print(r["set"], r["coder"], r["n"], round(r["agreement"], 3), "over", r["n_over"], "under", r["n_under"])
    for r in rows:
        print(r["coder"], "partial" if r["partial"] else "", r["n_benchmarks"], r["n_cells"], r["raw_agreement"],
              r["alpha_ordinal"])


if __name__ == "__main__":
    main()
