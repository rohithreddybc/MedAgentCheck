"""Stage 5: resolution rule (hash-frozen with the protocol).

Final level = the highest s in {2, 1} that at least 2 coders assign at s or above,
each with verified quotes, where the supporting coders include at least two model
families (the cross-family coder gpt-oss and at least one Claude coder). If no
level qualifies the cell is "not established": level 0, flagged. NA is accepted only
if at least 2 coders, spanning two families, say NA; otherwise the cell is treated
as 0. A level that qualifies takes precedence over an NA. A 0 counts as
established only if at least 2 coders, spanning two families, explicitly scored 0.
A majority-rule variant (raw scores, no verification, no family requirement) is
computed for sensitivity.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

from .items import ITEM_ORDER
from .util import read_json, write_json


def _accepts(coders: list[str], fam: dict[str, str], require_cross_family: bool) -> bool:
    if len(coders) < 2:
        return False
    return (not require_cross_family) or len({fam[c] for c in coders}) >= 2


def majority_level(votes: dict[str, dict], levels: tuple = (2, 1)) -> int | str:
    n = len(votes)
    if n == 0:
        return 0
    thr = n // 2 + 1
    na = sum(1 for v in votes.values() if v["raw"] == "NA")
    if na >= thr:
        return "NA"
    nums = [v["raw"] for v in votes.values() if v["raw"] != "NA"]
    for s in levels:
        if sum(1 for x in nums if x >= s) >= thr:
            return s
    return 0


def resolve_cell(votes: dict[str, dict], require_cross_family: bool = True, levels: tuple = (2, 1)) -> dict:
    """votes: coder -> {"raw": 0|1|2|"NA", "effective": 0|1|2|"NA", "family": str}.

    ``levels`` lists the positive levels from the top down. The checklist scale is (2, 1); the gold-validation
    runs use (1,) for ABC's binary scale and (3, 2, 1) for BetterBench's ordinal 0-3 scale."""
    fam = {c: v.get("family") or c for c, v in votes.items()}
    rec = {"final": 0, "status": None, "supporters": [], "fallback": False,
           "majority_final": majority_level(votes, levels), "votes": {c: {"raw": v["raw"], "effective": v["effective"]}
                                                              for c, v in votes.items()}}
    if len(votes) < 2:
        rec.update(status="insufficient_coders", fallback=True)
        return rec
    for s in levels:
        sup = sorted(c for c, v in votes.items() if v["effective"] != "NA" and v["effective"] >= s)
        if _accepts(sup, fam, require_cross_family):
            rec.update(final=s, status="resolved", supporters=sup)
            return rec
    na = sorted(c for c, v in votes.items() if v["effective"] == "NA")
    if _accepts(na, fam, require_cross_family):
        rec.update(final="NA", status="na_accepted", supporters=na)
        return rec
    zeros = sorted(c for c, v in votes.items() if v["raw"] == 0)
    if _accepts(zeros, fam, require_cross_family):
        rec.update(final=0, status="established_zero", supporters=zeros)
        return rec
    rec["final"] = 0
    rec["fallback"] = True
    rec["status"] = "na_rejected_as_zero" if na else "not_established"
    return rec


def collect_votes(run: Path, bench: str) -> dict[str, dict[str, dict]]:
    """item -> coder -> vote, from verified/ and coding/."""
    out: dict[str, dict[str, dict]] = {}
    base = Path(run) / "verified" / bench
    if not base.exists():
        return out
    for idir in sorted(base.iterdir()):
        for f in sorted(idir.glob("*.json")):
            v = read_json(f)
            out.setdefault(idir.name, {})[f.stem] = {
                "raw": v["score_raw"], "effective": v["effective"], "family": v.get("family"),
                "n_verified": v["n_verified"], "flags": v["flags"]}
    return out


def run_resolve(run: Path, benches: list[str], require_cross_family: bool = True) -> dict:
    allrows = []
    summary = {"benchmarks": {}, "rule": {"require_cross_family": require_cross_family}}
    for b in benches:
        votes = collect_votes(run, b)
        cells = {}
        for iid in ITEM_ORDER:
            if iid in votes:
                cells[iid] = resolve_cell(votes[iid], require_cross_family)
        write_json(Path(run) / "resolved" / f"{b}.json", {"bench": b, "cells": cells})
        n = len(cells)
        statuses: dict[str, int] = {}
        for c in cells.values():
            statuses[c["status"]] = statuses.get(c["status"], 0) + 1
        fb = sum(1 for c in cells.values() if c["fallback"])
        agree_maj = sum(1 for c in cells.values() if c["majority_final"] == c["final"])
        summary["benchmarks"][b] = {"cells": n, "status_counts": statuses, "fallback_cells": fb,
                                    "fallback_share": (fb / n if n else None),
                                    "primary_equals_majority": agree_maj}
        for iid, c in cells.items():
            allrows.append({"bench": b, "item": iid, "final": c["final"], "status": c["status"],
                            "fallback": c["fallback"], "majority_final": c["majority_final"],
                            "supporters": ";".join(c["supporters"]),
                            **{f"raw_{k}": v["raw"] for k, v in c["votes"].items()},
                            **{f"eff_{k}": v["effective"] for k, v in c["votes"].items()}})
    tot = sum(s["cells"] for s in summary["benchmarks"].values())
    fbt = sum(s["fallback_cells"] for s in summary["benchmarks"].values())
    summary["total_cells"] = tot
    summary["fallback_cells"] = fbt
    summary["fallback_share"] = fbt / tot if tot else None
    write_json(Path(run) / "resolved" / "summary.json", summary)
    if allrows:
        keys: list[str] = []
        for r in allrows:
            for k in r:
                if k not in keys:
                    keys.append(k)
        with open(Path(run) / "resolved" / "resolved.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            w.writerows(allrows)
    return summary
