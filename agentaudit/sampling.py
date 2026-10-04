"""Seeded samples (hash-frozen with the protocol). Everything here is a pure function of the seed and of
frozen input lists, so a sample can be regenerated and checked against the file that was frozen.

Ordering uses SHA-256 of ``"<seed>|<purpose>|<parts...>"`` and not ``random``, so the result does not depend on
the Python version.

Perturbation sample (protocol-v1 section 5): for every (item, variant type) the 45 frozen benchmarks are put in
a seeded order. A run takes the first ``N_PER_CELL`` (8) benchmarks in that order that are eligible
(see ``select_cells``), so every (item, type) cell has up to 8 variants drawn across the 45 benchmarks.

BetterBench sample: 20 of the 46 criteria, the 20 with the smallest hash.

ABC item list: every T.* and R.* item, plus any O.* item that the published assessment scores for at least
5 benchmarks. Items with a documented construct mismatch are excluded (``ABC_EXCLUDED``).
"""
from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from .items import ITEM_ORDER

SEED = 20261004
N_PER_CELL = 8
VARIANT_TYPES = ("inject", "buried", "paraphrase", "deletion", "decoy")
BB_SAMPLE_SIZE = 20
ABC_MIN_BENCHMARKS_O = 5
# ABC T.10: the instrument CSV (Sec. 4.1 prose) and the published assessment (App. D) define different constructs.
ABC_EXCLUDED = {"T.10": "construct mismatch: instrument CSV text (outlier inspection) differs from the "
                        "assessment's App. D definition (implementation free of vulnerabilities)"}


def rank_hash(seed: int, purpose: str, *parts: str) -> str:
    return hashlib.sha256("|".join([str(seed), purpose, *parts]).encode("utf-8")).hexdigest()


# ---------------------------------------------------------------- frozen list
def load_frozen_list(path: Path | str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    ids = [r["id"] for r in rows]
    if len(set(ids)) != len(ids):
        raise ValueError("duplicate ids in the frozen list")
    return rows


# ---------------------------------------------------------------- perturbation sample
def perturbation_order(seed: int, item: str, vtype: str, bench_ids: list[str]) -> list[str]:
    return sorted(bench_ids, key=lambda b: rank_hash(seed, "perturb", item, vtype, b))


def build_perturbation_sample(bench_ids: list[str], items: list[str] | None = None,
                              types: tuple = VARIANT_TYPES, seed: int = SEED) -> list[dict]:
    rows = []
    for it in items or ITEM_ORDER:
        for vt in types:
            for rank, b in enumerate(perturbation_order(seed, it, vt, bench_ids), 1):
                rows.append({"item": it, "vtype": vt, "rank": rank, "benchmark": b})
    return rows


def write_rows(path: Path | str, rows: list[dict], fields: list[str]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read_rows(path: Path | str) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_perturbation_sample(path: Path | str, rows: list[dict]) -> None:
    write_rows(path, rows, ["item", "vtype", "rank", "benchmark"])


def read_perturbation_sample(path: Path | str) -> list[dict]:
    rows = read_rows(path)
    for r in rows:
        r["rank"] = int(r["rank"])
    return rows


def eligible(vtype: str, base: dict | None) -> bool:
    """Eligibility of a benchmark for a (item, type) cell given its base result.

    base: {"level": 0|1|2|"NA", "evidence": [chunk ids]} or None when no base run exists (then every
    benchmark is eligible except for deletion, which needs the base evidence).

    inject, buried, paraphrase: base level 0 or 1, so the expected level 2 is informative (a base of 2 would pass
    trivially). decoy: base level 0 or 1 (a decoy cannot raise a base of 2). deletion: base level at least 1 with at
    least one verified quote chunk to remove. A base of NA is never eligible."""
    if base is None:
        return vtype != "deletion"
    lv = base.get("level")
    if lv == "NA" or lv is None:
        return False
    if vtype == "deletion":
        return int(lv) >= 1 and bool(base.get("evidence"))
    return int(lv) <= 1


def select_cells(sample: list[dict], base_of, available: set[str] | None = None, n: int = N_PER_CELL,
                 items: list[str] | None = None, types: tuple = VARIANT_TYPES, seed: int = SEED) -> list[dict]:
    """Take the first ``n`` eligible, available benchmarks per (item, type) in sample order.

    base_of(bench_id, item) -> base dict or None. available: benchmark ids whose packet exists (None = all).
    Returns cell dicts {item, vtype, benchmark, rank, s4_comment}. For ``buried``, half of the selected variants
    (floor(n_selected / 2), those with the smallest hash) also carry an S4 code-comment chunk."""
    by_cell: dict[tuple[str, str], list[dict]] = {}
    for r in sample:
        by_cell.setdefault((r["item"], r["vtype"]), []).append(r)
    out: list[dict] = []
    for it in items or ITEM_ORDER:
        for vt in types:
            chosen = []
            for r in sorted(by_cell.get((it, vt), []), key=lambda r: r["rank"]):
                if len(chosen) >= n:
                    break
                if available is not None and r["benchmark"] not in available:
                    continue
                if not eligible(vt, base_of(r["benchmark"], it)):
                    continue
                chosen.append({"item": it, "vtype": vt, "benchmark": r["benchmark"], "rank": r["rank"],
                               "s4_comment": False})
            if vt == "buried" and chosen:
                order = sorted(chosen, key=lambda c: rank_hash(seed, "s4comment", it, c["benchmark"]))
                for c in order[: len(chosen) // 2]:
                    c["s4_comment"] = True
            out.extend(chosen)
    return out


# ---------------------------------------------------------------- gold samples
def betterbench_sample(criterion_ids: list[str], k: int = BB_SAMPLE_SIZE, seed: int = SEED) -> list[str]:
    """The k criteria with the smallest hash, returned in the instrument's own order."""
    pick = set(sorted(criterion_ids, key=lambda c: rank_hash(seed, "betterbench", c))[:k])
    return [c for c in criterion_ids if c in pick]


def abc_item_list(instrument_ids: list[str], gold_benchmarks_per_item: dict[str, int],
                  min_o: int = ABC_MIN_BENCHMARKS_O) -> list[dict]:
    """Rows {item_id, included, reason} for every instrument item, in instrument order."""
    out = []
    for iid in instrument_ids:
        key = iid.split(" ")[0]  # "O.c.2 [App. D only]" -> "O.c.2"
        if key in ABC_EXCLUDED:
            out.append({"item_id": key, "included": "no", "reason": ABC_EXCLUDED[key]})
        elif key.startswith(("T.", "R.")):
            out.append({"item_id": key, "included": "yes", "reason": "T.* and R.* items"})
        elif key.startswith("O."):
            n = gold_benchmarks_per_item.get(key, 0)
            ok = n >= min_o
            out.append({"item_id": key, "included": "yes" if ok else "no",
                        "reason": f"O.* item scored for at least {min_o} benchmarks" if ok
                        else f"O.* item scored for fewer than {min_o} benchmarks in the published assessment"})
        else:
            out.append({"item_id": key, "included": "no", "reason": "not a T, R or O item"})
    return out
