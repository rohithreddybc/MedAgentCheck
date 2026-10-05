"""Coder test-retest (``agentaudit retest``; design-review-1 T4, decision log 2026-10-05).

The claude and codex command-line interfaces do not expose a temperature, so two of the three coders are probably
sampled. Each coder therefore re-scores a seeded sample of 10 of the 45 frozen packets (seed 20261004, purpose
``retest``; ``sampling.draw_retest_benchmarks``), with the same packet, the same cap, the same item groups and the
same prompt as the original audit run. The second scores go to ``<run>/retest/`` (same layout as a normal run), so
nothing in the audit run is overwritten. Intra-coder agreement is then computed per coder between its original and
its retest scores: raw agreement, ordinal Krippendorff's alpha (NA as missing; CI by bootstrap over the benchmarks),
Cohen's weighted kappa on the applicable cells, and agreement on the REPORTED/NOT REPORTED split. When all coders
were re-scored for a benchmark the retest run is also resolved, and the resolved levels are compared.

Reading: a low value here says the coder is not stable under repetition, so its agreement with other coders is bounded
by its own noise. It says nothing about correctness.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .agree import load_scores
from .items import ITEM_ORDER
from .packet_score import score_packet
from .sampling import RETEST_N, SEED, draw_retest_benchmarks, load_frozen_list
from .stats import alpha_ordinal, bootstrap_ci, cohen_kappa, raw_agreement, weighted_kappa, wilson
from .util import read_json, utcnow, write_json


def retest_dir(run: Path) -> Path:
    return Path(run) / "retest"


def plan_retest(run: Path, frozen_rows: list[dict], n: int = RETEST_N, seed: int = SEED) -> dict:
    """The drawn benchmarks and, for each, its packet directory in the run (None when the run has no packet)."""
    from .perturb import map_bench_dirs

    ids = [r["id"] for r in frozen_rows]
    drawn = draw_retest_benchmarks(ids, n, seed)
    dirs = map_bench_dirs(run, frozen_rows)
    return {"seed": seed, "n": n, "frozen_benchmarks": len(ids),
            "drawn": [{"id": b, "packet_dir": dirs.get(b)} for b in drawn]}


def prepare_retest_packet(run: Path, bench_dir: str) -> Path:
    """Copy the packet (manifest and chunks only, which is all scoring and verification read) into the retest
    run directory. The copy is byte-identical, so the retest sees exactly the original packet."""
    src = Path(run) / "packets" / bench_dir
    dst = retest_dir(run) / "packets" / bench_dir
    dst.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.json", "chunks.jsonl"):
        shutil.copyfile(src / name, dst / name)
    return dst


def run_retest(run: Path, frozen_rows: list[dict], coder_names: list[str], coders: dict[str, dict], make_backend,
               n: int = RETEST_N, seed: int = SEED, force: bool = False, log=print, dry_run: bool = False) -> dict:
    """Re-score the drawn benchmarks with every coder. ``make_backend(spec)`` returns the backend (not called on a
    dry run). A (benchmark, coder) pair without original results is skipped and reported."""
    plan = plan_retest(run, frozen_rows, n, seed)
    rrun = retest_dir(run)
    out = {"plan": plan, "scored": [], "skipped": [], "failed": [], "blocked": None}
    backends: dict[str, object] = {}
    for d in plan["drawn"]:
        bdir = d["packet_dir"]
        if not bdir:
            out["skipped"].append({"bench": d["id"], "reason": "no packet in the run"})
            continue
        todo = []
        for c in coder_names:
            orig = Path(run) / "scoring" / bdir / c
            if not (orig / "results.json").exists():
                out["skipped"].append({"bench": bdir, "coder": c, "reason": "no original results"})
            else:
                todo.append(c)
        if not todo:
            continue
        if not dry_run:
            prepare_retest_packet(run, bdir)
        for c in todo:
            spec = coders[c]
            oman = read_json(Path(run) / "scoring" / bdir / c / "packet_manifest.json")
            groups = len(oman["groups"])
            if dry_run:
                out["scored"].append({"bench": bdir, "coder": c, "dry_run": True, "groups": groups,
                                      "cap_tokens": oman["cap_tokens"], "tokens_sent": oman["tokens_sent"]})
                continue
            if c not in backends:
                backends[c] = make_backend(spec)
            s = score_packet(rrun, bdir, c, spec, backends[c], groups=groups, cap_tokens=oman["cap_tokens"],
                             force=force, log=log)
            nman = read_json(rrun / "scoring" / bdir / c / "packet_manifest.json")
            s["same_rendered_packet"] = nman["rendered_packet_sha256"] == oman["rendered_packet_sha256"]
            out["scored"].append(s)
            if s["failed"]:
                out["failed"].append({"bench": bdir, "coder": c, "failed": s["failed"]})
            if s["blocked"]:
                out["blocked"] = {"bench": bdir, "coder": c, **s["blocked"]}
                log(f"[retest] blocked at {bdir}/{c}; rerun after the limit resets to resume")
                return out
    if not dry_run:
        write_json(rrun / "retest_run.json", {"written_utc": utcnow(), **{k: out[k] for k in ("plan", "skipped", "failed", "blocked")},
                                              "n_scored": len(out["scored"])})
    return out


# ------------------------------------------------------------------ agreement
def _pair_stats(pairs: list[tuple], groups: dict[str, list], n_boot: int, seed: int) -> dict:
    """pairs: [(orig, retest)] raw scores (0|1|2|'NA'). groups: bench -> [[orig, retest]] for the bootstrap."""
    n = len(pairs)
    appl = [(a, b) for a, b in pairs if a != "NA" and b != "NA"]
    na_mismatch = sum(1 for a, b in pairs if (a == "NA") != (b == "NA"))
    out = {"n_cells": n, "n_applicable_both": len(appl), "n_na_mismatch": na_mismatch,
           "raw_agreement": None, "raw_agreement_wilson95": None, "alpha_ordinal": None, "alpha_ci95": None,
           "weighted_kappa_quadratic": None, "cohen_kappa": None, "reported_split_agreement": None,
           "n_exact": 0}
    if not n:
        return out
    exact = sum(1 for a, b in pairs if a == b)
    out["n_exact"] = exact
    out["raw_agreement"] = exact / n
    w = wilson(exact, n)
    out["raw_agreement_wilson95"] = list(w) if w else None
    units = [[a, b] for a, b in pairs]
    out["alpha_ordinal"] = alpha_ordinal(units)
    if out["alpha_ordinal"] is not None and len(groups) >= 2:
        ci = bootstrap_ci(groups, alpha_ordinal, n_boot=n_boot, seed=seed)
        out["alpha_ci95"] = list(ci) if ci else None
    if appl:
        a, b = [x for x, _ in appl], [y for _, y in appl]
        out["weighted_kappa_quadratic"] = weighted_kappa(a, b, (0, 1, 2), "quadratic")
        out["cohen_kappa"] = cohen_kappa(a, b)
        out["reported_split_agreement"] = raw_agreement([int(x >= 1) for x in a], [int(y >= 1) for y in b])
    return out


def compare_retest(run: Path, frozen_rows: list[dict], n: int = RETEST_N, seed: int = SEED, n_boot: int = 2000) -> dict:
    """Intra-coder agreement between the original and the retest scores, over the drawn benchmarks."""
    plan = plan_retest(run, frozen_rows, n, seed)
    rrun = retest_dir(run)
    benches = [d["packet_dir"] for d in plan["drawn"] if d["packet_dir"]]
    o_cells, o_fam = load_scores(run, benches)
    r_cells, r_fam = load_scores(rrun, benches)
    coders = sorted(set(o_fam) & set(r_fam))
    res: dict = {"written_utc": utcnow(), "seed": seed, "n_drawn": len(plan["drawn"]),
                 "drawn": plan["drawn"], "n_boot": n_boot, "coders": {}, "resolved": None,
                 "note": "intra-coder agreement between the original and the retest score of the same cell; alpha is "
                         "ordinal on [original, retest] pairs, NA as missing, CI by bootstrap over benchmarks"}
    for c in coders:
        pairs, groups, per_item = [], {}, {}
        used = set()
        for (b, it), votes in sorted(o_cells.items()):
            rv = r_cells.get((b, it), {})
            if c not in votes or c not in rv:
                continue
            p = (votes[c], rv[c])
            pairs.append(p)
            groups.setdefault(b, []).append(list(p))
            used.add(b)
            d = per_item.setdefault(it, [0, 0])
            d[0] += 1
            d[1] += p[0] == p[1]
        st = _pair_stats(pairs, groups, n_boot, seed)
        st["family"] = o_fam[c]
        st["n_benchmarks"] = len(used)
        st["per_item_agreement"] = {it: {"n": per_item[it][0], "agree": per_item[it][1]}
                                    for it in ITEM_ORDER if it in per_item}
        # same model answering both times?
        ids = {}
        for b in sorted(used):
            for tag, root in (("original", Path(run)), ("retest", rrun)):
                gp = root / "scoring" / b / c / "group1.json"
                if gp.exists():
                    ids.setdefault(tag, set()).add(read_json(gp).get("model_id"))
        st["model_ids"] = {k: sorted(map(str, v)) for k, v in ids.items()}
        st["same_model_id"] = (ids.get("original") == ids.get("retest")) if ids else None
        res["coders"][c] = st
    # resolved levels, when the retest run has been resolved for the drawn benchmarks
    pairs = []
    for b in benches:
        po, pr = Path(run) / "resolved" / f"{b}.json", rrun / "resolved" / f"{b}.json"
        if po.exists() and pr.exists():
            co, cr = read_json(po)["cells"], read_json(pr)["cells"]
            pairs.extend((co[i]["final"], cr[i]["final"]) for i in ITEM_ORDER if i in co and i in cr)
    if pairs:
        res["resolved"] = {"n_cells": len(pairs), "raw_agreement": sum(a == b for a, b in pairs) / len(pairs),
                           "alpha_ordinal": alpha_ordinal([list(p) for p in pairs])}
    write_json(rrun / "retest_agreement.json", res)
    return res
