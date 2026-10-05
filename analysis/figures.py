"""Paper figures, vector PDF at IEEE sizes (column 3.5 in, full width 7.16 in).

  Fig. 2  fig2_flow.pdf          PRISMA-style flow, numbers parsed from research/eligibility/flow_counts.md
  Fig. 4  fig4_prevalence.pdf    per-item prevalence dot plot with Wilson 95% CIs, core versus agent module
                                 (reads analysis/out/rq1_prevalence.csv, written by rq1_rq2.py)
  Fig. 5  fig5_ci_width.pdf      arrow plot, headline-score CI width at 1 run versus 5 runs per benchmark x condition
                                 (reads analysis/out/rq3_ci_width.csv and rq3_status.json, written by rq3_reruns.py)

Colour: Okabe-Ito blue (#0072B2) and vermillion (#D55E00); the pair passes the dataviz validator (light surface,
CVD DeltaE >= 21, contrast >= 3:1). Colour is never the only code: modules and conditions also differ in marker
shape and fill, and every figure reads in greyscale. Text is 6.5 to 8 pt at final size.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

from common import FIGURES, OUT, ROOT, read_csv  # noqa: E402

COL_W, FULL_W = 3.5, 7.16
BLUE, VERM, INK, MUTED, GRID = "#0072B2", "#D55E00", "#222222", "#666666", "#DDDDDD"
FLOW_MD = ROOT / "research" / "eligibility" / "flow_counts.md"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Times", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "font.size": 7.5, "axes.labelsize": 7.5, "xtick.labelsize": 7, "ytick.labelsize": 6.8, "legend.fontsize": 7,
    "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.0, "xtick.major.size": 2.5,
    "ytick.major.size": 0, "axes.edgecolor": INK, "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": INK, "ytick.color": INK,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "standard",
})


def _save(fig, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, format="pdf")
    plt.close(fig)
    return path


def _f(x):
    return None if x in ("", None) else float(x)


# ------------------------------------------------------------------ Fig. 4
SHORT = {"C9": "Side effects detectable", "C10": "Trivial success unlikely", "C13": "Non-determinism safeguards",
         "A1": "Run count per number", "A2": "Uncertainty, resampling unit", "A3": "Action-level repeat reliability",
         "A4": "Model and harness pinning", "A5": "Tool contract specified", "A6": "Tool contract verified",
         "A7": "Write-action disclosure", "A8": "Grader reads state", "A9": "Agent-channel contamination",
         "A10": "Slice reporting", "A11": "Environment-state provenance"}


def short_label(item: str, title: str) -> str:
    t = SHORT.get(item) or re.sub(r"\s*\([a-h](?:/[a-h])?\)\.?$", "", title).strip()
    return f"{item}  {t}"


def fig_prevalence(csv_path: Path, out: Path, rule: str = "resolved") -> Path:
    rows = [r for r in read_csv(csv_path) if r["rule"] == rule]
    if not rows:
        raise ValueError(f"no rows with rule={rule} in {csv_path}")
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, 3.9), sharex=True, layout="constrained",
                             gridspec_kw={"width_ratios": [14, 11]})
    fig.get_layout_engine().set(w_pad=0.04, h_pad=0.04, wspace=0.06)
    spec = {"core": ("Core module (reused items)", BLUE, "o"), "agent": ("Agent module (new items)", VERM, "D")}
    for ax, mod in zip(axes, ("core", "agent")):
        title, colour, marker = spec[mod]
        sel = sorted((r for r in rows if r["module"] == mod), key=lambda r: (-(_f(r["share_reported"]) or 0), r["item"]))
        n = len(sel)
        for i, r in enumerate(sel):
            y = n - 1 - i
            for off, key, lo, hi, filled in ((0.16, "share_reported", "reported_lo", "reported_hi", True),
                                             (-0.16, "share_full", "full_lo", "full_hi", False)):
                v = _f(r[key])
                if v is None:
                    continue
                ax.hlines(y + off, 100 * _f(r[lo]), 100 * _f(r[hi]), color=colour, lw=0.9, alpha=0.9, zorder=2)
                ax.plot(100 * v, y + off, marker=marker, ms=3.6 if marker == "o" else 3.2, zorder=3,
                        mfc=colour if filled else "white", mec=colour, mew=0.9, ls="none")
        ax.set_yticks(range(n))
        ax.set_yticklabels([short_label(r["item"], r["title"]) for r in reversed(sel)])
        ax.set_ylim(-0.7, n - 0.3)
        ax.set_xlim(-3, 103)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.xaxis.grid(True, color=GRID, lw=0.5, zorder=0)
        ax.set_axisbelow(True)
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.set_title(title, loc="left", fontsize=7.5, color=colour, fontweight="bold", pad=3)
        ax.set_xlabel("Benchmarks reporting the property (%)")
    handles = [Line2D([], [], marker="o", ls="none", mfc=MUTED, mec=MUTED, ms=3.6, label="Reported (level 1 or 2)"),
               Line2D([], [], marker="o", ls="none", mfc="white", mec=MUTED, mew=0.9, ms=3.6,
                      label="Fully reported (level 2)")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False, handletextpad=0.3,
               columnspacing=1.6)
    return _save(fig, out)


# ------------------------------------------------------------------ Fig. 5
def fig_ci_width(csv_path: Path, out: Path, status_path: Path | None = None) -> Path:
    rows = [r for r in read_csv(csv_path) if r.get("ci_width_1run") not in ("", None)]
    if not rows:
        raise ValueError(f"no rows with a CI width in {csv_path}")
    names = {"AgentClinic": "AgentClinic", "RadABench": "RadA-BenchPlat", "synthetic_hospital": "Synthetic Hospital"}
    partial = any(r.get("partial") in ("True", "true", "1") for r in rows)
    if status_path and Path(status_path).exists():
        partial = bool(json.loads(Path(status_path).read_text(encoding="utf-8")).get("partial", partial))
    h = max(1.5, 0.34 * len(rows) + 0.95)
    fig, ax = plt.subplots(figsize=(COL_W, h), layout="constrained")
    fig.get_layout_engine().set(w_pad=0.04, h_pad=0.04)
    style = {"A": (BLUE, "o"), "B": (VERM, "D")}
    n = len(rows)
    ymax = 0.0
    for i, r in enumerate(rows):
        y = n - 1 - i
        w1, w5 = float(r["ci_width_1run"]), float(r["ci_width_5run"])
        ymax = max(ymax, w1, w5)
        colour, marker = style.get(r["condition"], (INK, "s"))
        ax.add_patch(FancyArrowPatch((w1, y), (w5, y), arrowstyle="-|>", mutation_scale=7, lw=1.0, color=colour,
                                     shrinkA=3.2, shrinkB=3.2, zorder=2))
        ax.plot(w1, y, marker=marker, ms=4.2, mfc="white", mec=colour, mew=1.0, ls="none", zorder=3)
        ax.plot(w5, y, marker=marker, ms=4.2, mfc=colour, mec=colour, mew=1.0, ls="none", zorder=3)
    ax.set_yticks(range(n))
    ax.set_yticklabels([f'{names.get(r["bench"], r["bench"])} {r["condition"]} ($n$={r["n_tasks"]})'
                        for r in reversed(rows)])
    ax.set_ylim(-0.6, n - 0.4)
    ax.set_xlim(-0.04, max(1.0, ymax * 1.08))
    ax.set_xlabel("Width of the 95% CI of the headline score")
    ax.xaxis.grid(True, color=GRID, lw=0.5, zorder=0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right", "left"]].set_visible(False)
    handles = [Line2D([], [], marker="o", ls="none", mfc="white", mec=MUTED, mew=1.0, ms=4.2, label="1 run"),
               Line2D([], [], marker="o", ls="none", mfc=MUTED, mec=MUTED, ms=4.2, label="5 runs")]
    fig.legend(handles=handles, loc="outside lower center", ncol=2, frameon=False, handletextpad=0.3,
               columnspacing=1.4)
    if partial:
        ax.set_title("PARTIAL DATA (draft)", loc="right", fontsize=6.5, color=VERM, fontweight="bold", pad=3)
    return _save(fig, out)


# ------------------------------------------------------------------ Fig. 2
def parse_flow(md: str) -> dict:
    def num(s: str) -> int:
        return int(s.replace(",", ""))

    f: dict = {}
    f["sources"] = {m.group(1): (num(m.group(2)), num(m.group(3))) for m in re.finditer(
        r"^\|\s*(arxiv|pubmed|acl_anthology|chaining)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)", md, re.M)}
    m = re.search(r"\*\*total\*\*\s*\|\s*\*\*([\d,]+)\*\*\s*\|\s*\*\*([\d,]+)\*\*", md)
    f["raw_total"], f["unique"] = num(m.group(1)), num(m.group(2))
    m = re.search(r"Duplicates removed:.*?\*\*([\d,]+)\*\*", md)
    f["dups"] = num(m.group(1))
    m = re.search(r"Added outside the keyword search.*?:\s*(\d+)\s+records", md)
    f["added"] = int(m.group(1)) if m else 0
    m = re.search(r"Screened:\s*([\d,]+)\.\s*Excluded:\s*\*\*([\d,]+)\*\*\s*\(([^)]*)\)", md)
    f["screened"], f["ta_excluded"] = num(m.group(1)), num(m.group(2))
    f["ta_reasons"] = [(k, num(v)) for k, v in
                       re.findall(r"([A-Z_]+)\s+([\d,]+)", m.group(3))]
    m = re.search(r"Passed to full text:\s*(\d+).*?=\s*\*\*(\d+)\s+full-text assessed\*\*", md)
    f["passed"], f["fulltext"] = int(m.group(1)), int(m.group(2))
    ft = md.split("## Full-text assessment", 1)[1].split("###", 1)[0]
    f["ft_reasons"] = [(code, name.replace("_", " ").lower().capitalize(), int(n)) for code, name, n in re.findall(
        r"^\|\s*(X\d)\s*\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|", ft, re.M)]
    if sum(n for _, _, n in f["ft_reasons"]) != int(re.search(r"\*\*excluded total\*\*\s*\|\s*\|\s*\*\*(\d+)\*\*", ft).group(1)):
        raise ValueError("full-text exclusion reasons do not sum to the excluded total")
    m = re.search(r"\*\*excluded total\*\*\s*\|\s*\|\s*\*\*(\d+)\*\*", ft)
    f["ft_excluded"] = int(m.group(1))
    m = re.search(r"\*\*INCLUDE\*\*\s*\|\s*\|\s*\*\*(\d+)\*\*", ft)
    f["included"] = int(m.group(1))
    if f["ft_excluded"] + f["included"] != f["fulltext"]:
        raise ValueError("flow counts do not add up: "
                         f'{f["ft_excluded"]} + {f["included"]} != {f["fulltext"]}')
    if f["raw_total"] - f["dups"] != f["unique"] or f["ta_excluded"] + f["passed"] != f["screened"]:
        raise ValueError("identification or screening counts do not add up")
    return f


def _fmt(n: int) -> str:
    return f"{n:,}"


TA_LABELS = {"NOT_AGENT": "not about agents", "NOT_BENCHMARK": "not a benchmark", "NOT_CLINICAL": "not clinical",
             "OUT_OF_DATE": "outside the date window", "DUPLICATE": "duplicate"}
FT_LABELS = {"X1": "Not a benchmark", "X2": "Dialogue only", "X3": "Static question answering",
             "X4": "Not clinical care", "X5": "Outside the date window", "X6": "Payer side (listed, not scored)",
             "X7": "Duplicate or superseded", "X8": "No documentation", "X9": "Not an LLM agent"}


def fig_flow(md_path: Path, out: Path) -> Path:
    f = parse_flow(Path(md_path).read_text(encoding="utf-8"))
    W, H = FULL_W, 3.35
    fig = plt.figure(figsize=(W, H))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")
    LH = 0.135  # line height, inches
    fs = 7.0

    def box(x, ytop, w, lines, fill="#F2F2F2", lw=0.7, bold=1, fsz=fs, pad=0.07):
        h = LH * len(lines) + 2 * pad
        ax.add_patch(FancyBboxPatch((x, ytop - h), w, h, boxstyle="round,pad=0,rounding_size=0.05", fc=fill, ec=INK,
                                    lw=lw, zorder=2))
        for i, ln in enumerate(lines):
            ax.text(x + 0.09, ytop - pad - LH * (i + 0.5), ln, ha="left", va="center", fontsize=fsz, zorder=3,
                    fontweight="bold" if i < bold else "normal")
        return ytop - h

    def arrow(p0, p1):
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=7, lw=0.8, color=INK, zorder=1,
                                     shrinkA=0, shrinkB=0))

    LX, LW, RX, RW = 0.03, 3.0, 3.55, 3.55
    names = {"arxiv": "arXiv", "pubmed": "PubMed", "acl_anthology": "ACL Anthology", "chaining": "chaining"}
    src = [f"{names[k]} {_fmt(v[0])}" for k, v in f["sources"].items()]
    y = H - 0.03
    mid = lambda yt, yb: (yt + yb) / 2  # noqa: E731
    b1 = box(LX, y, LW, ["Identification", f"Records retrieved: {_fmt(f['raw_total'])}", ", ".join(src[:2]) + ",",
                         ", ".join(src[2:])])
    r1 = box(RX, y, RW, [f"Duplicates removed: {_fmt(f['dups'])}", f"Unique records: {_fmt(f['unique'])}"], bold=0)
    arrow((LX + LW, mid(y, b1)), (RX, mid(y, b1)))
    y2 = b1 - 0.32
    arrow((LX + LW / 2, b1), (LX + LW / 2, y2))
    b2 = box(LX, y2, LW, ["Title and abstract screening", f"Records screened: {_fmt(f['screened'])}"])
    ta = [f"{TA_LABELS.get(k, k.lower())} {_fmt(v)}" for k, v in f["ta_reasons"]]
    r2 = box(RX, y2, RW, [f"Excluded: {_fmt(f['ta_excluded'])}", ", ".join(ta[:2]) + ",", ", ".join(ta[2:])],
             bold=1)
    arrow((LX + LW, mid(y2, b2)), (RX, mid(y2, b2)))
    y3 = min(b2, r2) - 0.32
    arrow((LX + LW / 2, b2), (LX + LW / 2, y3))
    add = f" + {f['added']} added by hand" if f["added"] else ""
    b3 = box(LX, y3, LW, ["Full-text assessment", f"Records assessed: {_fmt(f['fulltext'])}",
                          f"({f['passed']} passed screening{add})"])
    ft = [f"{c}  {FT_LABELS.get(c, n)}: {k}" for c, n, k in sorted(f["ft_reasons"], key=lambda t: (-t[2], t[0])) if k]
    r3 = box(RX, y3, RW, [f"Excluded: {_fmt(f['ft_excluded'])}"] + ft, bold=1, fsz=6.7)
    arrow((LX + LW, mid(y3, b3)), (RX, mid(y3, b3)))
    y4 = b3 - 0.32
    arrow((LX + LW / 2, b3), (LX + LW / 2, y4))
    box(LX, y4, LW, ["Included", f"{f['included']} action-taking clinical agent benchmarks"], fill="#D4D4D4", lw=1.6)
    return _save(fig, out)


def _wrap(text: str, width: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------------ CLI
def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("which", nargs="*", help="any of: all fig2 fig4 fig5 (default all)")
    ap.add_argument("--out", type=Path, default=FIGURES)
    ap.add_argument("--data", type=Path, default=OUT, help="directory with the rq*.csv files")
    ap.add_argument("--flow", type=Path, default=FLOW_MD)
    a = ap.parse_args(argv)
    bad = set(a.which) - {"all", "fig2", "fig4", "fig5"}
    if bad:
        ap.error(f"unknown figure(s): {sorted(bad)}")
    todo = {"fig2", "fig4", "fig5"} if (not a.which or "all" in a.which) else set(a.which)
    if "fig2" in todo:
        print(fig_flow(a.flow, a.out / "fig2_flow.pdf"))
    if "fig4" in todo:
        p = a.data / "rq1_prevalence.csv"
        print(fig_prevalence(p, a.out / "fig4_prevalence.pdf") if p.exists() else f"skip fig4: {p} not found")
    if "fig5" in todo:
        p = a.data / "rq3_ci_width.csv"
        print(fig_ci_width(p, a.out / "fig5_ci_width.pdf", a.data / "rq3_status.json")
              if p.exists() else f"skip fig5: {p} not found")


if __name__ == "__main__":
    main()
