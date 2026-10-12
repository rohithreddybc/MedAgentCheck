"""Reproduce perturbation sensitivity and specificity (Wilson and cluster-bootstrap intervals) from results/perturbation/.

Port of analysis/postfreeze/rq1_rq2.py (perturbation_table) and of analysis/revision_round2.py (_cluster_block,
perturb_clusters). Input: results/perturbation/summary.json, the 2,496 labelled rows (variant, item, perturbation type,
coder, level, ok) of the 39 variant packets that ran. Compared with results/analysis_out/rq2_perturbation.csv,
rev2_perturb_clusters.csv, revision_round2.json (key "perturb") and the tables of analysis/out/RESULTS_SUMMARY.md
(sections 3.4 and 8.2).

    python repro/reproduce_perturbation.py [--out repro/out]
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _lib import ANALYSIS_OUT, N_BOOT, REPO, RESULTS, SEED, SUMMARY_MD, Checker, read_json  # noqa: E402
from reproduce_audit import write_csv  # noqa: E402

from agentaudit.items import ITEM_ORDER  # noqa: E402
from agentaudit.stats import wilson  # noqa: E402

POSITIVE = ("inject", "buried", "paraphrase")
NEGATIVE = ("deletion", "decoy")
VTYPES = ("inject", "buried", "paraphrase", "deletion", "decoy")


# ------------------------------------------------------------------ Wilson table (rq1_rq2.perturbation_table)
def _share(k: int, n: int):
    if n <= 0:
        return None, None, None
    ci = wilson(k, n)
    return k / n, ci[0], ci[1]


def _metrics(rows: list[dict]) -> list[tuple[str, int, int]]:
    pos = [r for r in rows if r["vtype"] in POSITIVE]
    neg = [r for r in rows if r["vtype"] in NEGATIVE]
    return [("sensitivity", sum(bool(r["ok"]) for r in pos), len(pos)),
            ("sensitivity_any_level", sum(r["level"] >= 1 for r in pos), len(pos)),
            ("specificity", sum(bool(r["ok"]) for r in neg), len(neg))]


def perturbation_table(rows: list[dict]) -> list[dict]:
    out = []

    def emit(scope, coder, item, vtype, sel):
        for metric, k, n in _metrics(sel):
            if not n:
                continue
            r, lo, hi = _share(k, n)
            out.append({"scope": scope, "coder": coder, "item": item or "", "vtype": vtype or "", "metric": metric,
                        "hits": k, "n": n, "rate": r, "wilson_lo": lo, "wilson_hi": hi})

    for coder in sorted({r["coder"] for r in rows}, key=lambda c: (c == "RESOLVED", c)):
        sel = [r for r in rows if r["coder"] == coder]
        emit("overall", coder, None, None, sel)
        for vt in VTYPES:
            emit("type", coder, None, vt, [r for r in sel if r["vtype"] == vt])
        for it in ITEM_ORDER:
            s2 = [r for r in sel if r["item"] == it]
            if not s2:
                continue
            emit("item", coder, it, None, s2)
            for vt in VTYPES:
                emit("item_type", coder, it, vt, [r for r in s2 if r["vtype"] == vt])
    return out


# ------------------------------------------------------------------ cluster bootstrap (revision_round2._cluster_block)
def cluster_block(rows: list[dict]) -> dict:
    metrics = {
        "sensitivity": (POSITIVE, lambda r: bool(r["ok"])),
        "inject": (("inject",), lambda r: bool(r["ok"])),
        "buried": (("buried",), lambda r: bool(r["ok"])),
        "paraphrase": (("paraphrase",), lambda r: bool(r["ok"])),
        "specificity": (NEGATIVE, lambda r: bool(r["ok"])),
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
            cl = {}
            for r in sel:
                cl.setdefault(r[ckey], []).append(1.0 if ok(r) else 0.0)
            res[m] = {"hits": k, "n": n, "rate": k / n, "wilson": list(w), "cluster_boot": ci,
                      "clusters_with_cells": len(cl), "width_ratio": (ci[1] - ci[0]) / (w[1] - w[0])}
        out["clusters"][ckey] = res
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=REPO / "repro" / "out")
    a = ap.parse_args()
    rows = read_json(RESULTS / "perturbation" / "summary.json")["rows"]
    ck = Checker("perturbation sensitivity and specificity")
    ck.eq("perturbation rows", len(rows), 2496)
    for c in ("codex", "sonnet", "RESOLVED"):
        ck.eq(f"cells {c}", len([r for r in rows if r["coder"] == c]), 832)
    son = [r for r in rows if r["coder"] == "sonnet"]
    ck.eq("sonnet sensitivity hits/n", (sum(r["ok"] for r in son if r["vtype"] in POSITIVE),
                                        len([r for r in son if r["vtype"] in POSITIVE])), (527, 542))
    ck.eq("sonnet specificity hits/n", (sum(r["ok"] for r in son if r["vtype"] in NEGATIVE),
                                        len([r for r in son if r["vtype"] in NEGATIVE])), (117, 290))

    table = perturbation_table(rows)
    write_csv(a.out / "rq2_perturbation.csv", table)
    ck.csv_rows("rq2_perturbation.csv", table, ANALYSIS_OUT / "rq2_perturbation.csv",
                ["scope", "coder", "item", "vtype", "metric"])

    by_coder = {c: cluster_block([r for r in rows if r["coder"] == c]) for c in ("codex", "sonnet", "RESOLVED")}
    flat = []
    for coder, blk in by_coder.items():
        for ck_, d in blk["clusters"].items():
            for m, v in d.items():
                flat.append({"coder": coder, "cluster": ck_, "metric": m, "hits": v["hits"], "n": v["n"], "rate": v["rate"],
                             "wilson_lo": v["wilson"][0], "wilson_hi": v["wilson"][1], "cluster_lo": v["cluster_boot"][0],
                             "cluster_hi": v["cluster_boot"][1], "clusters_with_cells": v["clusters_with_cells"],
                             "width_ratio": v["width_ratio"]})
    write_csv(a.out / "rev2_perturb_clusters.csv", flat)
    ck.csv_rows("rev2_perturb_clusters.csv", flat, ANALYSIS_OUT / "rev2_perturb_clusters.csv", ["coder", "cluster", "metric"])
    ref = read_json(ANALYSIS_OUT / "revision_round2.json")["perturb"]["by_coder"]
    for coder, blk in by_coder.items():
        for ckey, d in blk["clusters"].items():
            for m, v in d.items():
                r = ref[coder]["clusters"][ckey][m]
                for f in ("hits", "n", "clusters_with_cells"):
                    ck.eq(f"json {coder}/{ckey}/{m}/{f}", v[f], r[f])
                for f in ("rate", "width_ratio"):
                    ck.eq(f"json {coder}/{ckey}/{m}/{f}", v[f], r[f], 1e-9)
                ck.eq(f"json {coder}/{ckey}/{m}/wilson", v["wilson"], r["wilson"], 1e-9)
                ck.eq(f"json {coder}/{ckey}/{m}/cluster_boot", v["cluster_boot"], r["cluster_boot"], 1e-9)

    # the tables as printed in RESULTS_SUMMARY.md (3.4 and 8.2)
    txt = SUMMARY_MD.read_text(encoding="utf-8")
    pc = lambda x: f"{100 * x:.1f}%"  # noqa: E731
    pci = lambda lo, hi: f"[{100 * lo:.1f}, {100 * hi:.1f}]"  # noqa: E731
    for coder in ("codex", "sonnet", "RESOLVED"):
        for metric, scope, vt in ([("sensitivity", "overall", ""), ("sensitivity_any_level", "overall", "")]
                                  + [("sensitivity", "type", t) for t in POSITIVE] + [("specificity", "overall", "")]
                                  + [("specificity", "type", t) for t in NEGATIVE]):
            r = next(x for x in table if (x["coder"], x["scope"], x["metric"], x["vtype"]) == (coder, scope, metric, vt)
                     and not x["item"])
            ck.in_text(f"3.4 {coder} {metric} {vt}", f"| {coder} | {metric} | {vt or 'all'} | {r['hits']}/{r['n']} | "
                                                      f"{pc(r['rate'])} | {pci(r['wilson_lo'], r['wilson_hi'])} |", txt)
        cl = by_coder[coder]["clusters"]
        for m in ("sensitivity", "inject", "buried", "paraphrase", "specificity", "deletion", "decoy"):
            v, it = cl["variant_id"][m], cl["item"][m]
            ck.in_text(f"8.2 {coder} {m}", f"| {coder} | {m} | {v['hits']}/{v['n']} | {100 * v['rate']:.1f}% | "
                                            f"{pci(*v['wilson'])} | {pci(*v['cluster_boot'])} | {v['width_ratio']:.2f} | "
                                            f"{pci(*it['cluster_boot'])} | {it['width_ratio']:.2f} |", txt)
    ck.done()
    for coder in ("codex", "sonnet", "RESOLVED"):
        s = next(x for x in table if (x["coder"], x["scope"], x["metric"], x["vtype"]) == (coder, "overall", "sensitivity", ""))
        p = next(x for x in table if (x["coder"], x["scope"], x["metric"], x["vtype"]) == (coder, "overall", "specificity", ""))
        print(f"{coder}: sensitivity {s['hits']}/{s['n']} ({pc(s['rate'])}), specificity {p['hits']}/{p['n']} ({pc(p['rate'])})")


if __name__ == "__main__":
    main()
