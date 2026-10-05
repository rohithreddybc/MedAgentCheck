"""Shared helpers for the analysis scripts: paths, CSV and LaTeX writers, scorer imports."""
from __future__ import annotations

import csv
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
OUT = ANALYSIS / "out"
TABLES = ROOT / "paper" / "tables"
FIGURES = ROOT / "paper" / "figures"
SEED = 20261004

# The scorer package is normally installed (editable); fall back to the sibling folder.
try:  # pragma: no cover - environment dependent
    import agentaudit  # noqa: F401
except ImportError:  # pragma: no cover
    sys.path.insert(0, str(ROOT / "scorer"))


def _cell(v):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return ""
    if isinstance(v, float):
        return round(v, 6)
    return v


def write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fields is None:
        fields = []
        for r in rows:
            for k in r:
                if k not in fields:
                    fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r.get(k)) for k in fields})
    return path


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tex_escape(s: str) -> str:
    out = str(s)
    for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"),
                 ("$", r"\$"), ("{", r"\{"), ("}", r"\}")):
        out = out.replace(a, b)
    return out


def fnum(x, nd: int = 2, dash: str = "--") -> str:
    """Format a number for a table; missing -> dash."""
    if x is None or (isinstance(x, float) and math.isnan(x)) or x == "":
        return dash
    return f"{float(x):.{nd}f}"


def fci(lo, hi, nd: int = 2) -> str:
    if lo is None or hi is None or any(isinstance(v, float) and math.isnan(v) for v in (lo, hi)) or lo == "" or hi == "":
        return "--"
    return f"[{float(lo):.{nd}f}, {float(hi):.{nd}f}]"


def booktabs(colspec: str, header: list[str], rows: list[list[str]], comment: str = "",
             midrules_after: set[int] | None = None) -> str:
    """A bare tabular in booktabs style. Rows are lists of already-escaped cell strings. The caption and the
    table environment live in the paper, so this file can be \\input."""
    lines = []
    for c in comment.splitlines():
        lines.append("% " + c)
    lines.append(r"\begin{tabular}{" + colspec + "}")
    lines.append(r"\toprule")
    lines.append(" & ".join(header) + r" \\")
    lines.append(r"\midrule")
    for i, r in enumerate(rows):
        lines.append(" & ".join(r) + r" \\")
        if midrules_after and i in midrules_after and i != len(rows) - 1:
            lines.append(r"\midrule")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    return "\n".join(lines) + "\n"
