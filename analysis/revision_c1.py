"""Review cycle 1 additions (analysis side).

  1 PAIR      Coder-pair (Claude Sonnet vs OpenAI gpt-5.5) PABAK and Gwet AC1 on exactly the cells and level coding of the
              like-for-like coder-pair kappas (analysis/gold_coder_pair.py: "common" cells = expert, codex and sonnet all
              scored; effective scores; ABC binary, BetterBench 0-3). Same statistic code as rev_pabak.csv
              (revision_rq12.chance_corrected), benchmark bootstrap (2,000 resamples, seed 20261004, percentile 95% CI).
              BetterBench also carries the quadratic-weighted PABAK and Gwet AC2. Coder-vs-expert rows on the same cells
              are recomputed as a check against rev_pabak.csv (ABC reproduces it exactly).
  2 NOT-EST   The main-audit cells that fall back to level 0 under the resolved rule (resolve_cell statuses
              "not_established" and "na_rejected_as_zero"; 190 of 1,100 cells), by reason, for all 25 items, the core
              module, A1-A10 and A11. Also: resolved REPORTED = 0 cells in which both coders sit at verified 0.
  3 A11       Stored verified quotations behind A11 credits (either coder, effective level >= 1) for the 44 audited
              benchmarks, classified by a Claude Sonnet 5.5 subagent reading the quotations (see A11_CLASS below) into D (dataset or data-source provenance or licence),
              E (environment or initial-state provenance), B (both), N (no credit). Writes analysis/out/a11_quote_classes.csv.

Nothing is rescored. Run from the project root (authors' working tree only; in the public release the script stops and names the missing inputs):
    python analysis/revision_c1.py
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import OUT, SEED, TABLES, write_csv  # noqa: E402

import gold_coder_pair as GP  # noqa: E402
import revision_rq12 as V  # noqa: E402
import rq1_rq2 as R  # noqa: E402
from agentaudit.items import ITEM_ORDER  # noqa: E402

N_BOOT = 2000
SUMMARY = OUT / "RESULTS_SUMMARY.md"
SECTION = "13. Review cycle 1 additions"
AGENT_A1_A10 = [f"A{i}" for i in range(1, 11)]
CORE = [i for i in ITEM_ORDER if i.startswith("C")]


def f2(x, nd=3):
    return "n/a" if x is None else f"{x:.{nd}f}"


def ci_s(c, nd=3):
    return "n/a" if not c else f"[{c[0]:.{nd}f}, {c[1]:.{nd}f}]"


# ================================================================== 1 coder-pair PABAK / AC1
def pair_block() -> dict:
    out = {}
    for s in ("abc", "betterbench"):
        d = GP.load_set(s)  # reproduces agreement.json (asserted inside)
        cfg, gold, preds, common = d["cfg"], d["gold"], d["preds"], d["common"]
        levels = tuple(cfg["levels"])
        keys = ["pabak", "gwet_ac1"] + (["pabak_weighted", "gwet_ac2"] if len(levels) > 2 else [])
        views = {"coder_pair": ("sonnet", "codex"), "claude_vs_expert": ("sonnet", None), "openai_vs_expert": ("codex", None)}
        res = {"levels": list(levels), "n_cells": len(common), "n_benchmarks": len({b for b, _ in common}), "pairs": {}}
        for name, (a, b) in views.items():
            av = [preds[a][c]["effective"] for c in common]
            bv = [preds[b][c]["effective"] for c in common] if b else [gold[c] for c in common]
            groups: dict[str, list] = {}
            for c, x, y in zip(common, av, bv):
                groups.setdefault(c[0], []).append((x, y))
            pt = V.chance_corrected(av, bv, levels)
            ci = V.boot_multi(groups, {k: V._stat_fn(k, levels) for k in keys}, N_BOOT, SEED)
            res["pairs"][name] = {"n": pt["n"], "raw_agreement": pt["po"], "cohen_kappa": GP.cohen_kappa(av, bv),
                                  **{k: pt.get(k) for k in keys}, "ci": ci}
            if len(levels) > 2:
                res["pairs"][name]["weighted_agreement"] = pt.get("pa_weighted")
        out[s] = res
    # check against rev_pabak.csv (ABC: identical cell set, must match)
    rows = {(r["set"], r["rule"]): r for r in __import__("csv").DictReader(open(OUT / "rev_pabak.csv", encoding="utf-8"))}
    for rule, key in (("claude", "claude_vs_expert"), ("openai", "openai_vs_expert")):
        r = rows[("abc", rule)]
        m = out["abc"]["pairs"][key]
        assert int(r["n"]) == m["n"] and abs(float(r["pabak"]) - m["pabak"]) < 1e-5 and abs(float(r["gwet_ac1"]) - m["gwet_ac1"]) < 1e-5
        assert abs(float(r["pabak_lo"]) - m["ci"]["pabak"][0]) < 1e-5 and abs(float(r["ac1_hi"]) - m["ci"]["gwet_ac1"][1]) < 1e-5
    out["_check"] = "ABC coder-vs-expert PABAK, AC1 and intervals reproduce rev_pabak.csv (claude, openai rows)"
    return out


# ================================================================== 2 not-established breakdown
def vstate(v: dict) -> str:
    """Z = scored 0; V = verified credit (effective >= 1); R = credit (raw >= 1) removed by quote verification; N = NA."""
    r, e = v["raw"], v["effective"]
    if r == "NA":
        return "N"
    if r == 0:
        return "Z"
    return "V" if e not in ("NA", 0) else "R"


CATS = [
    ("verified_credit_vs_zero", "One coder holds a verified credit, the other scored 0"),
    ("verified_credit_vs_removed", "One coder holds a verified credit, the other's credit was removed by quote verification"),
    ("removed_vs_zero", "One coder's credit was removed by quote verification, the other scored 0"),
    ("both_removed", "Both coders' credits were removed by quote verification"),
    ("one_sided_na", "One coder scored NA, the other did not"),
]


def categorize(votes: dict) -> tuple[str, str]:
    st = {c: vstate(v) for c, v in votes.items()}
    key = "".join(sorted(st.values()))
    cat = {"VZ": "verified_credit_vs_zero", "RV": "verified_credit_vs_removed", "RZ": "removed_vs_zero", "RR": "both_removed"}.get(key)
    if cat is None:
        assert "N" in key and key != "NN", key
        cat = "one_sided_na"
    return cat, key


def removal_reasons(run: Path, b: str, it: str, coder: str) -> list[str]:
    v = json.loads((run / "verified" / b / it / f"{coder}.json").read_text(encoding="utf-8"))
    rs = sorted({q.get("reason") for q in v.get("quotes", []) if not q.get("verified")})
    return rs or ["no_quote_supplied"]


def not_established_block(resolved: dict) -> dict:
    run = V.AUDIT
    cells = [(b, it, c) for b, cs in resolved.items() for it, c in cs.items()]
    assert len(cells) == 1100
    status = Counter(c["status"] for _, _, c in cells)
    fb = [(b, it, c) for b, it, c in cells if c["fallback"]]
    # definition check: fallback == statuses not_established + na_rejected_as_zero; nothing else sets fallback
    assert len(fb) == status["not_established"] + status["na_rejected_as_zero"] == 190
    assert all(c["status"] in ("not_established", "na_rejected_as_zero") for _, _, c in fb)
    # statuses established_zero require raw 0 from both coders (family rule)
    assert all(all(v["raw"] == 0 for v in c["votes"].values()) for _, _, c in cells if c["status"] == "established_zero")
    rows = []
    for b, it, c in fb:
        cat, key = categorize(c["votes"])
        credited = [k for k, v in c["votes"].items() if vstate(v) == "V"]
        top = max([c["votes"][k]["effective"] for k in credited], default=0)
        removed_reason = []
        for k, v in c["votes"].items():
            if vstate(v) == "R":
                removed_reason += removal_reasons(run, b, it, k)
        rows.append({"bench": b, "item": it, "cat": cat, "key": key, "status": c["status"],
                     "credit_coder": ",".join(credited), "credit_level": top, "removed_reasons": removed_reason,
                     "votes": {k: [v["raw"], v["effective"]] for k, v in c["votes"].items()}})

    def tally(items):
        sel = [r for r in rows if r["item"] in items]
        n_cells = sum(1 for b, it, c in cells if it in items)
        cnt = Counter(r["cat"] for r in sel)
        return {"cells": n_cells, "not_established": len(sel), "share_of_cells": len(sel) / n_cells if n_cells else None,
                "by_category": {k: cnt.get(k, 0) for k, _ in CATS},
                "by_category_share": {k: (cnt.get(k, 0) / len(sel) if sel else None) for k, _ in CATS}}

    out = {"definition": ("fallback cells = resolve_cell status 'not_established' (no level reaches two cross-family verified "
                          "supporters and no cross-family pair of raw 0s) plus 'na_rejected_as_zero' (an NA that lacks a "
                          "cross-family second NA). Both coders raw 0 is 'established_zero' and is NOT in the set. "
                          "Both coders NA is 'na_accepted' and is NOT in the set."),
           "status_counts": dict(status), "fallback_cells": len(fb), "fallback_share": len(fb) / 1100,
           "all_25": tally(set(ITEM_ORDER)), "core_C1_C14": tally(set(CORE)), "agent_A1_A10": tally(set(AGENT_A1_A10)),
           "agent_A11": tally({"A11"}), "by_item": {it: tally({it}) for it in ITEM_ORDER}}
    # verified-credit vs zero: which coder credits, which level
    vz = [r for r in rows if r["cat"] == "verified_credit_vs_zero"]
    out["verified_credit_vs_zero_detail"] = {
        "claude_credits_openai_zero": sum(r["credit_coder"] == "sonnet" for r in vz),
        "openai_credits_claude_zero": sum(r["credit_coder"] == "codex" for r in vz),
        "credit_level_1": sum(r["credit_level"] == 1 for r in vz), "credit_level_2": sum(r["credit_level"] == 2 for r in vz)}
    vr = [r for r in rows if r["cat"] == "verified_credit_vs_removed"]
    out["verified_credit_vs_removed_detail"] = {
        "claude_holds_credit": sum(r["credit_coder"] == "sonnet" for r in vr),
        "openai_holds_credit": sum(r["credit_coder"] == "codex" for r in vr),
        "removed_quote_reasons": dict(Counter(x for r in rows if r["cat"] in ("verified_credit_vs_removed", "removed_vs_zero", "both_removed")
                                              for x in r["removed_reasons"]))}
    na = [r for r in rows if r["cat"] == "one_sided_na"]
    out["one_sided_na_detail"] = {"NA_vs_zero": sum("Z" in r["key"] for r in na), "NA_vs_verified_credit": sum("V" in r["key"] for r in na)}
    # any-credit-involved vs zero-only etc.
    out["cells_with_a_verified_credit"] = sum("V" in r["key"] for r in rows)
    out["cells_with_no_verified_credit"] = sum("V" not in r["key"] for r in rows)
    # REPORTED = 0 cells (resolved final 0, applicable = not NA)
    zero = [(b, it, c) for b, it, c in cells if c["final"] == 0]
    both_eff0 = [x for x in zero if all(v["effective"] == 0 for v in x[2]["votes"].values())]
    both_raw0 = [x for x in zero if all(v["raw"] == 0 for v in x[2]["votes"].values())]

    def zsub(items):
        z = [x for x in zero if x[1] in items]
        return {"reported_zero_cells": len(z),
                "both_verified_zero": sum(1 for x in z if all(v["effective"] == 0 for v in x[2]["votes"].values())),
                "both_raw_zero": sum(1 for x in z if all(v["raw"] == 0 for v in x[2]["votes"].values()))}
    out["reported_zero"] = {"all_25": zsub(set(ITEM_ORDER)), "core_C1_C14": zsub(set(CORE)), "agent_A1_A10": zsub(set(AGENT_A1_A10)),
                            "agent_A11": zsub({"A11"}),
                            "note": "REPORTED = 0 means resolved final level 0 (NA cells are not applicable and leave the denominator). "
                                    "'both verified zero' = effective 0 for both coders, which includes cells where a raw credit was removed by quote verification."}
    out["_rows"] = rows
    return out


# ================================================================== 3 A11 quote classes
# Hand classification after reading every stored verified quotation. Default class is D (dataset or data-source provenance,
# licence, de-identification or access terms). E only when the quote is about the state of the environment the agent acts in.
# (bench, coder, quote prefix) -> (class, reason, borderline)
E_QUOTES = {
    ("medcua-bench", "codex", "the OpenEMR tier is seeded"): ("E", "seed state of the OpenEMR environment (synthetic demonstration patients)", False),
    ("medcua-bench", "sonnet", "the OpenEMR tier is seeded"): ("E", "seed state of the OpenEMR environment (synthetic demonstration patients)", False),
    ("physicianbench", "codex", "distributed as a Docker image archive"): ("E", "environment snapshot: pre-loaded FHIR server shipped as a Docker image (context in README)", False),
    ("klinikebench", "sonnet", "These responses are simulated clinical observations"): ("E", "content returned by the simulator/tool cache is LLM-authored, not real measurements", True),
    ("patientagentbench", "sonnet", "In our experiments, we use Claude Sonnet 4.6"): ("E", "names the model that generates the healthcare sandbox state (scenario enrichment and sandbox generation)", True),
}
# D quotes that could be read as environment-state provenance (kept D, flagged borderline)
BORDERLINE_D = {
    ("fhir-agentbench", "codex", "de-identified, real patient records from MIMIC-IV-FHIR"): "records served by the FHIR system, but the sentence states data source only",
    ("fhir-agentbench", "sonnet", "which offers real, de-identified patient data in the mandated FHIR format"): "data source in FHIR format; no statement about the server's loaded state",
    ("synthetic-hospital", "sonnet", "Kimi 2.5 then realizes each fixed cluster"): "generation of the synthetic hospital records; could be read as initial-state provenance",
    ("synthetic-hospital", "codex", "The released data files are fully synthetic"): "released data files, licence/redistribution framing",
    ("healthcare-ai-gym", "codex", "All patient data is **synthetic**"): "patient data of a gym environment, stated as data property",
    ("healthcare-ai-gym", "sonnet", "All patient data is **synthetic**"): "patient data of a gym environment, stated as data property",
    ("openhospital", "sonnet", "OpenHospital is constructed entirely using synthetic data"): "whole benchmark built on synthetic data",
    ("openhospital", "codex", "a multi-stage data synthesis pipeline"): "data synthesis pipeline",
}


def default_reason(text: str) -> str:
    t = text.lower()
    if re.search(r"licen|apache|cc by|cc-by|cc0|openrail|open database|redistribut|do not redistribute", t):
        return "dataset or code licence or redistribution terms"
    if re.search(r"credential|data use|data-use|physionet|citi|access|irb|ethics|approval", t):
        return "source-dataset access, approval or governance terms"
    if re.search(r"de-identif|deidentif|anonym|identifiable|phi\b|pii\b|unidentif|protected health", t):
        return "de-identification of the source data"
    if re.search(r"synthe|simulated|generated|llm|gpt|deepseek", t):
        return "synthetic data generation (dataset content)"
    return "origin of the source cases or records"


def a11_block(resolved: dict) -> tuple[dict, list[dict]]:
    run = V.AUDIT
    rows = []
    cls = {}
    for b in sorted(resolved):
        cell = resolved[b].get("A11")
        assert cell is not None, b
        classes = set()
        credit_coders = []
        borderline = False
        for coder in ("codex", "sonnet"):
            v = json.loads((run / "verified" / b / "A11" / f"{coder}.json").read_text(encoding="utf-8"))
            eff = v["effective"]
            if eff in ("NA", 0):
                continue
            credit_coders.append(coder)
            for q in v["quotes"]:
                if not q["verified"]:
                    continue
                text = " ".join(q["text"].split())
                hit = next((val for (bb, cc, pre), val in E_QUOTES.items() if (bb, cc) == (b, coder) and text.startswith(pre)), None)
                if hit:
                    k, reason, bl = hit
                else:
                    k, reason, bl = "D", None, False
                    bd = next((r for (bb, cc, pre), r in BORDERLINE_D.items() if (bb, cc) == (b, coder) and text.startswith(pre)), None)
                    reason = default_reason(text)
                    if bd:
                        reason, bl = f"{reason}; borderline: {bd}", True
                classes.add(k)
                borderline |= bl
                rows.append({"bench": b, "coder": coder, "level": eff, "quote": text[:200], "class": k, "reason": reason,
                             "borderline": "y" if bl else ""})
        c = "N" if not credit_coders else ("B" if classes == {"D", "E"} else next(iter(classes)))
        cls[b] = {"class": c, "credit_coders": credit_coders, "resolved_final": cell["final"], "borderline": borderline}
        if c == "N":
            rows.append({"bench": b, "coder": "both", "level": 0, "quote": "", "class": "N",
                         "reason": "no verified credit from either coder (A11 scored 0 by both)", "borderline": ""})
    for r in rows:
        r["bench_class"] = cls[r["bench"]]["class"]
    write_csv(OUT / "a11_quote_classes.csv", rows, ["bench", "coder", "level", "quote", "class", "reason", "borderline", "bench_class"])
    cnt = Counter(v["class"] for v in cls.values())
    qcnt = Counter(r["class"] for r in rows if r["class"] != "N")
    # sensitivity: borderline E quotes counted as D (strict) / borderline D quotes counted as E (liberal)
    def bench_class(strict: bool) -> Counter:
        out = Counter()
        for b in cls:
            qs = [r for r in rows if r["bench"] == b and r["class"] != "N"]
            if not qs:
                out["N"] += 1
                continue
            ks = set()
            for r in qs:
                k = r["class"]
                if r["borderline"]:
                    k = "D" if strict else "E"
                ks.add(k)
            out["B" if ks == {"D", "E"} else next(iter(ks))] += 1
        return out
    res = {"n_benchmarks": len(cls), "bench_class_counts": {k: cnt.get(k, 0) for k in "DEBN"},
           "quote_class_counts": dict(qcnt), "n_quotes": sum(qcnt.values()),
           "bench_class_counts_borderline_all_D": {k: bench_class(True).get(k, 0) for k in "DEBN"},
           "bench_class_counts_borderline_all_E": {k: bench_class(False).get(k, 0) for k in "DEBN"},
           "bench_by_class": {k: sorted(b for b, v in cls.items() if v["class"] == k) for k in "DEBN"},
           "benchmarks_with_any_credit": sum(1 for v in cls.values() if v["class"] != "N"),
           "resolved_final_ge1": sum(1 for v in cls.values() if v["resolved_final"] not in (0, "NA")),
           "note": ("Class assigned by reading each stored verified quote; E only where the quote concerns the state of the environment "
                    "the agent acts in. Borderline = plausible alternative reading; the *_borderline_all_D / _E counts give both bounds.")}
    return res, rows


# ================================================================== 4 item-level association
def _spearman(x: list, y: list):
    import math
    from scipy.stats import spearmanr
    if len(x) < 3 or len(set(x)) < 2 or len(set(y)) < 2:
        return None
    r = spearmanr(x, y)[0]
    return None if math.isnan(r) else float(r)


def _item_stats(cells_by_item: dict) -> dict:
    """cells_by_item: item -> list of (claude, openai, expert) effective scores. Returns item -> stats."""
    out = {}
    for it, cs in cells_by_item.items():
        n = len(cs)
        if not n:
            continue
        pair = sum(a == b for a, b, _ in cs) / n
        ce = sum(a == e for a, _, e in cs) / n
        oe = sum(b == e for _, b, e in cs) / n
        out[it] = {"n": n, "pair_agr": pair, "claude_expert_agr": ce, "openai_expert_agr": oe, "coder_expert_agr": (ce + oe) / 2,
                   "pair_kappa": GP.cohen_kappa([a for a, _, _ in cs], [b for _, b, _ in cs]),
                   "claude_expert_kappa": GP.cohen_kappa([a for a, _, _ in cs], [e for _, _, e in cs]),
                   "openai_expert_kappa": GP.cohen_kappa([b for _, b, _ in cs], [e for _, _, e in cs])}
    return out


def _assoc(stats_list: list) -> dict:
    """Association summaries over the union of items in the given item-stat dicts (pooled = several instruments)."""
    items = [v for st in stats_list for v in st.values()]
    x = [v["pair_agr"] for v in items]
    y = [v["coder_expert_agr"] for v in items]
    hi = [v["coder_expert_agr"] for v in items if v["pair_agr"] >= 0.9]
    return {"n_items": len(items), "rho": _spearman(x, y),
            "share_pair_gt_expert": sum(a > b for a, b in zip(x, y)) / len(items),
            "share_pair_ge_expert": sum(a >= b for a, b in zip(x, y)) / len(items),
            "n_pair_ge_0.9": len(hi), "expert_agr_range_pair_ge_0.9": [min(hi), max(hi)] if hi else None,
            "median_expert_agr_pair_ge_0.9": sorted(hi)[len(hi) // 2] if hi else None}


def item_assoc_block() -> dict:
    import random
    import numpy as np
    from scipy.stats import spearmanr
    data = {}
    for s in ("abc", "betterbench"):
        d = GP.load_set(s)
        preds, gold, common = d["preds"], d["gold"], d["common"]
        items = sorted({c[1] for c in common})
        by_b: dict = {}
        for c in common:
            by_b.setdefault(c[0], {}).setdefault(c[1], []).append((preds["sonnet"][c]["effective"], preds["codex"][c]["effective"], gold[c]))
        data[s] = {"items": items, "by_b": by_b, "n_cells": len(common)}

    def stats_for(s: str, benches: list) -> dict:
        acc: dict = {it: [] for it in data[s]["items"]}
        for b in benches:
            for it, cs in data[s]["by_b"][b].items():
                acc[it].extend(cs)
        return _item_stats(acc)

    point = {s: stats_for(s, sorted(data[s]["by_b"])) for s in data}
    out = {"seed": SEED, "n_boot": N_BOOT,
           "scope": ("Items are the ABC items and the BetterBench criteria on exactly the 'common' cells of the coder-pair kappas "
                     "(expert, Claude and OpenAI all scored; effective scores; ABC binary, BetterBench 0-3 exact match). "
                     "Per item: raw agreement of the coder pair, raw agreement of each coder with the expert, and their mean (coder-expert). "
                     "Spearman rho across items between coder-pair and coder-expert agreement; benchmark bootstrap (2,000 resamples, seed 20261004, "
                     "percentile 95% CI) recomputes every item statistic in each resample; an item absent from a resample is dropped for that resample. "
                     "Pooled = the ABC and BetterBench items together; benchmarks are resampled separately within each instrument (the two "
                     "benchmark sets differ), so the pooled ranking mixes two scales and is secondary."),
           "n_cells": {s: data[s]["n_cells"] for s in data}, "n_benchmarks": {s: len(data[s]["by_b"]) for s in data},
           "instruments": {}}
    sets = {"abc": ["abc"], "betterbench": ["betterbench"], "pooled": ["abc", "betterbench"]}
    rng = random.Random(SEED)
    keys = {s: sorted(data[s]["by_b"]) for s in data}
    boot = {k: {"rho": [], "share_gt": [], "hi_min": [], "hi_max": []} for k in sets}
    for _ in range(N_BOOT):
        st = {s: stats_for(s, [keys[s][rng.randrange(len(keys[s]))] for _k in range(len(keys[s]))]) for s in data}
        for k, ss in sets.items():
            a = _assoc([st[s] for s in ss])
            if a["rho"] is not None:
                boot[k]["rho"].append(a["rho"])
            boot[k]["share_gt"].append(a["share_pair_gt_expert"])
            if a["expert_agr_range_pair_ge_0.9"]:
                boot[k]["hi_min"].append(a["expert_agr_range_pair_ge_0.9"][0])
                boot[k]["hi_max"].append(a["expert_agr_range_pair_ge_0.9"][1])

    def ci(v):
        v = sorted(v)
        return [v[int(0.025 * (len(v) - 1))], v[int(0.975 * (len(v) - 1))]] if len(v) >= 20 else None
    for k, ss in sets.items():
        a = _assoc([point[s] for s in ss])
        xs = [v["pair_agr"] for s in ss for v in point[s].values()]
        ys = [v["coder_expert_agr"] for s in ss for v in point[s].values()]
        a["rho_p_value_asymptotic"] = float(spearmanr(xs, ys)[1])
        a["rho_ci95"] = ci(boot[k]["rho"])
        a["rho_boot_valid_resamples"] = len(boot[k]["rho"])
        a["share_pair_gt_expert_ci95"] = ci(boot[k]["share_gt"])
        a["mean_pair_agr"] = float(np.mean(xs))
        a["mean_coder_expert_agr"] = float(np.mean(ys))
        out["instruments"][k] = a
    out["items"] = {s: {it: v for it, v in sorted(point[s].items())} for s in point}
    out["hi_agreement_items"] = {s: sorted(((it, round(v["pair_agr"], 3), round(v["coder_expert_agr"], 3)) for it, v in point[s].items()
                                            if v["pair_agr"] >= 0.9), key=lambda t: t[2]) for s in point}
    return out


# ================================================================== 5 ablation, agent columns without A11
def ablation_noa11_block(resolved: dict) -> dict:
    levels = V.audit_levels(resolved)
    out = {"definition": ("Agent columns of paper/tables/rev_ablation.tex recomputed on A1-A10 (A11 dropped) for every rule row of that table, with "
                          "the same code path (revision_rq12.audit_levels -> rq1_rq2.module_summary, 2,000 benchmark bootstrap resamples, "
                          "percentile 95% intervals, seed 20261004). The table prints rounded point percentages only; intervals are given here."),
           "rules": {}}
    for rule, label in V.RULES:
        if rule in ("union_raw", "nofam"):
            continue  # not rows of the table (nofam merged into the resolved row, union_raw an extra)
        d = V.as_resolved(levels[rule])
        with_a11 = {r["module"]: r for r in R.module_summary(d, "final", N_BOOT)}["agent"]
        d10 = {b: {it: c for it, c in cells.items() if it != "A11"} for b, cells in d.items()}
        a = {r["module"]: r for r in R.module_summary(d10, "final", N_BOOT)}["agent"]
        out["rules"][rule] = {"label": label, "n_applicable_cells": a["n_applicable_cells"],
                              "share_reported": a["share_reported"], "reported_boot_ci": [a["reported_boot_lo"], a["reported_boot_hi"]],
                              "share_full": a["share_full"], "full_boot_ci": [a["full_boot_lo"], a["full_boot_hi"]],
                              "with_a11_share_reported": with_a11["share_reported"], "with_a11_share_full": with_a11["share_full"],
                              "with_a11_cells": with_a11["n_applicable_cells"]}
    chk = json.loads((OUT / "agent_without_a11.json").read_text(encoding="utf-8"))
    for rule in ("current", "union"):
        r = out["rules"][rule]
        assert abs(r["share_reported"] - chk[rule]["share_reported"]) < 1e-12 and abs(r["share_full"] - chk[rule]["share_full"]) < 1e-12, rule
        assert r["reported_boot_ci"] == [chk[rule]["reported_boot_lo"], chk[rule]["reported_boot_hi"]]
    assert round(100 * out["rules"]["current"]["share_reported"], 1) == 60.2 and round(100 * out["rules"]["current"]["share_full"], 1) == 5.2
    assert round(100 * out["rules"]["union"]["share_reported"], 1) == 74.8 and round(100 * out["rules"]["union"]["share_full"], 1) == 12.2
    out["_check"] = "resolved and union rows equal agent_without_a11.json (60.2/5.2 and 74.8/12.2)"
    src = (TABLES / "rev_ablation.tex").read_text(encoding="utf-8").splitlines()
    rule_rows = list(out["rules"])
    assert rule_rows == ["claude", "openai", "union", "current", "raw"], rule_rows
    res_lines, k = [], 0
    for ln in src:
        if ln.startswith(r"\textbf{Scoring rule}"):
            cells = [c.strip() for c in re.sub(r"\s*\\\\\s*$", "", ln).split(" & ")]
            assert cells[-2:] == [r"\textbf{Agent rep. (\%)}", r"\textbf{Agent full (\%)}"], cells[-2:]
            cells[-2:] = [r"\textbf{Agent rep., A1--A10 (\%)}", r"\textbf{Agent full, A1--A10 (\%)}"]
            ln = " & ".join(cells) + r" \\"
        elif ln.endswith(r"\\") and "&" in ln and not ln.startswith(r"\textbf"):
            cells = [c.strip() for c in re.sub(r"\s*\\\\\s*$", "", ln).split(" & ")]
            rule = rule_rows[k]
            k += 1
            r = out["rules"][rule]
            assert cells[0] == r["label"], (cells[0], r["label"])
            # sanity: the with-A11 values reproduce the printed agent cells
            assert (f"{100 * r['with_a11_share_reported']:.0f}", f"{100 * r['with_a11_share_full']:.0f}") == (cells[-2], cells[-1]), (rule, cells[-2:])
            cells[-2:] = [f"{100 * r['share_reported']:.0f}", f"{100 * r['share_full']:.0f}"]
            ln = " & ".join(cells) + r" \\"
        elif ln.startswith("% Generated by"):
            ln = ln + "\n% Agent columns recomputed on items A1-A10 only (A11 excluded) by analysis/revision_c1.py; every other column is identical to rev_ablation.tex."
        res_lines.append(ln)
    assert k == 5
    (TABLES / "rev_ablation_noA11.tex").write_text("\n".join(res_lines) + "\n", encoding="utf-8", newline="\n")
    return out


# ================================================================== summary
def markdown(r: dict) -> str:
    L = [f"## {SECTION}", "",
         "Source: `analysis/revision_c1.py` -> `analysis/out/revision_c1.json`, `analysis/out/a11_quote_classes.csv`. Nothing rescored. "
         "2,000 benchmark bootstrap resamples, seed 20261004, percentile 95% intervals. Command: `python analysis/revision_c1.py`.", ""]
    # 13.1
    L += ["### 13.1 Coder-pair PABAK and Gwet AC1 (same cells and level coding as the coder-pair kappas of 5.1/5.2)", "",
          "Cells: expert, Claude Sonnet and OpenAI gpt-5.5 all scored; effective scores (a 1+ without a verified quote counts as 0). "
          "Statistic code is `revision_rq12.chance_corrected` (as `rev_pabak.csv`). The Claude-vs-expert and OpenAI-vs-expert rows on the same cells are "
          "given for comparison; for ABC they reproduce `rev_pabak.csv` exactly (asserted). For BetterBench the common set is 423 cells "
          "(`rev_pabak.csv` uses 425 for Claude), so those two rows differ slightly from it.", ""]
    for s, lab in (("abc", "ABC (binary)"), ("betterbench", "BetterBench (0-3)")):
        p = r["pair"][s]
        L.append(f"**{lab}**, {p['n_cells']} cells, {p['n_benchmarks']} benchmarks.")
        L.append("")
        wt = s == "betterbench"
        hdr = ["Pair", "n", "Raw agr.", "Cohen kappa", "PABAK [95% CI]", "Gwet AC1 [95% CI]"] + (["Weighted PABAK [95% CI]", "Gwet AC2 [95% CI]"] if wt else [])
        L.append("| " + " | ".join(hdr) + " |")
        L.append("|" + "---|" * len(hdr))
        for k, name in (("coder_pair", "Claude vs OpenAI"), ("claude_vs_expert", "Claude vs expert"), ("openai_vs_expert", "OpenAI vs expert")):
            q = p["pairs"][k]
            row = [name, str(q["n"]), f2(q["raw_agreement"]), f2(q["cohen_kappa"]),
                   f"{f2(q['pabak'])} {ci_s(q['ci']['pabak'])}", f"{f2(q['gwet_ac1'])} {ci_s(q['ci']['gwet_ac1'])}"]
            if wt:
                row += [f"{f2(q['pabak_weighted'])} {ci_s(q['ci']['pabak_weighted'])}", f"{f2(q['gwet_ac2'])} {ci_s(q['ci']['gwet_ac2'])}"]
            L.append("| " + " | ".join(row) + " |")
        L.append("")
    # 13.2
    n = r["not_established"]
    L += ["### 13.2 Cells that fall back to level 0 (\"not established\") in the main audit, by reason", "",
          f"Definition (from `scorer/agentaudit/resolve.py`, asserted on the stored `resolved/*.json`): {n['definition']} "
          f"Status counts over 1,100 cells: " + ", ".join(f"{k} {v}" for k, v in sorted(n['status_counts'].items())) +
          f". Fallback cells = {n['fallback_cells']} ({100 * n['fallback_share']:.1f}%). Reason categories use each coder's verified state: "
          "verified credit (effective >= 1), credit removed by quote verification (raw >= 1, effective 0), scored 0, NA. "
          "A pair where both are verified credits resolves, and a pair of two raw 0s is established_zero, so neither is in this set.", ""]
    hdr = ["Reason"] + ["All 25 items", "Core C1-C14", "Agent A1-A10", "A11"]
    L.append("| " + " | ".join(hdr) + " |")
    L.append("|" + "---|" * len(hdr))
    blocks = [n["all_25"], n["core_C1_C14"], n["agent_A1_A10"], n["agent_A11"]]
    L.append("| Cells | " + " | ".join(str(b["cells"]) for b in blocks) + " |")
    L.append("| Not established | " + " | ".join(f"{b['not_established']} ({100 * b['share_of_cells']:.1f}%)" for b in blocks) + " |")
    for k, lab in CATS:
        L.append(f"| {lab} | " + " | ".join(f"{b['by_category'][k]} ({100 * b['by_category_share'][k]:.1f}%)" if b["not_established"] else "0" for b in blocks) + " |")
    L.append("")
    d = n["verified_credit_vs_zero_detail"]
    L += [f"Verified credit vs 0 ({d['claude_credits_openai_zero'] + d['openai_credits_claude_zero']} cells): Claude credits and OpenAI scores 0 in "
             f"{d['claude_credits_openai_zero']}; OpenAI credits and Claude scores 0 in {d['openai_credits_claude_zero']}; the credited level is 1 in "
             f"{d['credit_level_1']} and 2 in {d['credit_level_2']}. "
             f"Verified credit vs removed credit: Claude holds the verified credit in {n['verified_credit_vs_removed_detail']['claude_holds_credit']}, OpenAI in "
             f"{n['verified_credit_vs_removed_detail']['openai_holds_credit']}. One-sided NA: {n['one_sided_na_detail']['NA_vs_zero']} NA vs 0, "
             f"{n['one_sided_na_detail']['NA_vs_verified_credit']} NA vs verified credit (the latter are not zeros in intent but fall to 0 under the rule). "
             f"Cells with at least one verified credit: {n['cells_with_a_verified_credit']} of {n['fallback_cells']}; none: {n['cells_with_no_verified_credit']}. "
             "Reasons stored for removed quotes (quote-level, a cell may carry several): "
             + ", ".join(f"{k} {v}" for k, v in sorted(n['verified_credit_vs_removed_detail']['removed_quote_reasons'].items(), key=lambda x: -x[1])) + ".", ""]
    L.append("Per item (not established / cells; then the five reasons in the order of the table above):")
    L.append("")
    L.append("| Item | Not est. / cells | VZ | VR | RZ | RR | NA |")
    L.append("|---|---|---|---|---|---|---|")
    for it in ITEM_ORDER:
        b = n["by_item"][it]
        L.append(f"| {it} | {b['not_established']} / {b['cells']} | " + " | ".join(str(b["by_category"][k]) for k, _ in CATS) + " |")
    L.append("")
    z = n["reported_zero"]
    L.append("Resolved REPORTED = 0 cells (final level 0, applicable) and agreed absence:")
    L.append("")
    L.append("| Scope | REPORTED = 0 cells | Both coders raw 0 (established zero) | Both coders verified (effective) 0 |")
    L.append("|---|---|---|---|")
    for k, lab in (("all_25", "All 25 items"), ("core_C1_C14", "Core C1-C14"), ("agent_A1_A10", "Agent A1-A10"), ("agent_A11", "A11")):
        q = z[k]
        L.append(f"| {lab} | {q['reported_zero_cells']} | {q['both_raw_zero']} ({100 * q['both_raw_zero'] / q['reported_zero_cells']:.1f}%) | "
                 f"{q['both_verified_zero']} ({100 * q['both_verified_zero'] / q['reported_zero_cells']:.1f}%) |")
    L.append("")
    L.append(z["note"])
    L.append("")
    # 13.3
    a = r["a11"]
    c = a["bench_class_counts"]
    L += ["### 13.3 A11 credits in the main audit: what the stored verified quotations support", "",
          f"All {a['n_benchmarks']} audited benchmarks. A credit = either coder's effective A11 level >= 1; {a['n_quotes']} verified quotations read and classified by a Claude Sonnet 5.5 subagent "
          "(`analysis/out/a11_quote_classes.csv`). D = dataset or data-source provenance or licence only; E = environment or initial-state provenance "
          "(E only where the quote is about the state of the environment the agent acts in); B = both; N = no credit.", "",
          "| Class | Benchmarks | Borderline-as-D bound | Borderline-as-E bound |", "|---|---|---|---|"]
    for k, lab in (("D", "D: dataset/source only"), ("E", "E: environment state only"), ("B", "B: both"), ("N", "N: no credit")):
        L.append(f"| {lab} | {c[k]} | {a['bench_class_counts_borderline_all_D'][k]} | {a['bench_class_counts_borderline_all_E'][k]} |")
    L.append("")
    L.append("Benchmarks by class: " + "; ".join(f"{k}: {', '.join(v) if v else 'none'}" for k, v in a["bench_by_class"].items()) + ".")
    L.append("")
    L.append(f"Quote level: {a['quote_class_counts']}. Resolved A11 level >= 1 in {a['resolved_final_ge1']} benchmarks; "
             f"at least one coder credit in {a['benchmarks_with_any_credit']}. {a['note']}")
    L.append("")
    # 13.4
    ia = r.get("item_association")
    if ia:
        L += ["### 13.4 Item-level association: does high inter-coder agreement on an item predict high coder-expert agreement?", "",
              ia["scope"], "",
              f"Cells: ABC {ia['n_cells']['abc']} ({ia['n_benchmarks']['abc']} benchmarks), BetterBench {ia['n_cells']['betterbench']} ({ia['n_benchmarks']['betterbench']} benchmarks). "
              "Coder-expert agreement = mean of Claude-vs-expert and OpenAI-vs-expert raw agreement on the item. Per-item values and kappas are in `revision_c1.json` (`item_association.items`).", "",
              "| Instrument | Items | Spearman rho [95% CI] | Mean pair agr. | Mean coder-expert agr. | Share pair > coder-expert [95% CI] | Items with pair >= 0.9 | Coder-expert range there |",
              "|---|---|---|---|---|---|---|---|"]
        for k, lab in (("abc", "ABC"), ("betterbench", "BetterBench"), ("pooled", "Pooled (secondary)")):
            q = ia["instruments"][k]
            rg = q["expert_agr_range_pair_ge_0.9"]
            rgs = "none" if not rg else f"{rg[0]:.3f} to {rg[1]:.3f}"
            L.append(f"| {lab} | {q['n_items']} | {f2(q['rho'])} {ci_s(q['rho_ci95'])} | {f2(q['mean_pair_agr'])} | {f2(q['mean_coder_expert_agr'])} | "
                     f"{f2(q['share_pair_gt_expert'])} {ci_s(q['share_pair_gt_expert_ci95'], 2)} | {q['n_pair_ge_0.9']} | {rgs} |")
        L.append("")
        L.append("Items with pair agreement >= 0.9 (item, pair agreement, coder-expert agreement): " +
                 "; ".join(f"{s}: " + ", ".join(f"{i} ({p:.3f}, {e:.3f})" for i, p, e in v) for s, v in ia["hi_agreement_items"].items()) + ".")
        L.append("")
    # 13.5
    ab = r.get("ablation_agent_without_a11")
    if ab:
        L += ["### 13.5 Scoring-rule ablation, Agent columns on A1-A10 only (A11 excluded)", "",
              ab["definition"] + " Table: `paper/tables/rev_ablation_noA11.tex` (all other columns identical to `rev_ablation.tex`). " + ab["_check"] + ".", "",
              "| Rule | Cells | Agent REPORTED, A1-A10 (%) [95% CI] | Agent fully reported, A1-A10 (%) [95% CI] | With A11 REPORTED / full (%) |", "|---|---|---|---|---|"]
        for rule, q in ab["rules"].items():
            L.append(f"| {q['label']} | {q['n_applicable_cells']} | {100 * q['share_reported']:.1f} [{100 * q['reported_boot_ci'][0]:.1f}, {100 * q['reported_boot_ci'][1]:.1f}] | "
                     f"{100 * q['share_full']:.1f} [{100 * q['full_boot_ci'][0]:.1f}, {100 * q['full_boot_ci'][1]:.1f}] | "
                     f"{100 * q['with_a11_share_reported']:.1f} / {100 * q['with_a11_share_full']:.1f} |")
        L.append("")
    return "\n".join(L)


def write_summary(md: str) -> None:
    txt = SUMMARY.read_text(encoding="utf-8")
    m = re.search(r"^## 13\. Review cycle 1 additions.*?(?=^## \d+\. |\Z)", txt, re.S | re.M)
    if m:
        txt = txt[:m.start()] + md.rstrip() + "\n" + txt[m.end():]
    else:
        txt = txt.rstrip() + "\n\n" + md.rstrip() + "\n"
    SUMMARY.write_text(txt, encoding="utf-8", newline="\n")


def require_inputs() -> None:
    """Release note: this script runs only in the authors' working tree. Stop with the missing inputs named."""
    need = {
        "audit/resolved/ and audit/verified/ (full scorer run directory with stored quote verification)": [V.AUDIT / "resolved", V.AUDIT / "verified"],
        "audit/gold_abc/ and audit/gold_bb/ (coder predictions on the expert-scored cells)": list(GP.RUNS.values()),
        "research/gold/ (published expert scores; not redistributed)": [GP.RDIR / "gold"],
        "analysis/out/rev_pabak.csv and analysis/out/agent_without_a11.json (authors' outputs; copies are in results/analysis_out/)": [OUT / "rev_pabak.csv", OUT / "agent_without_a11.json"],
        "paper/tables/rev_ablation.tex (the authors' LaTeX table; not in the release)": [TABLES / "rev_ablation.tex"],
    }
    missing = [f"  - {what}: {', '.join(str(p) for p in ps if not p.exists())}" for what, ps in need.items() if any(not p.exists() for p in ps)]
    if missing:
        sys.exit("analysis/revision_c1.py cannot run from the public release; these inputs are not redistributed or not present:" + chr(10)
                 + chr(10).join(missing) + chr(10) + "The released output is results/analysis_out/revision_c1.json (and a11_quote_classes.csv).")


def main() -> None:
    require_inputs()
    resolved = R.load_resolved(V.AUDIT)
    assert len(resolved) == 44, len(resolved)
    res = {"seed": SEED, "n_boot": N_BOOT}
    res["pair"] = pair_block()
    ne = not_established_block(resolved)
    res["a11"], _ = a11_block(resolved)
    rows = ne.pop("_rows")
    res["not_established"] = ne
    res["not_established_cells"] = rows
    res["item_association"] = item_assoc_block()
    res["ablation_agent_without_a11"] = ablation_noa11_block(resolved)
    (OUT / "revision_c1.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    md = markdown(res)
    write_summary(md)
    print(md)


if __name__ == "__main__":
    main()
