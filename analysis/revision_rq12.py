"""Revision analyses for RQ1 and RQ2 (simulated reviews, round 1: R1 M1c, M2, M3, M3b, M5; R2; R3).

Everything is computed from existing outputs; nothing is rescored. Reuses analysis/common.py, analysis/rq1_rq2.py
(module and item prevalence, alpha table) and the scorer (agentaudit.gold, agentaudit.resolve, agentaudit.stats).
Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, percentile 95% CI; within a block every
statistic uses the same resamples. Like-for-like gold agreement of coder pairs is NOT computed here
(analysis/gold_coder_pair.py).

Blocks
  1 ABLATION     rules {Claude only, OpenAI only, union, intersection without family requirement, current resolved
                 rule, current rule on raw scores (no quote verification)} (+ union on raw scores as an extra):
                 agreement with ABC gold (Cohen kappa) and BetterBench gold (quadratic weighted kappa) on the cells of
                 audit/gold_*/agreement, and RQ1 module shares on the 44 audit benchmarks. Counts: raw 1+ scores
                 removed by quote verification; cells changed by the family requirement.
  2 BOUNDS       RQ1 per-item and per-module prevalence as the interval [current rule, union rule].
  3 PABAK/AC     prevalence-adjusted agreement with gold: PABAK, Gwet AC1 (ABC, binary), weighted PABAK and Gwet AC2
                 with quadratic weights (BetterBench), confusion matrices.
  4 THRESHOLDS   per item share reported (>=1) and fully reported (=2), Wilson CIs, next to the cross-family alpha.
  5 MISCLASS     Rogan-Gladen correction of the module prevalence with sensitivity and specificity of the resolved
                 score against the experts (rates transferred from ABC / BetterBench items to ours: an assumption).
  6 EXCLUDE PILOT RQ1 shares and cross-family alpha without the five pilot benchmarks.

Run from the project root:
    python analysis/revision_rq12.py                  # computes, writes CSV/JSON/tables
    python analysis/revision_rq12.py --write-summary  # also (re)writes section 6 of analysis/out/RESULTS_SUMMARY.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, ROOT, SEED, TABLES, booktabs, fci, fnum, tex_escape, write_csv  # noqa: E402

import rq1_rq2 as R  # noqa: E402
from agentaudit import gold as G  # noqa: E402
from agentaudit.agree import load_scores  # noqa: E402
from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402
from agentaudit.resolve import resolve_cell  # noqa: E402
from agentaudit.stats import cohen_kappa, weighted_kappa, wilson  # noqa: E402

N_BOOT = 2000
AUDIT = ROOT / "audit"
RDIR = ROOT / "research"
RUNS = {"abc": ROOT / "audit" / "gold_abc", "betterbench": ROOT / "audit" / "gold_bb"}
SUMMARY = OUT / "RESULTS_SUMMARY.md"
CMD = "python analysis/revision_rq12.py --write-summary"
FAM = {"codex": "openai", "sonnet": "anthropic"}
# Pilot benchmarks (rubric/pilot: round 1 coderA/B_scores.csv, round 2 r2_coder*_scores.csv; decision log 2026-10-04;
# protocol-v1 "five pilot benchmarks"), as run slugs in audit/.
PILOT = {"agentclinic": "AgentClinic", "fhir-agentbench": "FHIR-AgentBench", "healthagentbench": "HealthAgentBench",
         "ehr-chatqa": "EHR-ChatQA", "medagentsim": "MedAgentSim"}
RULES = [
    ("claude", "Claude only (Sonnet), verified"),
    ("openai", "OpenAI only (gpt-5.5), verified"),
    ("union", "Union: max of the two verified scores"),
    ("nofam", "Intersection, no family requirement"),
    ("current", "Resolved rule (verified, both coders)"),
    ("raw", "Resolved rule on raw scores (no quote verification)"),
    ("union_raw", "Union on raw scores (extra)"),
]
RULE_LABEL = dict(RULES)
SET_LABEL = {"abc": "ABC", "betterbench": "BetterBench"}


# ------------------------------------------------------------------ rules
def _votes(votes: dict) -> dict:
    return {c: {"raw": v["raw"], "effective": v["effective"], "family": FAM[c]} for c, v in votes.items()}


def _union(votes: dict, key: str):
    nums = [v[key] for v in votes.values() if v[key] != "NA"]
    return max(nums) if nums else "NA"


def apply_rule(rule: str, votes: dict, levels: tuple):
    """votes: coder -> {"raw", "effective"}; levels: positive levels top down. Returns a level or "NA"."""
    v = _votes(votes)
    if rule == "claude":
        return v["sonnet"]["effective"]
    if rule == "openai":
        return v["codex"]["effective"]
    if rule == "union":
        return _union(v, "effective")
    if rule == "union_raw":
        return _union(v, "raw")
    if rule == "current":
        return resolve_cell(v, True, levels)["final"]
    if rule == "nofam":
        return resolve_cell(v, False, levels)["final"]
    if rule == "raw":
        r = {c: {"raw": x["raw"], "effective": x["raw"], "family": x["family"]} for c, x in v.items()}
        return resolve_cell(r, True, levels)["final"]
    raise ValueError(rule)


# ------------------------------------------------------------------ bootstrap helpers
def boot_multi(groups: dict[str, list], funcs: dict, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Resample benchmarks with replacement; every function in ``funcs`` sees the same resamples. Percentile 95% CI."""
    keys = sorted(groups)
    out = {k: None for k in funcs}
    if len(keys) < 2:
        return out
    rng = random.Random(seed)
    vals: dict[str, list] = {k: [] for k in funcs}
    for _ in range(n_boot):
        units: list = []
        for _k in range(len(keys)):
            units.extend(groups[keys[rng.randrange(len(keys))]])
        for k, f in funcs.items():
            v = f(units)
            if v is not None:
                vals[k].append(v)
    for k, vs in vals.items():
        if len(vs) >= 20:
            vs.sort()
            out[k] = [vs[int(0.025 * (len(vs) - 1))], vs[int(0.975 * (len(vs) - 1))]]
    return out


def chance_corrected(g: list, p: list, levels: tuple) -> dict:
    """Raw agreement, PABAK, Gwet AC1 (unweighted, q categories), and for q > 2 the quadratic-weighted analogues:
    weighted agreement, weighted PABAK ((pa_w - mean w)/(1 - mean w), uniform marginals), Gwet AC2.

    AC1: pe = sum_k pi_k (1 - pi_k) / (q - 1), pi_k = mean of the two raters' proportions in category k.
    AC2: pe = T_w / (q (q - 1)) * sum_k pi_k (1 - pi_k), T_w = sum_kl w_kl, w_kl = 1 - ((k - l) / (q - 1))^2."""
    n = len(g)
    q = len(levels)
    if not n or q < 2:
        return {}
    idx = {v: i for i, v in enumerate(levels)}
    gi, pi_ = [idx[x] for x in g], [idx[x] for x in p]
    po = sum(a == b for a, b in zip(gi, pi_)) / n
    pk = [(gi.count(k) + pi_.count(k)) / (2 * n) for k in range(q)]
    spq = sum(x * (1 - x) for x in pk)
    out = {"n": n, "po": po, "pabak": (po - 1 / q) / (1 - 1 / q)}
    pe1 = spq / (q - 1)
    out["gwet_ac1"] = (po - pe1) / (1 - pe1) if pe1 < 1 else None
    if q > 2:
        def w(a, b):
            return 1 - ((a - b) / (q - 1)) ** 2
        pa = sum(w(a, b) for a, b in zip(gi, pi_)) / n
        tw = sum(w(a, b) for a in range(q) for b in range(q))
        pe2 = tw / (q * (q - 1)) * spq
        peu = tw / (q * q)
        out["pa_weighted"] = pa
        out["pabak_weighted"] = (pa - peu) / (1 - peu)
        out["gwet_ac2"] = (pa - pe2) / (1 - pe2) if pe2 < 1 else None
    return out


def _stat_fn(key: str, levels: tuple):
    def f(units):
        if not units:
            return None
        return chance_corrected([u[0] for u in units], [u[1] for u in units], levels).get(key)
    return f


# ------------------------------------------------------------------ audit data
def audit_levels(resolved: dict[str, dict]) -> dict[str, dict[str, dict]]:
    """rule -> bench -> item -> level, from the votes stored in resolved/<bench>.json (both coders, raw and effective)."""
    out: dict[str, dict] = {r: {} for r, _ in RULES}
    for b, cells in resolved.items():
        for rule, _ in RULES:
            out[rule][b] = {}
        for it, c in cells.items():
            assert len(c["votes"]) == 2, (b, it)
            for rule, _ in RULES:
                out[rule][b][it] = apply_rule(rule, c["votes"], (2, 1))
    return out


def as_resolved(levels_b: dict) -> dict:
    """Shape expected by rq1_rq2.prevalence / module_summary: {bench: {item: {"final": level}}}."""
    return {b: {it: {"final": lv} for it, lv in cells.items()} for b, cells in levels_b.items()}


def verification_counts(resolved: dict[str, dict]) -> dict:
    out = {}
    for coder in ("codex", "sonnet"):
        n = pos = removed = na_raw = 0
        by_level = Counter()
        for cells in resolved.values():
            for c in cells.values():
                v = c["votes"][coder]
                n += 1
                if v["raw"] == "NA":
                    na_raw += 1
                    continue
                if v["raw"] >= 1:
                    pos += 1
                    if v["effective"] == 0:
                        removed += 1
                        by_level[int(v["raw"])] += 1
        out[coder] = {"cells": n, "raw_positive": pos, "removed": removed, "removed_share_of_positive": removed / pos if pos else None,
                      "removed_raw1": by_level[1], "removed_raw2": by_level[2], "raw_na": na_raw}
    return out


def family_changes(resolved: dict[str, dict]) -> dict:
    changed = changed_raw = total = 0
    differ_union = differ_raw = 0
    detail = []
    for b, cells in resolved.items():
        for it, c in cells.items():
            total += 1
            a = apply_rule("current", c["votes"], (2, 1))
            f = apply_rule("nofam", c["votes"], (2, 1))
            r = apply_rule("raw", c["votes"], (2, 1))
            u = apply_rule("union", c["votes"], (2, 1))
            assert a == c["final"], (b, it, a, c["final"])  # my current rule reproduces the stored final
            if a != f:
                changed += 1
                detail.append((b, it, a, f))
            differ_union += a != u
            differ_raw += a != r
            assert r == c["majority_final"], (b, it, r, c["majority_final"])  # raw rule == stored majority variant
    return {"cells": total, "changed_by_family_requirement": changed, "changed_detail": detail,
            "current_differs_from_union": differ_union, "current_differs_from_raw_rule": differ_raw}


# ------------------------------------------------------------------ gold data
def gold_cells(set_name: str) -> dict:
    cfg = G.set_cfg(set_name)
    gold = G.load_gold(set_name, RDIR)
    ids = set(G.items_for_set(set_name))
    preds, fam = G.load_predictions(RUNS[set_name], set_name)
    assert sorted(preds) == ["codex", "sonnet"], sorted(preds)
    both = {k: {c: preds[c][k] for c in ("codex", "sonnet")} for k in preds["codex"]
            if k in preds["sonnet"]}
    return {"cfg": cfg, "gold": gold, "ids": ids, "preds": preds, "both": both}


def rule_pairs(gc: dict, rule: str) -> list[tuple]:
    """(bench, item, gold, pred) on the cells of the scorer's agreement.json: a single coder uses its own cells,
    every other rule the cells scored by both coders. Cells with a gold value only, items of the set only."""
    cfg, gold, ids = gc["cfg"], gc["gold"], gc["ids"]
    top = cfg["top_down"]
    out = []
    if rule in ("claude", "openai"):
        c = "sonnet" if rule == "claude" else "codex"
        for (b, i), v in sorted(gc["preds"][c].items()):
            if (b, i) in gold and i in ids:
                out.append((b, i, gold[(b, i)], v["effective"]))
        return out
    for (b, i), votes in sorted(gc["both"].items()):
        if (b, i) in gold and i in ids:
            out.append((b, i, gold[(b, i)], apply_rule(rule, votes, top)))
    return out


def conf_counts(pairs: list[tuple], levels: tuple) -> dict:
    used = [(g, p) for _, _, g, p in pairs if g != "NA" and p != "NA"]
    return {str(g): {str(p): sum(1 for a, b in used if a == g and b == p) for p in levels} for g in levels}


def gold_block(n_boot: int) -> dict:
    res: dict = {}
    for s in ("abc", "betterbench"):
        gc = gold_cells(s)
        cfg = gc["cfg"]
        levels = tuple(cfg["levels"])
        rec = json.loads((G.gold_run_dir(RUNS[s], s) / "agreement" / "agreement.json").read_text(encoding="utf-8"))
        blk: dict = {"rules": {}, "validation": {}}
        pairs_by_rule: dict = {}
        for rule, _ in RULES:
            pairs = rule_pairs(gc, rule)
            pairs_by_rule[rule] = pairs
            st = G.agreement_stats(pairs, cfg, n_boot, SEED)
            used = [(b, i, g, p) for b, i, g, p in pairs if g != "NA" and p != "NA"]
            groups: dict[str, list] = {}
            for b, _, g, p in used:
                groups.setdefault(b, []).append((g, p))
            keys = ["pabak", "gwet_ac1"] + (["pabak_weighted", "gwet_ac2"] if len(levels) > 2 else [])
            point = chance_corrected([u[2] for u in used], [u[3] for u in used], levels)
            ci = boot_multi(groups, {k: _stat_fn(k, levels) for k in keys}, n_boot)
            blk["rules"][rule] = {
                "n": st.get("n_cells"), "n_gold_na": st.get("n_gold_na"), "n_pred_na": st.get("n_pred_na_where_gold_scored"),
                "benchmarks": len(groups),
                "raw_agreement": (st.get("raw_agreement") or {}).get("rate"),
                "cohen_kappa": st.get("cohen_kappa"),
                "weighted_kappa_quadratic": st.get("weighted_kappa_quadratic"),
                "primary_statistic": st.get("primary_statistic"), "primary_value": st.get("primary_value"),
                "primary_ci": st.get("primary_ci95_bootstrap_over_benchmarks"),
                "majority_baseline": st.get("majority_class_baseline_agreement"),
                "within_one": (st.get("within_one_level") or {}).get("rate"),
                "confusion": st.get("confusion") or conf_counts(pairs, levels),
                **{k: point.get(k) for k in keys + ["pa_weighted"] if k in point},
                "ci": ci, "groups": groups}
        # reproduction of agreement.json
        for rule, ref in (("openai", rec["by_coder"]["codex"]), ("claude", rec["by_coder"]["sonnet"]),
                          ("current", rec["resolved"])):
            mine = blk["rules"][rule]
            ok = (mine["n"] == ref["n_cells"] and abs(mine["primary_value"] - ref["primary_value"]) < 1e-9
                  and abs(mine["raw_agreement"] - ref["raw_agreement"]["rate"]) < 1e-9
                  and all(abs(a - b) < 1e-9 for a, b in zip(mine["primary_ci"], ref["primary_ci95_bootstrap_over_benchmarks"])))
            blk["validation"][rule] = {"reproduces_agreement_json": bool(ok), "n": mine["n"], "n_ref": ref["n_cells"]}
            assert ok, (s, rule, mine["n"], ref["n_cells"], mine["primary_value"], ref["primary_value"])
        # paired difference of the primary statistic, each rule minus the best single coder (common cells, same resamples)
        best = max(("claude", "openai"), key=lambda r: blk["rules"][r]["primary_value"])
        wk = (lambda a, b: cohen_kappa(a, b)) if cfg["primary"] == "cohen_kappa" else (lambda a, b: weighted_kappa(a, b, list(levels), "quadratic"))
        bp = {(b, i): (g, p) for b, i, g, p in pairs_by_rule[best] if g != "NA" and p != "NA"}
        blk["diff_vs_best"] = {"best": best}
        for rule, _ in RULES:
            if rule in ("claude", "openai"):
                continue
            rp = {(b, i): p for b, i, g, p in pairs_by_rule[rule] if g != "NA" and p != "NA"}
            grp: dict[str, list] = {}
            for (b, i), (gv, pb) in sorted(bp.items()):
                if (b, i) in rp:
                    grp.setdefault(b, []).append((gv, rp[(b, i)], pb))

            def dstat(units, wk=wk):
                g_ = [u[0] for u in units]
                a, c = wk(g_, [u[1] for u in units]), wk(g_, [u[2] for u in units])
                return None if a is None or c is None else a - c
            allu = [u for us in grp.values() for u in us]
            blk["diff_vs_best"][rule] = {"diff": dstat(allu), "n": len(allu),
                                         "ci": boot_multi(grp, {"d": dstat}, n_boot)["d"]}
        # verification and family counts on the gold cells
        blk["verification"] = {}
        for c in ("codex", "sonnet"):
            pos = rem = 0
            for (b, i), v in gc["preds"][c].items():
                if (b, i) in gc["gold"] and i in gc["ids"] and v["raw"] != "NA" and v["raw"] >= 1:
                    pos += 1
                    rem += v["effective"] == 0
            blk["verification"][c] = {"raw_positive": pos, "removed": rem}
        fam_ch = 0
        for (b, i), votes in gc["both"].items():
            if (b, i) in gc["gold"] and i in gc["ids"]:
                fam_ch += apply_rule("current", votes, cfg["top_down"]) != apply_rule("nofam", votes, cfg["top_down"])
        blk["changed_by_family"] = fam_ch
        blk["levels"] = list(levels)
        blk["n_benchmarks_gold"] = len({b for (b, i) in gc["gold"] if i in gc["ids"]})
        res[s] = blk
    return res


# ------------------------------------------------------------------ RQ1 blocks
def rq1_block(levels_by_rule: dict, n_boot: int) -> dict:
    out = {"modules": {}, "items": {}}
    for rule, _ in RULES:
        d = as_resolved(levels_by_rule[rule])
        out["modules"][rule] = {r["module"]: r for r in R.module_summary(d, "final", n_boot)}
        out["items"][rule] = {r["item"]: r for r in R.prevalence(d, "final")}
    return out


def bounds_block(rq1: dict) -> dict:
    items = load_items()
    rows = []
    for it in ITEM_ORDER:
        c, u = rq1["items"]["current"][it], rq1["items"]["union"][it]
        ur = rq1["items"]["union_raw"][it]
        rows.append({"item": it, "module": items[it].module, "title": items[it].title, "n_applicable": c["n_applicable"],
                     "n_applicable_union": u["n_applicable"],
                     "reported_current": c["share_reported"], "reported_union": u["share_reported"],
                     "reported_union_raw": ur["share_reported"],
                     "reported_lo_ci": c["reported_lo"], "reported_hi_ci": u["reported_hi"],
                     "full_current": c["share_full"], "full_union": u["share_full"], "full_union_raw": ur["share_full"],
                     "full_lo_ci": c["full_lo"], "full_hi_ci": u["full_hi"]})
    mods = []
    for m in ("core", "agent"):
        c, u = rq1["modules"]["current"][m], rq1["modules"]["union"][m]
        ur = rq1["modules"]["union_raw"][m]
        mods.append({"module": m, "n_cells": c["n_applicable_cells"], "n_cells_union": u["n_applicable_cells"],
                     "reported_current": c["share_reported"], "reported_union": u["share_reported"],
                     "reported_union_raw": ur["share_reported"],
                     "reported_lo_ci": c["reported_boot_lo"], "reported_hi_ci": u["reported_boot_hi"],
                     "full_current": c["share_full"], "full_union": u["share_full"], "full_union_raw": ur["share_full"],
                     "full_lo_ci": c["full_boot_lo"], "full_hi_ci": u["full_boot_hi"]})
    return {"items": rows, "modules": mods}


# ------------------------------------------------------------------ thresholds (alpha next to prevalence)
def threshold_block(resolved: dict, benches: list[str], alpha_full: list[dict]) -> dict:
    prev = {r["item"]: r for r in R.prevalence(resolved, "final")}
    alpha = {r["item"]: r for r in alpha_full if r["kind"] == "all_coders" and r["scope"] == "item"}
    cells, _ = load_scores(AUDIT, benches)
    rows = []
    cross = {}
    for it in ITEM_ORDER:
        ct = Counter()
        for (b, i), v in cells.items():
            if i == it and "codex" in v and "sonnet" in v:
                ct[(v["codex"], v["sonnet"])] += 1
        both = [(a, c) for (a, c), n in ct.items() for _ in range(n) if a != "NA" and c != "NA"]
        n = len(both)
        exact = sum(a == c for a, c in both)
        ge1 = sum((a >= 1) == (c >= 1) for a, c in both)
        eq2 = sum((a == 2) == (c == 2) for a, c in both)
        cross[it] = {f"{a}|{c}": n_ for (a, c), n_ in sorted(ct.items(), key=str)}
        p, al = prev[it], alpha.get(it, {})
        rows.append({"item": it, "module": p["module"], "n_applicable": p["n_applicable"], "n_na": p["n_na"],
                     "n_reported": p["n_reported"], "share_reported": p["share_reported"], "reported_lo": p["reported_lo"],
                     "reported_hi": p["reported_hi"], "n_full": p["n_full"], "share_full": p["share_full"],
                     "full_lo": p["full_lo"], "full_hi": p["full_hi"],
                     "alpha": al.get("alpha"), "alpha_lo": al.get("ci_lo"), "alpha_hi": al.get("ci_hi"),
                     "alpha_units": al.get("units"), "alpha_benchmarks": al.get("benchmarks"),
                     "n_pairs_both_scored": n, "exact_agreement": exact / n if n else None,
                     "agreement_reported_ge1": ge1 / n if n else None, "agreement_full_eq2": eq2 / n if n else None})
    return {"rows": rows, "crosstabs": cross}


# ------------------------------------------------------------------ misclassification
def rogan_gladen(p: float, se: float, sp: float) -> float | None:
    j = se + sp - 1
    return (p + sp - 1) / j if j > 0 else None


def misclass_block(resolved: dict, levels_by_rule: dict, gold: dict, n_boot: int) -> dict:
    """Core and agent module prevalence (resolved rule) corrected with sensitivity and specificity of the resolved
    score against the experts. Binarisations: ABC: the ABC binary scale (resolved level 1 = satisfied). BetterBench:
    resolved >= t versus expert >= t, t = 2 (partially met or better) for the reported share and t = 3 (fully met) for the
    fully-reported share. Se and Sp come from gold benchmarks (resampled), the apparent prevalence from the 44 audit
    benchmarks (resampled independently); both resampled in the same replicate."""
    items = load_items()
    mods = {m: [i for i in ITEM_ORDER if items[i].module == m] for m in ("core", "agent")}
    cur = levels_by_rule["current"]

    def audit_groups(m: str, thr: int) -> dict[str, list]:
        g = {}
        for b, cells in cur.items():
            u = [1 if cells[i] >= thr else 0 for i in mods[m] if i in cells and cells[i] != "NA"]
            if u:
                g[b] = u
        return g

    out = {"rows": []}
    specs = [("abc", "reported", 1, 1), ("abc", "full", 2, 1), ("betterbench", "reported", 1, 2), ("betterbench", "full", 2, 3)]
    for s, share, audit_thr, gold_thr in specs:
        gp = [(b, i, g, p) for b, i, g, p in rule_pairs(gold_cells(s), "current") if g != "NA" and p != "NA"]
        ggroups: dict[str, list] = {}
        for b, _, g, p in gp:
            ggroups.setdefault(b, []).append((1 if g >= gold_thr else 0, 1 if p >= gold_thr else 0))

        def se_sp(units):
            tp = sum(1 for g, p in units if g == 1 and p == 1)
            fn = sum(1 for g, p in units if g == 1 and p == 0)
            tn = sum(1 for g, p in units if g == 0 and p == 0)
            fp = sum(1 for g, p in units if g == 0 and p == 1)
            return tp, fn, tn, fp
        units_all = [u for us in ggroups.values() for u in us]
        tp, fn, tn, fp = se_sp(units_all)
        se, sp = tp / (tp + fn) if tp + fn else None, tn / (tn + fp) if tn + fp else None
        se_ci, sp_ci = wilson(tp, tp + fn), wilson(tn, tn + fp)
        for m in ("core", "agent"):
            ag = audit_groups(m, audit_thr)
            ua = [u for us in ag.values() for u in us]
            p_app = sum(ua) / len(ua)
            est = rogan_gladen(p_app, se, sp)
            rng = random.Random(SEED)
            akeys, gkeys = sorted(ag), sorted(ggroups)
            vals, clipped, dropped = [], [], 0
            for _ in range(n_boot):
                a_units = [u for _k in range(len(akeys)) for u in ag[akeys[rng.randrange(len(akeys))]]]
                g_units = [u for _k in range(len(gkeys)) for u in ggroups[gkeys[rng.randrange(len(gkeys))]]]
                t1, f1, t0, f0 = se_sp(g_units)
                if not (t1 + f1 and t0 + f0):
                    dropped += 1
                    continue
                v = rogan_gladen(sum(a_units) / len(a_units), t1 / (t1 + f1), t0 / (t0 + f0))
                if v is None or (t1 / (t1 + f1) + t0 / (t0 + f0) - 1) < 0.05:
                    dropped += 1
                    continue
                vals.append(v)
                clipped.append(min(1.0, max(0.0, v)))
            vals.sort()
            clipped.sort()

            def pct(v, q):
                return v[int(q * (len(v) - 1))] if v else None
            out["rows"].append({
                "set": s, "share": share, "module": m, "audit_threshold": f">={audit_thr}", "gold_threshold": f">={gold_thr}" if s == "betterbench" else "binary",
                "gold_positive": tp + fn, "gold_negative": tn + fp, "tp": tp, "fn": fn, "tn": tn, "fp": fp,
                "sensitivity": se, "sens_lo": se_ci[0], "sens_hi": se_ci[1], "specificity": sp, "spec_lo": sp_ci[0], "spec_hi": sp_ci[1],
                "youden_j": se + sp - 1, "apparent": p_app, "corrected": est,
                "corrected_clipped": min(1.0, max(0.0, est)) if est is not None else None,
                "ci_lo": pct(vals, 0.025), "ci_hi": pct(vals, 0.975),
                "ci_clipped_lo": pct(clipped, 0.025), "ci_clipped_hi": pct(clipped, 0.975),
                "boot_used": len(vals), "boot_dropped_j_le_0.05": dropped, "n_audit_cells": len(ua),
                "n_audit_benchmarks": len(ag), "n_gold_benchmarks": len(ggroups)})
    return out


# ------------------------------------------------------------------ pilot exclusion
def pilot_block(resolved: dict, alpha_full_rows: list[dict], n_boot: int) -> dict:
    missing = [b for b in PILOT if b not in resolved]
    assert not missing, missing
    sub = {b: c for b, c in resolved.items() if b not in PILOT}
    out = {"excluded": sorted(PILOT), "n_full": len(resolved), "n_sub": len(sub)}
    out["modules_full"] = {r["module"]: r for r in R.module_summary(resolved, "final", n_boot)}
    out["modules_excl"] = {r["module"]: r for r in R.module_summary(sub, "final", n_boot)}
    out["items_full"] = {r["item"]: r for r in R.prevalence(resolved, "final")}
    out["items_excl"] = {r["item"]: r for r in R.prevalence(sub, "final")}
    a_full = [r for r in alpha_full_rows if r["kind"] == "all_coders"]
    a_sub = [r for r in R.alpha_table(AUDIT, sorted(sub), n_boot) if r["kind"] == "all_coders"]
    out["alpha_full"] = {(r["item"] or "overall"): r for r in a_full}
    out["alpha_excl"] = {(r["item"] or "overall"): r for r in a_sub}
    return out


# ------------------------------------------------------------------ output: csv and tables
def pc(x, nd=1):
    return "--" if x is None or x == "" else f"{100 * x:.{nd}f}"


def kci(x, ci, nd=2):
    return "--" if x is None else (f"{x:.{nd}f}" + (f" [{ci[0]:.{nd}f}, {ci[1]:.{nd}f}]" if ci else ""))


def write_outputs(res: dict) -> None:
    g, rq1, bnd, thr, mis, pil = res["gold"], res["rq1"], res["bounds"], res["thresholds"], res["misclass"], res["pilot"]
    # ablation csv
    rows = []
    for rule, label in RULES:
        row = {"rule": rule, "label": label}
        for s in ("abc", "betterbench"):
            r = g[s]["rules"][rule]
            tag = "abc" if s == "abc" else "bb"
            row.update({f"{tag}_n": r["n"], f"{tag}_raw_agreement": r["raw_agreement"], f"{tag}_cohen_kappa": r["cohen_kappa"],
                        f"{tag}_primary": r["primary_value"], f"{tag}_ci_lo": (r["primary_ci"] or [None, None])[0],
                        f"{tag}_ci_hi": (r["primary_ci"] or [None, None])[1]})
            if s == "betterbench":
                row["bb_weighted_kappa_quadratic"] = r["weighted_kappa_quadratic"]
        for m in ("core", "agent"):
            r = rq1["modules"][rule][m]
            row.update({f"{m}_cells": r["n_applicable_cells"], f"{m}_reported": r["share_reported"],
                        f"{m}_reported_boot_lo": r["reported_boot_lo"], f"{m}_reported_boot_hi": r["reported_boot_hi"],
                        f"{m}_full": r["share_full"], f"{m}_full_boot_lo": r["full_boot_lo"], f"{m}_full_boot_hi": r["full_boot_hi"]})
        rows.append(row)
    write_csv(OUT / "rev_ablation.csv", rows)
    write_csv(OUT / "rev_bounds_items.csv", bnd["items"])
    write_csv(OUT / "rev_bounds_modules.csv", bnd["modules"])
    # pabak / gwet + confusion
    prow, crow = [], []
    for s in ("abc", "betterbench"):
        for rule, label in RULES:
            r = g[s]["rules"][rule]
            ci = r["ci"]
            d = {"set": s, "rule": rule, "n": r["n"], "raw_agreement": r["raw_agreement"], "cohen_kappa": r["cohen_kappa"],
                 "weighted_kappa_quadratic": r.get("weighted_kappa_quadratic"), "pabak": r["pabak"],
                 "pabak_lo": (ci["pabak"] or [None, None])[0], "pabak_hi": (ci["pabak"] or [None, None])[1],
                 "gwet_ac1": r["gwet_ac1"], "ac1_lo": (ci["gwet_ac1"] or [None, None])[0], "ac1_hi": (ci["gwet_ac1"] or [None, None])[1],
                 "majority_baseline": r["majority_baseline"]}
            if s == "betterbench":
                d.update({"pabak_weighted": r["pabak_weighted"], "pabak_w_lo": (ci["pabak_weighted"] or [None, None])[0],
                          "pabak_w_hi": (ci["pabak_weighted"] or [None, None])[1], "gwet_ac2": r["gwet_ac2"],
                          "ac2_lo": (ci["gwet_ac2"] or [None, None])[0], "ac2_hi": (ci["gwet_ac2"] or [None, None])[1]})
            prow.append(d)
            for gl, rr in r["confusion"].items():
                for pl, n in rr.items():
                    crow.append({"set": s, "rule": rule, "gold": gl, "pred": pl, "count": n})
    write_csv(OUT / "rev_pabak.csv", prow)
    write_csv(OUT / "rev_confusion.csv", crow)
    write_csv(OUT / "rev_thresholds.csv", thr["rows"])
    write_csv(OUT / "rev_misclass.csv", mis["rows"])
    # pilot exclusion
    pm = []
    for mod in ("core", "agent"):
        a, b = pil["modules_full"][mod], pil["modules_excl"][mod]
        pm.append({"module": mod, "n_bench_full": pil["n_full"], "n_bench_excl": pil["n_sub"], "cells_full": a["n_applicable_cells"],
                   "cells_excl": b["n_applicable_cells"], "reported_full": a["share_reported"], "reported_excl": b["share_reported"],
                   "reported_excl_boot_lo": b["reported_boot_lo"], "reported_excl_boot_hi": b["reported_boot_hi"],
                   "full_full": a["share_full"], "full_excl": b["share_full"], "full_excl_boot_lo": b["full_boot_lo"],
                   "full_excl_boot_hi": b["full_boot_hi"]})
    write_csv(OUT / "rev_excl_pilot_modules.csv", pm)
    pi = []
    for it in ITEM_ORDER:
        a, b = pil["items_full"][it], pil["items_excl"][it]
        al, bl = pil["alpha_full"].get(it, {}), pil["alpha_excl"].get(it, {})
        pi.append({"item": it, "n_full": a["n_applicable"], "n_excl": b["n_applicable"], "reported_full": a["share_reported"],
                   "reported_excl": b["share_reported"], "full_full": a["share_full"], "full_excl": b["share_full"],
                   "alpha_full": al.get("alpha"), "alpha_excl": bl.get("alpha"), "alpha_excl_lo": bl.get("ci_lo"),
                   "alpha_excl_hi": bl.get("ci_hi")})
    write_csv(OUT / "rev_excl_pilot_items.csv", pi)
    # json (without the bootstrap groups)
    def clean(o):
        if isinstance(o, dict):
            return {str(k): clean(v) for k, v in o.items() if k != "groups"}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        return o
    (OUT / "revision_rq12.json").write_text(json.dumps(clean(res), indent=1, default=str), encoding="utf-8", newline="\n")

    # ---- tex
    hdr = "Generated by analysis/revision_rq12.py from scorer outputs. Do not edit by hand."
    trows = []
    for rule, label in RULES:
        if rule == "union_raw":
            continue
        a, b = g["abc"]["rules"][rule], g["betterbench"]["rules"][rule]
        c, ag = rq1["modules"][rule]["core"], rq1["modules"][rule]["agent"]
        trows.append([tex_escape(label), kci(a["primary_value"], a["primary_ci"]), kci(b["primary_value"], b["primary_ci"]),
                      pc(c["share_reported"], 0), pc(c["share_full"], 0), pc(ag["share_reported"], 0), pc(ag["share_full"], 0)])
    (TABLES / "rev_ablation.tex").write_text(booktabs(
        "lcccccc", ["Rule", "ABC $\\kappa$ [95\\% CI]", "BetterBench $\\kappa_w$ [95\\% CI]", "Core rep.", "Core full",
                    "Agent rep.", "Agent full"], trows,
        hdr + "\nGold agreement on the cells of audit/gold_*/agreement (ABC 198, BetterBench 423 to 425), bootstrap over benchmarks.\n"
              "Module shares in percent on the 44 audit benchmarks; rep. = level 1 or 2, full = level 2.\n"
              "With two coders of two families the family requirement is always met, so the intersection without it is identical to the current rule.",
        {1, 2}), encoding="utf-8", newline="\n")
    brow = []
    for m in bnd["modules"]:
        brow.append([tex_escape(m["module"].capitalize() + " module"), "", f"{pc(m['reported_current'], 0)}--{pc(m['reported_union'], 0)}",
                     f"{pc(m['full_current'], 0)}--{pc(m['full_union'], 0)}"])
    mid = {len(brow) - 1}
    for r in bnd["items"]:
        brow.append([r["item"], tex_escape(R.ITEM_LABEL.get(r["item"], r["title"])),
                     f"{pc(r['reported_current'], 0)}--{pc(r['reported_union'], 0)}",
                     f"{pc(r['full_current'], 0)}--{pc(r['full_union'], 0)}"])
    (TABLES / "rev_bounds.tex").write_text(booktabs(
        "llcc", ["Item", "Property", "Reported (\\%): current--union", "Fully reported (\\%): current--union"], brow,
        hdr + "\nInterval = [current resolved rule, union rule (higher verified score of the two coders)]; percent of applicable cells.\n"
              "Core item labels fall back to the frozen item titles.", mid), encoding="utf-8", newline="\n")
    prow2 = []
    for s in ("abc", "betterbench"):
        for rule in ("openai", "claude", "current", "union"):
            r = g[s]["rules"][rule]
            ci = r["ci"]
            if s == "abc":
                kap, pab, ac = r["cohen_kappa"], (r["pabak"], ci["pabak"]), (r["gwet_ac1"], ci["gwet_ac1"])
            else:
                kap, pab, ac = r["weighted_kappa_quadratic"], (r["pabak_weighted"], ci["pabak_weighted"]), (r["gwet_ac2"], ci["gwet_ac2"])
            lab = {"openai": "OpenAI (gpt-5.5)", "claude": "Claude Sonnet", "current": "Resolved", "union": "Union"}[rule]
            prow2.append([SET_LABEL[s], lab, str(r["n"]), fnum(r["raw_agreement"]), fnum(kap), kci(*pab), kci(*ac)])
    (TABLES / "rev_pabak.tex").write_text(booktabs(
        "llccccc", ["Gold set", "Coder or rule", "Cells", "Raw agr.", "$\\kappa$ or $\\kappa_w$",
                    "PABAK or weighted PABAK [95\\% CI]", "Gwet AC1 or AC2 [95\\% CI]"], prow2,
        hdr + "\nABC: binary, Cohen kappa, PABAK = 2 p_o - 1, Gwet AC1. BetterBench: 0-3 scale, quadratic-weighted kappa, weighted PABAK "
              "(uniform marginals), Gwet AC2 (quadratic weights). CIs: bootstrap over benchmarks.", {3}),
        encoding="utf-8", newline="\n")


# ------------------------------------------------------------------ markdown
def md(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def section6(res: dict) -> str:
    g, rq1, bnd, thr, mis, pil = res["gold"], res["rq1"], res["bounds"], res["thresholds"], res["misclass"], res["pilot"]
    ver, fam = res["verification"], res["family"]
    L: list[str] = []
    A = L.append
    A("## 6. Revision analyses (reviews round 1)")
    A("")
    A("Added 2026-10-06 for the simulated reviews (R1 M1c, M2, M3, M3b, M5; R2; R3). Nothing was rescored: every value comes from `audit/resolved/*.json` "
      "(both coders' raw and effective scores per cell), `audit/coding`, `audit/gold_abc/gold-abc` and `audit/gold_bb/gold-betterbench`. "
      "Reuses `analysis/common.py`, `analysis/rq1_rq2.py` (prevalence, module summary, alpha table) and the scorer (`agentaudit.gold`, `agentaudit.resolve`, `agentaudit.stats`). "
      "Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, percentile 95% CI. Values in percent unless stated. "
      "Like-for-like coder-pair kappa on gold cells is in section 5 (`analysis/gold_coder_pair.py`) and is not repeated.")
    A("")
    A("Command (project root):")
    A("")
    A("```")
    A(CMD)
    A("```")
    A("")
    A("Outputs: `analysis/out/revision_rq12.json` (all values), `analysis/out/rev_*.csv`, `paper/tables/rev_ablation.tex`, `rev_bounds.tex`, `rev_pabak.tex`. "
      "Validation inside the script (assertions): the single-coder and current-rule gold statistics equal `agreement.json` (n, primary statistic, raw agreement, bootstrap CI); "
      "the current rule re-derived from the stored votes equals the stored `final` in all 1,100 audit cells; the raw-score rule equals the stored `majority_final` in all 1,100 cells.")
    A("")
    # ---- 6.1
    A("### 6.1 Ablation of the resolution rule (R1 M3)")
    A("")
    A("Rules, per cell, from the two coders' scores (codex = OpenAI gpt-5.5; sonnet = Claude Sonnet). Effective score = raw score with a 1+ set to 0 when no quote verifies (and NA set to 0 where NA is not allowed). "
      "Claude only / OpenAI only: that coder's effective score (NA leaves the denominator). Union: higher of the two effective scores (NA only if both NA; one NA takes the other coder's score). "
      "Current: highest level at least two coders support at that level or above, supporters spanning two families, else 0 (a level beats NA; NA accepted only from both coders). "
      "Intersection without family requirement: the same with the family test off. Raw: the current rule applied to raw scores (no quote verification). Union raw: extra row.")
    A("")
    A("**Is the intersection without the family requirement identical to the current rule?** Yes, by construction and empirically. Exactly two coders exist (one per family), so any set of "
      "at least two supporters is one coder of each family and the family test is always met. "
      f"Cells changed by the family requirement: {fam['changed_by_family_requirement']} of {fam['cells']} audit cells; ABC gold: {g['abc']['changed_by_family']}; BetterBench gold: {g['betterbench']['changed_by_family']}. "
      "With these two coders the current rule is the lower of the two effective scores, except that one NA with one numeric score gives 0.")
    A("")
    A("Agreement with gold (same cells as `agreement.json`; ABC: Cohen kappa, binary; BetterBench: quadratic weighted kappa, 0-3). CI: bootstrap over benchmarks.")
    A("")
    rows = []
    for rule, label in RULES:
        a, b = g["abc"]["rules"][rule], g["betterbench"]["rules"][rule]
        rows.append([label, a["n"], fnum(a["raw_agreement"]), kci(a["primary_value"], a["primary_ci"]), b["n"], fnum(b["raw_agreement"]),
                     kci(b["primary_value"], b["primary_ci"]), fnum(b["cohen_kappa"])])
    A(md(["Rule", "ABC n", "ABC raw agr.", "ABC Cohen kappa [95% CI]", "BB n", "BB raw agr.", "BB weighted kappa (quad.) [95% CI]", "BB unweighted kappa"], rows))
    A("")
    others = [r for r, _ in RULES if r not in ("claude", "openai")]
    rows = []
    for r in others:
        da, db = g["abc"]["diff_vs_best"][r], g["betterbench"]["diff_vs_best"][r]
        rows.append([RULE_LABEL[r], f"{da['diff']:+.2f} {fci(*(da['ci'] or [None, None]))}", da["n"],
                     f"{db['diff']:+.2f} {fci(*(db['ci'] or [None, None]))}", db["n"]])
    A(f"Does any rule beat the best single coder? Best single coder against gold: ABC {g['abc']['diff_vs_best']['best']} "
      f"({g['abc']['rules'][g['abc']['diff_vs_best']['best']]['primary_value']:.2f}); BetterBench {g['betterbench']['diff_vs_best']['best']} "
      f"({g['betterbench']['rules'][g['betterbench']['diff_vs_best']['best']]['primary_value']:.2f}). Paired difference in the primary statistic "
      "(rule minus best single coder, on the cells both scored, same bootstrap resamples):")
    A("")
    A(md(["Rule", "ABC difference [95% CI]", "ABC n", "BetterBench difference [95% CI]", "BetterBench n"], rows))
    A("")
    A("RQ1 module shares on the 44 audit benchmarks under each rule (REPORTED = level 1 or 2; FULL = level 2; bootstrap 95% CI over benchmarks).")
    A("")
    rows = []
    for rule, label in RULES:
        c, a = rq1["modules"][rule]["core"], rq1["modules"][rule]["agent"]
        rows.append([label, c["n_applicable_cells"], f"{pc(c['share_reported'])} {fci_pc(c['reported_boot_lo'], c['reported_boot_hi'])}",
                     f"{pc(c['share_full'])} {fci_pc(c['full_boot_lo'], c['full_boot_hi'])}", a["n_applicable_cells"],
                     f"{pc(a['share_reported'])} {fci_pc(a['reported_boot_lo'], a['reported_boot_hi'])}",
                     f"{pc(a['share_full'])} {fci_pc(a['full_boot_lo'], a['full_boot_hi'])}"])
    A(md(["Rule", "Core cells", "Core REPORTED", "Core FULL", "Agent cells", "Agent REPORTED", "Agent FULL"], rows))
    A("")
    A("Quote verification (audit, 1,100 cells per coder): raw 1+ scores whose effective score became 0 because no quote verified.")
    A("")
    rows = [[c, ver[c]["cells"], ver[c]["raw_positive"], ver[c]["removed"], pc(ver[c]["removed_share_of_positive"]),
             ver[c]["removed_raw1"], ver[c]["removed_raw2"], ver[c]["raw_na"]] for c in ("codex", "sonnet")]
    A(md(["Coder", "Cells", "Raw 1+ (not NA)", "Removed by verification", "Share of raw 1+ (%)", "of which raw 1", "of which raw 2", "Raw NA"], rows))
    A("")
    A(f"Gold cells (same item sets): ABC codex removed {g['abc']['verification']['codex']['removed']} of {g['abc']['verification']['codex']['raw_positive']} raw positives, sonnet {g['abc']['verification']['sonnet']['removed']} of {g['abc']['verification']['sonnet']['raw_positive']}; "
      f"BetterBench codex {g['betterbench']['verification']['codex']['removed']} of {g['betterbench']['verification']['codex']['raw_positive']}, sonnet {g['betterbench']['verification']['sonnet']['removed']} of {g['betterbench']['verification']['sonnet']['raw_positive']}. "
      f"Audit cells where the current rule differs from the raw-score rule: {fam['current_differs_from_raw_rule']} of {fam['cells']}; where it differs from the union: {fam['current_differs_from_union']}.")
    A("")
    # ---- 6.2
    A("### 6.2 Bounds on RQ1 prevalence: [current rule, union rule] (R1 M3b)")
    A("")
    A("The interval is between the current (conservative: lower of the two verified scores) and the union rule (higher of the two). Denominators are identical under both rules "
      "(a cell is NA under either rule only when both coders gave NA), so the intervals differ only in the numerators. These are rule bounds, not bounds on the truth: "
      "errors shared by both coders (and the 0.29 and 0.47 gold agreement in 5.1 and 5.2) are not covered. The last column pairs the lower Wilson (item) or bootstrap (module) limit of the current rule "
      "with the upper limit of the union rule.")
    A("")
    rows = []
    for m in bnd["modules"]:
        rows.append([m["module"] + " (module)", m["n_cells"], f"{pc(m['reported_current'])} to {pc(m['reported_union'])}",
                     fci_pc(m["reported_lo_ci"], m["reported_hi_ci"]), f"{pc(m['full_current'])} to {pc(m['full_union'])}",
                     fci_pc(m["full_lo_ci"], m["full_hi_ci"]), pc(m["reported_union_raw"]), pc(m["full_union_raw"])])
    for r in bnd["items"]:
        rows.append([f"{r['item']} {r['title']}", r["n_applicable"], f"{pc(r['reported_current'])} to {pc(r['reported_union'])}",
                     fci_pc(r["reported_lo_ci"], r["reported_hi_ci"]), f"{pc(r['full_current'])} to {pc(r['full_union'])}",
                     fci_pc(r["full_lo_ci"], r["full_hi_ci"]), pc(r["reported_union_raw"]), pc(r["full_union_raw"])])
    A(md(["Unit", "n appl.", "REPORTED: current to union", "CI envelope", "FULL: current to union", "CI envelope", "REPORTED union on raw", "FULL union on raw"], rows))
    A("")
    # ---- 6.3
    A("### 6.3 Prevalence-adjusted agreement with gold (R1 M1c)")
    A("")
    A("PABAK = (p_o - 1/q)/(1 - 1/q), equal to 2 p_o - 1 for binary ABC. Gwet AC1: p_e = sum_k pi_k (1 - pi_k)/(q - 1), pi_k the mean of the two raters' proportions in category k. "
      "BetterBench (q = 4): quadratic agreement weights w = 1 - ((k - l)/3)^2; weighted PABAK = (p_a - mean w)/(1 - mean w) with uniform marginals; Gwet AC2: p_e = T_w/(q(q - 1)) sum_k pi_k (1 - pi_k), "
      "T_w = sum of all weights. CI: bootstrap over benchmarks (same resamples for all statistics of a row).")
    A("")
    for s, title in (("abc", "ABC (binary)"), ("betterbench", "BetterBench (0-3)")):
        A(f"**{title}**")
        A("")
        rows = []
        for rule, label in RULES:
            r = g[s]["rules"][rule]
            ci = r["ci"]
            if s == "abc":
                rows.append([label, r["n"], fnum(r["raw_agreement"]), fnum(r["majority_baseline"]), fnum(r["cohen_kappa"]),
                             kci(r["pabak"], ci["pabak"]), kci(r["gwet_ac1"], ci["gwet_ac1"])])
            else:
                rows.append([label, r["n"], fnum(r["raw_agreement"]), fnum(r["majority_baseline"]), fnum(r["weighted_kappa_quadratic"]),
                             kci(r["pabak_weighted"], ci["pabak_weighted"]), kci(r["gwet_ac2"], ci["gwet_ac2"]), fnum(r["pabak"]), fnum(r["gwet_ac1"])])
        if s == "abc":
            A(md(["Rule", "n", "Raw agr.", "Majority-class baseline", "Cohen kappa", "PABAK [95% CI]", "Gwet AC1 [95% CI]"], rows))
        else:
            A(md(["Rule", "n", "Raw agr.", "Majority-class baseline", "Weighted kappa (quad.)", "Weighted PABAK [95% CI]", "Gwet AC2 [95% CI]",
                  "Unweighted PABAK", "Unweighted AC1"], rows))
        A("")
    A("Confusion matrices (rows expert, columns scorer; counts of cells; aggregate counts only, no per-cell ABC gold values). ABC, 0 = not satisfied, 1 = satisfied:")
    A("")
    rows = []
    for rule, label in RULES:
        c = g["abc"]["rules"][rule]["confusion"]
        rows.append([label, c["0"]["0"], c["0"]["1"], c["1"]["0"], c["1"]["1"]])
    A(md(["Rule", "gold 0 / scorer 0", "gold 0 / scorer 1", "gold 1 / scorer 0", "gold 1 / scorer 1"], rows))
    A("")
    for rule in ("current", "union"):
        A(f"BetterBench, {RULE_LABEL[rule]} (rows expert 0-3, columns scorer 0-3):")
        A("")
        c = g["betterbench"]["rules"][rule]["confusion"]
        A(md(["gold \\ scorer", "0", "1", "2", "3"], [[k] + [c[k][str(p)] for p in range(4)] for k in ("0", "1", "2", "3")]))
        A("")
    A("Confusion matrices for every rule are in `analysis/out/rev_confusion.csv`.")
    A("")
    # ---- 6.4
    A("### 6.4 Thresholds: per-item prevalence next to cross-family alpha (R1 M5)")
    A("")
    A("Prevalence: resolved rule, share of applicable cells at level 1 or 2 (REPORTED) and at level 2 (FULL), Wilson 95% CI. Alpha: ordinal Krippendorff alpha on raw scores, NA missing, "
      "codex vs sonnet, bootstrap CI over benchmarks (equals `rq2_alpha.csv`). Agreement columns: share of cells where both coders scored (neither NA) with the same score (exact), "
      "the same side of the REPORTED threshold (>=1), and the same side of the FULL threshold (=2).")
    A("")
    rows = []
    for r in thr["rows"]:
        rows.append([r["item"], r["module"], r["n_applicable"], f"{pc(r['share_reported'])} {fci_pc(r['reported_lo'], r['reported_hi'])}",
                     f"{pc(r['share_full'])} {fci_pc(r['full_lo'], r['full_hi'])}", kci(r["alpha"], [r["alpha_lo"], r["alpha_hi"]] if r["alpha_lo"] is not None else None),
                     r["n_pairs_both_scored"], pc(r["exact_agreement"], 0), pc(r["agreement_reported_ge1"], 0), pc(r["agreement_full_eq2"], 0)])
    A(md(["Item", "Module", "n appl.", "REPORTED", "FULL", "Alpha [95% CI]", "Pairs", "Exact agr. (%)", "Agr. at >=1 (%)", "Agr. at =2 (%)"], rows))
    A("")
    a7 = next(r for r in thr["rows"] if r["item"] == "A7")
    ct = thr["crosstabs"]["A7"]
    num = {tuple(k.split("|")): v for k, v in ct.items() if "NA" not in k}
    nn = sum(num.values())
    cm = Counter()
    sm = Counter()
    for (x, y), v in num.items():
        cm[x] += v
        sm[y] += v
    a7_chance = sum(cm[k] * sm[k] for k in cm) / (nn * nn)
    A(f"**A7 verification.** Alpha = {a7['alpha']:.3f} [{a7['alpha_lo']:.2f}, {a7['alpha_hi']:.2f}] on {a7['alpha_units']} units ({a7['n_pairs_both_scored']} pairable) from {a7['alpha_benchmarks']} benchmarks: confirmed (the flagged 0.02). "
      f"Codex x sonnet raw scores (codex|sonnet: count): " + ", ".join(f"{k}: {v}" for k, v in ct.items()) + ". "
      f"Among the {a7['n_pairs_both_scored']} cells scored by both, no cell has a 0 from either coder: the coders agree on whether write-actions are disclosed ({pc(a7['agreement_reported_ge1'], 0)}% at >=1) "
      f"but split on 1 versus 2 ({pc(a7['agreement_full_eq2'], 0)}% at =2; exact {pc(a7['exact_agreement'], 0)}%). The low alpha is a threshold (level 1 versus 2) disagreement in a range-restricted item, not disagreement on presence. "
      f"Expected exact agreement by chance from the two coders' marginals is {a7_chance:.2f}, against {a7['exact_agreement']:.2f} observed. "
      f"The item is NA (both coders) in {ct.get('NA|NA', 0)} of 44 cells.")
    A("")
    # ---- 6.5
    A("### 6.5 Misclassification sensitivity: Rogan-Gladen correction (R1 M5)")
    A("")
    A("Correction: p_true = (p_apparent + Sp - 1)/(Se + Sp - 1), p_apparent the resolved-rule share on the audit cells, Se and Sp the sensitivity and specificity of the resolved score against the experts. "
      "**Assumption (not tested):** these rates are measured on 9 ABC benchmarks (22 task-validity and outcome-validity items) and 22 BetterBench benchmarks (20 criteria) and are transferred unchanged to our 25 reporting items on 44 medical-agent benchmarks; "
      "the experts are a reference, not truth (ABC and BetterBench have no published human-human agreement, section 5.3), and error rates need not be the same across items, instrument or domain. "
      "Binarisations: ABC is binary, resolved level 1 = satisfied (used for both the REPORTED and the FULL share; ABC has no partial level). BetterBench: resolved >= t versus expert >= t with t = 2 (partially met or better) for REPORTED and t = 3 (fully met) for FULL. "
      "Bootstrap: audit benchmarks and gold benchmarks resampled independently in the same replicate (2,000, seed 20261004); replicates with Se + Sp - 1 <= 0.05 are dropped (counts below); CI is the percentile interval of the unclipped corrected value, clipped CI in the last column.")
    A("")
    rows = []
    for r in mis["rows"]:
        rows.append([SET_LABEL[r["set"]], r["share"], r["module"], f"{r['tp']}/{r['gold_positive']} = {r['sensitivity']:.2f} {fci(r['sens_lo'], r['sens_hi'])}",
                     f"{r['tn']}/{r['gold_negative']} = {r['specificity']:.2f} {fci(r['spec_lo'], r['spec_hi'])}", fnum(r["youden_j"]),
                     pc(r["apparent"]), pc(r["corrected"]), fci_pc(r["ci_lo"], r["ci_hi"]), fci_pc(r["ci_clipped_lo"], r["ci_clipped_hi"]),
                     f"{r['boot_used']} / {r['boot_dropped_j_le_0.05']}"])
    A(md(["Gold set", "Share", "Module", "Sensitivity (Wilson)", "Specificity (Wilson)", "Youden J", "Apparent (%)", "Corrected (%)", "Bootstrap 95% CI", "CI clipped to 0-100", "Replicates used / dropped"], rows))
    A("")
    bad = [r for r in mis["rows"] if r["corrected"] is not None and not (0 <= r["corrected"] <= 1)]
    ok_ = [r for r in mis["rows"] if r not in bad]
    A("Reading: the correction is only informative where the apparent share exceeds the false-positive rate (1 - Sp) and Youden's J is not small. "
      + ("Outside [0, 100] (apparent share below 1 - Sp, or an overshoot): " + "; ".join(
          f"{SET_LABEL[r['set']]} {r['share']} {r['module']} ({100 * r['corrected']:.1f})" for r in bad) + ". These are not prevalence estimates; they show the expert-derived rates cannot be applied there. " if bad else "")
      + "Within range (the ABC agent upper limit still exceeds 100): " + "; ".join(f"{SET_LABEL[r['set']]} {r['share']} {r['module']}: {pc(r['apparent'])} to {pc(r['corrected'])} (CI {fci_pc(r['ci_lo'], r['ci_hi'])})" for r in ok_) + ".")
    A("")
    # ---- 6.6
    A("### 6.6 Excluding the five pilot benchmarks (R1 M2)")
    A("")
    A("Pilot benchmarks (rubric/pilot: round 1 `coderA/B_scores.csv` = AgentClinic, FHIR-AgentBench, HealthAgentBench; round 2 `r2_coder*_scores.csv` = EHR-ChatQA, MedAgentSim; "
      "decision log 2026-10-04; protocol-v1 \"five pilot benchmarks\"): " + ", ".join(f"`{k}`" for k in pil["excluded"]) + f". Remaining: {pil['n_sub']} of {pil['n_full']} benchmarks. Resolved rule; CI: bootstrap over benchmarks.")
    A("")
    rows = []
    for mod in ("core", "agent"):
        a, b = pil["modules_full"][mod], pil["modules_excl"][mod]
        rows.append([mod, a["n_applicable_cells"], f"{pc(a['share_reported'])} {fci_pc(a['reported_boot_lo'], a['reported_boot_hi'])}",
                     f"{pc(a['share_full'])} {fci_pc(a['full_boot_lo'], a['full_boot_hi'])}", b["n_applicable_cells"],
                     f"{pc(b['share_reported'])} {fci_pc(b['reported_boot_lo'], b['reported_boot_hi'])}",
                     f"{pc(b['share_full'])} {fci_pc(b['full_boot_lo'], b['full_boot_hi'])}"])
    A(md(["Module", "Cells (all 44)", "REPORTED (all 44)", "FULL (all 44)", "Cells (39)", "REPORTED (39)", "FULL (39)"], rows))
    A("")
    ao, ae = pil["alpha_full"]["overall"], pil["alpha_excl"]["overall"]
    A(f"Cross-family alpha (overall): all 44 benchmarks {kci(ao['alpha'], [ao['ci_lo'], ao['ci_hi']], 3)} on {ao['units']} units; excluding the pilot {kci(ae['alpha'], [ae['ci_lo'], ae['ci_hi']], 3)} on {ae['units']} units from {ae['benchmarks']} benchmarks.")
    A("")
    rows = []
    for it in ITEM_ORDER:
        a, b = pil["items_full"][it], pil["items_excl"][it]
        al, bl = pil["alpha_full"].get(it, {}), pil["alpha_excl"].get(it, {})
        rows.append([it, f"{pc(a['share_reported'])} ({a['n_applicable']})", f"{pc(b['share_reported'])} ({b['n_applicable']})",
                     f"{pc(a['share_full'])}", f"{pc(b['share_full'])}", fnum(al.get("alpha"), 2), kci(bl.get("alpha"), [bl.get("ci_lo"), bl.get("ci_hi")] if bl.get("ci_lo") is not None else None)])
    A(md(["Item", "REPORTED, 44 (n)", "REPORTED, 39 (n)", "FULL, 44", "FULL, 39", "Alpha, 44", "Alpha, 39 [95% CI]"], rows))
    A("")
    return "\n".join(L) + "\n"


def fci_pc(lo, hi) -> str:
    return "--" if lo is None or hi is None else f"[{100 * lo:.1f}, {100 * hi:.1f}]"


def write_summary(text: str) -> None:
    """Replace section 6 if present (removing it first), then insert it before section 7 if there is one, else append.
    Other sections are left untouched."""
    cur = SUMMARY.read_text(encoding="utf-8")
    cur = re.sub(r"^## 6\. Revision analyses \(reviews round 1\).*?(?=^## \d+\. |\Z)", "", cur, flags=re.S | re.M)
    m = re.search(r"^## 7\. ", cur, re.M)
    if m:
        cur = cur[: m.start()] + text + "\n" + cur[m.start():]
    else:
        cur = cur.rstrip("\n") + "\n\n" + text
    SUMMARY.write_text(cur, encoding="utf-8", newline="\n")


# ------------------------------------------------------------------ main
def compute(n_boot: int = N_BOOT) -> dict:
    resolved = R.load_resolved(AUDIT)
    assert len(resolved) == 44, len(resolved)
    levels = audit_levels(resolved)
    res: dict = {"n_boot": n_boot, "seed": SEED, "benchmarks": sorted(resolved)}
    res["verification"] = verification_counts(resolved)
    res["family"] = family_changes(resolved)
    res["gold"] = gold_block(n_boot)
    res["rq1"] = rq1_block(levels, n_boot)
    res["bounds"] = bounds_block(res["rq1"])
    alpha_full = R.alpha_table(AUDIT, sorted(resolved), n_boot)
    res["thresholds"] = threshold_block(resolved, sorted(resolved), alpha_full)
    res["misclass"] = misclass_block(resolved, levels, res["gold"], n_boot)
    res["pilot"] = pilot_block(resolved, alpha_full, n_boot)
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--write-summary", action="store_true", help="(re)write section 6 of analysis/out/RESULTS_SUMMARY.md")
    a = ap.parse_args(argv)
    res = compute(a.n_boot)
    write_outputs(res)
    text = section6(res)
    if a.write_summary:
        write_summary(text)
    print(text)


if __name__ == "__main__":
    main()
