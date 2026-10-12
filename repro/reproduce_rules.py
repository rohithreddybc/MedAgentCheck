"""Reproduce the resolution-rule ablation and the prevalence-adjusted agreement (PABAK, Gwet AC1/AC2) from released files.

Port of analysis/revision_rq12.py, blocks 1 (ablation) and 3 (PABAK / Gwet AC), plus the quote-verification and
family-requirement counts on the audit cells. Inputs:

  repro/tables/gold_rule_contingency.csv   benchmark-level contingency table per rule: expert level x rule level, counts
                                           (gold set, rule, benchmark); no item id, no per-cell label
  repro/tables/gold_rule_vs_best.csv       expert x best-single-coder x rule counts per benchmark (for the paired difference
                                           "rule minus best single coder")
  results/resolved/*.json                  both coders' raw and effective scores per audit cell (RQ1 side of the ablation)

Rules: claude (Claude Sonnet only, verified), openai (gpt-5.5 only, verified), union (higher verified score), nofam
(intersection without the family requirement), current (the resolved rule), raw (the resolved rule on raw scores, no
quote verification), union_raw (extra). The statistics come from the frozen agentaudit/stats.py; the resolved rule is
the frozen agentaudit/resolve.py. Resampling: benchmarks, 2,000 resamples, seed 20261004, percentile interval.

Compared (assertions) with
  results/analysis_out/rev_ablation.csv, rev_pabak.csv, rev_confusion.csv
  results/analysis_out/revision_rq12.json   gold.{abc,betterbench}.rules / diff_vs_best, rq1 modules and items per rule,
                                            verification (quote verification per coder), family (changed cells)
  analysis/out/RESULTS_SUMMARY.md           section 6.1 (agreement, paired differences, RQ1 shares, verification table)
                                            and 6.3 (PABAK / AC tables, ABC confusion table)

Not reproduced: the per-set verification and family-requirement counts on the gold cells (they need the coders' raw
scores on the withheld gold items).

    python repro/reproduce_rules.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, SEED, SUMMARY_MD, TABLES, Checker, load_resolved, read_json  # noqa: E402
from reproduce_audit import module_summary, prevalence, write_csv  # noqa: E402
from reproduce_gold import CFG, agreement_stats_from_table  # noqa: E402

from agentaudit.resolve import resolve_cell  # noqa: E402
from agentaudit.stats import cohen_kappa, weighted_kappa  # noqa: E402

FAM = {"codex": "openai", "sonnet": "anthropic"}
RULES = [
    ("claude", "Claude only (Sonnet), verified"),
    ("openai", "OpenAI only (gpt-5.5), verified"),
    ("union", "Union: max of the two verified scores"),
    ("nofam", "Intersection, no family requirement"),
    ("current", "Current resolved rule (verified, cross-family)"),
    ("raw", "Current rule on raw scores (no quote verification)"),
    ("union_raw", "Union on raw scores (extra)"),
]
RULE_LABEL = dict(RULES)
SETS = ("abc", "betterbench")
LEVELS = {"abc": (0, 1), "betterbench": (0, 1, 2, 3)}
TOP_DOWN = (2, 1)  # positive levels of the audit rubric, top down (the gold sets pass their own, see gold.set_cfg)
TABLE_RULE = TABLES / "gold_rule_contingency.csv"
TABLE_BEST = TABLES / "gold_rule_vs_best.csv"


# ------------------------------------------------------------------ rules (copy of revision_rq12.apply_rule)
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


# ------------------------------------------------------------------ chance-corrected agreement (copy)
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
    """Raw agreement, PABAK, Gwet AC1 (q categories) and for q > 2 the quadratic-weighted analogues (copy of
    revision_rq12.chance_corrected)."""
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


# ------------------------------------------------------------------ tables
def _lv(s: str):
    return s if s == "NA" else int(s)


def load_rule_table(path: Path = TABLE_RULE) -> dict:
    """{(set, rule): {bench: {(rule_level, expert_level): count}}}; rows rater = rule (pred), columns = expert."""
    out: dict = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            out.setdefault((r["gold_set"], r["rule"]), {}).setdefault(r["benchmark"], {})[
                (_lv(r["rule_level"]), _lv(r["expert_level"]))] = int(r["count"])
    return out


def load_best_table(path: Path = TABLE_BEST) -> dict:
    """{(set, rule): (best_coder, {bench: [(expert, rule_level, best_level), ...]})}"""
    out: dict = {}
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            key = (r["gold_set"], r["rule"])
            best, d = out.setdefault(key, (r["best_coder"], {}))
            assert best == r["best_coder"]
            d.setdefault(r["benchmark"], []).extend(
                [(_lv(r["expert_level"]), _lv(r["rule_level"]), _lv(r["best_level"]))] * int(r["count"]))
    return out


def used_groups(tab: dict) -> dict[str, list]:
    """bench -> [(gold, pred)] on cells where both are numeric."""
    groups: dict[str, list] = {}
    for b, d in sorted(tab.items()):
        us = []
        for (p, g), n in sorted(d.items(), key=str):
            if p != "NA" and g != "NA":
                us += [(g, p)] * n
        if us:
            groups[b] = us
    return groups


def confusion(groups: dict, levels: tuple) -> dict:
    used = [u for us in groups.values() for u in us]
    return {str(g): {str(p): sum(1 for a, b in used if a == g and b == p) for p in levels} for g in levels}


# ------------------------------------------------------------------ gold block
def gold_block(n_boot: int = N_BOOT) -> dict:
    rt, bt = load_rule_table(), load_best_table()
    res: dict = {}
    for s in SETS:
        cfg = {"levels": LEVELS[s], "primary": CFG[s]["primary"]}
        levels = LEVELS[s]
        blk: dict = {"rules": {}, "diff_vs_best": {}}
        for rule, _ in RULES:
            tab = rt[(s, rule)]
            st = agreement_stats_from_table(tab, cfg, n_boot, SEED)
            groups = used_groups(tab)
            keys = ["pabak", "gwet_ac1"] + (["pabak_weighted", "gwet_ac2"] if len(levels) > 2 else [])
            used = [u for us in groups.values() for u in us]
            point = chance_corrected([u[0] for u in used], [u[1] for u in used], levels)
            ci = boot_multi(groups, {k: _stat_fn(k, levels) for k in keys}, n_boot)
            blk["rules"][rule] = {
                "n": st["n_cells"], "n_gold_na": st["n_gold_na"], "n_pred_na": st["n_pred_na_where_gold_scored"],
                "benchmarks": len(groups), "raw_agreement": st["raw_agreement"]["rate"], "cohen_kappa": st["cohen_kappa"],
                "weighted_kappa_quadratic": st.get("weighted_kappa_quadratic"), "primary_statistic": st["primary_statistic"],
                "primary_value": st["primary_value"], "primary_ci": st["primary_ci95_bootstrap_over_benchmarks"],
                "majority_baseline": st["majority_class_baseline_agreement"],
                "within_one": (st.get("within_one_level") or {}).get("rate"),
                "confusion": st["confusion"],
                **{k: point.get(k) for k in keys + ["pa_weighted"] if k in point}, "ci": ci}
        best = max(("claude", "openai"), key=lambda r: blk["rules"][r]["primary_value"])
        blk["diff_vs_best"]["best"] = best
        wk = (lambda a, b: cohen_kappa(a, b)) if cfg["primary"] == "cohen_kappa" else (
            lambda a, b: weighted_kappa(a, b, list(levels), "quadratic"))
        for rule, _ in RULES:
            if rule in ("claude", "openai"):
                continue
            bc, grp = bt[(s, rule)]
            assert bc == ("sonnet" if best == "claude" else "codex"), (s, rule, bc, best)

            def dstat(units, wk=wk):
                g_ = [u[0] for u in units]
                a, c = wk(g_, [u[1] for u in units]), wk(g_, [u[2] for u in units])
                return None if a is None or c is None else a - c
            allu = [u for us in grp.values() for u in us]
            blk["diff_vs_best"][rule] = {"diff": dstat(allu), "n": len(allu), "ci": boot_multi(grp, {"d": dstat}, n_boot)["d"]}
        res[s] = blk
    return res


# ------------------------------------------------------------------ audit side (results/resolved votes)
def as_resolved(levels_b: dict) -> dict:
    return {b: {it: {"final": lv} for it, lv in cells.items()} for b, cells in levels_b.items()}


def audit_side(resolved: dict, n_boot: int = N_BOOT) -> dict:
    levels = {r: {} for r, _ in RULES}
    for b, cells in resolved.items():
        for r, _ in RULES:
            levels[r][b] = {}
        for it, c in cells.items():
            assert len(c["votes"]) == 2, (b, it)
            for r, _ in RULES:
                levels[r][b][it] = apply_rule(r, c["votes"], TOP_DOWN)
    rq1 = {"modules": {}, "items": {}}
    for r, _ in RULES:
        d = as_resolved(levels[r])
        rq1["modules"][r] = {m["module"]: m for m in module_summary(d, "final", n_boot)}
        rq1["items"][r] = {m["item"]: m for m in prevalence(d, "final")}
    ver = {}
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
        ver[coder] = {"cells": n, "raw_positive": pos, "removed": removed,
                      "removed_share_of_positive": removed / pos if pos else None,
                      "removed_raw1": by_level[1], "removed_raw2": by_level[2], "raw_na": na_raw}
    changed = total = d_union = d_raw = 0
    for b, cells in resolved.items():
        for it, c in cells.items():
            total += 1
            a = apply_rule("current", c["votes"], TOP_DOWN)
            assert a == c["final"], (b, it, a, c["final"])
            assert apply_rule("raw", c["votes"], TOP_DOWN) == c["majority_final"], (b, it)
            changed += a != apply_rule("nofam", c["votes"], TOP_DOWN)
            d_union += a != apply_rule("union", c["votes"], TOP_DOWN)
            d_raw += a != apply_rule("raw", c["votes"], TOP_DOWN)
    fam = {"cells": total, "changed_by_family_requirement": changed, "current_differs_from_union": d_union,
           "current_differs_from_raw_rule": d_raw}
    return {"rq1": rq1, "verification": ver, "family": fam}


# ------------------------------------------------------------------ formatting (as analysis/revision_rq12.py)
def fnum(x, nd: int = 2) -> str:
    return "--" if x is None or x == "" else f"{float(x):.{nd}f}"


def fci(lo, hi, nd: int = 2) -> str:
    return "--" if lo is None or hi is None else f"[{float(lo):.{nd}f}, {float(hi):.{nd}f}]"


def kci(x, ci, nd: int = 2) -> str:
    return "--" if x is None else (f"{x:.{nd}f}" + (f" [{ci[0]:.{nd}f}, {ci[1]:.{nd}f}]" if ci else ""))


def pc(x, nd: int = 1) -> str:
    return "--" if x is None or x == "" else f"{100 * x:.{nd}f}"


def fci_pc(lo, hi) -> str:
    return "--" if lo is None or hi is None else f"[{100 * lo:.1f}, {100 * hi:.1f}]"


def row(cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


# ------------------------------------------------------------------ main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    ck = Checker("resolution-rule ablation and PABAK / Gwet AC on the gold cells")
    resolved = load_resolved()
    assert len(resolved) == 44, len(resolved)
    g = gold_block()
    au = audit_side(resolved)
    rq1 = au["rq1"]
    ref = read_json(ANALYSIS_OUT / "revision_rq12.json")

    # ---- CSV outputs
    abl, prow, crow = [], [], []
    for rule, label in RULES:
        r_ = {"rule": rule, "label": label}
        for s in SETS:
            r = g[s]["rules"][rule]
            tag = "abc" if s == "abc" else "bb"
            r_.update({f"{tag}_n": r["n"], f"{tag}_raw_agreement": r["raw_agreement"], f"{tag}_cohen_kappa": r["cohen_kappa"],
                       f"{tag}_primary": r["primary_value"], f"{tag}_ci_lo": (r["primary_ci"] or [None, None])[0],
                       f"{tag}_ci_hi": (r["primary_ci"] or [None, None])[1]})
            if s == "betterbench":
                r_["bb_weighted_kappa_quadratic"] = r["weighted_kappa_quadratic"]
        for m in ("core", "agent"):
            r = rq1["modules"][rule][m]
            r_.update({f"{m}_cells": r["n_applicable_cells"], f"{m}_reported": r["share_reported"],
                       f"{m}_reported_boot_lo": r["reported_boot_lo"], f"{m}_reported_boot_hi": r["reported_boot_hi"],
                       f"{m}_full": r["share_full"], f"{m}_full_boot_lo": r["full_boot_lo"], f"{m}_full_boot_hi": r["full_boot_hi"]})
        abl.append(r_)
    for s in SETS:
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
    for name, rows in (("rev_ablation", abl), ("rev_pabak", prow), ("rev_confusion", crow)):
        write_csv(a.out / f"{name}.csv", rows)
    ck.csv_rows("rev_ablation.csv", abl, ANALYSIS_OUT / "rev_ablation.csv", ["rule"])
    ck.csv_rows("rev_pabak.csv", prow, ANALYSIS_OUT / "rev_pabak.csv", ["set", "rule"])
    ck.csv_rows("rev_confusion.csv", crow, ANALYSIS_OUT / "rev_confusion.csv", ["set", "rule", "gold", "pred"])

    # ---- revision_rq12.json
    for s in SETS:
        for rule, _ in RULES:
            mine, want = g[s]["rules"][rule], ref["gold"][s]["rules"][rule]
            for k, v in want.items():
                if k == "groups":
                    continue
                if k in ("ci", "confusion"):
                    if k == "ci":
                        for kk, vv in v.items():
                            ck.eq(f"json {s}.{rule}.ci.{kk}", mine["ci"][kk], vv, 1e-9)
                    else:
                        ck.eq(f"json {s}.{rule}.confusion", mine["confusion"], v)
                elif k == "primary_ci":
                    ck.eq(f"json {s}.{rule}.primary_ci", mine[k], v, 1e-9)
                else:
                    ck.eq(f"json {s}.{rule}.{k}", mine.get(k), v, 1e-9)
        wd = ref["gold"][s]["diff_vs_best"]
        ck.eq(f"json {s}.diff_vs_best.best", g[s]["diff_vs_best"]["best"], wd["best"])
        for rule, _ in RULES:
            if rule in ("claude", "openai"):
                continue
            ck.eq(f"json {s}.diff.{rule}.diff", g[s]["diff_vs_best"][rule]["diff"], wd[rule]["diff"], 1e-9)
            ck.eq(f"json {s}.diff.{rule}.n", g[s]["diff_vs_best"][rule]["n"], wd[rule]["n"])
            ck.eq(f"json {s}.diff.{rule}.ci", g[s]["diff_vs_best"][rule]["ci"], wd[rule]["ci"], 1e-9)
    for rule, _ in RULES:
        for m in ("core", "agent"):
            for k, v in ref["rq1"]["modules"][rule][m].items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) or v is None:
                    ck.eq(f"json rq1.modules.{rule}.{m}.{k}", rq1["modules"][rule][m].get(k), v, 1e-9)
        for it, rr in ref["rq1"]["items"][rule].items():
            for k, v in rr.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool) or v is None:
                    ck.eq(f"json rq1.items.{rule}.{it}.{k}", rq1["items"][rule][it].get(k), v, 1e-9)
    for coder in ("codex", "sonnet"):
        for k, v in ref["verification"][coder].items():
            ck.eq(f"json verification.{coder}.{k}", au["verification"][coder][k], v, 1e-9)
    for k, v in au["family"].items():
        ck.eq(f"json family.{k}", v, ref["family"][k])

    # ---- RESULTS_SUMMARY.md, sections 6.1 and 6.3
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    for rule, label in RULES:
        ra, rb = g["abc"]["rules"][rule], g["betterbench"]["rules"][rule]
        ck.in_text(f"6.1 gold {rule}", row([label, ra["n"], fnum(ra["raw_agreement"]), kci(ra["primary_value"], ra["primary_ci"]), rb["n"],
                                           fnum(rb["raw_agreement"]), kci(rb["primary_value"], rb["primary_ci"]), fnum(rb["cohen_kappa"])]), txt)
        c, ag = rq1["modules"][rule]["core"], rq1["modules"][rule]["agent"]
        ck.in_text(f"6.1 RQ1 {rule}", row([
            label, c["n_applicable_cells"], f"{pc(c['share_reported'])} {fci_pc(c['reported_boot_lo'], c['reported_boot_hi'])}",
            f"{pc(c['share_full'])} {fci_pc(c['full_boot_lo'], c['full_boot_hi'])}", ag["n_applicable_cells"],
            f"{pc(ag['share_reported'])} {fci_pc(ag['reported_boot_lo'], ag['reported_boot_hi'])}",
            f"{pc(ag['share_full'])} {fci_pc(ag['full_boot_lo'], ag['full_boot_hi'])}"]), txt)
        ra_ = g["abc"]["rules"][rule]
        rb_ = g["betterbench"]["rules"][rule]
        ci_a, ci_b = ra_["ci"], rb_["ci"]
        ck.in_text(f"6.3 ABC {rule}", row([label, ra_["n"], fnum(ra_["raw_agreement"]), fnum(ra_["majority_baseline"]), fnum(ra_["cohen_kappa"]),
                                           kci(ra_["pabak"], ci_a["pabak"]), kci(ra_["gwet_ac1"], ci_a["gwet_ac1"])]), txt)
        ck.in_text(f"6.3 BB {rule}", row([label, rb_["n"], fnum(rb_["raw_agreement"]), fnum(rb_["majority_baseline"]),
                                          fnum(rb_["weighted_kappa_quadratic"]), kci(rb_["pabak_weighted"], ci_b["pabak_weighted"]),
                                          kci(rb_["gwet_ac2"], ci_b["gwet_ac2"]), fnum(rb_["pabak"]), fnum(rb_["gwet_ac1"])]), txt)
        c_ = ra_["confusion"]
        ck.in_text(f"6.3 ABC confusion {rule}", row([label, c_["0"]["0"], c_["0"]["1"], c_["1"]["0"], c_["1"]["1"]]), txt)
    for rule, _ in RULES:
        if rule in ("claude", "openai"):
            continue
        da, db = g["abc"]["diff_vs_best"][rule], g["betterbench"]["diff_vs_best"][rule]
        ck.in_text(f"6.1 paired diff {rule}", row([RULE_LABEL[rule], f"{da['diff']:+.2f} {fci(*(da['ci'] or [None, None]))}", da["n"],
                                                   f"{db['diff']:+.2f} {fci(*(db['ci'] or [None, None]))}", db["n"]]), txt)
    for c in ("codex", "sonnet"):
        v = au["verification"][c]
        ck.in_text(f"6.1 verification {c}", row([c, v["cells"], v["raw_positive"], v["removed"], pc(v["removed_share_of_positive"]),
                                                  v["removed_raw1"], v["removed_raw2"], v["raw_na"]]), txt)
    f_ = au["family"]
    ck.in_text("6.1 rule differences", f"Audit cells where the current rule differs from the raw-score rule: {f_['current_differs_from_raw_rule']} of "
                                       f"{f_['cells']}; where it differs from the union: {f_['current_differs_from_union']}.", txt)
    ck.done()
    for s in SETS:
        r = g[s]["rules"]["current"]
        print(f"{s}: resolved rule primary {r['primary_value']:.3f} (n={r['n']}), PABAK "
              f"{r['pabak_weighted'] if 'pabak_weighted' in r else r['pabak']:.3f}, AC{'2' if s == 'betterbench' else '1'} "
              f"{r['gwet_ac2'] if s == 'betterbench' else r['gwet_ac1']:.3f}")


if __name__ == "__main__":
    main()
