"""AUTHORS' TOOL (needs the withheld inputs). Build repro/tables/gold_rule_contingency.csv, gold_rule_vs_best.csv and cap_flags.csv.

Post-freeze; not part of the frozen method. It reads the authors' working tree, which is not released:
    <root>/audit/gold_abc, <root>/audit/gold_bb      per-coder gold scoring files (coder predictions, withheld)
    <root>/research/gold, <root>/research/instruments  published expert scores and item lists (ABC unlicensed; not redistributed)
    <root>/audit/transport/prompts/<bench>/meta.json  per-benchmark prompt metadata (token count before the cap, dropped chunks)
and writes only aggregate counts and per-benchmark flags. No item id, no item text, no per-cell label, no prompt text
or hash is written. Everyone else reproduces from the released tables with repro/reproduce_rules.py and
repro/reproduce_cap.py.

Run from the repository root (the folder holding repro/):
    python repro/make_rule_cap_tables.py --root <authors' project root>

gold_rule_contingency.csv   per gold set, resolution rule and benchmark: counts of (expert level, rule level) over the cells
                            of the scorer's agreement.json (single coders: their own cells; other rules: cells scored by both
                            coders; level NA kept, so the NA bookkeeping can be read off). The cell sets and the rules copy
                            analysis/revision_rq12.py (gold_cells, rule_pairs, apply_rule).
gold_rule_vs_best.csv       per gold set, rule and benchmark: counts of (expert, best single coder, rule) over the cells where
                            all three are numeric; the best single coder is the one with the higher primary statistic.
cap_flags.csv               per benchmark: whether the packet was cut by the 150,000-token cap, the token count before the cap,
                            tokens sent and dropped chunks (analysis/revision_round2.py cap_flags).
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentaudit import gold as G  # noqa: E402  (frozen scorer module, read-only)
from agentaudit.stats import cohen_kappa, weighted_kappa  # noqa: E402
from reproduce_rules import RULES, apply_rule  # noqa: E402

TABLES = REPO / "repro" / "tables"
RUNS = {"abc": "gold_abc", "betterbench": "gold_bb"}


def rule_pairs(gc: dict, rule: str) -> list[tuple]:
    cfg, gold, ids = gc["cfg"], gc["gold"], gc["ids"]
    out = []
    if rule in ("claude", "openai"):
        c = "sonnet" if rule == "claude" else "codex"
        for (b, i), v in sorted(gc["preds"][c].items()):
            if (b, i) in gold and i in ids:
                out.append((b, i, gold[(b, i)], v["effective"]))
        return out
    for (b, i), votes in sorted(gc["both"].items()):
        if (b, i) in gold and i in ids:
            out.append((b, i, gold[(b, i)], apply_rule(rule, votes, cfg["top_down"])))
    return out


def gold_cells(root: Path, set_name: str) -> dict:
    cfg = G.set_cfg(set_name)
    gold = G.load_gold(set_name, root / "research")
    ids = set(G.items_for_set(set_name))
    preds, _fam = G.load_predictions(root / "audit" / RUNS[set_name], set_name)
    assert sorted(preds) == ["codex", "sonnet"], sorted(preds)
    both = {k: {c: preds[c][k] for c in ("codex", "sonnet")} for k in preds["codex"] if k in preds["sonnet"]}
    return {"cfg": cfg, "gold": gold, "ids": ids, "preds": preds, "both": both}


def primary(cfg: dict, g: list, p: list) -> float:
    levels = list(cfg["levels"])
    return cohen_kappa(g, p) if cfg["primary"] == "cohen_kappa" else weighted_kappa(g, p, levels, "quadratic")


def gold_tables(root: Path) -> tuple[list[dict], list[dict]]:
    rows, rows3 = [], []
    for s in ("abc", "betterbench"):
        gc = gold_cells(root, s)
        pairs = {rule: rule_pairs(gc, rule) for rule, _ in RULES}
        for rule, _ in RULES:
            c = Counter((b, str(g), str(p)) for b, _i, g, p in pairs[rule])
            for (b, g, p), n in sorted(c.items()):
                rows.append({"gold_set": s, "rule": rule, "benchmark": b, "expert_level": g, "rule_level": p, "count": n})
        prim = {}
        for rule in ("claude", "openai"):
            used = [(g, p) for _b, _i, g, p in pairs[rule] if g != "NA" and p != "NA"]
            prim[rule] = primary(gc["cfg"], [u[0] for u in used], [u[1] for u in used])
        best = max(("claude", "openai"), key=lambda r: prim[r])
        bp = {(b, i): (g, p) for b, i, g, p in pairs[best] if g != "NA" and p != "NA"}
        for rule, _ in RULES:
            if rule in ("claude", "openai"):
                continue
            rp = {(b, i): p for b, i, g, p in pairs[rule] if g != "NA" and p != "NA"}
            c = Counter((b, str(gv), str(bpv), str(rp[(b, i)])) for (b, i), (gv, bpv) in bp.items() if (b, i) in rp)
            for (b, g, bl, rl), n in sorted(c.items()):
                rows3.append({"gold_set": s, "rule": rule, "best_coder": "sonnet" if best == "claude" else "codex",
                              "benchmark": b, "expert_level": g, "best_level": bl, "rule_level": rl, "count": n})
    return rows, rows3


def cap_table(root: Path) -> list[dict]:
    rows = []
    for p in sorted((root / "audit" / "transport" / "prompts").glob("*/meta.json")):
        m = json.loads(p.read_text(encoding="utf-8"))
        capped = bool(m["n_dropped_chunks"] or m["tokens_before_cap"] > m["cap_tokens"])
        rows.append({"benchmark": m["bench"], "capped": "yes" if capped else "no", "tokens_before_cap": m["tokens_before_cap"],
                     "tokens_sent": m["tokens_sent"], "n_dropped_chunks": m["n_dropped_chunks"],
                     "over_cap": "yes" if m["over_cap"] else "no", "cap_tokens": m["cap_tokens"]})
    return rows


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows)} rows -> {path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=REPO.parents[1],
                    help="the authors' project root (holds audit/ and research/); default: two levels above the repo")
    a = ap.parse_args()
    rows, rows3 = gold_tables(a.root)
    write(TABLES / "gold_rule_contingency.csv", ["gold_set", "rule", "benchmark", "expert_level", "rule_level", "count"], rows)
    write(TABLES / "gold_rule_vs_best.csv",
          ["gold_set", "rule", "best_coder", "benchmark", "expert_level", "best_level", "rule_level", "count"], rows3)
    write(TABLES / "cap_flags.csv", ["benchmark", "capped", "tokens_before_cap", "tokens_sent", "n_dropped_chunks", "over_cap",
                                     "cap_tokens"], cap_table(a.root))


if __name__ == "__main__":
    main()
