"""Seeded samples (hash-frozen with the protocol). Everything here is a pure function of the seed and of
frozen input lists, so a sample can be regenerated and checked against the file that was frozen.

Ordering uses SHA-256 of ``"<seed>|<purpose>|<parts...>"`` and not ``random``, so the result does not depend on
the Python version.

Perturbation design (protocol-v1 section 5, multiplexed): 40 variant packets drawn from the 45 frozen benchmarks.
In every variant each of the 25 items receives exactly one perturbation type, dealt so that each (item, type) pair
occurs exactly 8 times: 25 x 5 x 8 = 1,000 labelled cells. A variant is scored once with the normal 25-item
whole-packet call. Cells that fail the eligibility rule (``eligible``) at run time are dropped and counted.

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
N_VARIANTS = 40  # variant packets; each item gets one perturbation type per variant
N_PER_PAIR = 8  # occurrences of every (item, type) pair across the variants
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


# ---------------------------------------------------------------- perturbation design (multiplexed)
def draw_variant_benchmarks(bench_ids: list[str], n_variants: int = N_VARIANTS, seed: int = SEED) -> list[str]:
    """Benchmarks of the variant packets: the first ``n_variants`` of the seeded order. Only when fewer
    benchmarks exist than variants does the order repeat (replacement, used only if needed)."""
    order = sorted(bench_ids, key=lambda b: rank_hash(seed, "variant-benchmark", b))
    return [order[i % len(order)] for i in range(n_variants)]


def build_perturbation_design(bench_ids: list[str], items: list[str] | None = None, types: tuple = VARIANT_TYPES,
                              n_variants: int = N_VARIANTS, seed: int = SEED) -> list[dict]:
    """Balanced multiplexed design. Variant packet j (j = 1..n_variants) is one benchmark's packet in which every
    item receives exactly one perturbation type. Per item, the multiset {each type x n_variants / len(types)} is
    dealt to the variants in seeded order, so each (item, type) pair occurs exactly n_variants / len(types) times
    (8 for 40 variants and 5 types: 25 x 5 x 8 = 1,000 labelled cells). Each row: variant, benchmark, item, vtype,
    slot (position slot 0..24 of inline insertions in S1, a seeded permutation of the items per variant) and
    s4_comment (buried only: the 4 of the item's 8 buried variants with the smallest hash also carry the sentence
    in a synthetic S4 code comment)."""
    items = list(items or ITEM_ORDER)
    if n_variants % len(types):
        raise ValueError("n_variants must be a multiple of the number of types")
    reps = n_variants // len(types)
    benches = draw_variant_benchmarks(bench_ids, n_variants, seed)
    vid = [f"v{j:02d}" for j in range(1, n_variants + 1)]
    assign: dict[str, list[str]] = {}
    for it in items:
        deal = sorted(((t, k) for t in types for k in range(reps)),
                      key=lambda tk: rank_hash(seed, "assign", it, tk[0], str(tk[1])))
        assign[it] = [t for t, _ in deal]
    s4: set[tuple[str, str]] = set()
    for it in items:
        bur = [vid[j] for j in range(n_variants) if assign[it][j] == "buried"]
        for v in sorted(bur, key=lambda v: rank_hash(seed, "s4comment", it, v))[: len(bur) // 2]:
            s4.add((v, it))
    rows = []
    for j, v in enumerate(vid):
        slots = {it: n for n, it in enumerate(sorted(items, key=lambda it: rank_hash(seed, "slot", v, it)))}
        for it in items:
            rows.append({"variant": v, "benchmark": benches[j], "item": it, "vtype": assign[it][j], "slot": slots[it],
                         "s4_comment": "yes" if (v, it) in s4 else "no"})
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


DESIGN_FIELDS = ["variant", "benchmark", "item", "vtype", "slot", "s4_comment"]


def write_perturbation_design(path: Path | str, rows: list[dict]) -> None:
    write_rows(path, rows, DESIGN_FIELDS)


def read_perturbation_design(path: Path | str) -> list[dict]:
    rows = read_rows(path)
    for r in rows:
        r["slot"] = int(r["slot"])
        r["s4_comment"] = r["s4_comment"] == "yes"
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
