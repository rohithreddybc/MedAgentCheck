"""Like-for-like agreement on the gold cells: coder-vs-coder and coder-vs-expert, same cells, same statistics.

Reviewer objection: the paper sets cross-family Krippendorff alpha (audit items) beside coder-vs-expert kappa on the
gold sets. This script computes, on the SAME gold cells and with the SAME statistics,
  (a) codex vs sonnet,  (b) each coder vs the published expert score,  (c) the two-family resolved score vs expert,
  (d) benchmark-level bootstrap CIs (2,000 resamples, seed 20261004) for the coder-pair minus coder-expert kappa.

It reuses the scorer's own code (agentaudit.gold: load_gold, items_for_set, load_predictions, resolved_predictions,
agreement_stats; agentaudit.stats): effective score (a 1+ without a verified quote counts as 0), the same item set, NA
exclusion, BetterBench 0/5/10/15 -> 0..3, and the same gold cutoff/pins. Statistics reproduced from the scorer are
asserted against audit/gold_*/.../agreement/agreement.json.

Cell sets. "original": the cells in agreement.json (per coder, expert non-NA and coder non-NA; for BetterBench the
coders' sets differ by a few cells where one coder answered NA). "common": cells where the expert and BOTH coders have
a score. The pair statistics and all like-for-like comparisons use the common set. ABC: original == common.

Run from the project root:
    python analysis/gold_coder_pair.py            # prints, writes analysis/out/gold_coder_pair.json
    python analysis/gold_coder_pair.py --write-summary   # also (re)writes section 5 of analysis/out/RESULTS_SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, ROOT, SEED  # noqa: E402  (also puts the scorer on sys.path)

from agentaudit import gold as G  # noqa: E402
from agentaudit.stats import alpha_ordinal, cohen_kappa, raw_agreement, weighted_kappa, wilson  # noqa: E402

N_BOOT = 2000
RDIR = ROOT / "research"
RUNS = {"abc": ROOT / "audit" / "gold_abc", "betterbench": ROOT / "audit" / "gold_bb"}
SUMMARY = OUT / "RESULTS_SUMMARY.md"
CMD = "python analysis/gold_coder_pair.py --write-summary"


def primary(cfg: dict, a: list, b: list) -> float | None:
    levels = list(cfg["levels"])
    return cohen_kappa(a, b) if cfg["primary"] == "cohen_kappa" else weighted_kappa(a, b, levels, "quadratic")


def stats_on(cfg: dict, a: list, b: list) -> dict:
    levels = list(cfg["levels"])
    n = len(a)
    ag = sum(1 for x, y in zip(a, b) if x == y)
    out = {"n": n, "raw_agreement": ag / n, "raw_agreement_wilson95": list(wilson(ag, n)),
           "cohen_kappa": cohen_kappa(a, b),
           "krippendorff_alpha_ordinal": alpha_ordinal([(x, y) for x, y in zip(a, b)], levels),
           "primary_statistic": cfg["primary"], "primary_value": primary(cfg, a, b)}
    if len(levels) > 2:
        out["weighted_kappa_quadratic"] = weighted_kappa(a, b, levels, "quadratic")
    return out


def pctl(vals: list[float], alpha: float = 0.05) -> list[float] | None:
    vals = sorted(v for v in vals if v is not None)
    if len(vals) < 20:
        return None
    return [vals[int((alpha / 2) * (len(vals) - 1))], vals[int((1 - alpha / 2) * (len(vals) - 1))]]


def load_set(set_name: str) -> dict:
    cfg = G.set_cfg(set_name)
    run = RUNS[set_name]
    gold = G.load_gold(set_name, RDIR)
    ids = set(G.items_for_set(set_name))
    preds, fam = G.load_predictions(run, set_name)
    assert sorted(preds) == ["codex", "sonnet"], sorted(preds)
    recorded = json.loads((G.gold_run_dir(run, set_name) / "agreement" / "agreement.json").read_text(encoding="utf-8"))

    # (1) reproduce agreement.json with the scorer's own function
    repro = {}
    for c in ("codex", "sonnet"):
        pairs = [(b, i, gold[(b, i)], v["effective"]) for (b, i), v in sorted(preds[c].items()) if (b, i) in gold and i in ids]
        repro[c] = G.agreement_stats(pairs, cfg, N_BOOT, SEED)
    res, _ = G.resolved_predictions(preds, fam, cfg["top_down"])
    pairs = [(b, i, gold[(b, i)], p) for (b, i), p in sorted(res.items()) if (b, i) in gold and i in ids]
    repro["resolved"] = G.agreement_stats(pairs, cfg, N_BOOT, SEED)
    for k, st in repro.items():
        rec = recorded["resolved"] if k == "resolved" else recorded["by_coder"][k]
        for f in ("n_cells", "n_gold_na", "n_pred_na_where_gold_scored", "n_both_na"):
            assert st[f] == rec[f], (set_name, k, f, st[f], rec[f])
        for f in ("cohen_kappa", "weighted_kappa_quadratic", "primary_value"):
            if f in rec:
                assert abs(st[f] - rec[f]) < 1e-9, (set_name, k, f, st[f], rec[f])
        assert st["raw_agreement"]["agree"] == rec["raw_agreement"]["agree"]
        ci_r, ci_s = rec["primary_ci95_bootstrap_over_benchmarks"], st["primary_ci95_bootstrap_over_benchmarks"]
        assert all(abs(x - y) < 1e-9 for x, y in zip(ci_r, ci_s)), (set_name, k, ci_r, ci_s)

    # (2) cell sets
    def usable(p):
        return p != "NA"
    orig = {c: {cell: v["effective"] for cell, v in preds[c].items()
                if cell in gold and cell[1] in ids and gold[cell] != "NA" and usable(v["effective"])} for c in preds}
    common = sorted(set(orig["codex"]) & set(orig["sonnet"]))
    resolved_cells = {cell: res[cell] for cell in common if cell in res and res[cell] != "NA"}
    return {"cfg": cfg, "gold": gold, "preds": preds, "orig": orig, "common": common, "res": res,
            "resolved_common": resolved_cells, "recorded": recorded, "repro": repro}


def analyse(set_name: str) -> dict:
    d = load_set(set_name)
    cfg, gold, preds, common = d["cfg"], d["gold"], d["preds"], d["common"]
    g = {c: gold[c] for c in common}
    cx = {c: preds["codex"][c]["effective"] for c in common}
    sn = {c: preds["sonnet"][c]["effective"] for c in common}
    benches = sorted({b for b, _ in common})

    def vecs(cells, x, y):
        return [x[c] for c in cells], [y[c] for c in cells]

    pairs = {"codex_vs_sonnet": (cx, sn), "codex_vs_expert": (cx, g), "sonnet_vs_expert": (sn, g)}
    out: dict = {"set": set_name, "primary_statistic": cfg["primary"], "levels": list(cfg["levels"]),
                 "n_cells_common": len(common), "n_benchmarks": len(benches), "benchmarks": benches,
                 "n_cells_original": {c: len(d["orig"][c]) for c in d["orig"]},
                 "n_cells_resolved_original": d["repro"]["resolved"]["n_cells"],
                 "reproduced_agreement_json": True, "pairs": {}, "original_cells": {}}
    for name, (x, y) in pairs.items():
        out["pairs"][name] = stats_on(cfg, *vecs(common, x, y))
    # resolved vs expert on the common cells (resolved has no NA-free guarantee, so use its own cell set)
    rc = sorted(d["resolved_common"])
    out["pairs"]["resolved_vs_expert"] = stats_on(cfg, [d["resolved_common"][c] for c in rc], [gold[c] for c in rc])
    out["n_cells_resolved_common"] = len(rc)
    # as published (original cell sets) for the record
    for k, st in d["repro"].items():
        out["original_cells"][k] = {"n": st["n_cells"], "cohen_kappa": st["cohen_kappa"],
                                    "weighted_kappa_quadratic": st.get("weighted_kappa_quadratic"),
                                    "primary_value": st["primary_value"],
                                    "primary_ci95": st["primary_ci95_bootstrap_over_benchmarks"],
                                    "raw_agreement": st["raw_agreement"]["rate"]}

    # (3) joint benchmark bootstrap on the common cells (same resample for every statistic)
    by_b = {b: [c for c in common if c[0] == b] for b in benches}
    rng = random.Random(SEED)
    keys = benches
    names = list(pairs)
    draws = {n: [] for n in names}
    diffs = {"pair_minus_codex_expert": [], "pair_minus_sonnet_expert": [], "pair_minus_mean_coder_expert": [],
             "sonnet_expert_minus_codex_expert": []}
    for _ in range(N_BOOT):
        cells: list = []
        for _k in range(len(keys)):
            cells.extend(by_b[keys[rng.randrange(len(keys))]])
        v = {n: primary(cfg, *vecs(cells, *pairs[n])) for n in names}
        for n in names:
            draws[n].append(v[n])
        if None not in v.values():
            diffs["pair_minus_codex_expert"].append(v["codex_vs_sonnet"] - v["codex_vs_expert"])
            diffs["pair_minus_sonnet_expert"].append(v["codex_vs_sonnet"] - v["sonnet_vs_expert"])
            diffs["pair_minus_mean_coder_expert"].append(
                v["codex_vs_sonnet"] - (v["codex_vs_expert"] + v["sonnet_vs_expert"]) / 2)
            diffs["sonnet_expert_minus_codex_expert"].append(v["sonnet_vs_expert"] - v["codex_vs_expert"])
    for n in names:
        out["pairs"][n]["primary_ci95_bootstrap_over_benchmarks"] = pctl(draws[n])
    pv = {n: out["pairs"][n]["primary_value"] for n in names}
    point = {"pair_minus_codex_expert": pv["codex_vs_sonnet"] - pv["codex_vs_expert"],
             "pair_minus_sonnet_expert": pv["codex_vs_sonnet"] - pv["sonnet_vs_expert"],
             "pair_minus_mean_coder_expert": pv["codex_vs_sonnet"] - (pv["codex_vs_expert"] + pv["sonnet_vs_expert"]) / 2,
             "sonnet_expert_minus_codex_expert": pv["sonnet_vs_expert"] - pv["codex_vs_expert"]}
    out["differences_in_primary_statistic"] = {
        k: {"point": point[k], "ci95_bootstrap_over_benchmarks": pctl(v), "n_boot": N_BOOT, "seed": SEED,
            "share_resamples_positive": sum(1 for x in v if x > 0) / len(v)} for k, v in diffs.items()}
    # a check: when the common set equals the original set, the joint bootstrap reproduces the recorded CIs
    for c in ("codex", "sonnet"):
        if set(d["orig"][c]) == set(common):
            rec = d["recorded"]["by_coder"][c]["primary_ci95_bootstrap_over_benchmarks"]
            mine = out["pairs"][f"{c}_vs_expert"]["primary_ci95_bootstrap_over_benchmarks"]
            assert all(abs(x - y) < 1e-9 for x, y in zip(rec, mine)), (set_name, c, rec, mine)
    out["agreement_json_values"] = {
        k: (d["recorded"]["resolved"] if k == "resolved" else d["recorded"]["by_coder"][k])["primary_value"]
        for k in ("codex", "sonnet", "resolved")}
    return out


# ------------------------------------------------------------------ output
def f(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def ci(c):
    return "n/a" if not c else f"[{c[0]:.2f}, {c[1]:.2f}]"


def markdown(res: dict) -> str:
    L = ["## 5. Like-for-like agreement on gold cells (added 2026-10-06)", ""]
    L.append("Question: is the coder-vs-expert kappa (ABC 0.29 Cohen; BetterBench 0.47 quadratic-weighted) comparable with the "
             "cross-family alpha (0.77, audit items)? Not as printed: they use different statistics on different cells. Here "
             "the same gold cells carry the same statistics for coder-vs-coder (codex vs sonnet) and coder-vs-expert. "
             "Scorer code paths (`agentaudit.gold`: `load_gold`, `items_for_set`, `load_predictions`, `resolved_predictions`, "
             "`agreement_stats`) are reused: effective score (a 1+ without a verified quote counts as 0), same item set, NA "
             "cells left out, BetterBench 0/5/10/15 mapped to 0-3, same gold cutoff. The script asserts that the per-coder "
             "and resolved n, kappa, weighted kappa, raw agreement and bootstrap CIs equal `agreement.json`.")
    L.append("")
    L += ["Command (project root):", "", "```", CMD, "```", "",
          "Script `analysis/gold_coder_pair.py`; machine-readable output `analysis/out/gold_coder_pair.json`. "
          "Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, the same resample used for every statistic "
          "in a set (so differences are paired), percentile 95% CI. Values to two decimals.", ""]
    for s, title, unit in (("abc", "ABC gold (primary statistic: Cohen kappa)", "benchmarks"),
                           ("betterbench", "BetterBench gold (primary statistic: quadratic-weighted kappa)", "benchmarks")):
        r = res[s]
        L.append(f"### 5.{1 if s == 'abc' else 2} {title}")
        L.append("")
        orig = r["n_cells_original"]
        L.append(f"Common cells (expert, codex and sonnet all scored): n = {r['n_cells_common']} cells, {r['n_benchmarks']} {unit}. "
                 f"agreement.json n_cells: codex {orig['codex']}, sonnet {orig['sonnet']}, resolved {r['n_cells_resolved_original']}"
                 + (" (identical to the common set)." if orig['codex'] == orig['sonnet'] == r['n_cells_common'] else
                    "; the common set drops cells where one coder answered NA, so coder-vs-expert values below can differ slightly "
                    "from agreement.json (the published values are in the last paragraph of this subsection)."))
        L.append("")
        hdr = ["Pair", "n", "Primary (95% CI)", "Cohen kappa", "Raw agreement", "Krippendorff alpha (ordinal)"]
        L.append("| " + " | ".join(hdr) + " |")
        L.append("|" + "---|" * len(hdr))
        names = {"codex_vs_sonnet": "codex vs sonnet", "codex_vs_expert": "codex vs expert",
                 "sonnet_vs_expert": "sonnet vs expert", "resolved_vs_expert": "resolved vs expert"}
        for k, lab in names.items():
            p = r["pairs"][k]
            prim = f"{f(p['primary_value'])} {ci(p.get('primary_ci95_bootstrap_over_benchmarks'))}" if k != "resolved_vs_expert" \
                else f(p["primary_value"])
            L.append(f"| {lab} | {p['n']} | {prim} | {f(p['cohen_kappa'])} | {f(p['raw_agreement'])} | "
                     f"{f(p['krippendorff_alpha_ordinal'])} |")
        L.append("")
        L.append("Differences in the primary statistic (coder pair minus coder-vs-expert), paired bootstrap over benchmarks:")
        L.append("")
        L.append("| Difference | Point | 95% CI | Share of resamples > 0 |")
        L.append("|---|---|---|---|")
        lab = {"pair_minus_codex_expert": "pair - codex/expert", "pair_minus_sonnet_expert": "pair - sonnet/expert",
               "pair_minus_mean_coder_expert": "pair - mean(coder/expert)",
               "sonnet_expert_minus_codex_expert": "sonnet/expert - codex/expert"}
        for k, v in r["differences_in_primary_statistic"].items():
            L.append(f"| {lab[k]} | {v['point']:+.2f} | {ci(v['ci95_bootstrap_over_benchmarks'])} | {v['share_resamples_positive']:.3f} |")
        L.append("")
        oc = r["original_cells"]
        L.append("agreement.json values reproduced on the original cell sets (assertion passed): "
                 + "; ".join(f"{k} n={v['n']}, primary {f(v['primary_value'], 4)}, CI {ci(v['primary_ci95'])}" for k, v in oc.items()) + ".")
        L.append("")
    L.append("### 5.3 Human-human ceiling in the literature")
    L.append("")
    L.append("`research/instruments/crosswalk.md` section 1 records no human-human agreement figure for ABC and none for "
             "BetterBench. The only published human ceiling on a comparable instrument is MedCheck's Fleiss kappa of 0.78 on 5 "
             "benchmarks, on MedCheck's own instrument; it does not transfer to ABC or BetterBench items. This script did not "
             "re-verify those papers; the statement rests on the crosswalk (its Reliability-statistic row: MedCheck Fleiss 0.78, ABC none reported, BetterBench none reported).")
    L.append("")
    return "\n".join(L)


def write_summary(md: str) -> None:
    txt = SUMMARY.read_text(encoding="utf-8")
    m = re.search(r"^## 5\. Like-for-like agreement on gold cells.*?(?=^## \d+\. |\Z)", txt, re.S | re.M)
    if m:
        txt = txt[:m.start()] + md.rstrip() + "\n" + txt[m.end():]
    else:
        txt = txt.rstrip() + "\n\n" + md.rstrip() + "\n"
    SUMMARY.write_text(txt, encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-summary", action="store_true")
    a = ap.parse_args()
    res = {s: analyse(s) for s in ("abc", "betterbench")}
    (OUT / "gold_coder_pair.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    md = markdown(res)
    print(md)
    if a.write_summary:
        write_summary(md)
        print(f"\nwrote section 5 to {SUMMARY}")


if __name__ == "__main__":
    main()
