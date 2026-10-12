"""AUTHORS' TOOL (needs the withheld inputs). Build repro/tables/gold_contingency.csv from the gold scoring runs.

Post-freeze; not part of the frozen method. It reads the authors' working tree, which is not released:
    <root>/audit/gold_abc, <root>/audit/gold_bb      per-coder gold scoring files (coder predictions, withheld)
    <root>/research/gold, <root>/research/instruments  published expert scores and item lists (ABC unlicensed; not redistributed)
and writes only aggregate counts: for each gold set, comparison and benchmark, the cross-tabulation of two raters'
levels. No item id, no item text and no per-cell label is written, so the table cannot be turned back into the
expert scores or the coder predictions. Everyone else reproduces from the released table with repro/reproduce_gold.py.

Run from the repository root (the folder holding repro/):
    python repro/make_gold_tables.py --root <authors' project root>

Comparisons (row rater first, column rater second, so the table of "codex_vs_expert" has codex levels in rows):
    codex_vs_sonnet, codex_vs_expert, sonnet_vs_expert, resolved_vs_expert
Cell sets:
    common    cells where the expert and BOTH coders have a score (NA excluded); the like-for-like analysis of
              analysis/gold_coder_pair.py and analysis/revision_round2.py. For resolved_vs_expert: the common cells
              whose resolved level is not NA.
    original  the cells of the scorer's agreement.json (per rater; expert NA and rater NA kept as level "NA", so the
              counts n_gold_na, n_pred_na_where_gold_scored and n_both_na can be read off). Pair comparison
              codex_vs_sonnet has no original cell set.
The cell-set logic copies analysis/gold_coder_pair.py (load_set); it uses agentaudit.gold (frozen) read-only.
"""
from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from agentaudit import gold as G  # noqa: E402  (frozen scorer module, read-only)

OUT = REPO / "repro" / "tables" / "gold_contingency.csv"
RUNS = {"abc": "gold_abc", "betterbench": "gold_bb"}


def cells_for_set(root: Path, set_name: str) -> list[dict]:
    cfg = G.set_cfg(set_name)
    run = root / "audit" / RUNS[set_name]
    rdir = root / "research"
    gold = G.load_gold(set_name, rdir)
    ids = set(G.items_for_set(set_name))
    preds, fam = G.load_predictions(run, set_name)
    assert sorted(preds) == ["codex", "sonnet"], sorted(preds)
    res, _ = G.resolved_predictions(preds, fam, cfg["top_down"])
    rows: list[dict] = []

    def add(comparison, cell_set, pairs):
        c = Counter((b, str(x), str(y)) for b, x, y in pairs)
        for (b, x, y), n in sorted(c.items()):
            rows.append({"gold_set": set_name, "comparison": comparison, "cell_set": cell_set, "benchmark": b,
                         "row_level": x, "col_level": y, "count": n})

    # original cell sets (agreement.json): every scored cell that has a gold entry and an item of the set
    for coder in ("codex", "sonnet"):
        add(f"{coder}_vs_expert", "original",
            [(b, v["effective"], gold[(b, i)]) for (b, i), v in sorted(preds[coder].items())
             if (b, i) in gold and i in ids])
    add("resolved_vs_expert", "original",
        [(b, p, gold[(b, i)]) for (b, i), p in sorted(res.items()) if (b, i) in gold and i in ids])

    # common cells: expert and both coders have a level
    orig = {c: {cell: v["effective"] for cell, v in preds[c].items()
                if cell in gold and cell[1] in ids and gold[cell] != "NA" and v["effective"] != "NA"} for c in preds}
    common = sorted(set(orig["codex"]) & set(orig["sonnet"]))
    cx = {c: preds["codex"][c]["effective"] for c in common}
    sn = {c: preds["sonnet"][c]["effective"] for c in common}
    g = {c: gold[c] for c in common}
    add("codex_vs_sonnet", "common", [(c[0], cx[c], sn[c]) for c in common])
    add("codex_vs_expert", "common", [(c[0], cx[c], g[c]) for c in common])
    add("sonnet_vs_expert", "common", [(c[0], sn[c], g[c]) for c in common])
    add("resolved_vs_expert", "common",
        [(c[0], res[c], g[c]) for c in common if c in res and res[c] != "NA"])
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=REPO.parents[1],
                    help="the authors' project root (holds audit/ and research/); default: two levels above the repo")
    ap.add_argument("--out", type=Path, default=OUT)
    a = ap.parse_args()
    rows = []
    for s in ("abc", "betterbench"):
        rows += cells_for_set(a.root, s)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["gold_set", "comparison", "cell_set", "benchmark", "row_level", "col_level",
                                          "count"], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows, {sum(r['count'] for r in rows)} counted cells -> {a.out}")


if __name__ == "__main__":
    main()
