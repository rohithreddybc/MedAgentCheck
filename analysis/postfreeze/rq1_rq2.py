"""RQ1 and RQ2 from the scorer's output directories (the 45-benchmark audit).

Input: one scorer run directory (``--run``), laid out as written by ``agentaudit`` (scorer/ARCHITECTURE.md v3):

  resolved/<bench>.json                  {"bench", "cells": {item: {"final", "status", "supporters", "fallback",
                                          "majority_final", "votes": {coder: {"raw", "effective"}}}}}
  coding/<bench>/<item>/<coder>.json     {"status", "family", "parsed": {"score", ...}}      (raw scores: alpha)
  verified/<bench>/<item>/<coder>.json   {"score_raw", "effective", "contradicted", "contradiction_verified",
                                          "family", ...}                                       (contradiction flags)
  perturb/summary.json                   {"rows": [{variant_id, item, vtype, coder, level, ok, ...}]}
  gold-<set>/agreement/agreement.json    {"by_coder": {coder: stats}, "resolved": stats}      (abc, betterbench)

Outputs (CSV to ``--out``, bare booktabs tabulars to ``--tables``):

  RQ1  rq1_prevalence.csv/.tex     per item: share REPORTED (final >= 1) and fully reported (final == 2) among
                                   applicable cells, Wilson 95% CI; the majority-rule variant alongside
       rq1_modules.csv/.tex        core versus agent module: pooled cell shares (Wilson, plus a bootstrap CI over
                                   benchmarks) and the mean per-benchmark fraction of the maximum score
       rq1_contradictions.csv      cells carrying a coder-raised contradiction flag, per item (candidates only)
       rq1_contradictions_by_bench.csv
       rq1_resolution.csv          resolution status counts and fallback share
  RQ2  rq2_alpha.csv/.tex          ordinal Krippendorff's alpha, all coders and each cross-family pair, overall and
                                   per item, bootstrap CI over benchmarks (agentaudit.stats)
       rq2_perturbation.csv/.tex   sensitivity and specificity per coder (and RESOLVED), overall, per variant type,
                                   per item and per item x type, Wilson 95% CI
       rq2_gold.csv/.tex           agreement with published expert scores (kappa or weighted kappa) per coder and
                                   resolved, from the scorer's gold agreement files

R-rule sensitivity (``--exclude-rule-affected``; design-review-1 T7). Rules R1-R7 and R6a were written on 2026-10-04 while the
first-pass full-text decisions were being adjudicated (research/eligibility/adjudication.md). The switch drops every
benchmark whose inclusion depends on such a rule, that is, a frozen-list row whose ``rule_applied`` names an R rule (rows
marked "none ... re-checked, no change" are kept) or whose adjudicated decision differs from the first-pass decision and
is INCLUDE (research/eligibility/overrides_final.csv), recomputes RQ1 and the alpha table on the remaining benchmarks, and
writes the results with the suffix ``_ruleexcl`` (the primary outputs are not touched), plus the excluded list and a
per-item comparison with the full set. Perturbation and gold tables are not benchmark-population results and are skipped.

Cells scored NA are not applicable and leave the denominator. A cell "not established" is level 0 (resolution rule).
Cells are not independent (items within a benchmark), so the pooled Wilson interval is a descriptive width; the
benchmark-clustered bootstrap CI is given for the module summaries.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from itertools import combinations
from pathlib import Path

import numpy as np

from common import OUT, ROOT, SEED, TABLES, booktabs, fci, fnum, tex_escape, write_csv

from agentaudit.agree import load_scores  # noqa: E402
from agentaudit.items import ITEM_ORDER, load_items  # noqa: E402
from agentaudit.perturb import bench_dir_candidates  # noqa: E402
from agentaudit.stats import alpha_ordinal, bootstrap_ci, wilson  # noqa: E402

N_BOOT = 2000
POSITIVE = ("inject", "buried", "paraphrase")
NEGATIVE = ("deletion", "decoy")
VTYPES = ("inject", "buried", "paraphrase", "deletion", "decoy")
GOLD_SETS = ("abc", "betterbench")
ELIGIBILITY = ROOT / "research" / "eligibility"
FROZEN_LIST = ELIGIBILITY / "frozen_list_v1.csv"
OVERRIDES = ELIGIBILITY / "overrides_final.csv"
SENS_SUFFIX = "_ruleexcl"
_RULE = re.compile(r"\bR[1-7]a?\b")
# Table labels used in the paper (paper/sections/checklist.tex, Table II item names; coder names as in Section IV).
# They change the printed labels only; items.yaml (frozen) and the CSV outputs are untouched.
ITEM_LABEL = {
    "A1": "Run count per reported number", "A2": "Uncertainty with stated unit", "A3": "Repeat-run reliability",
    "A4": "Model and harness pinning", "A5": "Tool contract specified", "A6": "Tool contract verified",
    "A7": "Write-action disclosure", "A8": "Grader input and validation", "A9": "Agent-channel contamination",
    "A10": "Slice reporting", "A11": "Environment-state provenance",
}
CODER_LABEL = {"codex": "OpenAI (gpt-5.5)", "sonnet": "Claude Sonnet"}


def coder_label(name: str) -> str:
    return CODER_LABEL.get(name, name)


# ------------------------------------------------------------------ loading
def _rj(p: Path):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load_resolved(run: Path) -> dict[str, dict]:
    base = Path(run) / "resolved"
    out = {}
    if base.exists():
        for f in sorted(base.glob("*.json")):
            if f.stem == "summary":
                continue
            cells = _rj(f)["cells"]
            if cells:  # ANALYSIS-SIDE FIX 5: a coder failure (HealthCraft) has no cells; it is reported separately, not as a benchmark
                out[f.stem] = cells
    return out


def load_verified(run: Path, benches: list[str]) -> dict[tuple[str, str], dict[str, dict]]:
    out: dict[tuple[str, str], dict[str, dict]] = {}
    for b in benches:
        base = Path(run) / "verified" / b
        if not base.exists():
            continue
        for idir in sorted(base.iterdir()):
            for f in sorted(idir.glob("*.json")):
                out.setdefault((b, idir.name), {})[f.stem] = _rj(f)
    return out


def _share(k: int, n: int):
    if n <= 0:
        return None, None, None
    ci = wilson(k, n)
    return k / n, ci[0], ci[1]


# ------------------------------------------------------------------ R-rule sensitivity
def _read_csv(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def rule_affected(frozen_list: Path = FROZEN_LIST, overrides: Path = OVERRIDES) -> list[dict]:
    """Frozen-list rows whose inclusion depends on a rule written after the first pass (R1-R7, R6a).

    A row counts when its ``rule_applied`` names an R rule (a "none (... R1-R7 re-checked, no change)" entry does not),
    or when overrides_final.csv records a first-pass decision that differs from an INCLUDE final decision. Returns
    rows {id, benchmark_name, reason, _row}."""
    ov = {r["id"]: r for r in _read_csv(overrides)} if Path(overrides).exists() else {}
    out = []
    for r in _read_csv(frozen_list):
        why = []
        rule = (r.get("rule_applied") or "").strip()
        if rule and not rule.lower().startswith("none") and _RULE.search(rule):
            why.append(f"rule_applied: {rule}")
        o = ov.get(r["id"])
        if o and o["first_pass"] != o["final"] and o["final"].startswith("INCLUDE"):
            why.append(f"decision changed {o['first_pass']} -> {o['final']} ({o.get('rule', '')})")
        if why:
            out.append({"id": r["id"], "benchmark_name": r.get("benchmark_name", ""), "reason": "; ".join(why),
                        "_row": r})
    return out


MANIFESTS = ROOT / "audit" / "manifests"


def manifest_slugs(manifests: Path = MANIFESTS) -> dict[str, str]:
    """frozen-list id -> packet/run slug, read from audit/manifests/<slug>.yaml (``name`` and ``frozen_list_id``).

    ANALYSIS-SIDE FIX 4 (2026-10-06): the frozen ``bench_dir_candidates`` builds underscore slugs and bare names, so it
    cannot find hyphenated packet directories (diaggym-diagbench, healthcare-ai-gym, med-inquire, medagentbench-v2) or
    slugs that differ from the benchmark name (rha-safety, clinicalagent-bench, evimed). With it alone 7 of 14
    rule-affected benchmarks were not matched and silently stayed in the sensitivity sample. The manifests carry the
    exact mapping. The frozen package is not edited."""
    out: dict[str, str] = {}
    if Path(manifests).exists():
        for f in sorted(Path(manifests).glob("*.yaml")):
            txt = f.read_text(encoding="utf-8")
            n = re.search(r"^name:\s*(\S+)", txt, re.M)
            i = re.search(r"^frozen_list_id:\s*(\S+)", txt, re.M)
            if n and i:
                out[i.group(1).strip("'\"")] = n.group(1).strip("'\"")
    return out


def rule_affected_benches(benches: list[str], frozen_list: Path = FROZEN_LIST,
                          overrides: Path = OVERRIDES, manifests: Path = MANIFESTS) -> tuple[dict[str, dict], list[dict]]:
    """Map the affected frozen rows to the benchmark names in the run. Returns ({bench: row}, [rows with no
    bench in the run])."""
    have = set(benches)
    slugs = manifest_slugs(manifests)
    hit: dict[str, dict] = {}
    unmatched = []
    for a in rule_affected(frozen_list, overrides):
        cands = ([slugs[a["id"]]] if a["id"] in slugs else []) + bench_dir_candidates(a["_row"])
        name = next((c for c in cands if c in have), None)
        row = {k: v for k, v in a.items() if k != "_row"}
        if name:
            hit[name] = row
        else:
            unmatched.append(row)
    return hit, unmatched


def sensitivity_delta(full: list[dict], sub: list[dict]) -> list[dict]:
    """Per-item share reported and fully reported on all benchmarks versus after excluding the rule-affected ones."""
    f = {r["item"]: r for r in full if r["rule"] == "resolved"}
    rows = []
    for r in sub:
        if r["rule"] != "resolved":
            continue
        a = f.get(r["item"], {})

        def diff(x, y):
            return x - y if x is not None and y is not None else None

        rows.append({"item": r["item"], "n_all": a.get("n_applicable"), "reported_all": a.get("share_reported"),
                     "n_excl": r["n_applicable"], "reported_excl": r["share_reported"],
                     "reported_diff": diff(r["share_reported"], a.get("share_reported")),
                     "full_all": a.get("share_full"), "full_excl": r["share_full"],
                     "full_diff": diff(r["share_full"], a.get("share_full"))})
    return rows


# ------------------------------------------------------------------ RQ1
def level_of(v) -> int | None:
    """Numeric level, or None for NA."""
    return None if v == "NA" else int(v)


def prevalence(resolved: dict[str, dict], rule: str = "final") -> list[dict]:
    items = load_items()
    rows = []
    for it in ITEM_ORDER:
        cells = [(b, c[it]) for b, c in resolved.items() if it in c]
        if not cells:
            continue
        lv = [level_of(c[rule]) for _, c in cells]
        app = [x for x in lv if x is not None]
        n_rep = sum(x >= 1 for x in app)
        n_full = sum(x == 2 for x in app)
        r = _share(n_rep, len(app))
        f = _share(n_full, len(app))
        rows.append({
            "item": it, "module": items[it].module, "title": items[it].title,
            "rule": "resolved" if rule == "final" else "majority",
            "n_cells": len(cells), "n_na": len(lv) - len(app), "n_applicable": len(app),
            "n_reported": n_rep, "share_reported": r[0], "reported_lo": r[1], "reported_hi": r[2],
            "n_full": n_full, "share_full": f[0], "full_lo": f[1], "full_hi": f[2],
            "n_fallback": sum(1 for _, c in cells if c.get("fallback")) if rule == "final" else None})
    return rows


def module_summary(resolved: dict[str, dict], rule: str = "final", n_boot: int = N_BOOT) -> list[dict]:
    items = load_items()
    rows = []
    for mod in ("core", "agent"):
        ids = [i for i in ITEM_ORDER if items[i].module == mod]
        groups: dict[str, list] = {}
        frac: list[float] = []
        for b, cells in resolved.items():
            units = []
            for i in ids:
                if i in cells and level_of(cells[i][rule]) is not None:
                    x = level_of(cells[i][rule])
                    units.append((x >= 1, x == 2, x))
            if units:
                groups[b] = units
                frac.append(sum(u[2] for u in units) / (2 * len(units)))
        units = [u for g in groups.values() for u in g]
        n = len(units)
        if not n:
            continue
        k_rep, k_full = sum(u[0] for u in units), sum(u[1] for u in units)
        wr, wf = wilson(k_rep, n), wilson(k_full, n)
        br = bootstrap_ci(groups, lambda us: sum(u[0] for u in us) / len(us) if us else None, n_boot=n_boot)
        bf = bootstrap_ci(groups, lambda us: sum(u[1] for u in us) / len(us) if us else None, n_boot=n_boot)
        rows.append({
            "module": mod, "rule": "resolved" if rule == "final" else "majority", "n_items": len(ids),
            "n_benchmarks": len(groups), "n_applicable_cells": n,
            "share_reported": k_rep / n, "reported_wilson_lo": wr[0], "reported_wilson_hi": wr[1],
            "reported_boot_lo": br[0] if br else None, "reported_boot_hi": br[1] if br else None,
            "share_full": k_full / n, "full_wilson_lo": wf[0], "full_wilson_hi": wf[1],
            "full_boot_lo": bf[0] if bf else None, "full_boot_hi": bf[1] if bf else None,
            "mean_bench_fraction_of_max": float(np.mean(frac)), "median_bench_fraction_of_max": float(np.median(frac))})
    return rows


def resolution_summary(resolved: dict[str, dict]) -> list[dict]:
    counts: dict[str, int] = {}
    total = fb = same = 0
    for cells in resolved.values():
        for c in cells.values():
            counts[c["status"]] = counts.get(c["status"], 0) + 1
            total += 1
            fb += bool(c.get("fallback"))
            same += c["final"] == c["majority_final"]
    rows = [{"status": k, "n_cells": v, "share": v / total} for k, v in sorted(counts.items())]
    rows.append({"status": "ALL_FALLBACK", "n_cells": fb, "share": fb / total if total else None})
    rows.append({"status": "PRIMARY_EQUALS_MAJORITY", "n_cells": same, "share": same / total if total else None})
    rows.append({"status": "TOTAL_CELLS", "n_cells": total, "share": 1.0 if total else None})
    return rows


def contradictions(verified: dict[tuple[str, str], dict[str, dict]]) -> tuple[list[dict], list[dict]]:
    per_item: dict[str, dict] = {i: {"item": i, "cells_with_flag": 0, "cells_flag_verified_quote": 0,
                                     "cells_flag_two_families": 0, "coder_flags": 0} for i in ITEM_ORDER}
    per_bench: dict[str, dict] = {}
    for (b, it), votes in sorted(verified.items()):
        fl = {c: v for c, v in votes.items() if v.get("contradicted")}
        pb = per_bench.setdefault(b, {"bench": b, "cells_with_flag": 0, "cells_flag_verified_quote": 0,
                                      "cells_flag_two_families": 0, "items": []})
        if not fl:
            continue
        ver = any(v.get("contradiction_verified") for v in fl.values())
        fams = {v.get("family") or c for c, v in fl.items()}
        d = per_item.setdefault(it, {"item": it, "cells_with_flag": 0, "cells_flag_verified_quote": 0,
                                     "cells_flag_two_families": 0, "coder_flags": 0})
        d["cells_with_flag"] += 1
        d["cells_flag_verified_quote"] += ver
        d["cells_flag_two_families"] += len(fams) >= 2
        d["coder_flags"] += len(fl)
        pb["cells_with_flag"] += 1
        pb["cells_flag_verified_quote"] += ver
        pb["cells_flag_two_families"] += len(fams) >= 2
        pb["items"].append(it)
    for d in per_bench.values():
        d["items"] = ";".join(d["items"])
    items = list(per_item.values())
    note = "candidate flags only until checked against the benchmark's documentation and offered right of reply"
    for d in items:
        d["status"] = note
    return items, list(per_bench.values())


# ------------------------------------------------------------------ RQ2: alpha
def alpha_table(run: Path, benches: list[str], n_boot: int = N_BOOT, seed: int = SEED) -> list[dict]:
    cells, fam = load_scores(run, benches)
    coders = sorted(fam)
    sets: dict[str, list[str]] = {}
    if len(coders) >= 2:
        sets["all:" + "+".join(coders)] = coders
    for a, b in combinations(coders, 2):
        if fam[a] != fam[b]:
            sets[f"cross-family:{a}|{b}"] = [a, b]

    def one(cs: list[str], item: str | None) -> dict:
        groups: dict[str, list] = {b: [] for b in benches}
        for (b, it), votes in sorted(cells.items()):
            if (item is not None and it != item) or not all(c in votes for c in cs):
                continue
            groups[b].append([votes[c] for c in cs])
        groups = {b: u for b, u in groups.items() if u}
        units = [u for us in groups.values() for u in us]
        a = alpha_ordinal(units)
        ci = bootstrap_ci(groups, alpha_ordinal, n_boot=n_boot, seed=seed) if a is not None else None
        return {"alpha": a, "ci_lo": ci[0] if ci else None, "ci_hi": ci[1] if ci else None,
                "units": len(units), "benchmarks": len(groups)}

    rows = []
    for name, cs in sets.items():
        kind = "all_coders" if name.startswith("all:") else "cross_family_pair"
        for item in [None] + ITEM_ORDER:
            r = one(cs, item)
            if item is not None and not r["units"]:
                continue
            rows.append({"set": name, "kind": kind, "scope": "overall" if item is None else "item",
                         "item": item or "", **r, "n_boot": n_boot, "seed": seed})
    return rows


# ------------------------------------------------------------------ RQ2: perturbation
def _metrics(rows: list[dict]) -> list[tuple[str, int, int]]:
    pos = [r for r in rows if r["vtype"] in POSITIVE]
    neg = [r for r in rows if r["vtype"] in NEGATIVE]
    return [("sensitivity", sum(bool(r["ok"]) for r in pos), len(pos)),
            ("sensitivity_any_level", sum(r["level"] >= 1 for r in pos), len(pos)),
            ("specificity", sum(bool(r["ok"]) for r in neg), len(neg))]


def perturbation_table(run: Path) -> list[dict]:
    p = Path(run) / "perturb" / "summary.json"
    if not p.exists():
        return []
    rows = _rj(p).get("rows", [])
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


# ------------------------------------------------------------------ RQ2: gold
def gold_table(run: Path, gold_dirs: dict[str, Path] | None = None) -> list[dict]:
    """``gold_dirs`` (ANALYSIS-SIDE ADDITION, 2026-10-06): the gold agreement outputs live in audit/gold_abc/gold-abc and
    audit/gold_bb/gold-betterbench rather than in <run>/gold-<set>; map set -> directory holding agreement/agreement.json."""
    rows = []
    for s in GOLD_SETS:
        gd = (gold_dirs or {}).get(s)
        p = (Path(gd) if gd else Path(run) / f"gold-{s}") / "agreement" / "agreement.json"
        if not p.exists():
            continue
        res = _rj(p)
        entries = list(res.get("by_coder", {}).items())
        if res.get("resolved"):
            entries.append(("RESOLVED", res["resolved"]))
        for coder, st in entries:
            ra = st.get("raw_agreement") or {}
            ci = st.get("primary_ci95_bootstrap_over_benchmarks") or [None, None]
            rows.append({"set": s, "coder": coder, "n_cells": st.get("n_cells"),
                         "n_gold_na": st.get("n_gold_na"), "raw_agreement": ra.get("rate"),
                         "raw_lo": (ra.get("wilson95") or [None, None])[0],
                         "raw_hi": (ra.get("wilson95") or [None, None])[1],
                         "majority_baseline": st.get("majority_class_baseline_agreement"),
                         "cohen_kappa": st.get("cohen_kappa"),
                         "weighted_kappa_quadratic": st.get("weighted_kappa_quadratic"),
                         "primary_statistic": st.get("primary_statistic"), "primary_value": st.get("primary_value"),
                         "primary_ci_lo": ci[0], "primary_ci_hi": ci[1]})
    return rows


# ------------------------------------------------------------------ tex
def _pct(x, lo, hi) -> str:
    if x is None or x == "":
        return "--"
    return f"{100 * x:.0f} [{100 * lo:.0f}, {100 * hi:.0f}]"


def tex_all(res: dict) -> dict[str, str]:
    out = {}
    hdr = "Generated by analysis/rq1_rq2.py from scorer outputs. Do not edit by hand."
    prev = [r for r in res["prevalence"] if r["rule"] == "resolved"]
    if prev:
        rows = []
        for r in prev:
            rows.append([r["item"], tex_escape(ITEM_LABEL.get(r["item"], r["title"])), str(r["n_applicable"]),
                         _pct(r["share_reported"], r["reported_lo"], r["reported_hi"]),
                         _pct(r["share_full"], r["full_lo"], r["full_hi"])])
        core_idx = [i for i, r in enumerate(prev) if r["module"] == "core"]
        mid = {max(core_idx)} if core_idx and len(core_idx) < len(prev) else set()
        out["rq1_prevalence.tex"] = booktabs(
            "llccc", ["Item", "Property", "$n$", "Reported (\\%) [95\\% CI]", "Fully reported (\\%) [95\\% CI]"], rows,
            hdr + "\nReported = level 1 or 2; fully reported = level 2; NA cells leave the denominator.", mid)
    if res["modules"]:
        rows = []
        for r in res["modules"]:
            if r["rule"] != "resolved":
                continue
            rows.append([r["module"].capitalize(), str(r["n_applicable_cells"]),
                         _pct(r["share_reported"], r["reported_boot_lo"] if r["reported_boot_lo"] is not None
                              else r["reported_wilson_lo"], r["reported_boot_hi"] if r["reported_boot_hi"] is not None
                              else r["reported_wilson_hi"]),
                         _pct(r["share_full"], r["full_boot_lo"] if r["full_boot_lo"] is not None
                              else r["full_wilson_lo"], r["full_boot_hi"] if r["full_boot_hi"] is not None
                              else r["full_wilson_hi"]),
                         fnum(r["mean_bench_fraction_of_max"])])
        out["rq1_modules.tex"] = booktabs(
            "lcccc", ["Module", "Cells", "Reported (\\%)", "Fully reported (\\%)", "Mean fraction of max."], rows,
            hdr + "\nCIs: bootstrap over benchmarks (Wilson when fewer than two benchmarks).")
    al = [r for r in res["alpha"] if r["scope"] == "overall"]
    if al:
        def _alpha_labels(r):
            if r["kind"] == "all_coders":
                return "Both coders", "all coders"
            names = r["set"].replace("cross-family:", "").split("|")
            return "Cross-family pair", " vs ".join(coder_label(n) for n in names)
        rows = [[tex_escape(_alpha_labels(r)[0]), tex_escape(_alpha_labels(r)[1]),
                 fnum(r["alpha"], 3), fci(r["ci_lo"], r["ci_hi"], 3), str(r["units"])] for r in al]
        out["rq2_alpha.tex"] = booktabs("llccr", ["Coders", "Set", "$\\alpha$", "95\\% CI", "Cells"], rows,
                                        hdr + "\nOrdinal Krippendorff alpha on raw scores, NA as missing; "
                                              "CI by bootstrap over benchmarks.")
    pt = res["perturbation"]
    if pt:
        coders = sorted({r["coder"] for r in pt}, key=lambda c: (c == "RESOLVED", c))
        rows = []
        for c in coders:
            def get(metric, scope="overall", vt=""):
                for r in pt:
                    if (r["coder"], r["metric"], r["scope"], r["vtype"]) == (c, metric, scope, vt) and not r["item"]:
                        return r
                return None
            cells = []
            for metric, scope, vt in [("sensitivity", "overall", "")] + [
                    ("sensitivity", "type", t) for t in POSITIVE] + [("specificity", "overall", "")] + [
                    ("specificity", "type", t) for t in NEGATIVE]:
                g = get(metric, scope, vt)
                cells.append(_pct(g["rate"], g["wilson_lo"], g["wilson_hi"]) if g else "--")
            rows.append([tex_escape(coder_label(c))] + cells)
        out["rq2_perturbation.tex"] = booktabs(
            "lccccccc", ["Coder", "Sens.", "Inject", "Buried", "Paraphr.", "Spec.", "Deletion", "Decoy"], rows,
            hdr + ("\nPARTIAL (DRAFT): one coder family only, no RESOLVED row; regenerate when the second family is coded."
                   if len([c for c in coders if c != "RESOLVED"]) < 2 else "") +
            "\nPercent [Wilson 95% CI]. Sensitivity: inject, buried, paraphrase. Specificity: deletion, decoy.")
    gd = res["gold"]
    if gd:
        rows = []
        for r in gd:
            primary = r["weighted_kappa_quadratic"] if r["set"] == "betterbench" else r["cohen_kappa"]
            rows.append([r["set"].upper() if r["set"] == "abc" else "BetterBench", tex_escape(coder_label(r["coder"])),
                         str(r["n_cells"]), fnum(r["raw_agreement"]), fnum(primary, 2),
                         fci(r["primary_ci_lo"], r["primary_ci_hi"]) if r["primary_ci_lo"] not in (None, "") else "--"])
        out["rq2_gold.tex"] = booktabs(
            "llcccc", ["Gold set", "Coder", "Cells", "Raw agr.", "$\\kappa$ or $\\kappa_w$", "95\\% CI"], rows,
            hdr + "\nABC: Cohen kappa. BetterBench: quadratic weighted kappa. CI by bootstrap over benchmarks.")
    return out


# ------------------------------------------------------------------ main
def run(run_dir: Path, out_dir: Path = OUT, tables_dir: Path = TABLES, n_boot: int = N_BOOT,
        exclude_rule_affected: bool = False, frozen_list: Path = FROZEN_LIST, overrides: Path = OVERRIDES,
        gold_dirs: dict[str, Path] | None = None, perturb_run: Path | None = None) -> dict:
    run_dir, out_dir, tables_dir = Path(run_dir), Path(out_dir), Path(tables_dir)
    resolved = load_resolved(run_dir)
    sfx = ""
    res: dict = {}
    if exclude_rule_affected:
        sfx = SENS_SUFFIX
        full_prev = prevalence(resolved, "final")
        hit, unmatched = rule_affected_benches(sorted(resolved), frozen_list, overrides)
        resolved = {b: c for b, c in resolved.items() if b not in hit}
        res["excluded"] = [{"bench": b, **r} for b, r in sorted(hit.items())]
        res["excluded_no_bench_in_run"] = unmatched
    benches = sorted(resolved)
    verified = load_verified(run_dir, benches)
    res["benchmarks"] = benches
    res["prevalence"] = prevalence(resolved, "final") + prevalence(resolved, "majority_final")
    res["modules"] = module_summary(resolved, "final", n_boot) + module_summary(resolved, "majority_final", n_boot)
    res["resolution"] = resolution_summary(resolved)
    res["contradictions"], res["contradictions_by_bench"] = contradictions(verified)
    res["alpha"] = alpha_table(run_dir, benches, n_boot)
    if exclude_rule_affected:  # perturbation and gold are not population results; skipped in the sensitivity run
        res["perturbation"], res["gold"] = [], []
        res["delta"] = sensitivity_delta(full_prev, res["prevalence"])
    else:
        res["perturbation"] = perturbation_table(perturb_run or run_dir)
        res["gold"] = gold_table(run_dir, gold_dirs)
    keys = [("rq1_prevalence", "prevalence"), ("rq1_modules", "modules"), ("rq1_resolution", "resolution"),
            ("rq1_contradictions", "contradictions"), ("rq1_contradictions_by_bench", "contradictions_by_bench"),
            ("rq2_alpha", "alpha"), ("rq2_perturbation", "perturbation"), ("rq2_gold", "gold")]
    for name, key in keys:
        if res.get(key):
            write_csv(out_dir / f"{name}{sfx}.csv", res[key])
    if exclude_rule_affected:
        for name, key in [("rq1_rule_excluded", "excluded"), ("rq1_rule_excluded_no_bench", "excluded_no_bench_in_run"),
                          ("rq1_rule_sensitivity_delta", "delta")]:
            if res.get(key):
                write_csv(out_dir / f"{name}.csv", res[key])
    tables_dir.mkdir(parents=True, exist_ok=True)
    for name, text in tex_all(res).items():
        stem, ext = name.rsplit(".", 1)
        (tables_dir / f"{stem}{sfx}.{ext}").write_text(text, encoding="utf-8", newline="\n")
    return res


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--run", type=Path, required=True, help="scorer run directory (resolved/, coding/, ...)")
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--tables", type=Path, default=TABLES)
    ap.add_argument("--n-boot", type=int, default=N_BOOT)
    ap.add_argument("--exclude-rule-affected", action="store_true",
                    help="R-rule sensitivity: drop benchmarks whose inclusion depends on R1-R7/R6a "
                         "(writes *_ruleexcl outputs; the primary outputs are not touched)")
    ap.add_argument("--gold-abc", type=Path, help="dir holding agreement/agreement.json for the ABC gold set")
    ap.add_argument("--gold-betterbench", type=Path, help="same, BetterBench")
    ap.add_argument("--perturb-run", type=Path, help="run dir whose perturb/summary.json to use (default: --run)")
    ap.add_argument("--frozen-list", type=Path, default=FROZEN_LIST)
    ap.add_argument("--overrides", type=Path, default=OVERRIDES)
    a = ap.parse_args(argv)
    gd = {k: v for k, v in (("abc", a.gold_abc), ("betterbench", a.gold_betterbench)) if v}
    res = run(a.run, a.out, a.tables, a.n_boot, a.exclude_rule_affected, a.frozen_list, a.overrides, gd or None,
              a.perturb_run)
    if a.exclude_rule_affected:
        print(f"excluded {len(res['excluded'])} rule-affected benchmarks "
              f"({len(res['excluded_no_bench_in_run'])} affected rows have no bench in the run)")
    print(f"{len(res['benchmarks'])} benchmarks; prevalence rows {len(res['prevalence'])}; alpha rows "
          f"{len(res['alpha'])}; perturbation rows {len(res['perturbation'])}; gold rows {len(res['gold'])}")


if __name__ == "__main__":
    main()
