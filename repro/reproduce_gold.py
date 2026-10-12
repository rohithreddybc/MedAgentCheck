"""Reproduce the like-for-like gold comparison from the benchmark-level contingency tables (repro/tables/).

The published expert scores of ABC and BetterBench and the coders' predictions on them are withheld. What reproduces
every kappa, interval and test is the cross-tabulation of two raters' levels per gold set, comparison and benchmark,
released as aggregate counts in repro/tables/gold_contingency.csv (no item ids; see repro/make_gold_tables.py).

Port of
  analysis/gold_coder_pair.py   coder pair versus coder-vs-expert statistics on the common cells (n, raw agreement,
                                Cohen kappa, ordinal alpha, primary statistic), the joint benchmark bootstrap
                                (2,000 resamples, seed 20261004) and the paired differences,
  analysis/revision_round2.py   gaps_for_set: percentile, BCa and Bayesian-bootstrap intervals, the exact cluster-swap
                                (sign-flip) permutation test over all 2^B benchmark swaps, the sign test,
  agentaudit/gold.py            agreement_stats on the original cell sets (per coder and resolved, NA bookkeeping,
                                confusion, weighted kappas, bootstrap CI over benchmarks),
  analysis/rq2_extras.py        over- and under-credit counts (rq2_gold_direction.csv).
Statistics come from the frozen agentaudit/stats.py.

Compared (assertions) with
  results/gold/{abc,betterbench}/agreement.json   scorer's agreement statistics (n, kappas, raw agreement, CI, confusion)
  results/analysis_out/gold_coder_pair.json       section 5 values
  results/analysis_out/revision_round2.json (gaps), rev2_gold_gaps.csv, rq2_gold.csv, rq2_gold_direction.csv
  analysis/out/RESULTS_SUMMARY.md                 sections 5.1, 5.2 (complete text) and 8.1 (table rows)

    python repro/reproduce_gold.py [--out repro/out] [--skip-swap]

The exact swap test enumerates 2^22 = 4,194,304 swaps for BetterBench (about a minute); --skip-swap omits it
(assertions on the swap p-values are then skipped).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, RESULTS, SEED, SUMMARY_MD, TABLES, Checker, read_json  # noqa: E402
from reproduce_audit import write_csv  # noqa: E402

from agentaudit.stats import alpha_ordinal, bootstrap_ci, cohen_kappa, raw_agreement, weighted_kappa, wilson  # noqa: E402

N_BAYES = 20000
# gold-set configuration (agentaudit.gold.SETS): comparison scale, primary statistic, positive levels
CFG = {"abc": {"levels": (0, 1), "primary": "cohen_kappa"},
       "betterbench": {"levels": (0, 1, 2, 3), "primary": "weighted_kappa_quadratic"}}
LABEL = {"abc": "ABC", "betterbench": "BetterBench"}


# ------------------------------------------------------------------ tables
def load_tables(path: Path = TABLES / "gold_contingency.csv") -> dict:
    """{(set, comparison, cell_set): {bench: {(row_level, col_level): count}}}; levels are int or "NA"."""
    out: dict = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            lv = lambda s: s if s == "NA" else int(s)  # noqa: E731
            key = (r["gold_set"], r["comparison"], r["cell_set"])
            out.setdefault(key, {}).setdefault(r["benchmark"], {})[(lv(r["row_level"]), lv(r["col_level"]))] = int(r["count"])
    return out


def pair_lists(tab: dict, bench_order: list[str] | None = None) -> dict[str, list[tuple]]:
    """bench -> list of (row_level, col_level) cells (one entry per counted cell), NA cells excluded."""
    out = {}
    for b in (bench_order if bench_order is not None else sorted(tab)):
        cells = []
        for (x, y), n in sorted(tab.get(b, {}).items(), key=str):
            if x != "NA" and y != "NA":
                cells += [(x, y)] * n
        out[b] = cells
    return out


def matrix(cells: list[tuple], levels: tuple) -> np.ndarray:
    idx = {v: i for i, v in enumerate(levels)}
    T = np.zeros((len(levels), len(levels)))
    for x, y in cells:
        T[idx[x], idx[y]] += 1
    return T


# ------------------------------------------------------------------ agreement_stats (agentaudit.gold, original cells)
def primary(cfg: dict, a: list, b: list):
    levels = list(cfg["levels"])
    return cohen_kappa(a, b) if cfg["primary"] == "cohen_kappa" else weighted_kappa(a, b, levels, "quadratic")


def agreement_stats_from_table(tab: dict, cfg: dict, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Port of agentaudit.gold.agreement_stats. Table rows = rater (pred), columns = expert (gold); NA kept as "NA"."""
    levels = list(cfg["levels"])
    all_cells = [(b, x, y, n) for b, d in tab.items() for (x, y), n in d.items()]  # x = pred, y = gold
    g_na = sum(n for _, x, y, n in all_cells if y == "NA")
    p_na = sum(n for _, x, y, n in all_cells if x == "NA" and y != "NA")
    both_na = sum(n for _, x, y, n in all_cells if y == "NA" and x == "NA")
    used = [(b, y, x) for b, x, y, n in all_cells if y != "NA" and x != "NA" for _ in range(n)]  # (bench, gold, pred)
    gs, ps = [u[1] for u in used], [u[2] for u in used]
    n = len(used)
    out: dict = {"n_cells": n, "n_gold_na": g_na, "n_pred_na_where_gold_scored": p_na, "n_both_na": both_na}
    agree = sum(1 for g, p in zip(gs, ps) if g == p)
    out["raw_agreement"] = {"agree": agree, "n": n, "rate": agree / n, "wilson95": list(wilson(agree, n))}
    out["cohen_kappa"] = cohen_kappa(gs, ps)
    out["majority_class_baseline_agreement"] = max(gs.count(v) for v in set(gs)) / n
    out["confusion"] = {str(g): {str(p): sum(1 for a, b in zip(gs, ps) if a == g and b == p) for p in levels}
                        for g in levels}
    if len(levels) > 2:
        out["weighted_kappa_quadratic"] = weighted_kappa(gs, ps, levels, "quadratic")
        out["weighted_kappa_linear"] = weighted_kappa(gs, ps, levels, "linear")
        w1 = sum(1 for g, p in zip(gs, ps) if abs(g - p) <= 1)
        out["within_one_level"] = {"hits": w1, "n": n, "rate": w1 / n, "wilson95": list(wilson(w1, n))}
    groups: dict[str, list] = {}
    for b, g, p in used:
        groups.setdefault(b, []).append((g, p))

    def stat(units):
        a, c = [u[0] for u in units], [u[1] for u in units]
        return cohen_kappa(a, c) if cfg["primary"] == "cohen_kappa" else weighted_kappa(a, c, levels, "quadratic")

    ci = bootstrap_ci(groups, stat, n_boot=n_boot, seed=seed)
    out["primary_statistic"] = cfg["primary"]
    out["primary_value"] = out.get(cfg["primary"])
    out["primary_ci95_bootstrap_over_benchmarks"] = list(ci) if ci else None
    return out


# ------------------------------------------------------------------ gold_coder_pair.py: pair statistics
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


def pctl(vals: list, alpha: float = 0.05):
    vals = sorted(v for v in vals if v is not None)
    if len(vals) < 20:
        return None
    return [vals[int((alpha / 2) * (len(vals) - 1))], vals[int((1 - alpha / 2) * (len(vals) - 1))]]


def analyse(set_name: str, T: dict) -> dict:
    """Port of gold_coder_pair.analyse from the tables. Returns the structure of gold_coder_pair.json[set]."""
    cfg = {**CFG[set_name]}
    levels = cfg["levels"]
    cs = pair_lists(T[(set_name, "codex_vs_sonnet", "common")])
    benches = sorted(cs)
    common = {
        "codex_vs_sonnet": cs,
        "codex_vs_expert": pair_lists(T[(set_name, "codex_vs_expert", "common")], benches),
        "sonnet_vs_expert": pair_lists(T[(set_name, "sonnet_vs_expert", "common")], benches),
    }
    flat = {k: [c for b in benches for c in v[b]] for k, v in common.items()}
    vec = lambda cells: ([c[0] for c in cells], [c[1] for c in cells])  # noqa: E731
    orig = {c: agreement_stats_from_table(T[(set_name, f"{c}_vs_expert", "original")], cfg)
            for c in ("codex", "sonnet", "resolved")}
    res_common = pair_lists(T[(set_name, "resolved_vs_expert", "common")])
    rc = [c for b in sorted(res_common) for c in res_common[b]]

    out: dict = {"set": set_name, "primary_statistic": cfg["primary"], "levels": list(levels),
                 "n_cells_common": len(flat["codex_vs_sonnet"]), "n_benchmarks": len(benches), "benchmarks": benches,
                 "n_cells_original": {c: orig[c]["n_cells"] for c in ("codex", "sonnet")},
                 "n_cells_resolved_original": orig["resolved"]["n_cells"],
                 "reproduced_agreement_json": True, "pairs": {}, "original_cells": {}}
    for name, cells in flat.items():
        out["pairs"][name] = stats_on(cfg, *vec(cells))
    # resolved on the common cells: stats_on(resolved, expert) with the expert in the second position
    out["pairs"]["resolved_vs_expert"] = stats_on(cfg, [c[0] for c in rc], [c[1] for c in rc])
    out["n_cells_resolved_common"] = len(rc)
    for k, st in orig.items():
        out["original_cells"][k] = {"n": st["n_cells"], "cohen_kappa": st["cohen_kappa"],
                                    "weighted_kappa_quadratic": st.get("weighted_kappa_quadratic"),
                                    "primary_value": st["primary_value"],
                                    "primary_ci95": st["primary_ci95_bootstrap_over_benchmarks"],
                                    "raw_agreement": st["raw_agreement"]["rate"]}
    # joint benchmark bootstrap on the common cells (same resample for every statistic)
    rng = random.Random(SEED)
    names = list(common)
    draws = {n: [] for n in names}
    diffs = {"pair_minus_codex_expert": [], "pair_minus_sonnet_expert": [], "pair_minus_mean_coder_expert": [],
             "sonnet_expert_minus_codex_expert": []}
    for _ in range(N_BOOT):
        picks = [benches[rng.randrange(len(benches))] for _k in range(len(benches))]
        v = {n: primary(cfg, *vec([c for b in picks for c in common[n][b]])) for n in names}
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
    out["agreement_json_values"] = {k: orig[k]["primary_value"] for k in ("codex", "sonnet", "resolved")}
    return out


# ------------------------------------------------------------------ revision_round2.py: gaps and swap test
def _weights(q: int, kind: str) -> np.ndarray:
    i = np.arange(q)
    if kind == "cohen_kappa":
        return np.eye(q)
    return 1.0 - ((i[:, None] - i[None, :]) / (q - 1)) ** 2


def kappa_tables(T: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Cohen (W = identity) or weighted kappa from count tables of shape (..., q, q)."""
    n = T.sum(axis=(-1, -2))
    p = T / n[..., None, None]
    r, c = p.sum(axis=-1), p.sum(axis=-2)
    po = (W * p).sum(axis=(-1, -2))
    pe = (W * (r[..., :, None] * c[..., None, :])).sum(axis=(-1, -2))
    with np.errstate(divide="ignore", invalid="ignore"):
        return (po - pe) / (1.0 - pe)


def gaps_for_set(set_name: str, T: dict, skip_swap: bool = False) -> dict:
    cfg = CFG[set_name]
    levels = cfg["levels"]
    q = len(levels)
    W = _weights(q, cfg["primary"])
    cs = pair_lists(T[(set_name, "codex_vs_sonnet", "common")])
    benches = sorted(cs)
    B = len(benches)
    lists = {"cs": cs, "cE": pair_lists(T[(set_name, "codex_vs_expert", "common")], benches),
             "sE": pair_lists(T[(set_name, "sonnet_vs_expert", "common")], benches)}
    M = {k: np.zeros((B, q, q)) for k in lists}
    raw = {k: np.zeros((B, 2)) for k in lists}
    for bi, b in enumerate(benches):
        for k in lists:
            cells = lists[k][b]
            M[k][bi] = matrix(cells, levels)
            raw[k][bi] = (sum(1 for u, v in cells if u == v), len(cells))
    gaps = {"pair_minus_codex_expert": (M["cs"], M["cE"]),
            "pair_minus_sonnet_expert": (np.transpose(M["cs"], (0, 2, 1)), M["sE"])}

    def gap_of(P, X, m):
        return float(kappa_tables(np.tensordot(m, P, 1), W) - kappa_tables(np.tensordot(m, X, 1), W))

    def mean_gap(m):
        kcs = kappa_tables(np.tensordot(m, M["cs"], 1), W)
        return float(kcs - (kappa_tables(np.tensordot(m, M["cE"], 1), W) + kappa_tables(np.tensordot(m, M["sE"], 1), W)) / 2)

    stat_fns = {k: (lambda m, P=P, X=X: gap_of(P, X, m)) for k, (P, X) in gaps.items()}
    stat_fns["pair_minus_mean_coder_expert"] = mean_gap
    ones = np.ones(B)
    point = {k: f(ones) for k, f in stat_fns.items()}
    rng = random.Random(SEED)
    draws = {k: [] for k in stat_fns}
    for _ in range(N_BOOT):
        m = np.zeros(B)
        for _k in range(B):
            m[rng.randrange(B)] += 1
        for k, f in stat_fns.items():
            v = f(m)
            if np.isfinite(v):
                draws[k].append(v)
    out = {"set": set_name, "n_cells": int(sum(M["cs"].sum(axis=(1, 2)))), "n_benchmarks": B,
           "primary_statistic": cfg["primary"], "gaps": {}}
    for k, f in stat_fns.items():
        v = sorted(draws[k])
        pct = [v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]]
        arr = np.array(v)
        z0 = sps.norm.ppf((np.sum(arr < point[k]) + 0.5 * np.sum(arr == point[k])) / len(arr))
        jack = []
        for j in range(B):
            mj = np.ones(B)
            mj[j] = 0
            jack.append(f(mj))
        jack = np.array(jack)
        dj = jack.mean() - jack
        acc = float((dj ** 3).sum() / (6.0 * ((dj ** 2).sum() ** 1.5))) if (dj ** 2).sum() > 0 else 0.0
        bca = []
        for al in (0.025, 0.975):
            zq = sps.norm.ppf(al)
            a1 = sps.norm.cdf(z0 + (z0 + zq) / (1 - acc * (z0 + zq)))
            bca.append(float(np.quantile(arr, min(max(a1, 0.0), 1.0))))
        brng = np.random.default_rng(SEED)
        wts = brng.dirichlet(np.ones(B), size=N_BAYES)
        bb = np.array([f(w) for w in wts])
        bb = bb[np.isfinite(bb)]
        out["gaps"][k] = {"point": point[k], "percentile_95": pct, "bca_95": bca, "bca_z0": float(z0), "bca_accel": acc,
                          "bayes_95": [float(np.quantile(bb, 0.025)), float(np.quantile(bb, 0.975))],
                          "bayes_share_positive": float((bb > 0).mean()), "n_boot": N_BOOT, "n_bayes": len(bb),
                          "boot_share_positive": float((arr > 0).mean())}

    def perm(P, X, chunk=1 << 18):
        S, Tt = P.sum(0), X.sum(0)
        diff = (X - P).reshape(B, q * q)  # swapping benchmark b moves X_b into the pair table and P_b out
        obs = float(kappa_tables(S, W) - kappa_tables(Tt, W))
        total, ge, two = 0, 0, 0
        for start in range(0, 1 << B, chunk):
            idx = np.arange(start, min(start + chunk, 1 << B), dtype=np.int64)
            bits = ((idx[:, None] >> np.arange(B)) & 1).astype(float)
            D = (bits @ diff).reshape(-1, q, q)
            gp = kappa_tables(S[None] + D, W) - kappa_tables(Tt[None] - D, W)
            total += len(idx)
            ge += int(np.sum(gp >= obs - 1e-12))
            two += int(np.sum(np.abs(gp) >= abs(obs) - 1e-12))
        return {"observed": obs, "n_swaps": total, "p_one_sided": ge / total, "p_two_sided": two / total}

    if not skip_swap:
        for k, (P, X) in gaps.items():
            out["gaps"][k]["permutation"] = perm(P, X)
    for k, (ka, kb) in {"pair_minus_codex_expert": ("cs", "cE"), "pair_minus_sonnet_expert": ("cs", "sE")}.items():
        dlt = raw[ka][:, 0] / raw[ka][:, 1] - raw[kb][:, 0] / raw[kb][:, 1]
        pos, neg, tie = int((dlt > 1e-12).sum()), int((dlt < -1e-12).sum()), int((np.abs(dlt) <= 1e-12).sum())
        p2 = float(sps.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else None
        out["gaps"][k]["sign_test"] = {"positive": pos, "negative": neg, "ties": tie, "p_two_sided": p2,
                                       "statistic": "per-benchmark raw agreement, pair minus coder-expert"}
    out["benchmarks"] = benches
    return out


# ------------------------------------------------------------------ over- and under-credit (rq2_extras.gold_direction)
def direction_rows(T: dict) -> list[dict]:
    rows = []
    for s in ("abc", "betterbench"):
        for coder, comp in (("codex", "codex_vs_expert"), ("sonnet", "sonnet_vs_expert"), ("RESOLVED", "resolved_vs_expert")):
            cells = [(x, y, n) for d in T[(s, comp, "original")].values() for (x, y), n in d.items()]  # x = pred, y = gold
            n_na = sum(n for x, y, n in cells if x == "NA" or y == "NA")
            used = [(x, y, n) for x, y, n in cells if x != "NA" and y != "NA"]
            n = sum(c for _, _, c in used)
            ag = sum(c for x, y, c in used if x == y)
            ov = sum(c for x, y, c in used if x > y)
            un = sum(c for x, y, c in used if x < y)
            w1 = sum(c for x, y, c in used if abs(x - y) <= 1)
            dis = ov + un
            lo, hi = wilson(ag, n)
            wl, wh = wilson(ov, dis) if dis else (None, None)
            rows.append({"set": LABEL[s], "coder": coder, "n_na_left_out": n_na, "n": n, "agree": ag, "agreement": ag / n,
                         "agree_lo": lo, "agree_hi": hi, "within_one": w1 / n, "n_over": ov, "n_under": un,
                         "share_over_of_disagree": ov / dis if dis else None, "over_lo": wl, "over_hi": wh})
    return rows


# ------------------------------------------------------------------ text as printed in RESULTS_SUMMARY.md
def f2(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def ci2(c, nd=2):
    return "n/a" if not c else f"[{c[0]:.{nd}f}, {c[1]:.{nd}f}]"


def pfmt(p):
    if p is None:
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def section5_sets(res: dict) -> list[str]:
    """Subsections 5.1 and 5.2 exactly as analysis/gold_coder_pair.markdown writes them."""
    L: list[str] = []
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
            prim = f"{f2(p['primary_value'])} {ci2(p.get('primary_ci95_bootstrap_over_benchmarks'))}" if k != "resolved_vs_expert" \
                else f2(p["primary_value"])
            L.append(f"| {lab} | {p['n']} | {prim} | {f2(p['cohen_kappa'])} | {f2(p['raw_agreement'])} | "
                     f"{f2(p['krippendorff_alpha_ordinal'])} |")
        L.append("")
        L.append("Differences in the primary statistic (coder pair minus coder-vs-expert), paired bootstrap over benchmarks:")
        L.append("")
        L.append("| Difference | Point | 95% CI | Share of resamples > 0 |")
        L.append("|---|---|---|---|")
        lab = {"pair_minus_codex_expert": "pair - codex/expert", "pair_minus_sonnet_expert": "pair - sonnet/expert",
               "pair_minus_mean_coder_expert": "pair - mean(coder/expert)",
               "sonnet_expert_minus_codex_expert": "sonnet/expert - codex/expert"}
        for k, v in r["differences_in_primary_statistic"].items():
            L.append(f"| {lab[k]} | {v['point']:+.2f} | {ci2(v['ci95_bootstrap_over_benchmarks'])} | {v['share_resamples_positive']:.3f} |")
        L.append("")
        oc = r["original_cells"]
        L.append("agreement.json values reproduced on the original cell sets (assertion passed): "
                 + "; ".join(f"{k} n={v['n']}, primary {f2(v['primary_value'], 4)}, CI {ci2(v['primary_ci95'])}" for k, v in oc.items()) + ".")
        L.append("")
    return L


GAPLAB = {"pair_minus_codex_expert": "pair minus OpenAI/expert", "pair_minus_sonnet_expert": "pair minus Claude/expert",
          "pair_minus_mean_coder_expert": "pair minus mean(coder/expert)"}


def section81_rows(gaps: dict) -> list[str]:
    L = []
    for s in ("abc", "betterbench"):
        r = gaps[s]
        L.append(f"**{LABEL[s]}** ({r['n_cells']} cells, {r['n_benchmarks']} benchmarks)")
        for k in ("pair_minus_codex_expert", "pair_minus_sonnet_expert", "pair_minus_mean_coder_expert"):
            g = r["gaps"][k]
            pm, sg = g.get("permutation"), g.get("sign_test")
            L.append(f"| {GAPLAB[k]} | {g['point']:+.2f} | {ci2(g['percentile_95'])} | {ci2(g['bca_95'])} | {ci2(g['bayes_95'])} | "
                     f"{g['bayes_share_positive']:.3f} | " +
                     (f"{pfmt(pm['p_one_sided'])} / {pfmt(pm['p_two_sided'])} ({pm['n_swaps']:,} swaps)" if pm else "n/a (not defined for the mean)") + " | " +
                     (f"{sg['positive']} / {sg['positive'] + sg['negative']} ({sg['ties']} ties); p {('= ' + pfmt(sg['p_two_sided'])) if sg['p_two_sided'] >= 0.001 else pfmt(sg['p_two_sided'])}" if sg else "n/a") + " |")
    return L


# ------------------------------------------------------------------ comparison helpers
def compare_json(ck: Checker, label: str, got, want, tol: float = 1e-9, skip: tuple = ()) -> None:
    """Every key of `want` must be present in `got` with an equal value (floats to `tol`)."""
    if isinstance(want, dict):
        for k, v in want.items():
            if k in skip:
                continue
            if not isinstance(got, dict) or k not in got:
                ck.fails.append(f"{label}/{k}: missing in reproduced output")
                ck.n += 1
                continue
            compare_json(ck, f"{label}/{k}", got[k], v, tol, skip)
    elif isinstance(want, list) and want and isinstance(want[0], (list, dict)):
        ck.eq(f"{label} (length)", len(got), len(want))
        for i, (a, b) in enumerate(zip(got, want)):
            compare_json(ck, f"{label}[{i}]", a, b, tol, skip)
    else:
        ck.eq(label, got, want, tol)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    ap.add_argument("--skip-swap", action="store_true", help="omit the exact swap test (2^22 swaps for BetterBench)")
    a = ap.parse_args()
    ck = Checker("like-for-like gold comparison (kappas, bootstrap intervals, swap test)")
    T = load_tables()

    # 1. agreement statistics on the original cell sets against the scorer's agreement.json (statistics only)
    pair_res = {s: analyse(s, T) for s in ("abc", "betterbench")}
    gold_rows = []
    for s in ("abc", "betterbench"):
        rec = read_json(RESULTS / "gold" / s / "agreement.json")
        cfg = CFG[s]
        for coder, key in (("codex", "codex"), ("sonnet", "sonnet"), ("RESOLVED", "resolved")):
            st = agreement_stats_from_table(T[(s, f"{key}_vs_expert", "original")], cfg)
            want = rec["resolved"] if coder == "RESOLVED" else rec["by_coder"][coder]
            compare_json(ck, f"agreement.json {s}/{coder}", st, want,
                         skip=("per_item_raw_agreement", "n_scored_items_without_gold", "status_counts", "fallback_cells"))
            ra = st["raw_agreement"]
            gold_rows.append({"set": s, "coder": coder, "n_cells": st["n_cells"], "n_gold_na": st["n_gold_na"],
                              "raw_agreement": ra["rate"], "raw_lo": ra["wilson95"][0], "raw_hi": ra["wilson95"][1],
                              "majority_baseline": st["majority_class_baseline_agreement"],
                              "cohen_kappa": st["cohen_kappa"], "weighted_kappa_quadratic": st.get("weighted_kappa_quadratic"),
                              "primary_statistic": st["primary_statistic"], "primary_value": st["primary_value"],
                              "primary_ci_lo": st["primary_ci95_bootstrap_over_benchmarks"][0],
                              "primary_ci_hi": st["primary_ci95_bootstrap_over_benchmarks"][1]})
    write_csv(a.out / "rq2_gold.csv", gold_rows)
    ck.csv_rows("rq2_gold.csv", gold_rows, ANALYSIS_OUT / "rq2_gold.csv", ["set", "coder"])
    direction = direction_rows(T)
    write_csv(a.out / "rq2_gold_direction.csv", direction)
    ck.csv_rows("rq2_gold_direction.csv", direction, ANALYSIS_OUT / "rq2_gold_direction.csv", ["set", "coder"])

    # 2. gold_coder_pair.json (section 5)
    ref5 = read_json(ANALYSIS_OUT / "gold_coder_pair.json")
    for s in ("abc", "betterbench"):
        compare_json(ck, f"gold_coder_pair.json/{s}", pair_res[s], ref5[s])
    (a.out).mkdir(parents=True, exist_ok=True)
    (a.out / "gold_coder_pair.json").write_text(json.dumps(pair_res, indent=2), encoding="utf-8")

    # 3. revision_round2.json (gaps): percentile, BCa, Bayesian bootstrap, swap test, sign test
    gaps = {s: gaps_for_set(s, T, a.skip_swap) for s in ("abc", "betterbench")}
    ref2 = read_json(ANALYSIS_OUT / "revision_round2.json")["gaps"]
    for s in ("abc", "betterbench"):
        compare_json(ck, f"revision_round2.json/gaps/{s}", gaps[s], ref2[s],
                     skip=("permutation",) if a.skip_swap else ())
        # the gap intervals of round 2 are the intervals of section 5 (asserted by the authors' script as well)
        for k in ("pair_minus_codex_expert", "pair_minus_sonnet_expert", "pair_minus_mean_coder_expert"):
            ck.eq(f"{s}/{k}: round-2 percentile CI == section-5 CI", gaps[s]["gaps"][k]["percentile_95"],
                  pair_res[s]["differences_in_primary_statistic"][k]["ci95_bootstrap_over_benchmarks"], 1e-9)
    rows = []
    for s, r in gaps.items():
        for k, g in r["gaps"].items():
            rows.append({"set": s, "gap": k, "n_cells": r["n_cells"], "n_benchmarks": r["n_benchmarks"], "point": g["point"],
                         "pct_lo": g["percentile_95"][0], "pct_hi": g["percentile_95"][1],
                         "bca_lo": g["bca_95"][0], "bca_hi": g["bca_95"][1],
                         "bayes_lo": g["bayes_95"][0], "bayes_hi": g["bayes_95"][1], "bayes_share_positive": g["bayes_share_positive"],
                         "perm_p_one": g.get("permutation", {}).get("p_one_sided"),
                         "perm_p_two": g.get("permutation", {}).get("p_two_sided"),
                         "perm_n_swaps": g.get("permutation", {}).get("n_swaps"),
                         "sign_pos": g.get("sign_test", {}).get("positive"), "sign_neg": g.get("sign_test", {}).get("negative"),
                         "sign_ties": g.get("sign_test", {}).get("ties"), "sign_p_two": g.get("sign_test", {}).get("p_two_sided")})
    write_csv(a.out / "rev2_gold_gaps.csv", rows)
    if not a.skip_swap:
        ck.csv_rows("rev2_gold_gaps.csv", rows, ANALYSIS_OUT / "rev2_gold_gaps.csv", ["set", "gap"])
    (a.out / "revision_round2_gaps.json").write_text(json.dumps(gaps, indent=2, default=float), encoding="utf-8")

    # 4. the text printed in RESULTS_SUMMARY.md
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    sec5 = "\n".join(section5_sets(pair_res)).rstrip()
    ck.in_text("RESULTS_SUMMARY.md sections 5.1 and 5.2 (complete text)", sec5, txt)
    for line in section81_rows(gaps):
        if a.skip_swap and "swaps" in line:
            continue
        ck.in_text("RESULTS_SUMMARY.md section 8.1", line, txt)
    ck.done()

    for s in ("abc", "betterbench"):
        p, d = pair_res[s]["pairs"], pair_res[s]["differences_in_primary_statistic"]
        print(f"{LABEL[s]}: pair {p['codex_vs_sonnet']['primary_value']:.2f}, codex/expert {p['codex_vs_expert']['primary_value']:.2f}, "
              f"sonnet/expert {p['sonnet_vs_expert']['primary_value']:.2f}, resolved/expert {p['resolved_vs_expert']['primary_value']:.2f}")
        for k in ("pair_minus_codex_expert", "pair_minus_sonnet_expert"):
            g = gaps[s]["gaps"][k]
            sw = g.get("permutation")
            print(f"  {k}: {g['point']:+.2f} {ci2(g['percentile_95'])}; swap p two-sided "
                  f"{pfmt(sw['p_two_sided']) if sw else 'skipped'}; sign test {g['sign_test']['positive']}/"
                  f"{g['sign_test']['positive'] + g['sign_test']['negative']}")


if __name__ == "__main__":
    main()
