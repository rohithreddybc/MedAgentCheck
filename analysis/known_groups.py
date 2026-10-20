"""Known-groups specificity and adjacent-construct convergence (post hoc; protocol/addendum-known-groups.md).

Plan fixed in the addendum (2026-10-14); this script follows it and changes nothing in the protocol, paper or scorer.

Inputs
  audit/known_groups/verified/<bench>/<item>/<coder>.json   effective level (0, 1, 2 or "NA") after quote verification
  audit/known_groups/resolved/<bench>.json                  resolved level, only for benchmarks with both coders
  research/gold/abc_scores.csv, betterbench_scores.csv      published expert labels (not redistributed)
Gold benchmark names map to packet directory names with agentaudit.util.safe_name (the rule used to build the packets),
e.g. "SWE-bench (Verified)" -> "SWE-bench_Verified", "MedMNIST v2" -> "MedMNIST_v2".

Study 1  N x {A3, A5, A6, A7, A9, A11}: false-credit rate (level >= 1; NA and 0 are both correct), Wilson 95% CI and
         percentile bootstrap over benchmarks (2,000 resamples, seed 20261004); per item; P minus N contrast of the
         credited share (same six items), bootstrap over benchmarks within each group.
Study 2  mapped agent items vs the expert reference per cell (BetterBench: mean of mapped criteria / 15; ABC: share of
         mapped items scored 1; expert NA or missing dropped; cells without a mapped item unused). Spearman rho pooled
         over cells with bootstrap over benchmarks, dichotomous agreement (coder >= 1 vs expert > 0) with Cohen kappa.

Second coder (added 2026-10-20). The OpenAI coder is labelled by the model id actually recorded in
audit/known_groups/coding/*/*/codex.json (cross-checked against transport/responses_known_groups_codex*/<bench>.meta.json);
gpt-6.1-sol is a disclosed substitute for gpt-5.5 ("substitute_for" in the JSON). Rules:
  - the Claude coder ("sonnet") keeps its own full results (30 benchmarks); they are asserted equal to the frozen copy in
    analysis/out/known_groups_claude_baseline.json (the values of the 2026-10-14 run) before anything is written;
  - every comparison that involves both coders or the resolved rule uses only the cells coded by BOTH coders
    ("common" scope; this drops e.g. ALE, which only the OpenAI coder coded; ALE is reported in a coverage note);
  - extended outputs per coder and for the resolved rule, on the common scope: per-item false credit, pooled false credit over the
    six items and over the five items without A11, known-groups contrast with and without A11, per-item adjacent-construct rho
    (benchmark bootstrap CI, permutation p, Holm), coder-coder agreement on the known-groups cells.
  - rerunning after more OpenAI packets arrive needs no code change; benchmarks without an OpenAI response are listed.

Run from the project root:   python analysis/known_groups.py
Writes analysis/out/known_groups.json and replaces section 11 of analysis/out/RESULTS_SUMMARY.md.
"""
from __future__ import annotations

import csv
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, ROOT, SEED  # noqa: E402  (also puts the scorer on sys.path)

from agentaudit.stats import cohen_kappa, wilson  # noqa: E402
from agentaudit.util import safe_name  # noqa: E402

N_BOOT = 2000
KG = ROOT / "audit" / "known_groups"
GOLD = ROOT / "research" / "gold"
TRANSPORT = ROOT / "audit" / "transport"
BASELINE = OUT / "known_groups_claude_baseline.json"
SUMMARY = OUT / "RESULTS_SUMMARY.md"
N_PERM = 10000
SUBSTITUTE_FOR = "gpt-5.5"
HEADING = "## 11. Known-groups and adjacent-construct validation (post hoc; added 2026-10-14)"
CODERS = ("sonnet", "codex")

NEG = ["ARC-Challenge", "BBQ", "BOLD", "DecodingTrust", "GPQA", "GSM8k", "HellaSwag", "HumanEval", "MedMNIST_v2",
       "MLCommons_AI_Safety_v0.5", "MMLU", "TruthfulQA", "WinoGrande"]
POS = ["BIRD-Bench", "GAIA", "KernelBench", "MLE-bench", "OSWorld", "SWE-Lancer", "SWE-bench_Verified", "WebArena",
       "tau-bench", "AgentBench"]
TEST_ITEMS = ["A3", "A5", "A6", "A7", "A9", "A11"]
TEST_ITEMS_NO_A11 = [i for i in TEST_ITEMS if i != "A11"]
MIN_ITEM_CELLS = 8

# item -> (BetterBench criteria, ABC items); addendum table, from crosswalk Supplementary Table S15
MAP = {
    "A1": (["J.3-17"], ["R.10"]),
    "A2": (["J.3-17"], ["R.10"]),
    "A3": (["J.3-17"], ["O.f.2", "O.c.1"]),
    "A5": ([], ["T.1", "T.2", "T.3", "T.6"]),
    "A6": ([], ["T.1", "T.2", "T.3", "T.6"]),
    "A8": (["J.1-13"], ["O.g.1", "O.g.2", "O.g.3", "T.7", "T.9", "R.13"]),
    "A9": (["J.2-3", "J.2-6", "J.2-7", "J.2-9"], ["R.3", "R.4", "T.5"]),
    "A10": (["J.3-14"], []),
    "A11": (["J.3-8", "J.3-11", "J.3-12", "J.3-13"], ["T.6"]),
}


# ------------------------------------------------------------------ loading
def load_levels() -> tuple[dict, dict]:
    """(coder -> {(bench, item): level}, resolved {(bench, item): level}); level in {0, 1, 2, "NA"}."""
    per: dict[str, dict] = {}
    for c in CODERS:
        d = {}
        for p in sorted(KG.glob(f"verified/*/*/{c}.json")):
            j = json.loads(p.read_text(encoding="utf-8"))
            d[(p.parent.parent.name, p.parent.name)] = j["effective"]
        if d:
            per[c] = d
    res = {}
    for p in sorted(KG.glob("resolved/*.json")):
        if p.name == "summary.json":
            continue
        j = json.loads(p.read_text(encoding="utf-8"))
        for it, c in j["cells"].items():
            res[(j["bench"], it)] = c["final"]
    return per, res


def coder_info(per: dict) -> dict:
    """Label and model id of each coder, read from the coding records (what was actually imported) and cross-checked
    against the response meta files of the OpenAI runs."""
    info = {}
    for role, d in per.items():
        ids = set()
        for p in sorted(KG.glob(f"coding/*/*/{role}.json")):
            m = json.loads(p.read_text(encoding="utf-8")).get("model_id")
            if m:
                ids.add(m)
        meta_ids = {}
        if role == "codex":
            for p in sorted(TRANSPORT.glob("responses_known_groups_codex*/*.meta.json")):
                m = json.loads(p.read_text(encoding="utf-8")).get("model_id")
                if m:
                    meta_ids.setdefault(p.parent.name, set()).add(m)
        ids_all = ids or {m for v in meta_ids.values() for m in v}
        mid = "+".join(sorted(ids_all)) if ids_all else role
        row = {"coder": role, "model_id": mid, "model_ids_in_coding_records": sorted(ids),
               "model_ids_in_meta_files": {k: sorted(v) for k, v in meta_ids.items()},
               "benchmarks_coded": len({b for b, _ in d}), "cells": len(d)}
        if role == "codex":
            row["label"] = mid
            row["substitute_for"] = SUBSTITUTE_FOR if mid != SUBSTITUTE_FOR else None
            row["disclosed_substitute"] = mid != SUBSTITUTE_FOR
        else:
            row["label"] = role
        info[role] = row
    return info


def restrict(lv: dict, keys: set) -> dict:
    return {k: v for k, v in lv.items() if k in keys}


def norm_id(s: str) -> str:
    return s.strip().split(" ")[0]


def load_expert() -> tuple[dict, dict]:
    """(bb[(bench, crit)] -> 0..1 or None for NA, abc[(bench, item)] -> 0/1), bench = packet directory name."""
    bb, abc = {}, {}
    with open(GOLD / "betterbench_scores.csv", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            s = r["score"].strip()
            bb[(safe_name(r["benchmark"]), norm_id(r["criterion_id"]))] = None if s.upper() == "NA" or s == "" else int(s) / 15.0
    with open(GOLD / "abc_scores.csv", encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            s = r["score"].strip()
            abc[(safe_name(r["benchmark"]), norm_id(r["item_id"]))] = None if s.upper() == "NA" or s == "" else int(s)
    return bb, abc


def _mean(vals: list) -> float:
    """Left-to-right float mean. Python 3.12 made sum() of floats compensated, which turns some mathematically equal
    BetterBench means (e.g. A11) into exact ties and moves pooled rho from 0.27873 to 0.27890. The 2026-10-14 values were
    computed with plain left-to-right addition; this keeps them reproducible on any Python version."""
    t = 0.0
    for v in vals:
        t += v
    return t / len(vals)


def expert_cells(bb: dict, abc: dict, packets: set[str]) -> list[dict]:
    """One row per (bench, agent item) with an expert reference; bench must have a packet."""
    rows = []
    bb_b = sorted({b for b, _ in bb} & packets)
    abc_b = sorted({b for b, _ in abc} & packets)
    for it, (bbc, abcc) in MAP.items():
        for b in bb_b:
            vals = [bb[(b, c)] for c in bbc if (b, c) in bb and bb[(b, c)] is not None]
            if vals:
                rows.append({"bench": b, "item": it, "set": "betterbench", "ref": _mean(vals), "k": len(vals)})
        for b in abc_b:
            vals = [abc[(b, c)] for c in abcc if (b, c) in abc and abc[(b, c)] is not None]
            if vals:
                rows.append({"bench": b, "item": it, "set": "abc", "ref": _mean(vals), "k": len(vals)})
    return rows


# ------------------------------------------------------------------ statistics
def pct(vals: list[float], q: float):
    return vals[int(q * (len(vals) - 1))]


def boot_ci(draw_fn, n_boot: int = N_BOOT, seed: int = SEED):
    """draw_fn(rng) -> statistic or None. Percentile 95% CI over resamples that returned a value."""
    rng = random.Random(seed)
    vals = [v for v in (draw_fn(rng) for _ in range(n_boot)) if v is not None]
    if len(vals) < 20:
        return None
    vals.sort()
    return [pct(vals, 0.025), pct(vals, 0.975)]


def resample(groups: dict[str, list], rng: random.Random) -> list:
    keys = sorted(groups)
    out = []
    for _ in range(len(keys)):
        out.extend(groups[keys[rng.randrange(len(keys))]])
    return out


def rank(v: list[float]) -> list[float]:
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def spearman(x: list[float], y: list[float]):
    if len(x) < 3:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    sxx = sum((a - mx) ** 2 for a in rx)
    syy = sum((b - my) ** 2 for b in ry)
    if sxx == 0 or syy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(rx, ry)) / (sxx * syy) ** 0.5


def spearman_perm_p(x: list[float], y: list[float], seed: int = SEED, n_perm: int = N_PERM):
    """Two-sided Monte Carlo permutation p for Spearman rho (cells permuted, benchmark clustering ignored)."""
    rho = spearman(x, y)
    if rho is None:
        return None
    rx, ry = rank(x), rank(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cx = [a - mx for a in rx]
    cy = [b - my for b in ry]
    den = (sum(a * a for a in cx) * sum(b * b for b in cy)) ** 0.5
    rng = random.Random(seed)
    hits = 0
    for _ in range(n_perm):
        rng.shuffle(cy)
        if abs(sum(a * b for a, b in zip(cx, cy)) / den) >= abs(rho) - 1e-12:
            hits += 1
    return (hits + 1) / (n_perm + 1)


def spearman_t_p(rho, n: int):
    """Two-sided t-approximation p for Spearman rho (df = n - 2)."""
    if rho is None or n < 3:
        return None
    if abs(rho) >= 1:
        return 0.0
    try:
        from scipy import stats as _st
    except ImportError:  # pragma: no cover
        return None
    t = rho * ((n - 2) / (1 - rho * rho)) ** 0.5
    return float(2 * _st.t.sf(abs(t), n - 2))


def holm(ps: dict) -> dict:
    """Holm step-down adjusted p over {key: p}; keys with p None are ignored."""
    items = sorted(((k, p) for k, p in ps.items() if p is not None), key=lambda kv: kv[1])
    m, run, out = len(items), 0.0, {}
    for j, (k, p) in enumerate(items):
        run = max(run, min(1.0, (m - j) * p))
        out[k] = run
    return out


def rate_block(groups: dict[str, list]) -> dict:
    """groups: bench -> list of 0/1 (1 = credited). Pooled rate, Wilson, bootstrap over benchmarks."""
    units = [u for us in groups.values() for u in us]
    n, k = len(units), sum(units)
    if not n:
        return {"n": 0, "k": 0, "rate": None, "wilson95": None, "boot95": None, "benchmarks": 0}
    ci = boot_ci(lambda rng: (lambda u: sum(u) / len(u) if u else None)(resample(groups, rng))) if len(groups) >= 2 else None
    return {"n": n, "k": k, "rate": k / n, "wilson95": list(wilson(k, n)), "boot95": ci, "benchmarks": len(groups)}


# ------------------------------------------------------------------ study 1
def credited(v) -> int:
    return 1 if v != "NA" and v >= 1 else 0


def study1(levels: dict) -> dict:
    """levels: {(bench, item): level} for one coder or the resolved rule."""
    def groups(benches, items):
        g: dict[str, list] = {}
        for b in benches:
            us = [credited(levels[(b, i)]) for i in items if (b, i) in levels]
            if us:
                g[b] = us
        return g

    def comp(benches):
        return sorted(b for b in benches if any((b, i) in levels for i in TEST_ITEMS))

    n_present, p_present = comp(NEG), comp(POS)
    out = {"n_benchmarks_present": len(n_present), "n_benchmarks_expected": len(NEG),
           "p_benchmarks_present": len(p_present), "p_benchmarks_expected": len(POS),
           "n_missing": sorted(set(NEG) - set(n_present)), "p_missing": sorted(set(POS) - set(p_present))}
    gn, gp = groups(NEG, TEST_ITEMS), groups(POS, TEST_ITEMS)
    out["N_false_credit"] = rate_block(gn)
    out["P_credited"] = rate_block(gp)
    cnt = {"NA": 0, "0": 0, "1": 0, "2": 0}
    for b in NEG:
        for i in TEST_ITEMS:
            if (b, i) in levels:
                cnt[str(levels[(b, i)])] += 1
    out["N_cell_levels"] = cnt
    cntp = {"NA": 0, "0": 0, "1": 0, "2": 0}
    for b in POS:
        for i in TEST_ITEMS:
            if (b, i) in levels:
                cntp[str(levels[(b, i)])] += 1
    out["P_cell_levels"] = cntp
    out["per_item"] = {}
    for i in TEST_ITEMS:
        gi_n, gi_p = groups(NEG, [i]), groups(POS, [i])
        out["per_item"][i] = {"N": rate_block(gi_n), "P": rate_block(gi_p)}
        un = [u for us in gi_n.values() for u in us]
        up = [u for us in gi_p.values() for u in us]
        out["per_item"][i]["contrast_P_minus_N"] = (sum(up) / len(up) - sum(un) / len(un)) if un and up else None

    def contrast(rng):
        a, b = resample(gp, rng), resample(gn, rng)
        return sum(a) / len(a) - sum(b) / len(b) if a and b else None
    if gn and gp:
        un = [u for us in gn.values() for u in us]
        up = [u for us in gp.values() for u in us]
        out["contrast_P_minus_N"] = {"value": sum(up) / len(up) - sum(un) / len(un),
                                     "boot95": boot_ci(contrast) if len(gn) >= 2 and len(gp) >= 2 else None}
    else:
        out["contrast_P_minus_N"] = None
    return out


# ------------------------------------------------------------------ study 1, extended (common scope)
def bench_groups(levels: dict, benches, items) -> dict[str, list]:
    g: dict[str, list] = {}
    for b in benches:
        us = [credited(levels[(b, i)]) for i in items if (b, i) in levels]
        if us:
            g[b] = us
    return g


def level_counts(levels: dict, benches, items) -> dict:
    cnt = {"NA": 0, "0": 0, "1": 0, "2": 0}
    for b in benches:
        for i in items:
            if (b, i) in levels:
                cnt[str(levels[(b, i)])] += 1
    return cnt


def contrast_block(levels: dict, items) -> dict | None:
    """Agentic (P) minus static (N) share credited over `items`; the 10 P and 13 N benchmarks are resampled separately."""
    gn, gp = bench_groups(levels, NEG, items), bench_groups(levels, POS, items)
    if not gn or not gp:
        return None
    un = [u for us in gn.values() for u in us]
    up = [u for us in gp.values() for u in us]

    def draw(rng):
        a, b = resample(gp, rng), resample(gn, rng)
        return sum(a) / len(a) - sum(b) / len(b) if a and b else None
    return {"items": list(items), "N_share": sum(un) / len(un), "P_share": sum(up) / len(up),
            "N_cells": len(un), "P_cells": len(up), "N_benchmarks": len(gn), "P_benchmarks": len(gp),
            "value": sum(up) / len(up) - sum(un) / len(un),
            "boot95": boot_ci(draw) if len(gn) >= 2 and len(gp) >= 2 else None}


def study1_ext(levels: dict) -> dict:
    out = {"per_item": {}}
    for i in TEST_ITEMS:
        rb = rate_block(bench_groups(levels, NEG, [i]))
        rb["N_cell_levels"] = level_counts(levels, NEG, [i])
        out["per_item"][i] = rb
    out["pooled_6"] = {"items": TEST_ITEMS, **rate_block(bench_groups(levels, NEG, TEST_ITEMS))}
    out["pooled_5_no_A11"] = {"items": TEST_ITEMS_NO_A11, **rate_block(bench_groups(levels, NEG, TEST_ITEMS_NO_A11))}
    out["contrast_6"] = contrast_block(levels, TEST_ITEMS)
    out["contrast_5_no_A11"] = contrast_block(levels, TEST_ITEMS_NO_A11)
    return out


def agreement(a_lv: dict, b_lv: dict, benches, items) -> dict:
    """Two coders on the same cells: raw agreement and Cohen kappa on credited (level >= 1; NA counts as not credited)."""
    cells = [(b, i) for b in benches for i in items if (b, i) in a_lv and (b, i) in b_lv]
    a = [credited(a_lv[c]) for c in cells]
    b = [credited(b_lv[c]) for c in cells]
    n = len(cells)
    return {"n": n, "benchmarks": len({c[0] for c in cells}),
            "raw_agreement": (sum(x == y for x, y in zip(a, b)) / n) if n else None,
            "kappa": cohen_kappa(a, b) if n else None, "a_credited": sum(a), "b_credited": sum(b),
            "both_credited": sum(x and y for x, y in zip(a, b)), "neither_credited": sum((not x) and (not y) for x, y in zip(a, b)),
            "exact_level_agreement": (sum(a_lv[c] == b_lv[c] for c in cells) / n) if n else None}


# ------------------------------------------------------------------ study 2
def study2(levels: dict, cells: list[dict]) -> dict:
    used, na = [], 0
    for c in cells:
        key = (c["bench"], c["item"])
        if key not in levels:
            continue
        v = levels[key]
        if v == "NA":
            na += 1
            continue
        used.append({**c, "lvl": v})
    groups: dict[str, list] = {}
    for u in used:
        groups.setdefault(u["bench"], []).append(u)

    def rho_of(us):
        return spearman([u["lvl"] for u in us], [u["ref"] for u in us])

    def kappa_block(us):
        a = [int(u["lvl"] >= 1) for u in us]
        b = [int(u["ref"] > 0) for u in us]
        n = len(us)
        return {"n": n, "raw_agreement": (sum(x == y for x, y in zip(a, b)) / n) if n else None,
                "kappa": cohen_kappa(a, b) if n else None, "coder_pos": sum(a), "expert_pos": sum(b)}

    out = {"n_cells": len(used), "n_benchmarks": len(groups), "n_coder_na_dropped": na,
           "rho": rho_of(used),
           "rho_boot95": boot_ci(lambda rng: rho_of(resample(groups, rng))) if len(groups) >= 2 else None,
           "dichotomous": kappa_block(used), "by_set": {}, "per_item": {}}
    for s in ("betterbench", "abc"):
        us = [u for u in used if u["set"] == s]
        out["by_set"][s] = {"n_cells": len(us), "n_benchmarks": len({u["bench"] for u in us}), "rho": rho_of(us)}
    for it in MAP:
        us = [u for u in used if u["item"] == it]
        out["per_item"][it] = {"n": len(us), "rho": rho_of(us) if len(us) >= 8 else None,
                               "reported": len(us) >= 8}
    # per-item rho with benchmark-bootstrap CI, permutation p and Holm adjustment (items with >= MIN_ITEM_CELLS cells)
    rows = {}
    for it in MAP:
        us = [u for u in used if u["item"] == it]
        if len(us) < MIN_ITEM_CELLS:
            rows[it] = {"n": len(us), "benchmarks": len({u["bench"] for u in us}), "reported": False}
            continue
        g: dict[str, list] = {}
        for u in us:
            g.setdefault(u["bench"], []).append(u)
        r = rho_of(us)
        row = {"n": len(us), "benchmarks": len(g), "reported": True, "rho": r,
               "boot95": boot_ci(lambda rng, g=g: rho_of(resample(g, rng))) if len(g) >= 2 else None,
               "p_perm": spearman_perm_p([u["lvl"] for u in us], [u["ref"] for u in us]),
               "p_t": spearman_t_p(r, len(us))}
        rows[it] = row
    hp = holm({it: r.get("p_perm") for it, r in rows.items() if r["reported"]})
    ht = holm({it: r.get("p_t") for it, r in rows.items() if r["reported"]})
    for it, r in rows.items():
        if r["reported"]:
            r["p_perm_holm"] = hp.get(it)
            r["p_t_holm"] = ht.get(it)
            r["ci_excludes_0"] = bool(r["boot95"] and (r["boot95"][0] > 0 or r["boot95"][1] < 0))
    rep = [r for r in rows.values() if r["reported"]]
    out["per_item_ci"] = rows
    out["per_item_ci_summary"] = {
        "items_reported": len(rep), "min_cells": MIN_ITEM_CELLS,
        "n_ci_exclude_0": sum(r["ci_excludes_0"] for r in rep),
        "n_holm_perm_lt_05": sum(1 for r in rep if r["p_perm_holm"] is not None and r["p_perm_holm"] < 0.05),
        "p_method": f"two-sided Monte Carlo permutation test of rho (cells permuted, {N_PERM} permutations, seed {SEED}; "
                    "benchmark clustering ignored), Holm step-down over the reported items; t-approximation (df = n - 2) shown as a check"}
    return out


# ------------------------------------------------------------------ output
def f2(x, nd=2):
    return "--" if x is None else f"{x:.{nd}f}"


def ci(c, nd=2):
    return "--" if not c else f"[{c[0]:.{nd}f}, {c[1]:.{nd}f}]"


def md_table(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def markdown(res: dict) -> str:
    L = [HEADING, ""]
    A = L.append
    st = res["status"]
    A("Source: `analysis/known_groups.py` -> `analysis/out/known_groups.json`; plan fixed in `protocol/addendum-known-groups.md` before coding. "
      "Post hoc; reported whatever the result. Verified (effective) levels from `audit/known_groups/verified`; the resolved level exists only for benchmarks coded by both coders. "
      "Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, percentile 95% CI. Wilson 95% intervals are on cells (not clustered). "
      "NA and 0 both count as correct in Study 1.")
    A("")
    sub = res["coder_info"].get("codex") or next((v for v in res["coder_info"].values() if v["coder"] == "codex"), None)
    A(f"**Status: {st['label']}.** Coders: `sonnet` (Claude, {st['sonnet_benchmarks']} benchmarks; its own results are unchanged from the 2026-10-14 run, "
      f"assertion {res['claude_only_assertion']['result']})"
      + (f" and `{sub['label']}` (OpenAI via codex exec, {st['codex_benchmarks']} benchmarks"
         + (f"; a disclosed substitute for {sub['substitute_for']}, which is no longer served to the project account" if sub.get("substitute_for") else "")
         + ")" if sub else "")
      + f". Every row for the OpenAI coder, every row for the resolved rule and every comparison between coders uses only the cells coded by both coders"
        f" ({res['common']['n_cells']} cells, {len(res['common']['benchmarks'])} benchmarks); `sonnet` rows in 11.1 and 11.2 use all of its cells.")
    if st["missing_codex"]:
        A("")
        A("The OpenAI coder has no response yet for: " + ", ".join(st["missing_codex"]) + ". All OpenAI and resolved numbers below are provisional until these are imported.")
    A("")
    A("Caveat: the negatives are construct-absent documentation (the construct is missing from the whole document), so the specificity below is an upper bound for documentation where the construct is partly present.")
    A("")
    A("### 11.1 Study 1: known-groups specificity (N x A3, A5, A6, A7, A9, A11)")
    A("")
    rows = []
    for name, s in res["study1"].items():
        n, p = s["N_false_credit"], s["P_credited"]
        rows.append([name, f"{s['n_benchmarks_present']}/{s['n_benchmarks_expected']}", f"{s['p_benchmarks_present']}/{s['p_benchmarks_expected']}",
                     n["n"], f"{n['k']} ({f2(n['rate'])})" if n["n"] else "--", ci(n["wilson95"]), ci(n["boot95"]),
                     f"{1 - n['rate']:.2f}" if n["n"] else "--",
                     s["N_cell_levels"]["NA"], s["N_cell_levels"]["0"],
                     p["n"], f2(p["rate"]),
                     f2(s["contrast_P_minus_N"]["value"]) if s["contrast_P_minus_N"] else "--",
                     ci(s["contrast_P_minus_N"]["boot95"]) if s["contrast_P_minus_N"] else "--"])
    A(md_table(["Coder / rule", "N benches", "P benches", "N cells", "False credit k (rate)", "Wilson 95%", "Bootstrap 95%", "Specificity",
                "N cells NA", "N cells 0", "P cells", "P credited share", "P minus N", "Contrast bootstrap 95%"], rows))
    A("")
    A("Per item (false-credit rate in N, credited share in P; k/n):")
    A("")
    rows = []
    for name, s in res["study1"].items():
        for i in TEST_ITEMS:
            pi = s["per_item"][i]
            n, p = pi["N"], pi["P"]
            rows.append([name, i, f"{n['k']}/{n['n']}", f2(n["rate"]), ci(n["wilson95"]), f"{p['k']}/{p['n']}", f2(p["rate"]),
                         f2(pi["contrast_P_minus_N"])])
    A(md_table(["Coder / rule", "Item", "N k/n", "N rate", "N Wilson 95%", "P k/n", "P rate", "P minus N"], rows))
    A("")
    A("### 11.2 Study 2: convergence with published expert labels on adjacent constructs")
    A("")
    A("Expert reference per cell (benchmark x agent item): BetterBench mean of mapped criteria / 15; ABC share of mapped items scored 1; expert NA or missing dropped; cells without a mapped item unused. "
      "Coder NA cells are dropped and counted. Spearman rho between coder level (0-2) and the reference, pooled over cells; CI by bootstrap over benchmarks. "
      "Dichotomous: coder level >= 1 versus expert reference > 0. Interpretation fixed in advance: an interval above 0 is convergent evidence; an interval spanning 0 is no evidence of convergence.")
    A("")
    rows = []
    for name, s in res["study2"].items():
        d = s["dichotomous"]
        rows.append([name, s["n_cells"], s["n_benchmarks"], s["n_coder_na_dropped"], f2(s["rho"]), ci(s["rho_boot95"]),
                     f2(d["raw_agreement"]), f2(d["kappa"]), f"{d['coder_pos']}/{d['expert_pos']}"])
    A(md_table(["Coder / rule", "Cells", "Benches", "Coder NA dropped", "Spearman rho", "Bootstrap 95%", "Raw agreement", "Cohen kappa", "Positives coder/expert"], rows))
    A("")
    A("Descriptive split by expert source (no CI): " + "; ".join(
        f"{name}: " + ", ".join(f"{k} n={v['n_cells']} rho={f2(v['rho'])}" for k, v in s["by_set"].items())
        for name, s in res["study2"].items()))
    A("")
    A("Per agent item (rho shown where n >= 8):")
    A("")
    rows = []
    for name, s in res["study2"].items():
        for it, v in s["per_item"].items():
            rows.append([name, it, v["n"], f2(v["rho"]) if v["reported"] else "n < 8"])
    A(md_table(["Coder / rule", "Item", "n cells", "rho"], rows))
    A("")
    A("Coverage: " + "; ".join(f"{k}: {v}" for k, v in res["coverage"].items()))
    A("")
    ext = res["common"]["sets"]
    A("### 11.3 Common-benchmark comparison of coders and resolved rule")
    A("")
    A(f"All rows: the {res['common']['n_cells']} cells coded by both coders ({len(res['common']['benchmarks'])} benchmarks). "
      "Static group N = 13 benchmarks; agentic group P = 10.")
    A("")
    A("False credit per item on N (level >= 1; Wilson on cells, bootstrap over the benchmarks; levels = NA/0/1/2 counts):")
    A("")
    rows = []
    for name, e in ext.items():
        for i in TEST_ITEMS:
            r = e["study1_ext"]["per_item"][i]
            lc = r["N_cell_levels"]
            rows.append([name, i, f"{r['k']}/{r['n']}", f2(r["rate"]), ci(r["wilson95"]), ci(r["boot95"]),
                         f"{lc['NA']}/{lc['0']}/{lc['1']}/{lc['2']}"])
    A(md_table(["Coder / rule", "Item", "k/n", "Rate", "Wilson 95%", "Bootstrap 95%", "NA/0/1/2"], rows))
    A("")
    A("Pooled false credit on N, six items (A3, A5, A6, A7, A9, A11) and five items without A11:")
    A("")
    rows = []
    for name, e in ext.items():
        for key, lab in (("pooled_6", "6 items"), ("pooled_5_no_A11", "5 items, no A11")):
            r = e["study1_ext"][key]
            rows.append([name, lab, f"{r['k']}/{r['n']}", f2(r["rate"]), ci(r["wilson95"]), ci(r["boot95"]), f"{1 - r['rate']:.2f}" if r["n"] else "--"])
    A(md_table(["Coder / rule", "Items", "k/n", "False-credit rate", "Wilson 95%", "Bootstrap 95%", "Specificity"], rows))
    A("")
    A("Known-groups contrast (share credited in P minus share credited in N; P and N benchmarks resampled separately):")
    A("")
    rows = []
    for name, e in ext.items():
        for key, lab in (("contrast_6", "6 items"), ("contrast_5_no_A11", "5 items, no A11")):
            c = e["study1_ext"][key]
            rows.append([name, lab, f2(c["P_share"]) if c else "--", f2(c["N_share"]) if c else "--",
                         f2(c["value"]) if c else "--", ci(c["boot95"]) if c else "--"])
    A(md_table(["Coder / rule", "Items", "P share", "N share", "P minus N", "Bootstrap 95%"], rows))
    A("")
    A("Adjacent constructs, pooled Spearman rho (common cells; bootstrap over benchmarks):")
    A("")
    rows = []
    for name, e in ext.items():
        s2 = e["study2"]
        rows.append([name, s2["n_cells"], s2["n_benchmarks"], f2(s2["rho"]), ci(s2["rho_boot95"])])
    A(md_table(["Coder / rule", "Cells", "Benches", "Spearman rho", "Bootstrap 95%"], rows))
    A("")
    sm0 = next(iter(ext.values()))["study2"]["per_item_ci_summary"]
    A(f"Per agent item (items with at least {sm0['min_cells']} cells). Bootstrap over benchmarks. p: {sm0['p_method']}.")
    A("")
    rows = []
    for name, e in ext.items():
        s2 = e["study2"]
        for it, r in s2["per_item_ci"].items():
            if r["reported"]:
                rows.append([name, it, r["n"], r["benchmarks"], f2(r["rho"]), ci(r["boot95"]), "yes" if r["ci_excludes_0"] else "no",
                             f2(r["p_perm"], 3), f2(r["p_perm_holm"], 3), f2(r["p_t"], 3)])
            else:
                rows.append([name, it, r["n"], r["benchmarks"], "n < 8", "--", "--", "--", "--", "--"])
    A(md_table(["Coder / rule", "Item", "n", "Benches", "rho", "Bootstrap 95%", "CI excludes 0", "p (perm)", "Holm p (perm)", "p (t approx)"], rows))
    A("")
    A("Intervals excluding 0: " + "; ".join(
        f"{name} {e['study2']['per_item_ci_summary']['n_ci_exclude_0']} of {e['study2']['per_item_ci_summary']['items_reported']}"
        f" (Holm permutation p < 0.05: {e['study2']['per_item_ci_summary']['n_holm_perm_lt_05']})" for name, e in ext.items()) + ".")
    A("")
    A("Coder-coder agreement on the known-groups cells (credited = level >= 1, NA counts as not credited; common cells):")
    A("")
    rows = []
    for lab_, g in res["common"]["agreement"].items():
        rows.append([lab_, g["n"], g["benchmarks"], f2(g["raw_agreement"]), f2(g["kappa"]), f"{g['a_credited']}/{g['b_credited']}",
                     g["both_credited"], g["neither_credited"], f2(g["exact_level_agreement"])])
    A(md_table(["Cells", "n", "Benches", "Raw agreement", "Cohen kappa", "Credited by sonnet / OpenAI", "Both credit", "Neither", "Exact level agreement"], rows))
    A("")
    A("Coverage notes: " + " ".join(res["common"]["coverage_notes"]))
    A("")
    return "\n".join(L)


def write_summary(md: str) -> None:
    # newline="" keeps every other byte of the file (it has mixed LF/CRLF) exactly as it is
    with open(SUMMARY, encoding="utf-8", newline="") as f:
        txt = f.read()
    m = re.search(r"^## 11\. Known-groups and adjacent-construct validation.*?(?=^## \d+\. |\Z)", txt, re.S | re.M)
    if m:
        txt = txt[:m.start()] + md.rstrip() + "\n" + txt[m.end():]
    else:
        txt = txt.rstrip("\r\n") + "\n\n" + md.rstrip() + "\n"
    with open(SUMMARY, "w", encoding="utf-8", newline="") as f:
        f.write(txt)


def norm_json(o):
    return json.loads(json.dumps(o))


def assert_subset(base, new, path="") -> int:
    """Every leaf of `base` must appear, equal, in `new` (new may add keys). Returns the number of leaves compared."""
    if isinstance(base, dict):
        assert isinstance(new, dict), f"{path}: not a dict"
        n = 0
        for k, v in base.items():
            assert k in new, f"{path}/{k}: missing"
            n += assert_subset(v, new[k], f"{path}/{k}")
        return n
    if isinstance(base, list):
        assert isinstance(new, list) and len(base) == len(new), f"{path}: list differs"
        return sum(assert_subset(x, y, f"{path}[{i}]") for i, (x, y) in enumerate(zip(base, new)))
    assert base == new, f"{path}: {base!r} != {new!r}"
    return 1


def main() -> None:
    # Release note: runs only in the authors' working tree; stop with the missing inputs named.
    miss = [str(p) for p in (KG / "verified", GOLD, BASELINE) if not p.exists()]
    if miss:
        sys.exit("analysis/known_groups.py cannot run from the public release; these inputs are not redistributed or not present: "
                 + "; ".join(miss) + ". The released output is results/analysis_out/known_groups.json.")
    per, resolved = load_levels()
    assert "sonnet" in per, "no Claude (sonnet) verified records"
    info = coder_info(per)
    lab = {r: info[r]["label"] for r in info}
    packets_dir = KG / "packets"
    packets = {p.name for p in packets_dir.iterdir() if p.is_dir()} if packets_dir.exists() else {b for d in per.values() for b, _ in d}
    bb, abc = load_expert()
    cells = expert_cells(bb, abc, packets)
    son, cod = per["sonnet"], per.get("codex")

    # ---- which benchmarks each coder covers
    have = {r: {b for b, _ in d} for r, d in per.items()}
    missing = {r: sorted(packets - have[r]) for r in per}
    common_keys = (set(son) & set(cod)) if cod else set(son)
    common_b = sorted({b for b, _ in common_keys})
    only_codex = sorted(have.get("codex", set()) - have["sonnet"])
    only_sonnet = sorted(have["sonnet"] - have.get("codex", set())) if cod else []
    n_cod = len(have.get("codex", ()))
    label = ((f"PARTIAL ({n_cod} of {len(packets)} codex packets)" if n_cod < len(packets)
              else f"COMPLETE ({n_cod} of {len(packets)} codex packets)") if cod else "Claude coder only")

    # ---- sets: legacy (sonnet = all cells; others = common cells) and common (all three on the same cells)
    legacy: dict[str, dict] = {"sonnet": son}
    common_sets: dict[str, dict] = {"sonnet": restrict(son, common_keys)}
    if cod:
        legacy[lab["codex"]] = restrict(cod, common_keys)
        common_sets[lab["codex"]] = restrict(cod, common_keys)
    if resolved:
        legacy["resolved"] = restrict(resolved, common_keys)
        common_sets["resolved"] = restrict(resolved, common_keys)

    res = {"coders": [lab[r] for r in per], "coder_info": {r: v for r, v in info.items()}, "seed": SEED, "n_boot": N_BOOT,
           "n_perm": N_PERM,
           "status": {"label": label, "packets": len(packets), "sonnet_benchmarks": len(have["sonnet"]),
                      "codex_benchmarks": n_cod, "missing_sonnet": missing["sonnet"], "missing_codex": missing.get("codex", [])},
           "study1": {}, "study2": {}, "coverage": {}}
    for name, lv in legacy.items():
        res["study1"][name] = study1(lv)
        res["study2"][name] = study2(lv, cells)
    res["expert_cells_available"] = len(cells)
    res["mapping"] = {k: {"betterbench": v[0], "abc": v[1]} for k, v in MAP.items()}
    for name in legacy:
        s = res["study1"][name]
        res["coverage"][name] = (f"N {s['n_benchmarks_present']}/13, P {s['p_benchmarks_present']}/10; missing N: "
                                 f"{', '.join(s['n_missing']) or 'none'}; missing P: {', '.join(s['p_missing']) or 'none'}")

    # ---- assertion: the Claude-only results equal the frozen 2026-10-14 values (raises before anything is written)
    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    n_leaves = assert_subset(base["study1"]["sonnet"], norm_json(res["study1"]["sonnet"]), "study1/sonnet")
    n_leaves += assert_subset(base["study2"]["sonnet"], norm_json(res["study2"]["sonnet"]), "study2/sonnet")
    res["claude_only_assertion"] = {"result": "passed", "leaves_compared": n_leaves, "baseline": BASELINE.name,
                                    "baseline_original_sha256": base.get("original_sha256")}

    # ---- common scope: extended outputs for each coder and the resolved rule
    com = {"n_cells": len(common_keys), "benchmarks": common_b,
           "excluded_openai_only_benchmarks": only_codex, "excluded_claude_only_benchmarks": only_sonnet,
           "sets": {}, "agreement": {}, "coverage_notes": []}
    for name, lv in common_sets.items():
        s1 = res["study1"][name] if name != "sonnet" else study1(lv)
        s2 = res["study2"][name] if name != "sonnet" else study2(lv, cells)
        e = study1_ext(lv)
        # internal consistency: the extended pooled/contrast blocks reproduce the legacy ones on the same cells
        assert norm_json(e["pooled_6"]["boot95"]) == norm_json(s1["N_false_credit"]["boot95"]) and e["pooled_6"]["k"] == s1["N_false_credit"]["k"]
        assert (e["contrast_6"] is None) == (s1["contrast_P_minus_N"] is None)
        if e["contrast_6"]:
            assert norm_json(e["contrast_6"]["boot95"]) == norm_json(s1["contrast_P_minus_N"]["boot95"])
        com["sets"][name] = {"study1": s1, "study1_ext": e, "study2": s2}
    if cod:
        a, b = restrict(son, common_keys), restrict(cod, common_keys)
        for lab_, bs in (("N (static, 13) x six items", NEG), ("P (agentic, 10) x six items", POS), ("N+P (23) x six items", NEG + POS)):
            com["agreement"][lab_] = agreement(a, b, bs, TEST_ITEMS)
        com["agreement"]["N+P (23) x five items, no A11"] = agreement(a, b, NEG + POS, TEST_ITEMS_NO_A11)
        com["agreement"]["all 25 items, all common benchmarks (context)"] = agreement(
            a, b, common_b, [f"C{i}" for i in range(1, 15)] + [f"A{i}" for i in range(1, 12)])
    notes = []
    if only_codex:
        ob = set(only_codex)
        oc = {k: v for k, v in cod.items() if k[0] in ob}
        o2 = study2(oc, cells)
        com["openai_only"] = {"benchmarks": only_codex, "cells": len(oc),
                              "test_item_levels": {b: {i: oc.get((b, i)) for i in TEST_ITEMS} for b in only_codex},
                              "study2_expert_cells_used": o2["n_cells"], "study2_rho": o2["rho"]}
        many = len(only_codex) > 1
        notes.append(f"{', '.join(only_codex)} {'were' if many else 'was'} coded by the OpenAI coder only (the Claude coder hit its context limit) and "
                     f"{'are' if many else 'is'} excluded from every pooled or two-coder comparison; neither group N nor group P contains "
                     f"{'them' if many else 'it'}, so Study 1 is unaffected. OpenAI-only levels on A3/A5/A6/A7/A9/A11: " + "; ".join(
                         f"{b} " + "/".join(str(oc.get((b, i), "--")) for i in TEST_ITEMS) for b in only_codex)
                     + f"; {o2['n_cells']} Study 2 expert cells (descriptive rho on those cells {f2(o2['rho'])}; not pooled).")
    if only_sonnet:
        notes.append("Coded by the Claude coder only: " + ", ".join(only_sonnet) + " (OpenAI response pending); they enter 11.1 and 11.2 for `sonnet` only.")
    if cod and missing["codex"]:
        notes.append("OpenAI packets still missing: " + ", ".join(missing["codex"]) + ".")
    com["coverage_notes"] = notes
    res["common"] = com

    (OUT / "known_groups.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    write_summary(markdown(res))

    # ---- compact print
    print(f"STATUS: {label}")
    for r in per:
        print(f"  {lab[r]:>14}: {len(have[r])} benchmarks coded, {len(per[r])} cells" + (f", model_id {info[r]['model_id']}" if r == "codex" else ""))
    if info.get("codex", {}).get("substitute_for"):
        print(f"  {lab['codex']} is a disclosed substitute for {info['codex']['substitute_for']}")
    print(f"  benchmarks WITHOUT a codex response ({len(missing.get('codex', []))}): {', '.join(missing.get('codex', [])) or 'none'}")
    print(f"  benchmarks WITHOUT a sonnet response ({len(missing['sonnet'])}): {', '.join(missing['sonnet']) or 'none'}")
    print(f"  common cells {len(common_keys)} over {len(common_b)} benchmarks; coded by codex only: {', '.join(only_codex) or 'none'}")
    print(f"  claude-only assertion: passed ({n_leaves} leaves equal to {BASELINE.name})")
    for name in legacy:
        s1, s2 = res["study1"][name], res["study2"][name]
        n, p = s1["N_false_credit"], s1["P_credited"]
        c = s1["contrast_P_minus_N"]
        print(f"[{name}] N {s1['n_benchmarks_present']}/13 P {s1['p_benchmarks_present']}/10 | "
              f"N false credit {n['k']}/{n['n']} = {f2(n['rate'])} W{ci(n['wilson95'])} B{ci(n['boot95'])} "
              f"(NA {s1['N_cell_levels']['NA']}, 0 {s1['N_cell_levels']['0']}) | "
              f"P credited {p['k']}/{p['n']} = {f2(p['rate'])} | P-N {f2(c['value']) if c else '--'} {ci(c['boot95']) if c else ''}")
        print(f"      Study2 cells {s2['n_cells']} ({s2['n_benchmarks']} benches, {s2['n_coder_na_dropped']} NA dropped) "
              f"rho {f2(s2['rho'])} {ci(s2['rho_boot95'])} | dich agree {f2(s2['dichotomous']['raw_agreement'])} "
              f"kappa {f2(s2['dichotomous']['kappa'])}")
    print("--- common scope ---")
    for name, e in com["sets"].items():
        x, s2 = e["study1_ext"], e["study2"]
        print(f"[{name}] per-item false credit: " + ", ".join(f"{i} {x['per_item'][i]['k']}/{x['per_item'][i]['n']}" for i in TEST_ITEMS))
        for key in ("pooled_6", "pooled_5_no_A11"):
            r = x[key]
            print(f"   {key}: {r['k']}/{r['n']} = {f2(r['rate'])} W{ci(r['wilson95'])} B{ci(r['boot95'])}")
        for key in ("contrast_6", "contrast_5_no_A11"):
            r = x[key]
            print(f"   {key}: P {f2(r['P_share'])} N {f2(r['N_share'])} diff {f2(r['value'])} B{ci(r['boot95'])}" if r else f"   {key}: --")
        sm = s2["per_item_ci_summary"]
        print(f"   adjacent: pooled rho {f2(s2['rho'])} B{ci(s2['rho_boot95'])} (n={s2['n_cells']}); per-item CIs excluding 0: "
              f"{sm['n_ci_exclude_0']}/{sm['items_reported']}; Holm perm p<.05: {sm['n_holm_perm_lt_05']}")
        for it, r in s2["per_item_ci"].items():
            if r["reported"]:
                print(f"      {it}: n={r['n']} rho {f2(r['rho'])} B{ci(r['boot95'])} p_perm {f2(r['p_perm'], 3)} holm {f2(r['p_perm_holm'], 3)} p_t {f2(r['p_t'], 3)}")
    for k, g in com["agreement"].items():
        print(f"agreement [{k}]: n={g['n']} raw {f2(g['raw_agreement'])} kappa {f2(g['kappa'])} (sonnet {g['a_credited']}, openai {g['b_credited']})")
    for n_ in notes:
        print("NOTE:", n_)
    print(f"wrote {OUT / 'known_groups.json'} and section 11 of {SUMMARY}")


if __name__ == "__main__":
    main()
