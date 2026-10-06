"""PROVISIONAL: direction of Claude-coder (sonnet) disagreement with the published ABC and BetterBench gold scores.

Over-credit = coder score above the experts' (coder reported more than the experts credited); under-credit = below.
Coder score is the effective score (a 1+ without a verified quote counts as 0), as in the scorer's agreement.csv.
Cells with NA on either side are left out (counted). Frozen agentaudit.gold is imported read-only; no scorer file is
edited and nothing under audit/ is written. ABC gold has no licence: only per-item aggregates are written, never
per-cell gold values.
"""
from __future__ import annotations

from common import OUT, ROOT, write_csv
from agentaudit.gold import SETS, items_for_set, load_gold, load_predictions
from agentaudit.stats import wilson

AUDIT = ROOT / "audit"
RDIR = ROOT / "research"
PROV = OUT / "provisional"
TAG = "PROVISIONAL: Claude coder only, not resolved"
CODER = "sonnet"


def cells(set_name):
    gold = load_gold(set_name, RDIR)
    ids = set(items_for_set(set_name))
    preds, _ = load_predictions(AUDIT / f"gold_{'abc' if set_name == 'abc' else 'bb'}", set_name)
    out, na = [], 0
    for (b, i), v in sorted(preds[CODER].items()):
        if (b, i) not in gold or i not in ids:
            continue
        g, p = gold[(b, i)], v["effective"]
        if g == "NA" or p == "NA":
            na += 1
            continue
        out.append((b, i, g, p))
    return out, na


def summarise(cs):
    n = len(cs)
    ag = sum(g == p for _, _, g, p in cs)
    over = sum(p > g for _, _, g, p in cs)
    under = sum(p < g for _, _, g, p in cs)
    dis = over + under
    return {"n": n, "agree": ag, "agreement": ag / n if n else None,
            "n_disagree": dis, "n_over": over, "n_under": under,
            "share_over_of_disagree": over / dis if dis else None,
            "share_under_of_disagree": under / dis if dis else None}


rows, md = [], []
for set_name, label in (("abc", "ABC"), ("betterbench", "BetterBench")):
    cs, na = cells(set_name)
    tot = summarise(cs)
    lo, hi = wilson(tot["agree"], tot["n"])
    n_dis = tot["n_disagree"]
    wl = wilson(tot["n_over"], n_dis)
    rows.append({"set": label, "item": "ALL", **tot, "flag_agreement_lt_0.5": "", "status": TAG})
    per = []
    for it in sorted({i for _, i, _, _ in cs}):
        s = summarise([c for c in cs if c[1] == it])
        s["flag_agreement_lt_0.5"] = "FLAG" if s["agreement"] < 0.5 else ""
        per.append(s | {"item": it})
        rows.append({"set": label, **s | {"item": it}, "status": TAG})
    low = sorted(per, key=lambda r: (r["agreement"], r["item"]))[:3]
    flagged = [r["item"] for r in per if r["agreement"] < 0.5]
    md.append(f"## {label}\n\n- Cells compared: {tot['n']} ({len(per)} items; {na} NA cells left out). "
              f"Agreement {tot['agreement']:.3f} (Wilson 95% {lo:.3f}-{hi:.3f}).\n"
              f"- Disagreements: {n_dis}. Over-credit (coder higher) {tot['n_over']} ({tot['share_over_of_disagree']:.1%}); "
              f"under-credit (coder lower) {tot['n_under']} ({tot['share_under_of_disagree']:.1%}). "
              f"Over-credit share Wilson 95% {wl[0]:.1%}-{wl[1]:.1%}.\n"
              f"- Items with agreement < 0.5 ({len(flagged)}): {', '.join(flagged) if flagged else 'none'}.\n"
              f"- Three lowest: " + "; ".join(f"{r['item']} {r['agreement']:.2f} (n={r['n']}, over {r['n_over']}, under {r['n_under']})" for r in low) + ".\n")

# overall across both sets (note: scales differ, direction is within-scale)
allr = [r for r in rows if r["item"] == "ALL"]
n = sum(r["n"] for r in allr); ag = sum(r["agree"] for r in allr)
ov = sum(r["n_over"] for r in allr); un = sum(r["n_under"] for r in allr)
rows.append({"set": "ABC+BetterBench", "item": "ALL", "n": n, "agree": ag, "agreement": ag / n,
             "n_disagree": ov + un, "n_over": ov, "n_under": un, "share_over_of_disagree": ov / (ov + un),
             "share_under_of_disagree": un / (ov + un), "flag_agreement_lt_0.5": "", "status": TAG})
md.append(f"## Overall (both sets pooled; scales differ, direction is within scale)\n\n- {n} cells, agreement {ag/n:.3f}; "
          f"over-credit {ov} ({ov/(ov+un):.1%} of {ov+un} disagreements), under-credit {un} ({un/(ov+un):.1%}).\n")

fields = ["set", "item", "n", "agree", "agreement", "n_disagree", "n_over", "n_under", "share_over_of_disagree",
          "share_under_of_disagree", "flag_agreement_lt_0.5", "status"]
write_csv(PROV / "gold_error_direction.csv", rows, fields)
(PROV / "gold_error_direction.md").write_text(
    f"# Gold error direction (Claude coder vs experts)\n\n**{TAG}.** Coder = sonnet (claude-sonnet-5-5 via Claude Code "
    "subagent), effective score (a 1+ without a verified quote counts as 0). NA cells left out. Over-credit means the "
    "coder scored higher than the published expert score. ABC gold is unlicensed, so only per-item aggregates are "
    "written. ABC is binary (9 benchmarks); BetterBench is 0-3 (22 benchmarks, 20 items).\n\n" + "\n".join(md),
    encoding="utf-8")
print("\n".join(md))
