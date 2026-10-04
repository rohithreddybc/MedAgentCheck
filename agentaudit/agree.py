"""Stage 6: Krippendorff's alpha (ordinal, NA as missing) per item and overall.

Reported for all coders together and for each cross-family pair (coders whose
families differ, e.g. gpt-oss vs Sonnet, gpt-oss vs Opus). Bootstrap CIs resample
benchmarks. Alpha is computed on raw coder scores (before quote verification).
"""
from __future__ import annotations

from itertools import combinations
from pathlib import Path

from .items import ITEM_ORDER
from .stats import alpha_ordinal, bootstrap_ci
from .util import read_json, write_json


def load_scores(run: Path, benches: list[str]) -> tuple[dict, dict]:
    """Return ({(bench,item): {coder: raw}}, {coder: family})."""
    cells: dict[tuple[str, str], dict[str, object]] = {}
    fam: dict[str, str] = {}
    for b in benches:
        base = Path(run) / "coding" / b
        if not base.exists():
            continue
        for idir in sorted(base.iterdir()):
            for f in sorted(idir.glob("*.json")):
                rec = read_json(f)
                if rec.get("status") != "ok":
                    continue
                cells.setdefault((b, idir.name), {})[f.stem] = rec["parsed"]["score"]
                fam[f.stem] = rec.get("family") or f.stem
    return cells, fam


def _alpha_for(cells: dict, coders: list[str], benches: list[str], item: str | None,
               n_boot: int, seed: int) -> dict:
    groups: dict[str, list] = {b: [] for b in benches}
    for (b, it), votes in sorted(cells.items()):
        if item is not None and it != item:
            continue
        if not all(c in votes for c in coders):
            continue
        groups[b].append([votes[c] for c in coders])
    groups = {b: u for b, u in groups.items() if u}
    units = [u for us in groups.values() for u in us]
    a = alpha_ordinal(units)
    ci = bootstrap_ci(groups, alpha_ordinal, n_boot=n_boot, seed=seed) if a is not None else None
    return {"alpha": a, "ci95": list(ci) if ci else None, "units": len(units), "benchmarks": len(groups)}


def run_agree(run: Path, benches: list[str], n_boot: int = 2000, seed: int = 20261004) -> dict:
    cells, fam = load_scores(run, benches)
    coders = sorted(fam)
    sets: dict[str, list[str]] = {}
    if len(coders) >= 2:
        sets["all:" + "+".join(coders)] = coders
    for a, b in combinations(coders, 2):
        if fam[a] != fam[b]:
            sets[f"cross-family:{a}|{b}"] = [a, b]
    out = {"coders": {c: fam[c] for c in coders}, "benchmarks": benches, "n_boot": n_boot, "seed": seed,
           "note": "ordinal alpha on raw scores, NA as missing; CIs resample benchmarks", "sets": {}}
    for name, cs in sets.items():
        res = {"overall": _alpha_for(cells, cs, benches, None, n_boot, seed), "per_item": {}}
        for it in ITEM_ORDER:
            r = _alpha_for(cells, cs, benches, it, n_boot, seed)
            if r["units"]:
                res["per_item"][it] = r
        out["sets"][name] = res
    write_json(Path(run) / "agreement" / "agreement.json", out)
    return out
