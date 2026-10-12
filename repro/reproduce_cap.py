"""Reproduce the cap-stratified RQ1 shares and cross-family alpha (and the MedAgentBench version merge) from released files.

Port of block C (cap_flags, strat_boot_diff, cap_block) of analysis/revision_round2.py. Inputs:

  repro/tables/cap_flags.csv   per benchmark: capped yes/no, tokens before the cap, tokens sent, dropped chunks
                               (taken from audit/transport/prompts/<bench>/meta.json by repro/make_rule_cap_tables.py;
                               no prompt text and no prompt hash)
  results/resolved/*.json      resolved levels and both coders' raw scores per cell

"Capped" = at least one S4 chunk was dropped by the 150,000-token cap (n_dropped_chunks > 0, or tokens before the cap above
the cap). Resolved rule; intervals are percentile bootstrap over benchmarks within the stratum (2,000 resamples, seed
20261004); the difference (capped minus uncapped) resamples each stratum independently.

Compared (assertions) with
  results/analysis_out/revision_round2.json   "cap" block (flags, module shares per stratum, differences, alpha per stratum,
                                              per-item shares, C13 and A4 cells, cap-aware shares, version merge)
  results/analysis_out/rev2_cap_items.csv
  analysis/out/RESULTS_SUMMARY.md             section 8.3 (all tables and sentences)

    python repro/reproduce_cap.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, SEED, SUMMARY_MD, TABLES, Checker, load_resolved, read_csv_rows, read_json  # noqa: E402
from reproduce_audit import alpha_table, level_of, module_summary, write_csv  # noqa: E402

from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402

TABLE = TABLES / "cap_flags.csv"


def cap_flags(path: Path = TABLE) -> dict[str, dict]:
    out = {}
    for r in read_csv_rows(path):
        out[r["benchmark"]] = {"tokens_before_cap": int(r["tokens_before_cap"]), "tokens_sent": int(r["tokens_sent"]),
                               "n_dropped_chunks": int(r["n_dropped_chunks"]), "over_cap": r["over_cap"] == "yes",
                               "capped": r["capped"] == "yes"}
        # the flag must follow from the columns: a dropped chunk or a token count above the cap
        assert out[r["benchmark"]]["capped"] == bool(int(r["n_dropped_chunks"]) or int(r["tokens_before_cap"]) > int(r["cap_tokens"]))
    return out


def _mod(resolved: dict) -> dict:
    return {r["module"]: r for r in module_summary(resolved, "final", N_BOOT)}


def strat_boot_diff(res_a: dict, res_b: dict, items: list[str], key: str = "rep") -> list[float]:
    """Difference (a minus b) in a module's pooled share with independent benchmark resampling within each stratum."""
    def units(res):
        g = {}
        for b, cells in res.items():
            us = []
            for i in items:
                if i in cells and level_of(cells[i]["final"]) is not None:
                    x = level_of(cells[i]["final"])
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


def cap_block(resolved: dict, flags: dict) -> dict:
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

    def alpha_overall(rr):
        rows = [r for r in alpha_table(rr, N_BOOT) if r["kind"] == "all_coders"]
        return {"overall": [r for r in rows if r["scope"] == "overall"][0],
                "items": {r["item"]: r for r in rows if r["scope"] == "item"}}
    out["alpha"] = {"capped": alpha_overall(rc), "uncapped": alpha_overall(ru)}
    pi = {}
    for it in ITEM_ORDER:
        row = {}
        for nm, rr in (("capped", rc), ("uncapped", ru)):
            lv = [level_of(c[it]["final"]) for c in rr.values() if it in c]
            app = [x for x in lv if x is not None]
            row[nm] = {"n": len(app), "rep": sum(x >= 1 for x in app) / len(app) if app else None,
                       "full": sum(x == 2 for x in app) / len(app) if app else None}
        pi[it] = row
    out["items"] = pi
    c13a4 = {}
    for it in ("C13", "A4"):
        zero = [b for b in capped if resolved[b][it]["final"] == 0]
        stat = {}
        for b in capped:
            stat[resolved[b][it]["status"]] = stat.get(resolved[b][it]["status"], 0) + 1
        c13a4[it] = {"cells_in_capped_packets": len(capped), "resolved_zero": len(zero), "zero_benchmarks": zero,
                     "status_counts": stat, "uncapped_zero": sum(1 for b in uncapped if resolved[b][it]["final"] == 0)}
    out["c13_a4"] = c13a4

    def cap_aware(res: dict) -> dict:
        mod = {}
        for m, ids in (("core", core), ("agent", agent)):
            k = kf = n = 0
            for b, cells in res.items():
                for i in ids:
                    if i not in cells or level_of(cells[i]["final"]) is None:
                        continue
                    x = level_of(cells[i]["final"])
                    if flags[b]["capped"] and i in ("C13", "A4") and x == 0:
                        continue
                    n += 1
                    k += x >= 1
                    kf += x == 2
            mod[m] = {"n": n, "rep": k / n, "full": kf / n}
        return mod
    out["cap_aware"] = cap_aware(resolved)

    v1, v2 = "medagentbench-v1", "medagentbench-v2"
    merged_cells = {}
    for it in resolved[v1]:
        a, b2 = level_of(resolved[v1][it]["final"]), level_of(resolved[v2][it]["final"])
        nums = [x for x in (a, b2) if x is not None]
        merged_cells[it] = {"final": max(nums) if nums else "NA", "majority_final": max(nums) if nums else "NA"}
    variants = {"all 44 (v1 and v2 separate)": resolved,
                "v2 dropped (v1 kept)": {b: c for b, c in resolved.items() if b != v2},
                "v1 dropped (v2 kept)": {b: c for b, c in resolved.items() if b != v1},
                "merged (higher level per item)": {**{b: c for b, c in resolved.items() if b not in (v1, v2)},
                                                   "medagentbench-merged": merged_cells}}
    keys = ("n_applicable_cells", "share_reported", "share_full", "reported_boot_lo", "reported_boot_hi", "full_boot_lo", "full_boot_hi")
    out["merge"] = {k: {"n_benchmarks": len(v), **{m: {kk: r[kk] for kk in keys} for m, r in _mod(v).items()}}
                    for k, v in variants.items()}
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    ck = Checker("cap-stratified RQ1 shares and alpha")
    resolved = load_resolved()
    assert len(resolved) == 44, len(resolved)
    flags = cap_flags()
    ck.eq("cap flag rows (44 coded benchmarks + HealthCraft)", len(flags), 45)
    cap = cap_block(resolved, flags)
    ref = read_json(ANALYSIS_OUT / "revision_round2.json")["cap"]

    ck.eq("capped benchmarks", cap["capped"], ref["capped"])
    ck.eq("uncapped benchmarks", cap["uncapped"], ref["uncapped"])
    ck.eq("n_capped", cap["n_capped"], ref["n_capped"])
    ck.eq("n_uncapped", cap["n_uncapped"], ref["n_uncapped"])
    ck.eq("flags", cap["flags"], ref["flags"])
    ck.eq("healthcraft flags", cap["healthcraft"], ref["healthcraft"])
    for st in ("capped", "uncapped", "all"):
        for m in ("core", "agent"):
            for k, v in ref["modules"][st][m].items():
                if isinstance(v, (int, float)) or v is None:
                    ck.eq(f"modules.{st}.{m}.{k}", cap["modules"][st][m].get(k), v, 1e-9)
    for k, v in ref["diff"].items():
        ck.eq(f"diff.{k}", cap["diff"][k], v, 1e-9)
    for st in ("capped", "uncapped"):
        for k, v in ref["alpha"][st]["overall"].items():
            ck.eq(f"alpha.{st}.overall.{k}", cap["alpha"][st]["overall"].get(k), v, 1e-9)
        ck.eq(f"alpha.{st} item set", sorted(cap["alpha"][st]["items"]), sorted(ref["alpha"][st]["items"]))
        for it, rr in ref["alpha"][st]["items"].items():
            for k, v in rr.items():
                ck.eq(f"alpha.{st}.{it}.{k}", cap["alpha"][st]["items"][it].get(k), v, 1e-9)
    for it, rr in ref["items"].items():
        for st in ("capped", "uncapped"):
            for k, v in rr[st].items():
                ck.eq(f"items.{it}.{st}.{k}", cap["items"][it][st][k], v, 1e-9)
    for it, rr in ref["c13_a4"].items():
        for k, v in rr.items():
            ck.eq(f"c13_a4.{it}.{k}", cap["c13_a4"][it][k], v)
    for m, rr in ref["cap_aware"].items():
        for k, v in rr.items():
            ck.eq(f"cap_aware.{m}.{k}", cap["cap_aware"][m][k], v, 1e-9)
    for name, rr in ref["merge"].items():
        ck.eq(f"merge.{name}.n_benchmarks", cap["merge"][name]["n_benchmarks"], rr["n_benchmarks"])
        for m in ("core", "agent"):
            for k, v in rr[m].items():
                ck.eq(f"merge.{name}.{m}.{k}", cap["merge"][name][m][k], v, 1e-9)

    crow = [{"item": it, "capped_n": cap["items"][it]["capped"]["n"], "capped_rep": cap["items"][it]["capped"]["rep"],
             "capped_full": cap["items"][it]["capped"]["full"], "uncapped_n": cap["items"][it]["uncapped"]["n"],
             "uncapped_rep": cap["items"][it]["uncapped"]["rep"], "uncapped_full": cap["items"][it]["uncapped"]["full"]}
            for it in ITEM_ORDER]
    write_csv(a.out / "rev2_cap_items.csv", crow)
    ck.csv_rows("rev2_cap_items.csv", crow, ANALYSIS_OUT / "rev2_cap_items.csv", ["item"])

    # ---- RESULTS_SUMMARY.md section 8.3
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    ck.in_text("8.3 cap definition", f"Capped = at least one S4 chunk dropped by the 150,000-token cap: {cap['n_capped']} of the 44 coded benchmarks "
                                     f"({', '.join(cap['capped'])}); the other {cap['n_uncapped']} are uncapped. HealthCraft is also capped and has no cells.", txt)
    for mod in ("core", "agent"):
        for st in ("capped", "uncapped", "all"):
            m = cap["modules"][st][mod]
            ck.in_text(f"8.3 module row {mod} {st}",
                       f"| {mod} | {st} | {m['n_benchmarks']} | {m['n_applicable_cells']} | {100 * m['share_reported']:.1f}% | "
                       f"[{100 * m['reported_boot_lo']:.1f}, {100 * m['reported_boot_hi']:.1f}] | {100 * m['share_full']:.1f}% | "
                       f"[{100 * m['full_boot_lo']:.1f}, {100 * m['full_boot_hi']:.1f}] |", txt)
    ck.in_text("8.3 differences", "Difference, capped minus uncapped, in points (percentile 95% interval): " + "; ".join(
        f"{k.replace('_', ' ')} {100 * v[0]:+.1f} [{100 * v[1]:+.1f}, {100 * v[2]:+.1f}]" for k, v in cap["diff"].items()) + ".", txt)
    al = cap["alpha"]
    ck.in_text("8.3 alpha", "Cross-family ordinal alpha (raw scores, NA missing), overall: capped "
               f"{al['capped']['overall']['alpha']:.3f} [{al['capped']['overall']['ci_lo']:.3f}, {al['capped']['overall']['ci_hi']:.3f}] "
               f"on {al['capped']['overall']['units']} cells in {al['capped']['overall']['benchmarks']} benchmarks; uncapped "
               f"{al['uncapped']['overall']['alpha']:.3f} [{al['uncapped']['overall']['ci_lo']:.3f}, {al['uncapped']['overall']['ci_hi']:.3f}] "
               f"on {al['uncapped']['overall']['units']} cells in {al['uncapped']['overall']['benchmarks']} benchmarks (all 44: 0.771).", txt)
    diffs = sorted(((it, 100 * (cap["items"][it]["capped"]["rep"] - cap["items"][it]["uncapped"]["rep"])) for it in ITEM_ORDER
                    if cap["items"][it]["capped"]["rep"] is not None and cap["items"][it]["uncapped"]["rep"] is not None),
                   key=lambda t: -abs(t[1]))[:6]
    for it, dv in diffs:
        c, u = cap["items"][it]["capped"], cap["items"][it]["uncapped"]
        ck.in_text(f"8.3 item row {it}", f"| {it} | {100 * c['rep']:.1f}% ({c['n']}) | {100 * u['rep']:.1f}% ({u['n']}) | {dv:+.1f} |", txt)
    for it in ("C13", "A4"):
        x = cap["c13_a4"][it]
        c, u = cap["items"][it]["capped"], cap["items"][it]["uncapped"]
        ck.in_text(f"8.3 {it} bullet", f"- {it}: {x['resolved_zero']} of {x['cells_in_capped_packets']} cells in capped packets resolved to 0 "
                                       f"(status counts {x['status_counts']}), against {x['uncapped_zero']} of {cap['n_uncapped']} in uncapped packets; "
                                       f"REPORTED {100 * c['rep']:.1f}% capped against {100 * u['rep']:.1f}% uncapped.", txt)
    ca = cap["cap_aware"]
    ck.in_text("8.3 cap-aware", f"- Cap-aware shares (the {cap['c13_a4']['C13']['resolved_zero'] + cap['c13_a4']['A4']['resolved_zero']} capped C13 and A4 "
                                f"cells that resolved to 0 are treated as not established and left out of the denominator): core REPORTED "
                                f"{100 * ca['core']['rep']:.1f}% (n = {ca['core']['n']}), fully reported {100 * ca['core']['full']:.1f}%; agent REPORTED "
                                f"{100 * ca['agent']['rep']:.1f}% (n = {ca['agent']['n']}), fully reported {100 * ca['agent']['full']:.1f}%.", txt)
    for nm, v in cap["merge"].items():
        c, ag = v["core"], v["agent"]
        ck.in_text(f"8.3 merge row {nm}",
                   f"| {nm} | {v['n_benchmarks']} | {c['n_applicable_cells']} | {100 * c['share_reported']:.1f}% "
                   f"[{100 * c['reported_boot_lo']:.1f}, {100 * c['reported_boot_hi']:.1f}] | {100 * c['share_full']:.1f}% | "
                   f"{ag['n_applicable_cells']} | {100 * ag['share_reported']:.1f}% [{100 * ag['reported_boot_lo']:.1f}, "
                   f"{100 * ag['reported_boot_hi']:.1f}] | {100 * ag['share_full']:.1f}% |", txt)
    ck.done()
    m = cap["modules"]
    print(f"capped {cap['n_capped']} / uncapped {cap['n_uncapped']} benchmarks; core REPORTED {100 * m['capped']['core']['share_reported']:.1f}% "
          f"vs {100 * m['uncapped']['core']['share_reported']:.1f}%; alpha {al['capped']['overall']['alpha']:.3f} vs {al['uncapped']['overall']['alpha']:.3f}")


if __name__ == "__main__":
    main()
