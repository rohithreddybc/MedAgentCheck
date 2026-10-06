"""Round-2 revision analyses (simulated reviews, round 2: R1 C3, C4; R2 conditions M3, M5; R3 new point 3).

Everything is computed from stored outputs; nothing is rescored and no model is called. Seed 20261004 throughout.
Reuses analysis/gold_coder_pair.py (gold cells), analysis/rq1_rq2.py (prevalence, module summary, alpha table) and the
scorer package (agentaudit.stats).

Blocks
  A GAPS      like-for-like gaps of Table 3 (coder pair minus coder against expert) with, beside the 9- and
              22-benchmark percentile interval: (i) an exact cluster-swap permutation test (the expert labels and the
              other coder's labels are exchanged benchmark by benchmark; all 2^9 and 2^22 swaps are enumerated),
              (ii) an exact sign test on per-benchmark raw-agreement differences, (iii) a BCa interval (jackknife over
              benchmarks), (iv) a Bayesian-bootstrap interval (Dirichlet(1) weights on benchmarks).
  B PERTURB   Claude Sonnet perturbation rates of Table 5 with packet-cluster (variant-level, 39 clusters) and
              item-cluster (25 clusters) percentile bootstrap intervals beside the Wilson intervals. OpenAI-coder and
              resolved rows are not touched (their runs are not final).
  C CAP       RQ1 shares and cross-family alpha for the 14 coded benchmarks whose packet was cut by the 150,000-token cap
              and the 30 that were not; capped C13 and A4 cells; MedAgentBench v1/v2 merge.
  D A3A8      the audit's resolved A3 and A8 levels, raw coder scores and quotes for AgentClinic, RadA-BenchPlat and
              Synthetic Hospital, next to the rerun findings.
  E ALPHA     A7 and C11 alpha and prevalence, and the list of items below alpha 0.5.

Cap flags: audit/packets/*/manifest.json carries no cap flag (the cap is applied at scoring time); the flags are
audit/transport/prompts/<bench>/meta.json (tokens_before_cap, n_dropped_chunks) and audit/BUILD_LOG.md.

Run from the project root:
    python analysis/revision_round2.py                  # computes, writes CSV/JSON/tables
    python analysis/revision_round2.py --write-summary  # also (re)writes section 8 of analysis/out/RESULTS_SUMMARY.md
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, ROOT, SEED, TABLES, booktabs, tex_escape, write_csv  # noqa: E402

import gold_coder_pair as GP  # noqa: E402
import rq1_rq2 as R  # noqa: E402
from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402
from agentaudit.stats import wilson  # noqa: E402

N_BOOT = 2000
N_BAYES = 20000
AUDIT = ROOT / "audit"
SUMMARY = OUT / "RESULTS_SUMMARY.md"
CMD = "python analysis/revision_round2.py --write-summary"


# ------------------------------------------------------------------ kappa from count tables
def _weights(q: int, kind: str) -> np.ndarray:
    i = np.arange(q)
    if kind == "cohen_kappa":
        return np.eye(q)
    return 1.0 - ((i[:, None] - i[None, :]) / (q - 1)) ** 2


def kappa_tables(T: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Cohen (W = identity) or weighted kappa from count tables of shape (..., q, q). Returns shape (...)."""
    n = T.sum(axis=(-1, -2))
    p = T / n[..., None, None]
    r, c = p.sum(axis=-1), p.sum(axis=-2)
    po = (W * p).sum(axis=(-1, -2))
    pe = (W * (r[..., :, None] * c[..., None, :])).sum(axis=(-1, -2))
    with np.errstate(divide="ignore", invalid="ignore"):
        return (po - pe) / (1.0 - pe)


def _table(cfg: dict, a: list, b: list) -> np.ndarray:
    lv = list(cfg["levels"])
    idx = {v: i for i, v in enumerate(lv)}
    T = np.zeros((len(lv), len(lv)))
    for x, y in zip(a, b):
        T[idx[x], idx[y]] += 1
    return T


# ------------------------------------------------------------------ A: gaps
def gaps_for_set(set_name: str) -> dict:
    d = GP.load_set(set_name)
    cfg, gold, preds, common = d["cfg"], d["gold"], d["preds"], d["common"]
    q = len(cfg["levels"])
    W = _weights(q, cfg["primary"])
    benches = sorted({b for b, _ in common})
    B = len(benches)
    cx = {c: preds["codex"][c]["effective"] for c in common}
    sn = {c: preds["sonnet"][c]["effective"] for c in common}
    g = {c: gold[c] for c in common}
    M = {k: np.zeros((B, q, q)) for k in ("cs", "cE", "sE")}
    raw = {k: np.zeros((B, 2)) for k in ("cs", "cE", "sE")}  # agreements, n
    for bi, b in enumerate(benches):
        cells = [c for c in common if c[0] == b]
        for k, (x, y) in {"cs": (cx, sn), "cE": (cx, g), "sE": (sn, g)}.items():
            xs, ys = [x[c] for c in cells], [y[c] for c in cells]
            M[k][bi] = _table(cfg, xs, ys)
            raw[k][bi] = (sum(1 for u, v in zip(xs, ys) if u == v), len(cells))
    # (1) validate the table kappa against the scorer's own statistic on all common cells
    for k, (x, y) in {"cs": (cx, sn), "cE": (cx, g), "sE": (sn, g)}.items():
        ref = GP.primary(cfg, [x[c] for c in common], [y[c] for c in common])
        mine = float(kappa_tables(M[k].sum(0), W))
        assert abs(ref - mine) < 1e-9, (set_name, k, ref, mine)

    # gap definitions: name -> (P matrices, X matrices); both oriented (anchor coder x other)
    gaps = {
        "pair_minus_codex_expert": (M["cs"], M["cE"]),                         # anchor = codex
        "pair_minus_sonnet_expert": (np.transpose(M["cs"], (0, 2, 1)), M["sE"]),  # anchor = sonnet
    }

    def gap_of(P, X, m):
        return float(kappa_tables(np.tensordot(m, P, 1), W) - kappa_tables(np.tensordot(m, X, 1), W))

    def mean_gap(m):
        kcs = kappa_tables(np.tensordot(m, M["cs"], 1), W)
        return float(kcs - (kappa_tables(np.tensordot(m, M["cE"], 1), W) + kappa_tables(np.tensordot(m, M["sE"], 1), W)) / 2)

    stat_fns = {k: (lambda m, P=P, X=X: gap_of(P, X, m)) for k, (P, X) in gaps.items()}
    stat_fns["pair_minus_mean_coder_expert"] = mean_gap
    ones = np.ones(B)
    point = {k: f(ones) for k, f in stat_fns.items()}

    # (2) percentile bootstrap, same draws as analysis/gold_coder_pair.py (asserted against section 5)
    rng = random.Random(SEED)
    draws = {k: [] for k in stat_fns}
    mult_all = []
    for _ in range(N_BOOT):
        m = np.zeros(B)
        for _k in range(B):
            m[rng.randrange(B)] += 1
        mult_all.append(m)
        for k, f in stat_fns.items():
            v = f(m)
            if np.isfinite(v):
                draws[k].append(v)
    out = {"set": set_name, "n_cells": len(common), "n_benchmarks": B, "primary_statistic": cfg["primary"], "gaps": {}}
    ref5 = GP.analyse(set_name)["differences_in_primary_statistic"]
    ref_key = {"pair_minus_codex_expert": "pair_minus_codex_expert", "pair_minus_sonnet_expert": "pair_minus_sonnet_expert",
               "pair_minus_mean_coder_expert": "pair_minus_mean_coder_expert"}
    for k, f in stat_fns.items():
        v = sorted(draws[k])
        pct = [v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]]
        r5 = ref5[ref_key[k]]
        assert abs(point[k] - r5["point"]) < 1e-9, (k, point[k], r5["point"])
        assert all(abs(a - b) < 1e-9 for a, b in zip(pct, r5["ci95_bootstrap_over_benchmarks"])), (k, pct, r5)
        # BCa
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
        # Bayesian bootstrap
        brng = np.random.default_rng(SEED)
        wts = brng.dirichlet(np.ones(B), size=N_BAYES)
        bb = np.array([f(w) for w in wts])
        bb = bb[np.isfinite(bb)]
        out["gaps"][k] = {"point": point[k], "percentile_95": pct, "bca_95": bca, "bca_z0": float(z0), "bca_accel": acc,
                          "bayes_95": [float(np.quantile(bb, 0.025)), float(np.quantile(bb, 0.975))],
                          "bayes_share_positive": float((bb > 0).mean()), "n_boot": N_BOOT, "n_bayes": len(bb),
                          "boot_share_positive": float((arr > 0).mean())}

    # (3) exact cluster-swap permutation test (coder-specific gaps)
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

    for k, (P, X) in gaps.items():
        out["gaps"][k]["permutation"] = perm(P, X)

    # (4) sign test on per-benchmark raw agreement differences
    for k, (ka, kb) in {"pair_minus_codex_expert": ("cs", "cE"), "pair_minus_sonnet_expert": ("cs", "sE")}.items():
        dlt = raw[ka][:, 0] / raw[ka][:, 1] - raw[kb][:, 0] / raw[kb][:, 1]
        pos, neg, tie = int((dlt > 1e-12).sum()), int((dlt < -1e-12).sum()), int((np.abs(dlt) <= 1e-12).sum())
        p2 = float(sps.binomtest(pos, pos + neg, 0.5).pvalue) if pos + neg else None
        out["gaps"][k]["sign_test"] = {"positive": pos, "negative": neg, "ties": tie, "p_two_sided": p2,
                                       "statistic": "per-benchmark raw agreement, pair minus coder-expert"}
    out["benchmarks"] = benches
    return out


# ------------------------------------------------------------------ B: perturbation clusters
def _cluster_block(rows: list[dict]) -> dict:
    pos_t, neg_t = R.POSITIVE, R.NEGATIVE
    metrics = {
        "sensitivity": (pos_t, lambda r: bool(r["ok"])),
        "inject": (("inject",), lambda r: bool(r["ok"])),
        "buried": (("buried",), lambda r: bool(r["ok"])),
        "paraphrase": (("paraphrase",), lambda r: bool(r["ok"])),
        "specificity": (neg_t, lambda r: bool(r["ok"])),
        "deletion": (("deletion",), lambda r: bool(r["ok"])),
        "decoy": (("decoy",), lambda r: bool(r["ok"])),
    }
    out = {"n_cells": len(rows), "clusters": {}}
    for ckey in ("variant_id", "item"):
        groups: dict[str, list] = {}
        for r in rows:
            groups.setdefault(r[ckey], []).append(r)
        keys = sorted(groups)
        rng = random.Random(SEED)
        vals = {m: [] for m in metrics}
        for _ in range(N_BOOT):
            cells = []
            for _k in range(len(keys)):
                cells.extend(groups[keys[rng.randrange(len(keys))]])
            for m, (vt, ok) in metrics.items():
                sel = [r for r in cells if r["vtype"] in vt]
                if sel:
                    vals[m].append(sum(ok(r) for r in sel) / len(sel))
        res = {}
        for m, (vt, ok) in metrics.items():
            sel = [r for r in rows if r["vtype"] in vt]
            k, n = sum(ok(r) for r in sel), len(sel)
            w = wilson(k, n)
            v = sorted(vals[m])
            ci = [v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]]
            # design effect from the cluster means (one-way ANOVA ICC on cell indicators)
            cl = {}
            for r in sel:
                cl.setdefault(r[ckey], []).append(1.0 if ok(r) else 0.0)
            res[m] = {"hits": k, "n": n, "rate": k / n, "wilson": list(w), "cluster_boot": ci,
                      "clusters_with_cells": len(cl), "width_ratio": (ci[1] - ci[0]) / (w[1] - w[0])}
        out["clusters"][ckey] = res
    return out


def perturb_clusters() -> dict:
    """Sonnet (the original block, kept under the top-level keys) and, since the OpenAI coder and the resolved level were
    completed (2026-10-06), the same block for codex and RESOLVED under ``by_coder``. Same resampling, same seed."""
    d = json.loads((AUDIT / "perturb" / "perturb" / "summary.json").read_text(encoding="utf-8"))
    pos_t, neg_t = R.POSITIVE, R.NEGATIVE
    rows = [r for r in d["rows"] if r["coder"] == "sonnet"]
    assert sum(r["ok"] for r in rows if r["vtype"] in pos_t) == 527 and len([r for r in rows if r["vtype"] in pos_t]) == 542
    assert sum(r["ok"] for r in rows if r["vtype"] in neg_t) == 117 and len([r for r in rows if r["vtype"] in neg_t]) == 290
    out = _cluster_block(rows)
    out["by_coder"] = {}
    for c in ("codex", "sonnet", "RESOLVED"):
        rc = [r for r in d["rows"] if r["coder"] == c]
        assert len(rc) == 832, (c, len(rc))
        out["by_coder"][c] = out if c == "sonnet" else _cluster_block(rc)
    out["by_coder"]["sonnet"] = {"n_cells": out["n_cells"], "clusters": out["clusters"]}
    return out


# ------------------------------------------------------------------ C: cap strata and version merge
def cap_flags() -> dict[str, dict]:
    out = {}
    for p in sorted((AUDIT / "transport" / "prompts").glob("*/meta.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        out[m["bench"]] = {"tokens_before_cap": m["tokens_before_cap"], "tokens_sent": m["tokens_sent"],
                           "n_dropped_chunks": m["n_dropped_chunks"], "over_cap": m["over_cap"],
                           "capped": bool(m["n_dropped_chunks"] or m["tokens_before_cap"] > m["cap_tokens"])}
    return out


def _mod(resolved: dict) -> dict:
    return {r["module"]: r for r in R.module_summary(resolved, "final", N_BOOT)}


def strat_boot_diff(res_a: dict, res_b: dict, items: list[str], key: str = "rep") -> list[float]:
    """Difference (a minus b) in a module's pooled share with independent benchmark resampling within each stratum."""
    def units(res):
        g = {}
        for b, cells in res.items():
            us = []
            for i in items:
                if i in cells and R.level_of(cells[i]["final"]) is not None:
                    x = R.level_of(cells[i]["final"])
                    us.append(x >= 1 if key == "rep" else x == 2)
            if us:
                g[b] = us
        return g
    ga, gb = units(res_a), units(res_b)
    ka, kb = sorted(ga), sorted(gb)
    rng = random.Random(SEED)
    vals = []
    for _ in range(N_BOOT):
        ua = [u for _k in range(len(ka)) for u in ga[ka[rng.randrange(len(ka))]]]
        ub = [u for _k in range(len(kb)) for u in gb[kb[rng.randrange(len(kb))]]]
        vals.append(sum(ua) / len(ua) - sum(ub) / len(ub))
    vals.sort()
    pa = [u for us in ga.values() for u in us]
    pb = [u for us in gb.values() for u in us]
    return [sum(pa) / len(pa) - sum(pb) / len(pb), vals[int(0.025 * (len(vals) - 1))], vals[int(0.975 * (len(vals) - 1))]]


def cap_block() -> dict:
    resolved = R.load_resolved(AUDIT)
    flags = cap_flags()
    capped = sorted(b for b in resolved if flags[b]["capped"])
    uncapped = sorted(b for b in resolved if not flags[b]["capped"])
    items = load_items()
    out = {"capped": capped, "uncapped": uncapped, "n_capped": len(capped), "n_uncapped": len(uncapped),
           "flags": {b: flags[b] for b in capped}, "healthcraft": flags.get("healthcraft")}
    rc = {b: resolved[b] for b in capped}
    ru = {b: resolved[b] for b in uncapped}
    out["modules"] = {"capped": _mod(rc), "uncapped": _mod(ru), "all": _mod(resolved)}
    core = [i for i in ITEM_ORDER if items[i].module == "core"]
    agent = [i for i in ITEM_ORDER if items[i].module == "agent"]
    out["diff"] = {}
    for mod, ids in (("core", core), ("agent", agent)):
        for key in ("rep", "full"):
            out["diff"][f"{mod}_{key}"] = strat_boot_diff(rc, ru, ids, key)
    # alpha per stratum (all coders = cross-family pair here), overall
    def alpha_overall(bs):
        rows = [r for r in R.alpha_table(AUDIT, bs, N_BOOT) if r["kind"] == "all_coders"]
        return {"overall": [r for r in rows if r["scope"] == "overall"][0],
                "items": {r["item"]: r for r in rows if r["scope"] == "item"}}
    out["alpha"] = {"capped": alpha_overall(capped), "uncapped": alpha_overall(uncapped)}
    # per item shares in each stratum
    pi = {}
    for it in ITEM_ORDER:
        row = {}
        for nm, rr in (("capped", rc), ("uncapped", ru)):
            lv = [R.level_of(c[it]["final"]) for c in rr.values() if it in c]
            app = [x for x in lv if x is not None]
            row[nm] = {"n": len(app), "rep": sum(x >= 1 for x in app) / len(app) if app else None,
                       "full": sum(x == 2 for x in app) / len(app) if app else None}
        pi[it] = row
    out["items"] = pi
    # capped C13 and A4 cells
    c13a4 = {}
    for it in ("C13", "A4"):
        zero = [b for b in capped if resolved[b][it]["final"] == 0]
        stat = {}
        for b in capped:
            stat[resolved[b][it]["status"]] = stat.get(resolved[b][it]["status"], 0) + 1
        c13a4[it] = {"cells_in_capped_packets": len(capped), "resolved_zero": len(zero), "zero_benchmarks": zero,
                     "status_counts": stat,
                     "uncapped_zero": sum(1 for b in uncapped if resolved[b][it]["final"] == 0)}
    out["c13_a4"] = c13a4

    # cap-aware module shares: capped C13 and A4 cells that resolved to 0 are treated as not established and dropped
    def cap_aware(res: dict) -> dict:
        mod = {}
        for m, ids in (("core", core), ("agent", agent)):
            k = kf = n = 0
            for b, cells in res.items():
                for i in ids:
                    if i not in cells or R.level_of(cells[i]["final"]) is None:
                        continue
                    x = R.level_of(cells[i]["final"])
                    if flags[b]["capped"] and i in ("C13", "A4") and x == 0:
                        continue
                    n += 1
                    k += x >= 1
                    kf += x == 2
            mod[m] = {"n": n, "rep": k / n, "full": kf / n}
        return mod
    out["cap_aware"] = cap_aware(resolved)

    # version merge: MedAgentBench v1 and v2 as one unit (higher of the two resolved levels per item; NA only if both NA)
    v1, v2 = "medagentbench-v1", "medagentbench-v2"
    merged_cells = {}
    for it in resolved[v1]:
        a, b2 = R.level_of(resolved[v1][it]["final"]), R.level_of(resolved[v2][it]["final"])
        nums = [x for x in (a, b2) if x is not None]
        merged_cells[it] = {"final": max(nums) if nums else "NA", "majority_final": max(nums) if nums else "NA"}
    variants = {"all 44 (v1 and v2 separate)": resolved,
                "v2 dropped (v1 kept)": {b: c for b, c in resolved.items() if b != v2},
                "v1 dropped (v2 kept)": {b: c for b, c in resolved.items() if b != v1},
                "merged (higher level per item)": {**{b: c for b, c in resolved.items() if b not in (v1, v2)},
                                                   "medagentbench-merged": merged_cells}}
    out["merge"] = {k: {"n_benchmarks": len(v), **{m: {kk: r[kk] for kk in ("n_applicable_cells", "share_reported", "share_full",
                                                                           "reported_boot_lo", "reported_boot_hi",
                                                                           "full_boot_lo", "full_boot_hi")}
                                                     for m, r in _mod(v).items()}} for k, v in variants.items()}
    return out


# ------------------------------------------------------------------ D: A3 and A8 beside the reruns
RERUN = {"agentclinic": "AgentClinic", "rada-benchplat": "RadA-BenchPlat", "synthetic-hospital": "Synthetic Hospital"}


def a3a8_block() -> dict:
    flags = cap_flags()
    resolved = R.load_resolved(AUDIT)
    out = {}
    for b in RERUN:
        cells = {}
        for it in ("A3", "A8"):
            c = resolved[b][it]
            voters = {}
            for co in ("codex", "sonnet"):
                p = json.loads((AUDIT / "coding" / b / it / f"{co}.json").read_text(encoding="utf-8"))["parsed"]
                v = json.loads((AUDIT / "verified" / b / it / f"{co}.json").read_text(encoding="utf-8"))
                voters[co] = {"raw": c["votes"][co]["raw"], "effective": c["votes"][co]["effective"],
                              "quotes": [q["text"] for q in p["quotes"]], "rationale": p["rationale"],
                              "quotes_verified": v.get("quotes_verified") if isinstance(v, dict) else None}
            cells[it] = {"resolved": c["final"], "status": c["status"], "fallback": c["fallback"], "votes": voters}
        out[b] = {"name": RERUN[b], "cap": {"tokens_before_cap": flags[b]["tokens_before_cap"],
                                            "n_dropped_chunks": flags[b]["n_dropped_chunks"], "capped": flags[b]["capped"]},
                  "cells": cells}
    # rerun findings, read from the stored result files
    div = {r["bench"]: {} for r in GP_rows(OUT / "rq3_divergence.csv")}
    for r in GP_rows(OUT / "rq3_divergence.csv"):
        div[r["bench"]][r["condition"]] = {"divergent": int(r["divergent_n"]), "unstable": int(r["unstable_n"]),
                                           "svda": int(r["same_verdict_diff_actions_n"])}
    val = {}
    for r in GP_rows(OUT / "rev_rq3_validity.csv"):
        val.setdefault(r["bench"], {})[r["condition"]] = {"invalid": int(r["n_invalid"]), "clean_groups": int(r["groups_clean"])}
    gs = {}
    for r in GP_rows(OUT / "rq3_grader_state.csv"):
        gs[r["condition"]] = {"episodes": int(r["n_episodes"]), "agree": int(r["agree"]), "disagree": int(r["disagree"]),
                              "neutral_set_required": int(r["neutral_set_required"]),
                              "no_submission": int(r["no_submission"])}
    jr = GP_rows(OUT / "rq3_judge_rerun.csv")
    judge = {"transcripts": len(jr), "unstable": sum(1 for r in jr if r["all_identical"] != "True"),
             "differ_from_recorded": sum(1 for r in jr if r["all_match_recorded"] != "True")}
    out["rerun"] = {"divergence": {"AgentClinic": div["AgentClinic"], "RadA-BenchPlat": div["RadABench"],
                                   "Synthetic Hospital": div["synthetic_hospital"]},
                    "validity": {"AgentClinic": val["AgentClinic"], "RadA-BenchPlat": val["RadABench"],
                                 "Synthetic Hospital": val["synthetic_hospital"]},
                    "grader_vs_state_synthetic_hospital": gs, "judge_only_agentclinic": judge}
    return out


def GP_rows(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ E: alpha for A7 and C11
def alpha_block() -> dict:
    rows = GP_rows(OUT / "rq2_alpha.csv")
    al = {r["item"]: r for r in rows if r["kind"] == "all_coders" and r["scope"] == "item"}
    prev = {r["item"]: r for r in GP_rows(OUT / "rq1_prevalence.csv") if r["rule"] == "resolved"}
    out = {"items": {}}
    for it in ITEM_ORDER:
        a = al[it]
        out["items"][it] = {"alpha": float(a["alpha"]), "lo": float(a["ci_lo"]), "hi": float(a["ci_hi"]),
                            "n_applicable": int(prev[it]["n_applicable"]), "reported": float(prev[it]["share_reported"]),
                            "full": float(prev[it]["share_full"])}
    out["below_half"] = [it for it in ITEM_ORDER if out["items"][it]["alpha"] < 0.5]
    out["at_least_point_eight"] = [it for it in ITEM_ORDER if out["items"][it]["alpha"] >= 0.8]
    return out


# ------------------------------------------------------------------ compute and write
def compute() -> dict:
    return {"gaps": {s: gaps_for_set(s) for s in ("abc", "betterbench")}, "perturb": perturb_clusters(),
            "cap": cap_block(), "a3a8": a3a8_block(), "alpha": alpha_block()}


def f2(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def ci2(c, nd=2):
    return "n/a" if not c else f"[{c[0]:.{nd}f}, {c[1]:.{nd}f}]"


def pfmt(p):
    if p is None:
        return "n/a"
    return "<0.001" if p < 0.001 else f"{p:.3f}"


GAPLAB = {"pair_minus_codex_expert": "pair minus OpenAI/expert", "pair_minus_sonnet_expert": "pair minus Claude/expert",
          "pair_minus_mean_coder_expert": "pair minus mean(coder/expert)"}


def write_outputs(res: dict) -> None:
    rows = []
    for s, r in res["gaps"].items():
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
    write_csv(OUT / "rev2_gold_gaps.csv", rows)
    prow = []
    for coder, blk in res["perturb"]["by_coder"].items():
      for ck, d in blk["clusters"].items():
        for m, v in d.items():
            prow.append({"coder": coder, "cluster": ck, "metric": m, "hits": v["hits"], "n": v["n"], "rate": v["rate"],
                         "wilson_lo": v["wilson"][0], "wilson_hi": v["wilson"][1], "cluster_lo": v["cluster_boot"][0],
                         "cluster_hi": v["cluster_boot"][1], "clusters_with_cells": v["clusters_with_cells"],
                         "width_ratio": v["width_ratio"]})
    write_csv(OUT / "rev2_perturb_clusters.csv", prow)
    cap = res["cap"]
    crow = []
    for it in ITEM_ORDER:
        r = cap["items"][it]
        crow.append({"item": it, "capped_n": r["capped"]["n"], "capped_rep": r["capped"]["rep"], "capped_full": r["capped"]["full"],
                     "uncapped_n": r["uncapped"]["n"], "uncapped_rep": r["uncapped"]["rep"], "uncapped_full": r["uncapped"]["full"]})
    write_csv(OUT / "rev2_cap_items.csv", crow)
    (OUT / "revision_round2.json").write_text(json.dumps(res, indent=2, default=float), encoding="utf-8")
    write_tables(res)


def write_tables(res: dict) -> None:
    """Small tabulars for the paper and supplement (bare booktabs, \\input)."""
    # Table: gold gaps, sensitivity of the interval and tests
    hdr = ["Set", "Gap", "Point", "Percentile", "BCa", "Bayesian", "Swap $p$", "Sign test"]
    rows = []
    for s, lab in (("abc", "ABC"), ("betterbench", "BetterBench")):
        r = res["gaps"][s]
        for k in ("pair_minus_codex_expert", "pair_minus_sonnet_expert", "pair_minus_mean_coder_expert"):
            g = r["gaps"][k]
            perm = g.get("permutation")
            sg = g.get("sign_test")
            rows.append([lab if k == "pair_minus_codex_expert" else "", GAPLAB[k].replace("minus", "$-$"),
                         f"{g['point']:+.2f}", ci2(g["percentile_95"]), ci2(g["bca_95"]), ci2(g["bayes_95"]),
                         ("$" + pfmt(perm["p_two_sided"]).replace("<", "<") + "$") if perm else "--",
                         f"{sg['positive']}/{sg['positive'] + sg['negative']}" if sg else "--"])
    (TABLES / "rev2_gaps.tex").write_text(
        booktabs("@{}llcccccc@{}", hdr, rows, "Generated by analysis/revision_round2.py. Do not edit by hand."),
        encoding="utf-8", newline="\n")
    # Table: perturbation cluster intervals (all three coder rows)
    hdr = ["Coder", "Rate", "Cells", "Percent", "Wilson", "Variant clusters", "Item clusters"]
    names = {"sensitivity": "Sensitivity", "inject": "Inject", "buried": "Buried", "paraphrase": "Paraphrase",
             "specificity": "Frozen specificity", "deletion": "Deletion", "decoy": "Decoy"}
    labels = {"codex": "OpenAI (gpt-5.5)", "sonnet": "Claude Sonnet", "RESOLVED": "Resolved"}
    rows = []
    pc = lambda c: f"[{100 * c[0]:.0f}, {100 * c[1]:.0f}]"
    for c in ("codex", "sonnet", "RESOLVED"):
        cl = res["perturb"]["by_coder"][c]["clusters"]
        for m in names:
            v, it = cl["variant_id"][m], cl["item"][m]
            rows.append([labels[c] if m == "sensitivity" else "", names[m], f"{v['hits']}/{v['n']}", f"{100 * v['rate']:.1f}",
                         pc(v["wilson"]), pc(v["cluster_boot"]), pc(it["cluster_boot"])])
    (TABLES / "rev2_perturb_clusters.tex").write_text(
        booktabs("@{}llccccc@{}", hdr, rows, "Generated by analysis/revision_round2.py. OpenAI coder, Claude Sonnet and the resolved level."),
        encoding="utf-8", newline="\n")
    # Table: A3 and A8 audit scores beside the rerun findings (main text)
    a3 = res["a3a8"]
    rr = a3["rerun"]
    hdr = ["Benchmark", "A3", "A8", "Divergent", "Unstable"]
    rows = []
    for b, nm in RERUN.items():
        c = a3[b]["cells"]

        def cell(it):
            x = c[it]
            return f"{x['resolved']} ({x['votes']['codex']['raw']}/{x['votes']['sonnet']['raw']})"
        dv = rr["divergence"][nm]
        rows.append([nm + (r"$^{\dagger}$" if a3[b]["cap"]["capped"] else ""), cell("A3"), cell("A8"),
                     f"{dv['A']['divergent']}, {dv['B']['divergent']}", f"{dv['A']['unstable']}, {dv['B']['unstable']}"])
    (TABLES / "rev2_a3a8.tex").write_text(
        booktabs("@{}lcccc@{}", hdr, rows, "Generated by analysis/revision_round2.py. Resolved level (OpenAI raw/Claude raw)."),
        encoding="utf-8", newline="\n")
    # Table: A3 and A8 coder scores and quotes (supplement)
    hdr = ["Benchmark", "Item", "Level", "Coder", "Raw", "Verbatim quotation"]
    rows = []
    for b, nm in RERUN.items():
        for it in ("A3", "A8"):
            c = a3[b]["cells"][it]
            for k, (co, lab) in enumerate((("codex", "OpenAI"), ("sonnet", "Claude"))):
                v = c["votes"][co]
                q = "; ".join("``" + tex_escape(t) + "''" for t in v["quotes"]) or "none"
                rows.append([nm if (it == "A3" and k == 0) else "", it if k == 0 else "", str(c["resolved"]) if k == 0 else "",
                             lab, str(v["raw"]), q])
    (TABLES / "rev2_a3a8_quotes.tex").write_text(
        booktabs("@{}llcclp{3.4in}@{}", hdr, rows, "Generated by analysis/revision_round2.py.", midrules_after={3, 7}),
        encoding="utf-8", newline="\n")
    # Table: cap strata and version merge (supplement)
    cap = res["cap"]
    hdr = ["Subset", "Benchmarks", "Core cells", "Core REPORTED", "Core full", "Agent cells", "Agent REPORTED", "Agent full"]

    def shr(m, k):
        return f"{100 * m[k]:.1f}"

    def shr_ci(m, k):
        pre = "reported" if k == "share_reported" else "full"
        return f"{100 * m[k]:.1f} [{100 * m[pre + '_boot_lo']:.0f}, {100 * m[pre + '_boot_hi']:.0f}]"
    rows = []
    for nm, key in (("Packet cut by the cap", "capped"), ("Packet not cut", "uncapped"), ("All 44", "all")):
        mm = cap["modules"][key]
        rows.append([nm, str(mm["core"]["n_benchmarks"]), str(mm["core"]["n_applicable_cells"]), shr_ci(mm["core"], "share_reported"),
                     shr_ci(mm["core"], "share_full"), str(mm["agent"]["n_applicable_cells"]),
                     shr_ci(mm["agent"], "share_reported"), shr_ci(mm["agent"], "share_full")])
    n_cut = len(rows)
    for nm, v in cap["merge"].items():
        rows.append([nm, str(v["n_benchmarks"]), str(v["core"]["n_applicable_cells"]), shr_ci(v["core"], "share_reported"),
                     shr_ci(v["core"], "share_full"), str(v["agent"]["n_applicable_cells"]),
                     shr_ci(v["agent"], "share_reported"), shr_ci(v["agent"], "share_full")])
    (TABLES / "rev2_cap.tex").write_text(
        booktabs("@{}lccccccc@{}", hdr, rows, "Generated by analysis/revision_round2.py. Percent [95% bootstrap over benchmarks].",
                 midrules_after={n_cut - 1}), encoding="utf-8", newline="\n")


# ------------------------------------------------------------------ markdown (section 8)
def section8(res: dict) -> str:
    L = ["## 8. Round-2 analyses (simulated reviews round 2; added 2026-10-06)", ""]
    L.append("Command (project root): `" + CMD + "`. Script `analysis/revision_round2.py`, seed 20261004. Nothing was rescored: "
             "every value comes from `audit/resolved`, `audit/coding`, `audit/verified`, `audit/gold_*`, "
             "`audit/perturb/perturb/summary.json`, `audit/transport/prompts/*/meta.json` and the files in `analysis/out/`. "
             "Outputs: `revision_round2.json`, `rev2_gold_gaps.csv`, `rev2_perturb_clusters.csv`, `rev2_cap_items.csv`; tables "
             "`paper/tables/rev2_gaps.tex`, `rev2_perturb_clusters.tex`. Validation inside the script (assertions): the "
             "table-based kappa equals the scorer's statistic on all common cells; the point estimates and the 2,000-resample "
             "percentile intervals equal section 5 exactly; the Claude perturbation counts equal 527/542 and 117/290 and each coder has 832 perturbation cells. "
             "All analyses here are post hoc.")
    L.append("")
    # 8.1
    L += ["### 8.1 Like-for-like gaps: benchmark-level tests and interval variants (R1 C3)", ""]
    L.append("Gap = kappa(coder pair) - kappa(coder, expert) on the identical cells of section 5 (ABC: Cohen kappa, 198 cells, 9 "
             "benchmarks; BetterBench: quadratic-weighted kappa, 423 cells, 22 benchmarks). Intervals: percentile = the 2,000-resample "
             "interval over benchmarks of section 5; BCa = bias-corrected and accelerated, acceleration from the leave-one-benchmark-out "
             "jackknife; Bayesian bootstrap = 20,000 Dirichlet(1) weight draws over benchmarks, 2.5th and 97.5th percentiles. "
             "**Swap test**: under the null that the expert labels and the other coder's labels are exchangeable with respect to the "
             "anchor coder, the labels of the two can be swapped benchmark by benchmark; all 2^9 = 512 (ABC) and 2^22 = 4,194,304 "
             "(BetterBench) swaps are enumerated and the p-value is the share of swaps whose gap is at least as large in absolute value "
             "(two-sided; the smallest attainable two-sided value is 2/2^B because the full swap gives the negative of the observed gap). "
             "**Sign test**: per benchmark, raw agreement of the pair minus raw agreement of the coder with the expert; exact two-sided binomial "
             "test on the non-tied benchmarks (a per-benchmark kappa is unstable on 20 to 30 cells, so raw agreement is used for the sign).")
    L.append("")
    for s, lab in (("abc", "ABC"), ("betterbench", "BetterBench")):
        r = res["gaps"][s]
        L.append(f"**{lab}** ({r['n_cells']} cells, {r['n_benchmarks']} benchmarks)")
        L.append("")
        L.append("| Gap | Point | Percentile 95% | BCa 95% | Bayesian bootstrap 95% | Posterior share > 0 | Swap test p (one-sided / two-sided) | Sign test (positive / non-tied; two-sided p) |")
        L.append("|---|---|---|---|---|---|---|---|")
        for k in ("pair_minus_codex_expert", "pair_minus_sonnet_expert", "pair_minus_mean_coder_expert"):
            g = r["gaps"][k]
            pm, sg = g.get("permutation"), g.get("sign_test")
            L.append(f"| {GAPLAB[k]} | {g['point']:+.2f} | {ci2(g['percentile_95'])} | {ci2(g['bca_95'])} | {ci2(g['bayes_95'])} | "
                     f"{g['bayes_share_positive']:.3f} | " +
                     (f"{pfmt(pm['p_one_sided'])} / {pfmt(pm['p_two_sided'])} ({pm['n_swaps']:,} swaps)" if pm else "n/a (not defined for the mean)") + " | " +
                     (f"{sg['positive']} / {sg['positive'] + sg['negative']} ({sg['ties']} ties); p {('= ' + pfmt(sg['p_two_sided'])) if sg['p_two_sided'] >= 0.001 else pfmt(sg['p_two_sided'])}" if sg else "n/a") + " |")
        L.append("")
    return "\n".join(L) + "\n"


def section8_rest(res: dict) -> str:
    L = []
    pt = res["perturb"]
    L += ["### 8.2 Perturbation table with packet-cluster intervals (R1 C3, M4)", ""]
    L.append("The 832 labelled cells of the 39 variant packets, for the OpenAI coder (gpt-5.5), Claude Sonnet and the resolved level. Each "
             "variant packet is built on a different benchmark (39 benchmarks for 39 variants, `perturb_diagnosis_cells.csv`), so the "
             "variant cluster is a packet cluster and a benchmark cluster at once. Percentile bootstrap, 2,000 resamples of clusters "
             "with replacement, seed 20261004, pooled rate per resample; the Wilson interval (cells independent) is beside it. Item "
             "clusters (25) are a second view: the same item is planted or deleted in many packets. The multiplexed design adds "
             "dependence that neither cluster view removes (cross-item interference, section 3.4 and `perturb_diagnosis.md`).")
    L.append("")
    L.append("| Coder | Rate | Hits/n | Rate | Wilson 95% | Variant-cluster 95% (39) | Width ratio vs Wilson | Item-cluster 95% (25) | Width ratio vs Wilson |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    pc = lambda c: f"[{100 * c[0]:.1f}, {100 * c[1]:.1f}]"
    for cd in ("codex", "sonnet", "RESOLVED"):
        cl = pt["by_coder"][cd]["clusters"]
        for m in ("sensitivity", "inject", "buried", "paraphrase", "specificity", "deletion", "decoy"):
            v, it = cl["variant_id"][m], cl["item"][m]
            L.append(f"| {cd} | {m} | {v['hits']}/{v['n']} | {100 * v['rate']:.1f}% | {pc(v['wilson'])} | {pc(v['cluster_boot'])} | "
                     f"{v['width_ratio']:.2f} | {pc(it['cluster_boot'])} | {it['width_ratio']:.2f} |")
    L.append("")
    cap = res["cap"]
    L += ["### 8.3 Cap-stratified RQ1 shares and alpha; version merge (R2 M3)", ""]
    L.append(f"Cap flags are in `audit/transport/prompts/<bench>/meta.json` (`tokens_before_cap`, `n_dropped_chunks`), not in "
             f"`audit/packets/*/manifest.json`, which carries no cap field (the cap is applied at scoring time; `audit/BUILD_LOG.md`). "
             f"Capped = at least one S4 chunk dropped by the 150,000-token cap: {cap['n_capped']} of the 44 coded benchmarks "
             f"({', '.join(cap['capped'])}); the other {cap['n_uncapped']} are uncapped. HealthCraft is also capped and has no cells. "
             "Resolved rule; CI = percentile bootstrap over benchmarks within the stratum (2,000, seed 20261004); the difference "
             "(capped minus uncapped) uses independent resampling in each stratum.")
    L.append("")
    L.append("| Module | Stratum | Benchmarks | Applicable cells | REPORTED | 95% CI | Fully reported | 95% CI |")
    L.append("|---|---|---|---|---|---|---|---|")
    for mod in ("core", "agent"):
        for st in ("capped", "uncapped", "all"):
            m = cap["modules"][st][mod]
            L.append(f"| {mod} | {st} | {m['n_benchmarks']} | {m['n_applicable_cells']} | {100 * m['share_reported']:.1f}% | "
                     f"[{100 * m['reported_boot_lo']:.1f}, {100 * m['reported_boot_hi']:.1f}] | {100 * m['share_full']:.1f}% | "
                     f"[{100 * m['full_boot_lo']:.1f}, {100 * m['full_boot_hi']:.1f}] |")
    L.append("")
    L.append("Difference, capped minus uncapped, in points (percentile 95% interval): " + "; ".join(
        f"{k.replace('_', ' ')} {100 * v[0]:+.1f} [{100 * v[1]:+.1f}, {100 * v[2]:+.1f}]" for k, v in cap["diff"].items()) + ".")
    L.append("")
    al = cap["alpha"]
    L.append("Cross-family ordinal alpha (raw scores, NA missing), overall: capped "
             f"{al['capped']['overall']['alpha']:.3f} [{al['capped']['overall']['ci_lo']:.3f}, {al['capped']['overall']['ci_hi']:.3f}] "
             f"on {al['capped']['overall']['units']} cells in {al['capped']['overall']['benchmarks']} benchmarks; uncapped "
             f"{al['uncapped']['overall']['alpha']:.3f} [{al['uncapped']['overall']['ci_lo']:.3f}, {al['uncapped']['overall']['ci_hi']:.3f}] "
             f"on {al['uncapped']['overall']['units']} cells in {al['uncapped']['overall']['benchmarks']} benchmarks (all 44: 0.771).")
    L.append("")
    L.append("Items with the largest capped-minus-uncapped difference in the REPORTED share (resolved rule; n = applicable benchmarks):")
    L.append("")
    diffs = sorted(((it, 100 * (cap["items"][it]["capped"]["rep"] - cap["items"][it]["uncapped"]["rep"])) for it in ITEM_ORDER
                    if cap["items"][it]["capped"]["rep"] is not None and cap["items"][it]["uncapped"]["rep"] is not None),
                   key=lambda t: -abs(t[1]))[:6]
    L.append("| Item | Capped (n) | Uncapped (n) | Difference (points) |")
    L.append("|---|---|---|---|")
    for it, dv in diffs:
        c, u = cap["items"][it]["capped"], cap["items"][it]["uncapped"]
        L.append(f"| {it} | {100 * c['rep']:.1f}% ({c['n']}) | {100 * u['rep']:.1f}% ({u['n']}) | {dv:+.1f} |")
    L.append("")
    for it in ("C13", "A4"):
        x = cap["c13_a4"][it]
        c, u = cap["items"][it]["capped"], cap["items"][it]["uncapped"]
        L.append(f"- {it}: {x['resolved_zero']} of {x['cells_in_capped_packets']} cells in capped packets resolved to 0 "
                 f"(status counts {x['status_counts']}), against {x['uncapped_zero']} of {cap['n_uncapped']} in uncapped packets; "
                 f"REPORTED {100 * c['rep']:.1f}% capped against {100 * u['rep']:.1f}% uncapped.")
    ca = cap["cap_aware"]
    L.append(f"- Cap-aware shares (the {cap['c13_a4']['C13']['resolved_zero'] + cap['c13_a4']['A4']['resolved_zero']} capped C13 and A4 "
             f"cells that resolved to 0 are treated as not established and left out of the denominator): core REPORTED "
             f"{100 * ca['core']['rep']:.1f}% (n = {ca['core']['n']}), fully reported {100 * ca['core']['full']:.1f}%; agent REPORTED "
             f"{100 * ca['agent']['rep']:.1f}% (n = {ca['agent']['n']}), fully reported {100 * ca['agent']['full']:.1f}%.")
    L.append("")
    L.append("MedAgentBench v1 and v2 merged (resolved rule; the merged unit takes the higher resolved level per item, NA only when both are NA):")
    L.append("")
    L.append("| Variant | Benchmarks | Core cells | Core REPORTED [95%] | Core full | Agent cells | Agent REPORTED [95%] | Agent full |")
    L.append("|---|---|---|---|---|---|---|---|")
    for nm, v in cap["merge"].items():
        c, a = v["core"], v["agent"]
        L.append(f"| {nm} | {v['n_benchmarks']} | {c['n_applicable_cells']} | {100 * c['share_reported']:.1f}% "
                 f"[{100 * c['reported_boot_lo']:.1f}, {100 * c['reported_boot_hi']:.1f}] | {100 * c['share_full']:.1f}% | "
                 f"{a['n_applicable_cells']} | {100 * a['share_reported']:.1f}% [{100 * a['reported_boot_lo']:.1f}, "
                 f"{100 * a['reported_boot_hi']:.1f}] | {100 * a['share_full']:.1f}% |")
    L.append("")
    a3 = res["a3a8"]
    L += ["### 8.4 Audit A3 and A8 beside the rerun findings (R2 M5)", ""]
    L.append("Resolved level = the audit's two-family rule (section 2); raw = each coder's score before quote verification; "
             "quotes are the coders' verbatim excerpts. Cap: whether the packet lost S4 chunks to the 150,000-token cap. "
             "A3 asks for action-level repeat-run reliability, A8 for the grader's input and its validation. No audit score was "
             "recomputed or compared statistically with a rerun outcome; the table sets stored results side by side.")
    L.append("")
    L.append("| Benchmark | Cap | Item | Resolved | Status | OpenAI raw / Claude raw | OpenAI quote | Claude quote |")
    L.append("|---|---|---|---|---|---|---|---|")
    for b, v in a3.items():
        if b == "rerun":
            continue
        for it in ("A3", "A8"):
            c = v["cells"][it]
            cx, sn = c["votes"]["codex"], c["votes"]["sonnet"]
            qs = lambda q: "; ".join(f"\"{t}\"" for t in q) or "none"
            L.append(f"| {v['name']} | {'capped (' + str(v['cap']['n_dropped_chunks']) + ' chunks dropped)' if v['cap']['capped'] else 'not capped'} | {it} | "
                     f"{c['resolved']} | {c['status']} | {cx['raw']} / {sn['raw']} | {qs(cx['quotes'])} | {qs(sn['quotes'])} |")
    L.append("")
    rr = a3["rerun"]
    L.append("Rerun findings (stored results, sections 1 and 7): task groups with more than one action sequence (condition A / B, of 10) "
             + "; ".join(f"{n} {v['A']['divergent']} / {v['B']['divergent']}" for n, v in rr["divergence"].items())
             + "; groups with an unstable verdict "
             + "; ".join(f"{n} {v['A']['unstable']} / {v['B']['unstable']}" for n, v in rr["divergence"].items())
             + ". Invalid episodes (of 50): " + "; ".join(f"{n} {v['A']['invalid']} / {v['B']['invalid']}" for n, v in rr["validity"].items())
             + ". Grader check (Synthetic Hospital): " + "; ".join(f"condition {k}: {v['disagree']} disagreements in {v['agree'] + v['disagree'] + v['neutral_set_required']} episodes with a submission ({v['no_submission']} with none)" for k, v in rr["grader_vs_state_synthetic_hospital"].items())
             + f". Judge-only rerun (AgentClinic): {rr['judge_only_agentclinic']['unstable']} of {rr['judge_only_agentclinic']['transcripts']} transcripts unstable, "
             f"{rr['judge_only_agentclinic']['differ_from_recorded']} of {rr['judge_only_agentclinic']['transcripts']} differing from the recorded verdict. "
             "RadA-BenchPlat has no grader check.")
    L.append("")
    dv = rr["divergence"]
    n_a, n_b = sum(v["A"]["divergent"] for v in dv.values()), sum(v["B"]["divergent"] for v in dv.values())
    lv = {n: {it: a3[b]["cells"][it]["resolved"] for it in ("A3", "A8")} for b, n in RERUN.items()}
    a3_zero = all(v["A3"] == 0 for v in lv.values())
    L.append(f"Reading (facts only): A3 resolves to {'0 (not REPORTED)' if a3_zero else 'a nonzero level for at least one benchmark'} "
             f"for {', '.join(n for n, v in lv.items() if v['A3'] == 0)}, so on the audit none of the three reports repeat-run "
             f"behaviour, and the reruns found more than one action sequence in {n_a} of 30 task groups at the benchmark's own "
             f"temperature (condition A) and {n_b} of 30 at 0.7 (condition B). For AgentClinic the A3 zero is a not-established cell "
             "(the OpenAI coder gave 1 on a score-level statement, Claude gave 0). A8 resolves to "
             + ", ".join(f"{v['A8']} for {n}" for n, v in lv.items())
             + "; the RadA-BenchPlat 0 is a not-established cell (both coders gave 1, one without a verified quote). None of the six "
             "A8 rationales reports a validation on known-correct and known-incorrect outcomes, and the rerun checks (a recomputation "
             "of a reward, a judge repeated at temperature 0) are not such a validation. The RadA-BenchPlat and Synthetic Hospital "
             "packets were capped, so a zero for them can reflect removed code.")
    L.append("")
    al = res["alpha"]
    L += ["### 8.5 Alpha and prevalence for the low-alpha extremes (R1 C4, R3)", ""]
    L.append("The text of section V-A named A7 among the items REPORTED by at least 90% and C11 as REPORTED by none while stating that items "
             "with alpha below 0.5 are not ranked. Values (cross-family ordinal alpha, 44 cells each, bootstrap CI over benchmarks; "
             "REPORTED share of applicable cells):")
    L.append("")
    L.append("| Item | Alpha [95% CI] | Applicable | REPORTED | Fully reported |")
    L.append("|---|---|---|---|---|")
    for it in ("A7", "C11", "C10", "C7", "A10", "C3", "C8"):
        x = al["items"][it]
        L.append(f"| {it} | {x['alpha']:.2f} [{x['lo']:.2f}, {x['hi']:.2f}] | {x['n_applicable']} | {100 * x['reported']:.1f}% | {100 * x['full']:.1f}% |")
    L.append("")
    L.append(f"Items with alpha below 0.5 ({len(al['below_half'])}): {', '.join(al['below_half'])}. Items at 0.8 or above "
             f"({len(al['at_least_point_eight'])}): {', '.join(al['at_least_point_eight'])}. The other high-share items are C2 "
             f"({100 * al['items']['C2']['reported']:.1f}%, alpha {al['items']['C2']['alpha']:.2f}) and A8 "
             f"({100 * al['items']['A8']['reported']:.1f}%, alpha {al['items']['A8']['alpha']:.2f}), which also lie below 0.8; "
             "A7 (96.8%, alpha 0.02) and C11 (0.0%, alpha 0.00) are the two extremes of the share ranking and have the two lowest alphas, "
             "so neither is a ranked extreme.")
    L.append("")
    return "\n".join(L) + "\n"


def write_summary(text: str) -> None:
    txt = SUMMARY.read_text(encoding="utf-8")
    m = re.search(r"^## 8\. Round-2 analyses.*?(?=^## \d+\. |\Z)", txt, re.S | re.M)
    if m:
        txt = txt[:m.start()] + text.rstrip() + "\n" + txt[m.end():]
    else:
        txt = txt.rstrip() + "\n\n" + text.rstrip() + "\n"
    SUMMARY.write_text(txt, encoding="utf-8", newline="\n")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--write-summary", action="store_true", help="(re)write section 8 of analysis/out/RESULTS_SUMMARY.md")
    a = ap.parse_args(argv)
    res = compute()
    write_outputs(res)
    text = section8(res) + section8_rest(res)
    if a.write_summary:
        write_summary(text)
    print(text)


if __name__ == "__main__":
    main()
