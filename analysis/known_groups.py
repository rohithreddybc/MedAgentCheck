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
SUMMARY = OUT / "RESULTS_SUMMARY.md"
HEADING = "## 11. Known-groups and adjacent-construct validation (post hoc; added 2026-10-14)"
CODERS = ("sonnet", "codex")

NEG = ["ARC-Challenge", "BBQ", "BOLD", "DecodingTrust", "GPQA", "GSM8k", "HellaSwag", "HumanEval", "MedMNIST_v2",
       "MLCommons_AI_Safety_v0.5", "MMLU", "TruthfulQA", "WinoGrande"]
POS = ["BIRD-Bench", "GAIA", "KernelBench", "MLE-bench", "OSWorld", "SWE-Lancer", "SWE-bench_Verified", "WebArena",
       "tau-bench", "AgentBench"]
TEST_ITEMS = ["A3", "A5", "A6", "A7", "A9", "A11"]

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


def expert_cells(bb: dict, abc: dict, packets: set[str]) -> list[dict]:
    """One row per (bench, agent item) with an expert reference; bench must have a packet."""
    rows = []
    bb_b = sorted({b for b, _ in bb} & packets)
    abc_b = sorted({b for b, _ in abc} & packets)
    for it, (bbc, abcc) in MAP.items():
        for b in bb_b:
            vals = [bb[(b, c)] for c in bbc if (b, c) in bb and bb[(b, c)] is not None]
            if vals:
                rows.append({"bench": b, "item": it, "set": "betterbench", "ref": sum(vals) / len(vals), "k": len(vals)})
        for b in abc_b:
            vals = [abc[(b, c)] for c in abcc if (b, c) in abc and abc[(b, c)] is not None]
            if vals:
                rows.append({"bench": b, "item": it, "set": "abc", "ref": sum(vals) / len(vals), "k": len(vals)})
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
    A("Source: `analysis/known_groups.py` -> `analysis/out/known_groups.json`; plan fixed in `protocol/addendum-known-groups.md` before coding. "
      "Post hoc; reported whatever the result. Verified (effective) levels from `audit/known_groups/verified`; the resolved level exists only for benchmarks coded by both coders. "
      "Bootstrap: 2,000 resamples of benchmarks with replacement, seed 20261004, percentile 95% CI. Wilson 95% intervals are on cells (not clustered). "
      "NA and 0 both count as correct in Study 1. Coders in the data: " + ", ".join(res["coders"]) + ".")
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


def main() -> None:
    per, resolved = load_levels()
    sets: dict[str, dict] = dict(per)
    if resolved:
        sets["resolved"] = resolved
    packets = {p.name for p in (KG / "packets").iterdir() if p.is_dir()} if (KG / "packets").exists() else {b for b, _ in
                                                                                                           [k for d in per.values() for k in d]}
    bb, abc = load_expert()
    cells = expert_cells(bb, abc, packets)
    res = {"coders": list(per), "seed": SEED, "n_boot": N_BOOT, "study1": {}, "study2": {}, "coverage": {}}
    for name, lv in sets.items():
        res["study1"][name] = study1(lv)
        res["study2"][name] = study2(lv, cells)
    res["expert_cells_available"] = len(cells)
    res["mapping"] = {k: {"betterbench": v[0], "abc": v[1]} for k, v in MAP.items()}
    for name, lv in sets.items():
        s = res["study1"][name]
        res["coverage"][name] = (f"N {s['n_benchmarks_present']}/13, P {s['p_benchmarks_present']}/10; missing N: "
                                 f"{', '.join(s['n_missing']) or 'none'}; missing P: {', '.join(s['p_missing']) or 'none'}")
    (OUT / "known_groups.json").write_text(json.dumps(res, indent=1), encoding="utf-8", newline="\n")
    write_summary(markdown(res))

    # compact print
    for name in sets:
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
        print("      per-item N false credit: " + ", ".join(
            f"{i} {s1['per_item'][i]['N']['k']}/{s1['per_item'][i]['N']['n']}" for i in TEST_ITEMS))
    print(f"wrote {OUT / 'known_groups.json'} and section 11 of {SUMMARY}")


if __name__ == "__main__":
    main()
