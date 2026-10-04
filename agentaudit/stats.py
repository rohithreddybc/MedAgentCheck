"""Krippendorff's alpha (ordinal), Cohen's and weighted kappa, Wilson intervals, benchmark-level bootstrap."""
from __future__ import annotations

import math
import random
from typing import Sequence


def alpha_ordinal(units: Sequence[Sequence], levels: Sequence = (0, 1, 2)) -> float | None:
    """Krippendorff's alpha, ordinal metric. Each unit is a sequence of values; None/'NA' are missing.

    Units with fewer than two values are not pairable and are dropped. Returns None when
    alpha is undefined (no pairable units, or no variation in the data).
    """
    lv = list(levels)
    idx = {v: i for i, v in enumerate(lv)}
    k = len(lv)
    o = [[0.0] * k for _ in range(k)]
    for u in units:
        vals = [idx[v] for v in u if v is not None and v != "NA" and v in idx]
        m = len(vals)
        if m < 2:
            continue
        for a in range(m):
            for b in range(m):
                if a != b:
                    o[vals[a]][vals[b]] += 1.0 / (m - 1)
    nc = [sum(row) for row in o]
    n = sum(nc)
    if n <= 1:
        return None

    def delta2(c: int, kk: int) -> float:
        if c == kk:
            return 0.0
        lo, hi = min(c, kk), max(c, kk)
        s = sum(nc[lo:hi + 1]) - (nc[lo] + nc[hi]) / 2.0
        return s * s

    d_o = sum(o[c][kk] * delta2(c, kk) for c in range(k) for kk in range(k) if c != kk) / n
    d_e = sum(nc[c] * nc[kk] * delta2(c, kk) for c in range(k) for kk in range(k) if c != kk) / (n * (n - 1))
    if d_e == 0:
        return None
    return 1.0 - d_o / d_e


def wilson(successes: int, n: int, z: float = 1.959964) -> tuple[float, float] | None:
    if n <= 0:
        return None
    p = successes / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


def bootstrap_ci(groups: dict[str, list], stat, n_boot: int = 2000, seed: int = 20261004,
                 alpha: float = 0.05) -> tuple[float, float] | None:
    """Resample groups (benchmarks) with replacement; stat(list_of_units) -> float|None."""
    keys = sorted(groups)
    if len(keys) < 2:
        return None
    rng = random.Random(seed)
    vals = []
    for _ in range(n_boot):
        units: list = []
        for _k in range(len(keys)):
            units.extend(groups[keys[rng.randrange(len(keys))]])
        v = stat(units)
        if v is not None:
            vals.append(v)
    if len(vals) < 20:
        return None
    vals.sort()
    lo = vals[int((alpha / 2) * (len(vals) - 1))]
    hi = vals[int((1 - alpha / 2) * (len(vals) - 1))]
    return (lo, hi)


def raw_agreement(a: Sequence, b: Sequence) -> float | None:
    """Share of positions where the two label sequences are equal."""
    if len(a) != len(b):
        raise ValueError("sequences differ in length")
    return sum(1 for x, y in zip(a, b) if x == y) / len(a) if a else None


def cohen_kappa(a: Sequence, b: Sequence) -> float | None:
    """Cohen's kappa (unweighted) for two label sequences. None when undefined (chance agreement is 1)."""
    if len(a) != len(b):
        raise ValueError("sequences differ in length")
    n = len(a)
    if n == 0:
        return None
    labels = sorted(set(a) | set(b), key=str)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pe = sum((sum(1 for x in a if x == c) / n) * (sum(1 for y in b if y == c) / n) for c in labels)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def weighted_kappa(a: Sequence, b: Sequence, levels: Sequence, weights: str = "quadratic") -> float | None:
    """Weighted Cohen's kappa for ordinal labels. ``levels`` is the full ordered scale (the weights depend on it,
    not on which levels happen to occur). weights: "quadratic" or "linear". None when undefined."""
    if len(a) != len(b):
        raise ValueError("sequences differ in length")
    n = len(a)
    k = len(levels)
    if n == 0 or k < 2:
        return None
    idx = {v: i for i, v in enumerate(levels)}
    o = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        o[idx[x]][idx[y]] += 1.0 / n
    ra = [sum(row) for row in o]
    rb = [sum(o[i][j] for i in range(k)) for j in range(k)]

    def w(i: int, j: int) -> float:
        d = abs(i - j) / (k - 1)
        return d * d if weights == "quadratic" else d

    if weights not in ("quadratic", "linear"):
        raise ValueError(f"unknown weights {weights}")
    num = sum(w(i, j) * o[i][j] for i in range(k) for j in range(k))
    den = sum(w(i, j) * ra[i] * rb[j] for i in range(k) for j in range(k))
    if den == 0:
        return None
    return 1.0 - num / den
