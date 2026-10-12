"""Shared helpers for the post-freeze reproduction scripts in repro/.

Everything here reads released files only: results/, reruns/ and repro/tables/ (plus the frozen
agentaudit/stats.py and agentaudit/items.py, imported read-only from this checkout; no installation of the
agentaudit package is needed, only PyYAML for items.yaml). Nothing under results/ or analysis/ is written.
All files are read as UTF-8 (the default of Windows consoles is not).
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # agentaudit.stats / agentaudit.items from this checkout (frozen files, read-only)

RESULTS = REPO / "results"
RESOLVED = RESULTS / "resolved"
ANALYSIS_OUT = RESULTS / "analysis_out"      # reference values written by the authors' analysis scripts
SUMMARY_MD = REPO / "analysis" / "out" / "RESULTS_SUMMARY.md"
RERUNS = REPO / "reruns"
TABLES = REPO / "repro" / "tables"
SEED = 20261004
N_BOOT = 2000


def read_json(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def load_resolved() -> dict[str, dict]:
    """bench -> {item: cell} for the 44 benchmarks with cells (HealthCraft has none), from results/resolved/*.json."""
    out = {}
    for f in sorted(RESOLVED.glob("*.json")):
        if f.stem == "summary":
            continue
        cells = read_json(f)["cells"]
        if cells:
            out[f.stem] = cells
    return out


def _s(v) -> str:
    return "" if v is None else str(v)


class Checker:
    """Collects comparisons between reproduced and released values; raises AssertionError at the end if any differ."""

    def __init__(self, name: str):
        self.name = name
        self.n = 0
        self.fails: list[str] = []

    def eq(self, label: str, got, want, tol: float = 0.0) -> None:
        self.n += 1
        if isinstance(got, (list, tuple)) and isinstance(want, (list, tuple)):
            ok = len(got) == len(want) and all(self._close(a, b, tol) for a, b in zip(got, want))
        else:
            ok = self._close(got, want, tol)
        if not ok:
            self.fails.append(f"{label}: reproduced {got!r}, released {want!r}")

    @staticmethod
    def _close(a, b, tol: float) -> bool:
        if a is None or b is None:
            return a is None and b is None
        if isinstance(a, bool) or isinstance(b, bool):
            return bool(a) == bool(b)
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if isinstance(a, float) and math.isnan(a):
                return isinstance(b, float) and math.isnan(b)
            return abs(a - b) <= tol
        return a == b

    def in_text(self, label: str, needle: str, text: str) -> None:
        self.n += 1
        if needle not in text:
            self.fails.append(f"{label}: line not found in RESULTS_SUMMARY.md: {needle[:160]}")

    def csv_rows(self, label: str, got: list[dict], ref_path: Path, keys: list[str], tol: float = 1.5e-6) -> None:
        """Compare reproduced rows with a CSV written by analysis/common.write_csv (floats rounded to 6 decimals)."""
        ref = read_csv_rows(ref_path)
        gmap = {tuple(_s(r.get(k)) for k in keys): r for r in got}
        if len(gmap) != len(got):
            self.fails.append(f"{label}: duplicate keys in reproduced rows")
        self.n += 1
        if len(ref) != len(got):
            self.fails.append(f"{label}: {len(got)} reproduced rows, {len(ref)} released rows ({ref_path.name})")
        for rr in ref:
            key = tuple(rr[k] for k in keys)
            g = gmap.get(key)
            if g is None:
                self.fails.append(f"{label}: released row {key} not reproduced")
                continue
            for col, want in rr.items():
                self.n += 1
                have = g.get(col)
                if want == "":
                    ok = have is None or have == "" or (isinstance(have, float) and math.isnan(have))
                elif want in ("True", "False"):
                    ok = _s(have) == want
                else:
                    try:
                        ok = have is not None and have != "" and abs(float(have) - float(want)) <= tol
                    except (TypeError, ValueError):
                        ok = _s(have) == want
                if not ok:
                    self.fails.append(f"{label}: row {key} column {col}: reproduced {have!r}, released {want!r}")

    def done(self) -> None:
        if self.fails:
            head = "\n  ".join(self.fails[:20])
            raise AssertionError(f"{self.name}: {len(self.fails)} of {self.n} comparisons differ\n  {head}")
        print(f"[OK] {self.name}: all {self.n} comparisons with the released values match")
