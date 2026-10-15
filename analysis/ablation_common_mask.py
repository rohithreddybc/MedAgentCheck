"""Post hoc check (review 2026-10-14): ablation of resolution rules on one common mask of expert-labelled cells.

Every rule of Table rev_ablation is re-scored on the cells where the expert score and every rule's score are
non-NA (ABC 198, BetterBench 423). Paired differences against the better single coder use the same cells and the
same benchmark resamples, as does the effect of quote verification (resolved rule on raw minus verified scores). Writes analysis/out/ablation_common_mask.json. Does not change any frozen output.
"""
from __future__ import annotations

import json
import sys

import revision_rq12 as V
from revision_rq12 import G, RULES, SEED, OUT, boot_multi, cohen_kappa, weighted_kappa


def main(n_boot: int = V.N_BOOT) -> None:
    res = {}
    for s in ("abc", "betterbench"):
        gc = V.gold_cells(s)
        cfg = gc["cfg"]
        levels = list(cfg["levels"])
        k = (lambda a, b: cohen_kappa(a, b)) if cfg["primary"] == "cohen_kappa" else (
            lambda a, b: weighted_kappa(a, b, levels, "quadratic"))
        by_rule = {r: {(b, i): (g, p) for b, i, g, p in V.rule_pairs(gc, r)} for r, _ in RULES}
        per_rule_n = {r: sum(1 for g, p in d.values() if g != "NA" and p != "NA") for r, d in by_rule.items()}
        keys = set.intersection(*[{c for c, (g, p) in d.items() if g != "NA" and p != "NA"} for d in by_rule.values()])
        blk = {"per_rule_n": per_rule_n, "common_n": len(keys),
               "common_benchmarks": len({b for b, _ in keys}), "rules": {}, "diff_vs_best": {}}
        groups = {}
        for (b, i) in sorted(keys):
            groups.setdefault(b, []).append((b, i))
        for r, _ in RULES:
            def f(units, r=r):
                return k([by_rule[r][u][0] for u in units], [by_rule[r][u][1] for u in units])
            allu = sorted(keys)
            grp = {b: us for b, us in groups.items()}
            blk["rules"][r] = {"kappa": f(allu), "ci": boot_multi(grp, {"k": f}, n_boot)["k"]}
        best = max(("claude", "openai"), key=lambda r: blk["rules"][r]["kappa"])
        blk["best"] = best
        for r, _ in RULES:
            if r in ("claude", "openai"):
                continue
            def d(units, r=r):
                g = [by_rule[r][u][0] for u in units]
                a = k(g, [by_rule[r][u][1] for u in units])
                c = k(g, [by_rule[best][u][1] for u in units])
                return None if a is None or c is None else a - c
            blk["diff_vs_best"][r] = {"diff": d(sorted(keys)), "ci": boot_multi(groups, {"d": d}, n_boot)["d"]}
        def dv(units):
            g = [by_rule["raw"][u][0] for u in units]
            a = k(g, [by_rule["raw"][u][1] for u in units])
            c = k(g, [by_rule["current"][u][1] for u in units])
            return None if a is None or c is None else a - c
        blk["raw_minus_current"] = {"diff": dv(sorted(keys)), "ci": boot_multi(groups, {"d": dv}, n_boot)["d"]}
        res[s] = blk
    (OUT / "ablation_common_mask.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for s, blk in res.items():
        print(s, "per-rule n", blk["per_rule_n"], "common", blk["common_n"], blk["common_benchmarks"], "best", blk["best"])
        for r, v in blk["rules"].items():
            print("  ", r, round(v["kappa"], 3), [round(x, 2) for x in v["ci"]])
        for r, v in blk["diff_vs_best"].items():
            print("   diff", r, round(v["diff"], 3), [round(x, 2) for x in v["ci"]])
        v = blk["raw_minus_current"]
        print("   raw minus current", round(v["diff"], 3), [round(x, 3) for x in v["ci"]])


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else V.N_BOOT)
